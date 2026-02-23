import uuid
import psycopg2
import bcrypt
from flask import Blueprint, request, jsonify
from ..auth import token_required, agent_required
from ..database import DatabaseConnection
from ..utils import format_datetime_brasilia

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
                        'created_at': format_datetime_brasilia(usuario[5]) if usuario[5] else None,
                        'departamento': departamento_info
                    })

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de usuários: {e}")
        return jsonify([]), 200

@user_bp.route('/usuarios-monitorados', methods=['GET'])
def get_monitored_users():
    """
    Endpoint para listar ou buscar/criar usuários monitorados.
    
    - Se tiver parâmetro 'nome': Busca/cria usuário específico (SEM autenticação)
    - Se não tiver parâmetro 'nome': Lista todos os usuários (REQUER autenticação)
    """
    # Verificar se foi passado um nome para buscar/criar usuário específico
    nome_usuario = request.args.get('nome')

    if nome_usuario:
        # Verificação de existência/criação: NÃO requer autenticação
        # Buscar usuário específico ou criar se não existir
        try:
            with DatabaseConnection() as db:
                # Primeiro, tentar encontrar o usuário (independente do status ativo)
                db.cursor.execute('''
                    SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                           um.escala_trabalho_id, um.horario_inicio_trabalho, um.horario_fim_trabalho, um.dias_trabalho, um.monitoramento_ativo,
                           d.nome as departamento_nome, d.cor as departamento_cor,
                           et.nome as escala_nome, et.horario_inicio_trabalho as escala_inicio, et.horario_fim_trabalho as escala_fim, et.dias_trabalho as escala_dias
                    FROM usuarios_monitorados um
                    LEFT JOIN departamentos d ON um.departamento_id = d.id
                    LEFT JOIN escalas_trabalho et ON um.escala_trabalho_id = et.id
                    WHERE um.nome = %s;
                ''', (nome_usuario,))

                usuario_existente = db.cursor.fetchone()

                if usuario_existente:
                    # Se usuário existe mas está inativo, reativar
                    if not usuario_existente[4]:  # ativo está no índice 4
                        print(f"🔄 Reativando usuário monitorado: {nome_usuario}")
                        db.cursor.execute('''
                            UPDATE usuarios_monitorados
                            SET ativo = TRUE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        ''', (usuario_existente[0],))
                        # Atualizar o valor na tupla para refletir a mudança
                        usuario_existente = list(usuario_existente)
                        usuario_existente[4] = True
                        usuario_existente = tuple(usuario_existente)
                        print(f"✅ Usuário monitorado reativado: {nome_usuario} (ID: {usuario_existente[0]})")
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
                        'created_at': format_datetime_brasilia(usuario_existente[5]) if usuario_existente[5] else None,
                        'updated_at': format_datetime_brasilia(usuario_existente[6]) if len(usuario_existente) > 6 and usuario_existente[6] else None,
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

                    try:
                        db.cursor.execute('''
                            INSERT INTO usuarios_monitorados (nome, departamento_id, cargo, escala_trabalho_id, horario_inicio_trabalho, horario_fim_trabalho, dias_trabalho, ativo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                            RETURNING id, nome, departamento_id, cargo, ativo, created_at, updated_at;
                        ''', (nome_usuario, None, 'Usuário', escala_padrao_id, '08:00:00', '18:00:00', '1,2,3,4,5'))

                        novo_usuario = db.cursor.fetchone()
                        print(f"✅ Usuário monitorado criado: {nome_usuario} (ID: {novo_usuario[0]})")
                    except Exception as insert_error:
                        # Se der erro de duplicação (unique constraint), tentar buscar novamente
                        if 'unique' in str(insert_error).lower() or 'duplicate' in str(insert_error).lower():
                            print(f"⚠️ Usuário já existe (erro de duplicação), buscando novamente: {nome_usuario}")
                            db.cursor.execute('''
                                SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                                       um.escala_trabalho_id, um.horario_inicio_trabalho, um.horario_fim_trabalho, um.dias_trabalho, um.monitoramento_ativo,
                                       d.nome as departamento_nome, d.cor as departamento_cor,
                                       et.nome as escala_nome, et.horario_inicio_trabalho as escala_inicio, et.horario_fim_trabalho as escala_fim, et.dias_trabalho as escala_dias
                                FROM usuarios_monitorados um
                                LEFT JOIN departamentos d ON um.departamento_id = d.id
                                LEFT JOIN escalas_trabalho et ON um.escala_trabalho_id = et.id
                                WHERE um.nome = %s;
                            ''', (nome_usuario,))
                            novo_usuario_row = db.cursor.fetchone()
                            
                            if novo_usuario_row:
                                # Reativar se estiver inativo
                                if not novo_usuario_row[4]:
                                    db.cursor.execute('''
                                        UPDATE usuarios_monitorados
                                        SET ativo = TRUE, updated_at = CURRENT_TIMESTAMP
                                        WHERE id = %s
                                    ''', (novo_usuario_row[0],))
                                    print(f"✅ Usuário monitorado reativado: {nome_usuario} (ID: {novo_usuario_row[0]})")
                                
                                # Construir resultado completo usando os dados buscados
                                departamento_info = None
                                if len(novo_usuario_row) > 12 and novo_usuario_row[12]:
                                    departamento_info = {
                                        'nome': novo_usuario_row[12],
                                        'cor': novo_usuario_row[13] if len(novo_usuario_row) > 13 else None
                                    }
                                
                                escala_info = None
                                if len(novo_usuario_row) > 14 and novo_usuario_row[14]:
                                    escala_info = {
                                        'nome': novo_usuario_row[14],
                                        'horario_inicio_trabalho': str(novo_usuario_row[15]) if novo_usuario_row[15] else '08:00:00',
                                        'horario_fim_trabalho': str(novo_usuario_row[16]) if novo_usuario_row[16] else '18:00:00',
                                        'dias_trabalho': novo_usuario_row[17] if novo_usuario_row[17] else '1,2,3,4,5'
                                    }
                                
                                horario_inicio = str(novo_usuario_row[15]) if escala_info and novo_usuario_row[15] else (str(novo_usuario_row[8]) if len(novo_usuario_row) > 8 and novo_usuario_row[8] else '08:00:00')
                                horario_fim = str(novo_usuario_row[16]) if escala_info and novo_usuario_row[16] else (str(novo_usuario_row[9]) if len(novo_usuario_row) > 9 and novo_usuario_row[9] else '18:00:00')
                                dias_trabalho = novo_usuario_row[17] if escala_info and novo_usuario_row[17] else (novo_usuario_row[10] if len(novo_usuario_row) > 10 and novo_usuario_row[10] else '1,2,3,4,5')
                                
                                result = {
                                    'id': novo_usuario_row[0],
                                    'nome': novo_usuario_row[1],
                                    'departamento_id': novo_usuario_row[2] if len(novo_usuario_row) > 2 else None,
                                    'cargo': novo_usuario_row[3] if len(novo_usuario_row) > 3 else None,
                                    'ativo': True,  # Já foi reativado se estava inativo
                                    'created_at': format_datetime_brasilia(novo_usuario_row[5]) if novo_usuario_row[5] else None,
                                    'updated_at': format_datetime_brasilia(novo_usuario_row[6]) if len(novo_usuario_row) > 6 and novo_usuario_row[6] else None,
                                    'escala_trabalho_id': novo_usuario_row[7] if len(novo_usuario_row) > 7 else None,
                                    'horario_inicio_trabalho': horario_inicio,
                                    'horario_fim_trabalho': horario_fim,
                                    'dias_trabalho': dias_trabalho,
                                    'monitoramento_ativo': novo_usuario_row[11] if len(novo_usuario_row) > 11 and novo_usuario_row[11] is not None else True,
                                    'departamento': departamento_info,
                                    'escala': escala_info,
                                    'created': False  # Não foi criado agora, apenas encontrado/reativado
                                }
                                print(f"✅ Usuário monitorado encontrado após erro de duplicação: {nome_usuario} (ID: {novo_usuario_row[0]})")
                                return jsonify(result)
                            else:
                                # Se ainda não encontrou, relançar o erro original
                                raise insert_error
                        else:
                            # Se for outro erro, relançar
                            raise insert_error

                    # Se chegou aqui, novo_usuario foi criado com sucesso
                    result = {
                        'id': novo_usuario[0],
                        'nome': novo_usuario[1],
                        'departamento_id': novo_usuario[2] if len(novo_usuario) > 2 else None,
                        'cargo': novo_usuario[3] if len(novo_usuario) > 3 else None,
                        'ativo': novo_usuario[4] if len(novo_usuario) > 4 else True,
                        'created_at': format_datetime_brasilia(novo_usuario[5]) if novo_usuario[5] else None,
                        'updated_at': format_datetime_brasilia(novo_usuario[6]) if len(novo_usuario) > 6 and novo_usuario[6] else None,
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
            import traceback
            traceback.print_exc()
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
                'error': f'Erro ao processar usuário: {str(e)}'
            }), 200

    else:
        # Listar todos os usuários monitorados: REQUER autenticação
        # Verificar autenticação manualmente
        token = request.headers.get('Authorization')
        user_name = request.headers.get('X-User-Name')
        
        # Tentar autenticação JWT primeiro
        current_user = None
        if token:
            try:
                from ..auth import verify_jwt_token
                if token.startswith('Bearer '):
                    token = token.split(' ')[1]
                user_id = verify_jwt_token(token)
                if user_id:
                    with DatabaseConnection() as db:
                        db.cursor.execute('''
                            SELECT id, nome, email, ativo, departamento_id
                            FROM usuarios
                            WHERE id = %s
                        ''', (user_id,))
                        user = db.cursor.fetchone()
                        if user and user[3]:  # Se existe e está ativo
                            current_user = user
            except Exception as e:
                print(f"⚠️ Erro ao verificar token JWT: {e}")
        
        # Se não tem token válido, tentar pelo nome do usuário (modo agente)
        if not current_user and user_name:
            try:
                with DatabaseConnection() as db:
                    db.cursor.execute('''
                        SELECT id, nome, cargo, departamento_id, ativo
                        FROM usuarios_monitorados
                        WHERE nome = %s
                    ''', (user_name,))
                    usuario_monitorado = db.cursor.fetchone()
                    if usuario_monitorado:
                        current_user = (
                            usuario_monitorado[0],  # id
                            usuario_monitorado[1],  # nome
                            None,  # email
                            usuario_monitorado[4],  # ativo
                            usuario_monitorado[3]   # departamento_id
                        )
            except Exception as e:
                print(f"⚠️ Erro ao buscar usuário monitorado: {e}")
        
        # Se não tem autenticação, retornar erro
        if not current_user:
            return jsonify({'message': 'Autenticação necessária para listar todos os usuários monitorados!'}), 401
        
        # Listar todos os usuários monitorados
        try:
            with DatabaseConnection() as db:
                db.cursor.execute('''
                    SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                           um.horario_inicio_trabalho, um.horario_fim_trabalho, um.dias_trabalho, um.monitoramento_ativo,
                           um.valor_contrato,
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
                            # Índices: 0=id, 1=nome, 2=departamento_id, 3=cargo, 4=ativo, 5=created_at, 6=updated_at,
                            # 7=horario_inicio, 8=horario_fim, 9=dias_trabalho, 10=monitoramento_ativo, 11=valor_contrato, 12=dept_nome, 13=dept_cor
                            departamento_info = None
                            if len(usuario) > 12 and usuario[12]:
                                departamento_info = {
                                    'nome': usuario[12],
                                    'cor': usuario[13] if len(usuario) > 13 else None
                                }
                            valor_contrato = float(usuario[11]) if len(usuario) > 11 and usuario[11] is not None else None
                            # Pendências: dados cadastrais (cargo), setor (departamento), valor de contrato (custo de produtividade)
                            pendencias = []
                            if not (usuario[3] and str(usuario[3]).strip()):
                                pendencias.append('dados_cadastrais')
                            if usuario[2] is None:
                                pendencias.append('setor')
                            if valor_contrato is None or valor_contrato <= 0:
                                pendencias.append('valor_contrato')

                            result.append({
                                'id': usuario[0],
                                'nome': usuario[1],
                                'departamento_id': usuario[2] if len(usuario) > 2 else None,
                                'cargo': usuario[3] if len(usuario) > 3 else None,
                                'ativo': usuario[4] if len(usuario) > 4 else True,
                                'created_at': format_datetime_brasilia(usuario[5]) if usuario[5] else None,
                                'updated_at': format_datetime_brasilia(usuario[6]) if len(usuario) > 6 and usuario[6] else None,
                                'horario_inicio_trabalho': str(usuario[7]) if len(usuario) > 7 and usuario[7] else '09:00:00',
                                'horario_fim_trabalho': str(usuario[8]) if len(usuario) > 8 and usuario[8] else '18:00:00',
                                'dias_trabalho': usuario[9] if len(usuario) > 9 and usuario[9] else '1,2,3,4,5',
                                'monitoramento_ativo': usuario[10] if len(usuario) > 10 and usuario[10] is not None else True,
                                'valor_contrato': valor_contrato,
                                'departamento': departamento_info,
                                'pendencias': pendencias
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
    valor_contrato = data.get('valor_contrato')
    if valor_contrato is not None and valor_contrato != '':
        try:
            valor_contrato = float(valor_contrato)
        except (ValueError, TypeError):
            valor_contrato = None
    else:
        valor_contrato = None

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
                INSERT INTO usuarios_monitorados (nome, departamento_id, cargo, escala_trabalho_id, horario_inicio_trabalho, horario_fim_trabalho, dias_trabalho, valor_contrato)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, nome, departamento_id, cargo, ativo, created_at, updated_at;
            ''', (nome, dept_id, cargo, escala_padrao_id, '08:00:00', '18:00:00', '1,2,3,4,5', valor_contrato))

            usuario = db.cursor.fetchone()
            return jsonify({
                'message': 'Usuário monitorado criado com sucesso!',
                'id': usuario[0],
                'nome': usuario[1],
                'cargo': usuario[2],
                'departamento_id': usuario[3],
                'ativo': usuario[4],
                'created_at': format_datetime_brasilia(usuario[5]) if usuario[5] else None,
                'updated_at': format_datetime_brasilia(usuario[6]) if usuario[6] else None
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
            if 'valor_contrato' in data:
                vc = data.get('valor_contrato')
                vc = float(vc) if vc is not None and vc != '' else None
                update_fields.append('valor_contrato = %s')
                update_values.append(vc)

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

# ========================================
# CRUD COMPLETO PARA USUÁRIOS DO SISTEMA
# ========================================

@user_bp.route('/usuarios', methods=['POST'])
@token_required
def create_system_user(current_user):
    """Criar novo usuário do sistema"""
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    # Validações obrigatórias
    required_fields = ['nome', 'senha']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({'message': f'Campo {field} é obrigatório!'}), 400

    nome = data['nome'].strip()
    senha = data['senha'].strip()
    email = data.get('email', '').strip() or None
    departamento_id = data.get('departamento_id')

    # Validações
    if len(nome) < 3:
        return jsonify({'message': 'Nome deve ter pelo menos 3 caracteres!'}), 400
    
    if len(senha) < 6:
        return jsonify({'message': 'Senha deve ter pelo menos 6 caracteres!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se usuário já existe
            db.cursor.execute('SELECT id FROM usuarios WHERE nome = %s;', (nome,))
            if db.cursor.fetchone():
                return jsonify({'message': 'Usuário já existe!'}), 409

            # Verificar departamento se fornecido
            if departamento_id:
                try:
                    dept_id = int(departamento_id)
                    db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (dept_id,))
                    if not db.cursor.fetchone():
                        return jsonify({'message': 'Departamento não encontrado!'}), 400
                except ValueError:
                    return jsonify({'message': 'ID de departamento inválido!'}), 400
            else:
                dept_id = None

            # Hash da senha
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Inserir usuário
            db.cursor.execute('''
                INSERT INTO usuarios (nome, senha, email, departamento_id, ativo)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id, nome, email, departamento_id, ativo, created_at;
            ''', (nome, senha_hash, email, dept_id))

            usuario = db.cursor.fetchone()

            # Buscar dados do departamento se existir
            departamento_info = None
            if dept_id:
                db.cursor.execute('SELECT nome, cor FROM departamentos WHERE id = %s;', (dept_id,))
                dept_data = db.cursor.fetchone()
                if dept_data:
                    departamento_info = {'nome': dept_data[0], 'cor': dept_data[1]}

            return jsonify({
                'message': 'Usuário criado com sucesso!',
                'usuario': {
                    'usuario_id': str(usuario[0]),
                    'usuario': usuario[1],
                    'email': usuario[2],
                    'departamento_id': usuario[3],
                    'ativo': usuario[4],
                    'created_at': format_datetime_brasilia(usuario[5]),
                    'departamento': departamento_info
                }
            }), 201

    except psycopg2.IntegrityError as e:
        if 'unique' in str(e).lower():
            return jsonify({'message': 'Usuário já existe!'}), 409
        return jsonify({'message': 'Erro de integridade dos dados!'}), 400
    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios/<uuid:usuario_id>', methods=['PUT'])
@token_required
def update_system_user(current_user, usuario_id):
    """Atualizar usuário do sistema"""
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário existe
            db.cursor.execute('SELECT id, nome FROM usuarios WHERE id = %s AND ativo = TRUE;', (usuario_id,))
            existing_user = db.cursor.fetchone()
            if not existing_user:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            update_fields = []
            update_values = []

            # Nome
            if 'nome' in data:
                nome = data['nome'].strip()
                if len(nome) < 3:
                    return jsonify({'message': 'Nome deve ter pelo menos 3 caracteres!'}), 400
                
                # Verificar se nome já existe (exceto o próprio usuário)
                db.cursor.execute('SELECT id FROM usuarios WHERE nome = %s AND id != %s;', (nome, usuario_id))
                if db.cursor.fetchone():
                    return jsonify({'message': 'Nome de usuário já existe!'}), 409
                
                update_fields.append('nome = %s')
                update_values.append(nome)

            # Email
            if 'email' in data:
                email = data['email'].strip() or None
                update_fields.append('email = %s')
                update_values.append(email)

            # Senha
            if 'senha' in data and data['senha'].strip():
                senha = data['senha'].strip()
                if len(senha) < 6:
                    return jsonify({'message': 'Senha deve ter pelo menos 6 caracteres!'}), 400
                
                senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                update_fields.append('senha = %s')
                update_values.append(senha_hash)

            # Departamento
            if 'departamento_id' in data:
                dept_id = data.get('departamento_id')
                if dept_id:
                    try:
                        dept_id = int(dept_id)
                        db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (dept_id,))
                        if not db.cursor.fetchone():
                            return jsonify({'message': 'Departamento não encontrado!'}), 400
                    except ValueError:
                        return jsonify({'message': 'ID de departamento inválido!'}), 400
                else:
                    dept_id = None
                
                update_fields.append('departamento_id = %s')
                update_values.append(dept_id)

            # Status ativo
            if 'ativo' in data:
                update_fields.append('ativo = %s')
                update_values.append(bool(data['ativo']))

            if not update_fields:
                return jsonify({'message': 'Nenhum campo válido para atualizar!'}), 400

            # Adicionar timestamp de atualização
            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            update_values.append(usuario_id)

            # Executar update
            db.cursor.execute(f'''
                UPDATE usuarios SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, nome, email, departamento_id, ativo, updated_at;
            ''', update_values)

            updated_user = db.cursor.fetchone()

            # Buscar dados do departamento se existir
            departamento_info = None
            if updated_user[3]:
                db.cursor.execute('SELECT nome, cor FROM departamentos WHERE id = %s;', (updated_user[3],))
                dept_data = db.cursor.fetchone()
                if dept_data:
                    departamento_info = {'nome': dept_data[0], 'cor': dept_data[1]}

            return jsonify({
                'message': 'Usuário atualizado com sucesso!',
                'usuario': {
                    'usuario_id': str(updated_user[0]),
                    'usuario': updated_user[1],
                    'email': updated_user[2],
                    'departamento_id': updated_user[3],
                    'ativo': updated_user[4],
                    'updated_at': format_datetime_brasilia(updated_user[5]),
                    'departamento': departamento_info
                }
            }), 200

    except psycopg2.IntegrityError as e:
        if 'unique' in str(e).lower():
            return jsonify({'message': 'Nome de usuário já existe!'}), 409
        return jsonify({'message': 'Erro de integridade dos dados!'}), 400
    except Exception as e:
        print(f"Erro ao atualizar usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios/<uuid:usuario_id>', methods=['DELETE'])
@token_required
def delete_system_user(current_user, usuario_id):
    """Deletar usuário do sistema (soft delete)"""
    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário existe
            db.cursor.execute('SELECT id, nome FROM usuarios WHERE id = %s AND ativo = TRUE;', (usuario_id,))
            existing_user = db.cursor.fetchone()
            if not existing_user:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            # Verificar se não é o próprio usuário logado
            if str(current_user['id']) == str(usuario_id):
                return jsonify({'message': 'Você não pode deletar sua própria conta!'}), 400

            # Soft delete - marcar como inativo
            db.cursor.execute('''
                UPDATE usuarios 
                SET ativo = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (usuario_id,))

            return jsonify({
                'message': f'Usuário {existing_user[1]} foi desativado com sucesso!'
            }), 200

    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios/<uuid:usuario_id>/reativar', methods=['PATCH'])
@token_required
def reactivate_system_user(current_user, usuario_id):
    """Reativar usuário do sistema"""
    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário existe (mesmo inativo)
            db.cursor.execute('SELECT id, nome, ativo FROM usuarios WHERE id = %s;', (usuario_id,))
            existing_user = db.cursor.fetchone()
            if not existing_user:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            if existing_user[2]:  # já está ativo
                return jsonify({'message': 'Usuário já está ativo!'}), 400

            # Reativar usuário
            db.cursor.execute('''
                UPDATE usuarios 
                SET ativo = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (usuario_id,))

            return jsonify({
                'message': f'Usuário {existing_user[1]} foi reativado com sucesso!'
            }), 200

    except Exception as e:
        print(f"Erro ao reativar usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios/<uuid:usuario_id>/reset-senha', methods=['PATCH'])
@token_required
def reset_user_password(current_user, usuario_id):
    """Resetar senha do usuário"""
    data = request.json

    if not data or 'nova_senha' not in data:
        return jsonify({'message': 'Nova senha é obrigatória!'}), 400

    nova_senha = data['nova_senha'].strip()
    if len(nova_senha) < 6:
        return jsonify({'message': 'Senha deve ter pelo menos 6 caracteres!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário existe
            db.cursor.execute('SELECT id, nome FROM usuarios WHERE id = %s AND ativo = TRUE;', (usuario_id,))
            existing_user = db.cursor.fetchone()
            if not existing_user:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            # Hash da nova senha
            senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Atualizar senha
            db.cursor.execute('''
                UPDATE usuarios 
                SET senha = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (senha_hash, usuario_id))

            return jsonify({
                'message': f'Senha do usuário {existing_user[1]} foi resetada com sucesso!'
            }), 200

    except Exception as e:
        print(f"Erro ao resetar senha: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@user_bp.route('/usuarios/inativos', methods=['GET'])
@token_required
def get_inactive_users(current_user):
    """Listar usuários inativos"""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT u.id, u.nome, u.email, u.departamento_id, u.ativo, u.created_at, u.updated_at,
                       d.nome as departamento_nome, d.cor as departamento_cor
                FROM usuarios u
                LEFT JOIN departamentos d ON u.departamento_id = d.id
                WHERE u.ativo = FALSE
                ORDER BY u.updated_at DESC;
            ''')
            usuarios = db.cursor.fetchall()

            result = []
            if usuarios:
                for usuario in usuarios:
                    departamento_info = None
                    if len(usuario) > 7 and usuario[7]:
                        departamento_info = {
                            'nome': usuario[7],
                            'cor': usuario[8] if len(usuario) > 8 else None
                        }

                    result.append({
                        'usuario_id': str(usuario[0]),
                        'usuario': usuario[1],
                        'email': usuario[2],
                        'departamento_id': usuario[3],
                        'ativo': usuario[4],
                        'created_at': format_datetime_brasilia(usuario[5]) if usuario[5] else None,
                        'updated_at': format_datetime_brasilia(usuario[6]) if usuario[6] else None,
                        'departamento': departamento_info
                    })

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de usuários inativos: {e}")
        return jsonify([]), 200

@user_bp.route('/usuarios/<uuid:usuario_id>', methods=['GET'])
@token_required
def get_system_user(current_user, usuario_id):
    """Obter detalhes de um usuário específico"""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT u.id, u.nome, u.email, u.departamento_id, u.ativo, u.created_at, u.updated_at, u.ultimo_login,
                       d.nome as departamento_nome, d.cor as departamento_cor
                FROM usuarios u
                LEFT JOIN departamentos d ON u.departamento_id = d.id
                WHERE u.id = %s;
            ''', (usuario_id,))
            usuario = db.cursor.fetchone()

            if not usuario:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            departamento_info = None
            if len(usuario) > 8 and usuario[8]:
                departamento_info = {
                    'nome': usuario[8],
                    'cor': usuario[9] if len(usuario) > 9 else None
                }

            result = {
                'usuario_id': str(usuario[0]),
                'usuario': usuario[1],
                'email': usuario[2],
                'departamento_id': usuario[3],
                'ativo': usuario[4],
                'created_at': format_datetime_brasilia(usuario[5]) if usuario[5] else None,
                'updated_at': format_datetime_brasilia(usuario[6]) if usuario[6] else None,
                'ultimo_login': format_datetime_brasilia(usuario[7]) if usuario[7] else None,
                'departamento': departamento_info
            }

            return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500