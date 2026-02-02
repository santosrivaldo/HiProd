
import jwt
import bcrypt
import uuid
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify
from .config import Config
from .database import DatabaseConnection

# Timezone de Brasília (UTC-3)
BRASILIA_TZ = timezone(timedelta(hours=-3))

def generate_token(user_id):
    """Gerar token JWT"""
    payload = {
        'user_id': str(user_id),
        'exp': datetime.now(BRASILIA_TZ) + Config.JWT_ACCESS_TOKEN_EXPIRES
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verificar token JWT"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator para rotas protegidas"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401

        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
        except IndexError:
            return jsonify({'message': 'Formato de token inválido!'}), 401

        user_id = verify_token(token)
        if not user_id:
            return jsonify({'message': 'Token inválido ou expirado!'}), 401

        try:
            with DatabaseConnection() as db:
                # Verificar se o usuário ainda existe
                db.cursor.execute("SELECT id, nome, senha, email, departamento_id, ativo FROM usuarios WHERE id = %s AND ativo = TRUE;", (uuid.UUID(user_id),))
                current_user = db.cursor.fetchone()
                if not current_user:
                    print(f"❌ Usuário não encontrado ou inativo para token: {user_id}")
                    return jsonify({'message': 'Usuário não encontrado ou inativo!'}), 401

                return f(current_user, *args, **kwargs)
        except Exception as e:
            print(f"Erro ao verificar usuário: {e}")
            return jsonify({'message': 'Erro interno do servidor!'}), 500

    return decorated

def agent_required(f):
    """
    Decorator para rotas do agente - aceita token OU nome do usuário no header X-User-Name
    Se X-User-Name estiver presente, usa ele. Caso contrário, tenta token.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verificar se há nome do usuário no header (modo agente sem autenticação)
        usuario_nome = request.headers.get('X-User-Name')
        
        if usuario_nome:
            # Modo agente: usar nome do usuário diretamente
            print(f"🔐 Autenticação via nome de usuário: {usuario_nome}")
            # Criar um objeto current_user simulado para compatibilidade
            # (None, nome, None, None, None, True) - similar ao formato de current_user
            current_user = (None, usuario_nome, None, None, None, True)
            return f(current_user, *args, **kwargs)
        
        # Se não tiver X-User-Name, tentar autenticação por token (modo normal)
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token ou nome de usuário (X-User-Name) não fornecido!'}), 401

        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
        except IndexError:
            return jsonify({'message': 'Formato de token inválido!'}), 401

        user_id = verify_token(token)
        if not user_id:
            return jsonify({'message': 'Token inválido ou expirado!'}), 401

        try:
            with DatabaseConnection() as db:
                # Verificar se o usuário ainda existe
                db.cursor.execute("SELECT id, nome, senha, email, departamento_id, ativo FROM usuarios WHERE id = %s AND ativo = TRUE;", (uuid.UUID(user_id),))
                current_user = db.cursor.fetchone()
                if not current_user:
                    print(f"❌ Usuário não encontrado ou inativo para token: {user_id}")
                    return jsonify({'message': 'Usuário não encontrado ou inativo!'}), 401

                return f(current_user, *args, **kwargs)
        except Exception as e:
            print(f"Erro ao verificar usuário: {e}")
            return jsonify({'message': 'Erro interno do servidor!'}), 500

    return decorated

def generate_api_token():
    """Gerar um token de API único e seguro"""
    return secrets.token_urlsafe(32)

def hash_api_token(token):
    """Hash do token para armazenamento seguro"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def api_token_required(f):
    """
    Decorator para rotas protegidas por token de API.
    Valida o token e verifica permissões por endpoint.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization') or request.headers.get('X-API-Token')
        
        if not token:
            return jsonify({'message': 'Token de API não fornecido!'}), 401

        try:
            # Remover 'Bearer ' se presente
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
        except (IndexError, AttributeError):
            return jsonify({'message': 'Formato de token inválido!'}), 401

        try:
            with DatabaseConnection() as db:
                # Buscar token no banco (armazenamos o token em texto plano para comparação)
                db.cursor.execute('''
                    SELECT id, nome, ativo, expires_at, created_by
                    FROM api_tokens
                    WHERE token = %s
                ''', (token,))
                
                token_data = db.cursor.fetchone()
                
                if not token_data:
                    return jsonify({'message': 'Token de API inválido!'}), 401
                
                token_id, token_nome, ativo, expires_at, created_by = token_data
                
                # Verificar se token está ativo
                if not ativo:
                    return jsonify({'message': 'Token de API desativado!'}), 403
                
                # Verificar expiração
                if expires_at:
                    expires_at_utc = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at
                    if datetime.now(timezone.utc) > expires_at_utc:
                        return jsonify({'message': 'Token de API expirado!'}), 403
                
                # Verificar permissões para o endpoint atual
                endpoint = request.path
                method = request.method
                
                # Buscar permissões do token
                db.cursor.execute('''
                    SELECT endpoint, method
                    FROM api_token_permissions
                    WHERE token_id = %s
                ''', (token_id,))
                
                permissions = db.cursor.fetchall()
                
                # Se não houver permissões específicas, negar acesso
                if not permissions:
                    return jsonify({'message': 'Token sem permissões configuradas!'}), 403
                
                # Verificar se o token tem permissão para este endpoint
                has_permission = False
                for perm_endpoint, perm_method in permissions:
                    # Suporte a wildcards (ex: /atividades/*)
                    if perm_endpoint.endswith('*'):
                        base_path = perm_endpoint[:-1]
                        if endpoint.startswith(base_path) and (perm_method == '*' or perm_method == method):
                            has_permission = True
                            break
                    elif perm_endpoint == endpoint and (perm_method == '*' or perm_method == method):
                        has_permission = True
                        break
                
                if not has_permission:
                    return jsonify({
                        'message': 'Token sem permissão para este endpoint!',
                        'endpoint': endpoint,
                        'method': method
                    }), 403
                
                # Atualizar último uso
                db.cursor.execute('''
                    UPDATE api_tokens
                    SET last_used_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (token_id,))
                
                # Passar informações do token para a função
                return f(token_data, *args, **kwargs)
                
        except Exception as e:
            print(f"Erro ao verificar token de API: {e}")
            return jsonify({'message': 'Erro interno do servidor!'}), 500

    return decorated
