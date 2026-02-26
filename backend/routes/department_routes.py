
import psycopg2
from flask import Blueprint, request, jsonify
from ..auth import token_required
from ..database import DatabaseConnection
from ..permissions import can_manage_system
from ..utils import format_datetime_brasilia

department_bp = Blueprint('department', __name__)

@department_bp.route('/departamentos', methods=['GET'])
@token_required
def get_departments(current_user):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute("SELECT * FROM departamentos WHERE ativo = TRUE ORDER BY nome;")
            departamentos = db.cursor.fetchall()

            if not departamentos:
                return jsonify([]), 200

            result = []
            for dept in departamentos:
                try:
                    # Verificar se created_at é datetime ou string
                    created_at_value = None
                    if len(dept) > 5 and dept[5]:
                        created_at_value = format_datetime_brasilia(dept[5])

                    result.append({
                        'id': dept[0],
                        'nome': dept[1],
                        'descricao': dept[2] if len(dept) > 2 and dept[2] else '',
                        'cor': dept[3] if len(dept) > 3 and dept[3] else '#6B7280',
                        'ativo': dept[4] if len(dept) > 4 and dept[4] is not None else True,
                        'created_at': created_at_value
                    })
                except (IndexError, AttributeError) as e:
                    print(f"Erro ao processar departamento: {e}")
                    continue

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de departamentos: {e}")
        return jsonify([]), 200

@department_bp.route('/departamentos', methods=['POST'])
@token_required
def create_department(current_user):
    if not can_manage_system(current_user):
        return jsonify({'message': 'Sem permissão. Apenas Admin pode criar departamentos.'}), 403
    data = request.json

    if not data or 'nome' not in data:
        return jsonify({'message': 'Nome do departamento é obrigatório!'}), 400

    nome = data['nome'].strip()
    descricao = data.get('descricao', '')
    cor = data.get('cor', '#6B7280')

    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO departamentos (nome, descricao, cor)
                VALUES (%s, %s, %s) RETURNING id;
            ''', (nome, descricao, cor))
            department_id = db.cursor.fetchone()[0]
            return jsonify({
                'message': 'Departamento criado com sucesso!',
                'id': department_id
            }), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Departamento já existe!'}), 409
    except Exception as e:
        print(f"Erro ao criar departamento: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@department_bp.route('/departamentos/<int:departamento_id>/configuracoes', methods=['GET'])
@token_required
def get_department_config(current_user, departamento_id):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT configuracao_chave, configuracao_valor
                FROM departamento_configuracoes
                WHERE departamento_id = %s;
            ''', (departamento_id,))

            configs = db.cursor.fetchall()
            result = {config[0]: config[1] for config in configs}
            return jsonify(result)
    except Exception as e:
        print(f"Erro ao obter configurações do departamento: {e}")
        return jsonify({}), 200

@department_bp.route('/departamentos/<int:departamento_id>/configuracoes', methods=['POST'])
@token_required
def set_department_config(current_user, departamento_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Configurações não fornecidas!'}), 400

    try:
        with DatabaseConnection() as db:
            for chave, valor in data.items():
                db.cursor.execute('''
                    INSERT INTO departamento_configuracoes (departamento_id, configuracao_chave, configuracao_valor)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (departamento_id, configuracao_chave)
                    DO UPDATE SET configuracao_valor = EXCLUDED.configuracao_valor;
                ''', (departamento_id, chave, str(valor)))

            return jsonify({'message': 'Configurações atualizadas com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500
