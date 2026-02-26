from flask import Blueprint, request, jsonify
from ..auth import token_required, generate_api_token
from ..database import DatabaseConnection
from ..permissions import can_manage_system
from ..utils import format_datetime_brasilia
from datetime import datetime, timedelta, timezone

token_bp = Blueprint('token', __name__)

@token_bp.route('/api-tokens', methods=['GET'])
@token_required
def get_tokens(current_user):
    """Lista todos os tokens de API (apenas Admin)."""
    if not can_manage_system(current_user):
        return jsonify({'message': 'Sem permissão. Apenas Admin pode gerenciar tokens de API.'}), 403
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT id, nome, descricao, token, ativo, created_by, created_at, updated_at, last_used_at, expires_at
                FROM api_tokens
                ORDER BY created_at DESC
            ''')
            tokens = db.cursor.fetchall()

            result = []
            for token in tokens:
                token_id, nome, descricao, token_value, ativo, created_by, created_at, updated_at, last_used_at, expires_at = token
                
                # Buscar nome do criador
                creator_name = None
                if created_by:
                    db.cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (created_by,))
                    creator_result = db.cursor.fetchone()
                    creator_name = creator_result[0] if creator_result else None
                
                # Buscar permissões do token
                db.cursor.execute('''
                    SELECT endpoint, method
                    FROM api_token_permissions
                    WHERE token_id = %s
                    ORDER BY endpoint, method
                ''', (token_id,))
                permissions = db.cursor.fetchall()
                
                result.append({
                    'id': token_id,
                    'nome': nome,
                    'descricao': descricao,
                    'token': token_value,  # Mostrar token completo
                    'ativo': ativo,
                    'created_by': str(created_by) if created_by else None,
                    'created_by_name': creator_name,
                    'created_at': format_datetime_brasilia(created_at) if created_at else None,
                    'updated_at': format_datetime_brasilia(updated_at) if updated_at else None,
                    'last_used_at': format_datetime_brasilia(last_used_at) if last_used_at else None,
                    'expires_at': format_datetime_brasilia(expires_at) if expires_at else None,
                    'permissions': [{'endpoint': p[0], 'method': p[1]} for p in permissions]
                })

            return jsonify(result), 200
    except Exception as e:
        print(f"❌ Erro ao listar tokens: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': 'Erro ao listar tokens!',
            'error': str(e)
        }), 500

@token_bp.route('/api-tokens', methods=['POST'])
@token_required
def create_token(current_user):
    """Cria um novo token de API (apenas Admin)."""
    if not can_manage_system(current_user):
        return jsonify({'message': 'Sem permissão. Apenas Admin pode criar tokens de API.'}), 403
    try:
        data = request.get_json()
        
        if not data or not data.get('nome'):
            return jsonify({'message': 'Nome do token é obrigatório!'}), 400
        
        nome = data.get('nome')
        descricao = data.get('descricao', '')
        expires_days = data.get('expires_days')  # Opcional, None = sem expiração
        permissions = data.get('permissions', [])  # Lista de {endpoint, method}
        
        if not permissions:
            return jsonify({'message': 'É necessário definir pelo menos uma permissão!'}), 400
        
        # Gerar token único
        token_value = generate_api_token()
        user_id = current_user[0]  # ID do usuário atual
        
        # Calcular data de expiração
        expires_at = None
        if expires_days:
            try:
                expires_days = int(expires_days)
                if expires_days > 0:
                    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
            except (ValueError, TypeError):
                return jsonify({'message': 'expires_days deve ser um número inteiro positivo!'}), 400
        
        with DatabaseConnection() as db:
            # Verificar se já existe token com mesmo nome
            db.cursor.execute('SELECT id FROM api_tokens WHERE nome = %s', (nome,))
            if db.cursor.fetchone():
                return jsonify({'message': 'Já existe um token com este nome!'}), 400
            
            # Inserir token
            db.cursor.execute('''
                INSERT INTO api_tokens (nome, descricao, token, created_by, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (nome, descricao, token_value, user_id, expires_at))
            
            token_id = db.cursor.fetchone()[0]
            
            # Inserir permissões
            for perm in permissions:
                endpoint = perm.get('endpoint')
                method = perm.get('method', 'GET')
                
                if not endpoint:
                    continue
                
                # Validar e normalizar método
                if isinstance(method, str):
                    method = method.upper()
                else:
                    method = 'GET'
                
                # Validar endpoint
                if not isinstance(endpoint, str) or len(endpoint.strip()) == 0:
                    continue
                
                try:
                    db.cursor.execute('''
                        INSERT INTO api_token_permissions (token_id, endpoint, method)
                        VALUES (%s, %s, %s)
                    ''', (token_id, endpoint.strip(), method))
                except Exception as perm_error:
                    print(f"⚠️ Erro ao inserir permissão {endpoint} ({method}): {perm_error}")
                    # Continuar com outras permissões mesmo se uma falhar
            
            return jsonify({
                'message': 'Token criado com sucesso!',
                'token': token_value,  # Retornar token completo
                'id': token_id,
                'nome': nome
            }), 201
            
    except Exception as e:
        print(f"❌ Erro ao criar token: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': 'Erro ao criar token!',
            'error': str(e)
        }), 500

@token_bp.route('/api-tokens/<int:token_id>', methods=['PUT'])
@token_required
def update_token(current_user, token_id):
    """Atualiza um token de API (apenas Admin)."""
    if not can_manage_system(current_user):
        return jsonify({'message': 'Sem permissão. Apenas Admin pode editar tokens de API.'}), 403
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'Dados não fornecidos!'}), 400
        
        nome = data.get('nome')
        descricao = data.get('descricao')
        ativo = data.get('ativo')
        expires_days = data.get('expires_days')
        permissions = data.get('permissions')
        
        with DatabaseConnection() as db:
            # Verificar se token existe
            db.cursor.execute('SELECT id FROM api_tokens WHERE id = %s', (token_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Token não encontrado!'}), 404
            
            # Atualizar token
            updates = []
            params = []
            
            if nome is not None:
                # Verificar se nome já existe em outro token
                db.cursor.execute('SELECT id FROM api_tokens WHERE nome = %s AND id != %s', (nome, token_id))
                if db.cursor.fetchone():
                    return jsonify({'message': 'Já existe um token com este nome!'}), 400
                updates.append('nome = %s')
                params.append(nome)
            
            if descricao is not None:
                updates.append('descricao = %s')
                params.append(descricao)
            
            if ativo is not None:
                updates.append('ativo = %s')
                params.append(ativo)
            
            if expires_days is not None:
                try:
                    if expires_days:
                        expires_days = int(expires_days)
                        if expires_days > 0:
                            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
                        else:
                            expires_at = None
                    else:
                        expires_at = None
                    updates.append('expires_at = %s')
                    params.append(expires_at)
                except (ValueError, TypeError):
                    return jsonify({'message': 'expires_days deve ser um número inteiro positivo ou null!'}), 400
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(token_id)
            
            if len(updates) > 1:  # Mais que apenas updated_at
                set_clause = ', '.join(updates)
                db.cursor.execute(f'''
                    UPDATE api_tokens
                    SET {set_clause}
                    WHERE id = %s
                ''', params)
            
            # Atualizar permissões se fornecidas
            if permissions is not None:
                # Remover permissões antigas
                db.cursor.execute('DELETE FROM api_token_permissions WHERE token_id = %s', (token_id,))
                
                # Inserir novas permissões
                for perm in permissions:
                    endpoint = perm.get('endpoint')
                    method = perm.get('method', 'GET')
                    
                    if not endpoint:
                        continue
                    
                    # Validar e normalizar método
                    if isinstance(method, str):
                        method = method.upper()
                    else:
                        method = 'GET'
                    
                    # Validar endpoint
                    if not isinstance(endpoint, str) or len(endpoint.strip()) == 0:
                        continue
                    
                    try:
                        db.cursor.execute('''
                            INSERT INTO api_token_permissions (token_id, endpoint, method)
                            VALUES (%s, %s, %s)
                        ''', (token_id, endpoint.strip(), method))
                    except Exception as perm_error:
                        print(f"⚠️ Erro ao inserir permissão {endpoint} ({method}): {perm_error}")
            
            return jsonify({'message': 'Token atualizado com sucesso!'}), 200
            
    except Exception as e:
        print(f"❌ Erro ao atualizar token: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': 'Erro ao atualizar token!',
            'error': str(e)
        }), 500

@token_bp.route('/api-tokens/<int:token_id>', methods=['DELETE'])
@token_required
def delete_token(current_user, token_id):
    """Exclui um token de API (apenas Admin)."""
    if not can_manage_system(current_user):
        return jsonify({'message': 'Sem permissão. Apenas Admin pode excluir tokens de API.'}), 403
    try:
        with DatabaseConnection() as db:
            # Verificar se token existe
            db.cursor.execute('SELECT id FROM api_tokens WHERE id = %s', (token_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Token não encontrado!'}), 404
            
            # Excluir token (cascade vai excluir permissões)
            db.cursor.execute('DELETE FROM api_tokens WHERE id = %s', (token_id,))
            
            return jsonify({'message': 'Token excluído com sucesso!'}), 200
            
    except Exception as e:
        print(f"❌ Erro ao excluir token: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': 'Erro ao excluir token!',
            'error': str(e)
        }), 500

@token_bp.route('/api-tokens/<int:token_id>/toggle', methods=['POST'])
@token_required
def toggle_token(current_user, token_id):
    """Ativa ou desativa um token de API (apenas Admin)."""
    if not can_manage_system(current_user):
        return jsonify({'message': 'Sem permissão. Apenas Admin pode alterar tokens de API.'}), 403
    try:
        with DatabaseConnection() as db:
            # Verificar se token existe
            db.cursor.execute('SELECT id, ativo FROM api_tokens WHERE id = %s', (token_id,))
            token_data = db.cursor.fetchone()
            
            if not token_data:
                return jsonify({'message': 'Token não encontrado!'}), 404
            
            current_status = token_data[1]
            new_status = not current_status
            
            # Atualizar status
            db.cursor.execute('''
                UPDATE api_tokens
                SET ativo = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (new_status, token_id))
            
            return jsonify({
                'message': f'Token {"ativado" if new_status else "desativado"} com sucesso!',
                'ativo': new_status
            }), 200
            
    except Exception as e:
        print(f"❌ Erro ao alterar status do token: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': 'Erro ao alterar status do token!',
            'error': str(e)
        }), 500

@token_bp.route('/api-tokens/endpoints', methods=['GET'])
@token_required
def get_available_endpoints(current_user):
    """Lista todos os endpoints disponíveis para configuração de permissões"""
    endpoints = [
        # Endpoints V1 para API Externa
        {'endpoint': '/api/v1/atividades', 'method': 'POST', 'description': 'V1 - Buscar atividades por usuário e período'},
        {'endpoint': '/api/v1/usuarios', 'method': 'GET', 'description': 'V1 - Listar usuários monitorados'},
        {'endpoint': '/api/v1/estatisticas', 'method': 'POST', 'description': 'V1 - Obter estatísticas de usuário'},
        {'endpoint': '/api/v1/health', 'method': 'GET', 'description': 'V1 - Health check (sem autenticação)'},
        {'endpoint': '/api/v1/*', 'method': '*', 'description': 'V1 - Todos os endpoints V1 (wildcard)'},
        
        # Atividades
        {'endpoint': '/atividades', 'method': 'GET', 'description': 'Listar atividades'},
        {'endpoint': '/atividades/*', 'method': '*', 'description': 'Todos os endpoints de atividades (wildcard)'},
        {'endpoint': '/api/atividades', 'method': 'POST', 'description': 'Buscar atividades por usuário e período (legado)'},
        
        # Usuários
        {'endpoint': '/usuarios', 'method': 'GET', 'description': 'Listar usuários'},
        {'endpoint': '/usuarios/*', 'method': '*', 'description': 'Todos os endpoints de usuários (wildcard)'},
        {'endpoint': '/usuarios-monitorados', 'method': 'GET', 'description': 'Listar usuários monitorados'},
        
        # Departamentos
        {'endpoint': '/departamentos', 'method': 'GET', 'description': 'Listar departamentos'},
        {'endpoint': '/departamentos/*', 'method': '*', 'description': 'Todos os endpoints de departamentos (wildcard)'},
        
        # Tags
        {'endpoint': '/tags', 'method': 'GET', 'description': 'Listar tags'},
        {'endpoint': '/tags/*', 'method': '*', 'description': 'Todos os endpoints de tags (wildcard)'},
        
        # Categorias
        {'endpoint': '/categorias', 'method': 'GET', 'description': 'Listar categorias'},
        {'endpoint': '/categorias/*', 'method': '*', 'description': 'Todos os endpoints de categorias (wildcard)'},
        
        # Escalas
        {'endpoint': '/escalas', 'method': 'GET', 'description': 'Listar escalas'},
        {'endpoint': '/escalas/*', 'method': '*', 'description': 'Todos os endpoints de escalas (wildcard)'},
    ]
    
    return jsonify(endpoints), 200
