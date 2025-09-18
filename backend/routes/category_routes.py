
import psycopg2
from flask import Blueprint, request, jsonify
from ..auth import token_required
from ..database import DatabaseConnection
from ..utils import format_datetime_brasilia

category_bp = Blueprint('category', __name__)

@category_bp.route('/categorias', methods=['POST'])
@token_required
def create_category(current_user):
    data = request.json

    if not data or 'nome' not in data or 'tipo_produtividade' not in data:
        return jsonify({'message': 'Nome e tipo de produtividade são obrigatórios!'}), 400

    nome = data['nome'].strip()
    tipo = data['tipo_produtividade']
    departamento_id = data.get('departamento_id')
    cor = data.get('cor', '#6B7280')
    descricao = data.get('descricao', '')
    is_global = data.get('is_global', False)

    if tipo not in ['productive', 'nonproductive', 'neutral']:
        return jsonify({'message': 'Tipo de produtividade inválido!'}), 400

    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO categorias_app (nome, departamento_id, tipo_produtividade, cor, descricao, is_global)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            ''', (nome, departamento_id, tipo, cor, descricao, is_global))
            category_id = db.cursor.fetchone()[0]
            return jsonify({
                'message': 'Categoria criada com sucesso!',
                'id': category_id
            }), 201
    except psycopg2.IntegrityError:
        return jsonify({'message': 'Categoria já existe para este departamento!'}), 409
    except Exception as e:
        print(f"Erro ao criar categoria: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@category_bp.route('/categorias', methods=['GET'])
@token_required
def get_categories(current_user):
    departamento_id = request.args.get('departamento_id')

    try:
        with DatabaseConnection() as db:
            if departamento_id:
                # Categorias específicas do departamento + globais
                db.cursor.execute('''
                    SELECT c.*, d.nome as departamento_nome FROM categorias_app c
                    LEFT JOIN departamentos d ON c.departamento_id = d.id
                    WHERE c.departamento_id = %s OR c.is_global = TRUE
                    ORDER BY c.nome;
                ''', (departamento_id,))
            else:
                # Todas as categorias
                db.cursor.execute('''
                    SELECT c.*, d.nome as departamento_nome FROM categorias_app c
                    LEFT JOIN departamentos d ON c.departamento_id = d.id
                    ORDER BY c.nome;
                ''')

            categorias = db.cursor.fetchall()
            result = [{
                'id': cat[0],
                'nome': cat[1],
                'departamento_id': cat[2],
                'tipo_produtividade': cat[3],
                'cor': cat[4],
                'descricao': cat[5],
                'is_global': cat[6],
                'created_at': format_datetime_brasilia(cat[7]) if cat[7] else None,
                'departamento_nome': cat[8] if len(cat) > 8 else None
            } for cat in categorias]
            return jsonify(result)
    except Exception as e:
        print(f"Erro ao obter categorias: {e}")
        return jsonify([]), 200
