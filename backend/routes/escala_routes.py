import psycopg2
from flask import Blueprint, request, jsonify
from ..auth import token_required
from ..database import DatabaseConnection

escala_bp = Blueprint('escala', __name__)

@escala_bp.route('/escalas', methods=['GET'])
@token_required
def get_escalas(current_user):
    """Lista todas as escalas de trabalho disponíveis"""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT id, nome, descricao, horario_inicio_trabalho, horario_fim_trabalho, 
                       dias_trabalho, ativo, created_at, updated_at
                FROM escalas_trabalho
                WHERE ativo = TRUE
                ORDER BY nome;
            ''')
            escalas = db.cursor.fetchall()

            result = []
            if escalas:
                for escala in escalas:
                    result.append({
                        'id': escala[0],
                        'nome': escala[1],
                        'descricao': escala[2],
                        'horario_inicio_trabalho': str(escala[3]) if escala[3] else '08:00:00',
                        'horario_fim_trabalho': str(escala[4]) if escala[4] else '18:00:00',
                        'dias_trabalho': escala[5] if escala[5] else '1,2,3,4,5',
                        'ativo': escala[6] if escala[6] is not None else True,
                        'created_at': escala[7].isoformat() if escala[7] else None,
                        'updated_at': escala[8].isoformat() if escala[8] else None
                    })

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de escalas: {e}")
        return jsonify([]), 200

@escala_bp.route('/escalas', methods=['POST'])
@token_required
def create_escala(current_user):
    """Cria uma nova escala de trabalho"""
    data = request.json

    if not data or 'nome' not in data:
        return jsonify({'message': 'Nome da escala é obrigatório!'}), 400

    nome = data['nome'].strip()
    descricao = data.get('descricao', '')
    horario_inicio = data.get('horario_inicio_trabalho', '08:00:00')
    horario_fim = data.get('horario_fim_trabalho', '18:00:00')
    dias_trabalho = data.get('dias_trabalho', '1,2,3,4,5')

    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO escalas_trabalho (nome, descricao, horario_inicio_trabalho, horario_fim_trabalho, dias_trabalho)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nome, descricao, horario_inicio_trabalho, horario_fim_trabalho, dias_trabalho, ativo, created_at, updated_at;
            ''', (nome, descricao, horario_inicio, horario_fim, dias_trabalho))

            escala = db.cursor.fetchone()
            return jsonify({
                'message': 'Escala de trabalho criada com sucesso!',
                'id': escala[0],
                'nome': escala[1],
                'descricao': escala[2],
                'horario_inicio_trabalho': str(escala[3]) if escala[3] else '08:00:00',
                'horario_fim_trabalho': str(escala[4]) if escala[4] else '18:00:00',
                'dias_trabalho': escala[5] if escala[5] else '1,2,3,4,5',
                'ativo': escala[6] if escala[6] is not None else True,
                'created_at': escala[7].isoformat() if escala[7] else None,
                'updated_at': escala[8].isoformat() if escala[8] else None
            }), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Escala com este nome já existe!'}), 409
    except Exception as e:
        print(f"Erro ao criar escala: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@escala_bp.route('/escalas/<int:escala_id>', methods=['PUT'])
@token_required
def update_escala(current_user, escala_id):
    """Atualiza uma escala de trabalho existente"""
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se a escala existe
            db.cursor.execute('SELECT id FROM escalas_trabalho WHERE id = %s;', (escala_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Escala não encontrada!'}), 404

            update_fields = []
            update_values = []

            if 'nome' in data:
                update_fields.append('nome = %s')
                update_values.append(data['nome'])
            if 'descricao' in data:
                update_fields.append('descricao = %s')
                update_values.append(data['descricao'])
            if 'horario_inicio_trabalho' in data:
                update_fields.append('horario_inicio_trabalho = %s')
                update_values.append(data['horario_inicio_trabalho'])
            if 'horario_fim_trabalho' in data:
                update_fields.append('horario_fim_trabalho = %s')
                update_values.append(data['horario_fim_trabalho'])
            if 'dias_trabalho' in data:
                update_fields.append('dias_trabalho = %s')
                update_values.append(data['dias_trabalho'])
            if 'ativo' in data:
                update_fields.append('ativo = %s')
                update_values.append(data['ativo'])

            if not update_fields:
                return jsonify({'message': 'Nenhum campo válido para atualizar!'}), 400

            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            update_values.append(escala_id)

            db.cursor.execute(f'''
                UPDATE escalas_trabalho SET {', '.join(update_fields)}
                WHERE id = %s;
            ''', update_values)

            return jsonify({'message': 'Escala atualizada com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar escala: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@escala_bp.route('/escalas/<int:escala_id>', methods=['DELETE'])
@token_required
def delete_escala(current_user, escala_id):
    """Desativa uma escala de trabalho"""
    try:
        with DatabaseConnection() as db:
            # Verificar se a escala existe
            db.cursor.execute('SELECT id FROM escalas_trabalho WHERE id = %s;', (escala_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Escala não encontrada!'}), 404

            # Desativar escala ao invés de deletar
            db.cursor.execute('''
                UPDATE escalas_trabalho 
                SET ativo = FALSE, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s;
            ''', (escala_id,))

            return jsonify({'message': 'Escala desativada com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao desativar escala: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500