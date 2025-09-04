import uuid
import psycopg2
from flask import Blueprint, request, jsonify
from ..auth import token_required
from ..database import DatabaseConnection

user_bp = Blueprint('user', __name__)

@user_bp.route('/usuarios', methods=['GET'])
@token_required
def get_users(current_user):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT u.id, u.nome, u.email, u.departamento_id, u.ativo, u.created_at, d.nome as departamento_nome, d.cor as departamento_cor
                FROM usuarios u
                LEFT JOIN departamentos d ON u.departamento_id = d.id
                WHERE u.ativo = TRUE
                ORDER BY u.nome;
            ''')
            usuarios = db.cursor.fetchall()

            result = []
            if usuarios:
                for usuario in usuarios:
                    # Verificar se temos dados suficientes do departamento
                    departamento_info = None
                    if len(usuario) > 6 and usuario[6]:  # departamento_nome existe
                        departamento_info = {
                            'nome': usuario[6],
                            'cor': usuario[7] if len(usuario) > 7 else None
                        }

                    result.append({
                        'usuario_id': str(usuario[0]) if usuario[0] else None,
                        'usuario': usuario[1],
                        'email': usuario[2],
                        'departamento_id': usuario[3],
                        'ativo': usuario[4],
                        'created_at': usuario[5].isoformat() if usuario[5] else None,
                        'departamento': departamento_info
                    })

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de usuários: {e}")
        return jsonify([]), 200

@user_bp.route('/usuarios-monitorados', methods=['GET'])
@token_required
def get_monitored_users(current_user):
    # Verificar se foi passado um nome para buscar/criar usuário específico
    nome_usuario = request.args.get('nome')

    if nome_usuario:
        # Buscar usuário específico ou criar se não existir
        try:
            with DatabaseConnection() as db:
                # Primeiro, tentar encontrar o usuário
                db.cursor.execute('''
                    SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                           um.escala_trabalho_id, um.horario_inicio_trabalho, um.horario_fim_trabalho, um.dias_trabalho, um.monitoramento_ativo,
                           d.nome as departamento_nome, d.cor as departamento_cor,
                           et.nome as escala_nome, et.horario_inicio_trabalho as escala_inicio, et.horario_fim_trabalho as escala_fim, et.dias_trabalho as escala_dias
                    FROM usuarios_monitorados um
                    LEFT JOIN departamentos d ON um.departamento_id = d.id
                    LEFT JOIN escalas_trabalho et ON um.escala_trabalho_id = et.id
                    WHERE um.nome = %s AND um.ativo = TRUE;
                ''', (nome_usuario,))

                usuario_existente = db.cursor.fetchone()

                if usuario_existente:
                    # Usuário existe, retornar seus dados
                    departamento_info = None
                    if len(usuario_existente) > 12 and usuario_existente[12]:
                        departamento_info = {
                            'nome': usuario_existente[12],
                            'cor': usuario_existente[13] if len(usuario_existente) > 13 else None
                        }

                    # Informações da escala (se tiver uma escala atribuída)
                    escala_info = None
                    if len(usuario_existente) > 14 and usuario_existente[14]:  # tem escala
                        escala_info = {
                            'nome': usuario_existente[14],
                            'horario_inicio_trabalho': str(usuario_existente[15]) if usuario_existente[15] else '08:00:00',
                            'horario_fim_trabalho': str(usuario_existente[16]) if usuario_existente[16] else '18:00:00',
                            'dias_trabalho': usuario_existente[17] if usuario_existente[17] else '1,2,3,4,5'
                        }

                    # Se tem escala, usar horários da escala; senão usar horários próprios
                    horario_inicio = str(usuario_existente[15]) if escala_info and usuario_existente[15] else (str(usuario_existente[8]) if len(usuario_existente) > 8 and usuario_existente[8] else '08:00:00')
                    horario_fim = str(usuario_existente[16]) if escala_info and usuario_existente[16] else (str(usuario_existente[9]) if len(usuario_existente) > 9 and usuario_existente[9] else '18:00:00')
                    dias_trabalho = usuario_existente[17] if escala_info and usuario_existente[17] else (usuario_existente[10] if len(usuario_existente) > 10 and usuario_existente[10] else '1,2,3,4,5')

                    result = {
                        'id': usuario_existente[0],
                        'nome': usuario_existente[1],
                        'departamento_id': usuario_existente[2] if len(usuario_existente) > 2 else None,
                        'cargo': usuario_existente[3] if len(usuario_existente) > 3 else None,
                        'ativo': usuario_existente[4] if len(usuario_existente) > 4 else True,
                        'created_at': usuario_existente[5].isoformat() if usuario_existente[5] else None,
                        'updated_at': usuario_existente[6].isoformat() if len(usuario_existente) > 6 and usuario_existente[6] else None,
                        'escala_trabalho_id': usuario_existente[7] if len(usuario_existente) > 7 else None,
                        'horario_inicio_trabalho': horario_inicio,
                        'horario_fim_trabalho': horario_fim,
                        'dias_trabalho': dias_trabalho,
                        'monitoramento_ativo': usuario_existente[11] if len(usuario_existente) > 11 and usuario_existente[11] is not None else True,
                        'departamento': departamento_info,
                        'escala': escala_info,
                        'created': False
                    }
                    print(f"✅ Usuário monitorado encontrado: {nome_usuario} (ID: {usuario_existente[0]})")
                    return jsonify(result)
                else:
                    # Usuário não existe, criar novo automaticamente
                    print(f"🔧 Criando novo usuário monitorado: {nome_usuario}")
                    # Buscar escala padrão
                    db.cursor.execute("SELECT id FROM escalas_trabalho WHERE nome = 'Comercial Padrão' AND ativo = TRUE LIMIT 1;")
                    escala_padrao = db.cursor.fetchone()
                    escala_padrao_id = escala_padrao[0] if escala_padrao else None

                    db.cursor.execute('''
                        INSERT INTO usuarios_monitorados (nome, departamento_id, cargo, escala_trabalho_id, horario_inicio_trabalho, horario_fim_trabalho, dias_trabalho)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, nome, departamento_id, cargo, ativo, created_at, updated_at;
                    ''', (nome_usuario, None, 'Usuário', escala_padrao_id, '08:00:00', '18:00:00', '1,2,3,4,5'))

                    novo_usuario = db.cursor.fetchone()
                    print(f"✅ Usuário monitorado criado: {nome_usuario} (ID: {novo_usuario[0]})")

                    result = {
                        'id': novo_usuario[0],
                        'nome': novo_usuario[1],
                        'departamento_id': novo_usuario[2] if len(novo_usuario) > 2 else None,
                        'cargo': novo_usuario[3] if len(novo_usuario) > 3 else None,
                        'ativo': novo_usuario[4] if len(novo_usuario) > 4 else True,
                        'created_at': novo_usuario[5].isoformat() if novo_usuario[5] else None,
                        'updated_at': novo_usuario[6].isoformat() if len(novo_usuario) > 6 and novo_usuario[6] else None,
                        'escala_trabalho_id': None,
                        'horario_inicio_trabalho': '08:00:00',
                        'horario_fim_trabalho': '18:00:00',
                        'dias_trabalho': '1,2,3,4,5',
                        'monitoramento_ativo': True,
                        'departamento': None,
                        'escala': None,
                        'created': True
                    }
                    return jsonify(result)

        except Exception as e:
            print(f"❌ Erro ao buscar/criar usuário monitorado {nome_usuario}: {e}")
            # Retornar um usuário básico para manter o agente funcionando
            return jsonify({
                'id': 0,
                'nome': nome_usuario,
                'departamento_id': None,
                'cargo': 'Usuário',
                'ativo': True,
                'created_at': None,
                'updated_at': None,
                'departamento': None,
                'created': False,
                'error': 'Erro ao processar usuário, usando fallback'
            }), 200

    else:
        # Listar todos os usuários monitorados (comportamento original)
        try:
            with DatabaseConnection() as db:
                db.cursor.execute('''
                    SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                           um.horario_inicio_trabalho, um.horario_fim_trabalho, um.dias_trabalho, um.monitoramento_ativo,
                           d.nome as departamento_nome, d.cor as departamento_cor
                    FROM usuarios_monitorados um
                    LEFT JOIN departamentos d ON um.departamento_id = d.id
                    WHERE um.ativo = TRUE
                    ORDER BY um.nome;
                ''')
                usuarios_monitorados = db.cursor.fetchall()

                result = []
                if usuarios_monitorados:
                    for usuario in usuarios_monitorados:
                        try:
                            # Verificar se campos do departamento existem
                            departamento_info = None
                            if len(usuario) > 11 and usuario[11]:
                                departamento_info = {
                                    'nome': usuario[11],
                                    'cor': usuario[12] if len(usuario) > 12 else None
                                }

                            result.append({
                                'id': usuario[0],
                                'nome': usuario[1],
                                'departamento_id': usuario[2] if len(usuario) > 2 else None,
                                'cargo': usuario[3] if len(usuario) > 3 else None,
                                'ativo': usuario[4] if len(usuario) > 4 else True,
                                'created_at': usuario[5].isoformat() if usuario[5] else None,
                                'updated_at': usuario[6].isoformat() if len(usuario) > 6 and usuario[6] else None,
                                'horario_inicio_trabalho': str(usuario[7]) if len(usuario) > 7 and usuario[7] else '09:00:00',
                                'horario_fim_trabalho': str(usuario[8]) if len(usuario) > 8 and usuario[8] else '18:00:00',
                                'dias_trabalho': usuario[9] if len(usuario) > 9 and usuario[9] else '1,2,3,4,5',
                                'monitoramento_ativo': usuario[10] if len(usuario) > 10 and usuario[10] is not None else True,
                                'departamento': departamento_info
                            })
                        except (IndexError, AttributeError) as e:
                            print(f"Erro ao processar usuário monitorado: {e}")
                            continue

                return jsonify(result)
        except Exception as e:
            print(f"Erro na consulta de usuários monitorados: {e}")
            return jsonify([]), 200

@user_bp.route('/usuarios-monitorados', methods=['POST'])
@token_required
def create_monitored_user(current_user):
    data = request.json

    if not data or 'nome' not in data:
        return jsonify({'message': 'Nome é obrigatório!'}), 400

    nome = data['nome'].strip()
    cargo = data.get('cargo', 'Usuário')
    departamento_id = data.get('departamento_id')

    try:
        with DatabaseConnection() as db:
            if departamento_id is not None:
                try:
                    dept_id = int(departamento_id)
                    # Verificar se o departamento existe e está ativo
                    db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (dept_id,))
                    if not db.cursor.fetchone():
                        return jsonify({'message': 'Departamento não encontrado ou inativo!'}), 400
                except ValueError:
                    return jsonify({'message': 'ID de departamento inválido!'}), 400
            else:
                dept_id = None

            # Buscar escala padrão
            db.cursor.execute("SELECT id FROM escalas_trabalho WHERE nome = 'Comercial Padrão' AND ativo = TRUE LIMIT 1;")
            escala_padrao = db.cursor.fetchone()
            escala_padrao_id = escala_padrao[0] if escala_padrao else None

            db.cursor.execute('''
                INSERT INTO usuarios_monitorados (nome, departamento_id, cargo, escala_trabalho_id, horario_inicio_trabalho, horario_fim_trabalho, dias_trabalho)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, nome, departamento_id, cargo, ativo, created_at, updated_at;
            ''', (nome, departamento_id, cargo, escala_padrao_id, '08:00:00', '18:00:00', '1,2,3,4,5'))

            usuario = db.cursor.fetchone()
            return jsonify({
                'message': 'Usuário monitorado criado com sucesso!',
                'id': usuario[0],
                'nome': usuario[1],
                'cargo': usuario[2],
                'departamento_id': usuario[3],
                'ativo': usuario[4],
                'created_at': usuario[5].isoformat() if usuario[5] else None,
                'updated_at': usuario[6].isoformat() if usuario[6] else None
            }), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Usuário monitorado já existe!'}), 409
    except Exception as e:
        print(f"Erro ao criar usuário monitorado: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios-monitorados/<int:user_id>', methods=['PUT'])
@token_required
def update_monitored_user(current_user, user_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário existe
            db.cursor.execute('SELECT id FROM usuarios_monitorados WHERE id = %s;', (user_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Usuário monitorado não encontrado!'}), 404

            update_fields = []
            update_values = []

            if 'nome' in data:
                update_fields.append('nome = %s')
                update_values.append(data['nome'])
            if 'cargo' in data:
                update_fields.append('cargo = %s')
                update_values.append(data['cargo'])
            if 'departamento_id' in data:
                dept_id = data.get('departamento_id')
                if dept_id is not None:
                    try:
                        dept_id = int(dept_id)
                        # Verificar se o departamento existe e está ativo
                        db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (dept_id,))
                        if not db.cursor.fetchone():
                            return jsonify({'message': 'Departamento não encontrado ou inativo!'}), 400
                    except ValueError:
                        return jsonify({'message': 'ID de departamento inválido!'}), 400
                else:
                    dept_id = None # Permitir definir departamento_id como NULL
                update_fields.append('departamento_id = %s')
                update_values.append(dept_id)
            if 'ativo' in data:
                update_fields.append('ativo = %s')
                update_values.append(data['ativo'])
            if 'escala_trabalho_id' in data:
                escala_id = data.get('escala_trabalho_id')
                if escala_id is not None:
                    try:
                        escala_id = int(escala_id)
                        # Verificar se a escala existe e está ativa
                        db.cursor.execute("SELECT id FROM escalas_trabalho WHERE id = %s AND ativo = TRUE;", (escala_id,))
                        if not db.cursor.fetchone():
                            return jsonify({'message': 'Escala não encontrada ou inativa!'}), 404
                    except ValueError:
                        return jsonify({'message': 'ID de escala inválido!'}), 400
                else:
                    escala_id = None  # Permitir definir escala como NULL
                update_fields.append('escala_trabalho_id = %s')
                update_values.append(escala_id)
            if 'horario_inicio_trabalho' in data:
                update_fields.append('horario_inicio_trabalho = %s')
                update_values.append(data['horario_inicio_trabalho'])
            if 'horario_fim_trabalho' in data:
                update_fields.append('horario_fim_trabalho = %s')
                update_values.append(data['horario_fim_trabalho'])
            if 'dias_trabalho' in data:
                update_fields.append('dias_trabalho = %s')
                update_values.append(data['dias_trabalho'])
            if 'monitoramento_ativo' in data:
                update_fields.append('monitoramento_ativo = %s')
                update_values.append(data['monitoramento_ativo'])

            if not update_fields:
                return jsonify({'message': 'Nenhum campo válido para atualizar!'}), 400

            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            update_values.append(user_id)

            db.cursor.execute(f'''
                UPDATE usuarios_monitorados SET {', '.join(update_fields)}
                WHERE id = %s;
            ''', update_values)

            return jsonify({'message': 'Usuário monitorado atualizado com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar usuário monitorado: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios/<uuid:usuario_id>/departamento', methods=['PATCH'])
@token_required
def update_user_department(current_user, usuario_id):
    data = request.json

    if not data or 'departamento_id' not in data:
        return jsonify({'message': 'ID do departamento é obrigatório!'}), 400

    departamento_id = data['departamento_id']

    try:
        with DatabaseConnection() as db:
            # Verificar se o departamento existe
            db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (departamento_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Departamento não encontrado!'}), 404

            db.cursor.execute('''
                UPDATE usuarios
                SET departamento_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (departamento_id, usuario_id))

            if db.cursor.rowcount == 0:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            return jsonify({'message': 'Departamento do usuário atualizado com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar departamento do usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500