
import psycopg2
from flask import Blueprint, request, jsonify
from ..auth import token_required
from ..database import DatabaseConnection

tag_bp = Blueprint('tag', __name__)

@tag_bp.route('/tags', methods=['GET'])
@token_required
def get_tags(current_user):
    departamento_id = request.args.get('departamento_id')
    ativo = request.args.get('ativo', 'true').lower() == 'true'
    busca = request.args.get('busca', '').strip()

    try:
        with DatabaseConnection() as db:
            # Construir query base
            base_query = '''
                SELECT t.id, t.nome, t.descricao, t.cor, t.produtividade, t.departamento_id,
                       t.ativo, t.created_at, t.updated_at, t.tier, d.nome as departamento_nome
                FROM tags t
                LEFT JOIN departamentos d ON t.departamento_id = d.id
                WHERE t.ativo = %s
            '''
            params = [ativo]

            # Adicionar filtro de departamento
            if departamento_id:
                base_query += ' AND (t.departamento_id = %s OR t.departamento_id IS NULL)'
                params.append(departamento_id)

            # Adicionar filtro de busca
            if busca:
                base_query += ' AND (t.nome ILIKE %s OR t.descricao ILIKE %s)'
                params.extend([f'%{busca}%', f'%{busca}%'])

            base_query += ' ORDER BY t.nome;'

            db.cursor.execute(base_query, params)
            tags = db.cursor.fetchall()
            result = []

            for tag in tags:
                # Buscar palavras-chave da tag
                db.cursor.execute('''
                    SELECT palavra_chave, peso
                    FROM tag_palavras_chave
                    WHERE tag_id = %s
                    ORDER BY peso DESC;
                ''', (tag[0],))
                palavras_chave = db.cursor.fetchall()

                result.append({
                    'id': tag[0],
                    'nome': tag[1],
                    'descricao': tag[2],
                    'cor': tag[3],
                    'produtividade': tag[4],
                    'departamento_id': tag[5],
                    'ativo': tag[6],
                    'created_at': tag[7].isoformat() if tag[7] else None,
                    'updated_at': tag[8].isoformat() if tag[8] else None,
                    'tier': tag[9] if len(tag) > 9 and tag[9] is not None else 3,
                    'departamento_nome': tag[10] if len(tag) > 10 else None,
                    'palavras_chave': [{'palavra': p[0], 'peso': p[1]} for p in palavras_chave]
                })

            return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar tags: {e}")
        return jsonify([]), 200

@tag_bp.route('/tags', methods=['POST'])
@token_required
def create_tag(current_user):
    data = request.json

    if not data or 'nome' not in data or 'produtividade' not in data:
        return jsonify({'message': 'Nome e produtividade são obrigatórios!'}), 400

    nome = data['nome'].strip()
    descricao = data.get('descricao', '')
    cor = data.get('cor', '#6B7280')
    produtividade = data['produtividade']
    departamento_id = data.get('departamento_id')
    palavras_chave = data.get('palavras_chave', [])
    tier = int(data.get('tier', 3))

    if tier < 1 or tier > 5:
        return jsonify({'message': 'Tier deve estar entre 1 e 5!'}), 400

    if produtividade not in ['productive', 'nonproductive', 'neutral']:
        return jsonify({'message': 'Produtividade inválida!'}), 400

    try:
        with DatabaseConnection() as db:
            # Criar tag
            db.cursor.execute('''
                INSERT INTO tags (nome, descricao, cor, produtividade, departamento_id, tier)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
            ''', (nome, descricao, cor, produtividade, departamento_id, tier))

            tag_id = db.cursor.fetchone()[0]

            # Adicionar palavras-chave
            palavras_adicionadas = set()  # Para evitar duplicatas
            for palavra in palavras_chave:
                if isinstance(palavra, dict):
                    palavra_chave = palavra.get('palavra', '')
                    peso = palavra.get('peso', 1)
                else:
                    palavra_chave = str(palavra)
                    peso = 1

                palavra_chave = palavra_chave.strip()
                if palavra_chave and palavra_chave not in palavras_adicionadas:
                    try:
                        db.cursor.execute('''
                            INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (tag_id, palavra_chave) DO UPDATE SET peso = EXCLUDED.peso;
                        ''', (tag_id, palavra_chave, peso))
                        palavras_adicionadas.add(palavra_chave)
                    except psycopg2.IntegrityError:
                        # Ignorar se já existe
                        continue

            return jsonify({'message': 'Tag criada com sucesso!', 'id': tag_id}), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Tag já existe para este departamento!'}), 409
    except Exception as e:
        print(f"Erro ao criar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@tag_bp.route('/tags/<int:tag_id>', methods=['PUT'])
@token_required
def update_tag(current_user, tag_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se a tag existe
            db.cursor.execute('SELECT id FROM tags WHERE id = %s;', (tag_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Tag não encontrada!'}), 404

            # Atualizar tag
            update_fields = []
            update_values = []

            if 'nome' in data:
                update_fields.append('nome = %s')
                update_values.append(data['nome'])
            if 'descricao' in data:
                update_fields.append('descricao = %s')
                update_values.append(data['descricao'])
            if 'cor' in data:
                update_fields.append('cor = %s')
                update_values.append(data['cor'])
            if 'produtividade' in data:
                if data['produtividade'] not in ['productive', 'nonproductive', 'neutral']:
                    return jsonify({'message': 'Produtividade inválida!'}), 400
                update_fields.append('produtividade = %s')
                update_values.append(data['produtividade'])
            if 'ativo' in data:
                update_fields.append('ativo = %s')
                update_values.append(data['ativo'])
            if 'tier' in data:
                tier_value = int(data['tier']) if data['tier'] is not None else 3
                if tier_value < 1 or tier_value > 5:
                    return jsonify({'message': 'Tier deve estar entre 1 e 5!'}), 400
                update_fields.append('tier = %s')
                update_values.append(tier_value)

            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            update_values.append(tag_id)

            db.cursor.execute(f'''
                UPDATE tags SET {', '.join(update_fields)}
                WHERE id = %s;
            ''', update_values)

            # Atualizar palavras-chave se fornecidas
            if 'palavras_chave' in data:
                # Remover palavras-chave existentes
                db.cursor.execute('DELETE FROM tag_palavras_chave WHERE tag_id = %s;', (tag_id,))

                # Adicionar novas palavras-chave
                palavras_adicionadas = set()  # Para evitar duplicatas
                for palavra in data['palavras_chave']:
                    if isinstance(palavra, dict):
                        palavra_chave = palavra.get('palavra', '')
                        peso = palavra.get('peso', 1)
                    else:
                        palavra_chave = str(palavra)
                        peso = 1

                    palavra_chave = palavra_chave.strip()
                    if palavra_chave and palavra_chave not in palavras_adicionadas:
                        try:
                            db.cursor.execute('''
                                INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                                VALUES (%s, %s, %s);
                            ''', (tag_id, palavra_chave, peso))
                            palavras_adicionadas.add(palavra_chave)
                        except psycopg2.IntegrityError:
                            # Ignorar se já existe (por segurança)
                            continue

            return jsonify({'message': 'Tag atualizada com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@tag_bp.route('/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def delete_tag(current_user, tag_id):
    try:
        with DatabaseConnection() as db:
            # Verificar se a tag existe
            db.cursor.execute('SELECT id FROM tags WHERE id = %s;', (tag_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Tag não encontrada!'}), 404

            # Deletar tag (as palavras-chave serão deletadas em cascata)
            db.cursor.execute('DELETE FROM tags WHERE id = %s;', (tag_id,))

            return jsonify({'message': 'Tag deletada com sucesso!'}), 200
    except Exception as e:
        print(f"Erro ao deletar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500
