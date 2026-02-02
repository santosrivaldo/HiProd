import jwt
import hashlib
import secrets
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timezone, timedelta
from .config import Config
from .database import DatabaseConnection

def generate_jwt_token(user_id):
    """Gera um token JWT para o usuário"""
    payload = {
        'user_id': str(user_id),
        'exp': datetime.now(timezone.utc) + Config.JWT_ACCESS_TOKEN_EXPIRES
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token):
    """Verifica e decodifica um token JWT"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator para rotas protegidas por JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
        except (IndexError, AttributeError):
            return jsonify({'message': 'Formato de token inválido!'}), 401
        
        user_id = verify_jwt_token(token)
        if not user_id:
            return jsonify({'message': 'Token inválido ou expirado!'}), 401
        
        # Buscar dados do usuário
        try:
            with DatabaseConnection() as db:
                db.cursor.execute('''
                    SELECT id, nome, email, ativo, departamento_id
                    FROM usuarios
                    WHERE id = %s
                ''', (user_id,))
                user = db.cursor.fetchone()
                
                if not user:
                    return jsonify({'message': 'Usuário não encontrado!'}), 404
                
                if not user[3]:  # ativo
                    return jsonify({'message': 'Usuário inativo!'}), 403
                
                return f(user, *args, **kwargs)
        except Exception as e:
            print(f"❌ Erro ao buscar usuário: {e}")
            return jsonify({'message': 'Erro ao validar usuário!'}), 500
    
    return decorated

def generate_api_token():
    """
    Gera um token de API seguro e único.
    Usa timestamp + random para garantir unicidade.
    """
    import time
    
    # Gerar token único usando timestamp + random
    timestamp = str(int(time.time() * 1000000))  # Microsegundos
    random_part = secrets.token_urlsafe(32)  # 32 bytes aleatórios
    
    # Combinar para criar token final (64 caracteres)
    combined = f"{timestamp}{random_part}"
    token = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:64]
    
    # Garantir que o token tenha exatamente 64 caracteres
    if len(token) < 64:
        token = token + secrets.token_urlsafe(64 - len(token))[:64 - len(token)]
    
    return token[:64]

def validate_api_token(token):
    """
    Valida um token de API e retorna os dados do token.
    Retorna None se inválido, ou uma tupla (token_id, token_nome, ativo, expires_at, created_by) se válido.
    """
    if not token:
        return None
    
    # Limpar token
    token = token.strip()
    
    # Remover 'Bearer ' se presente
    if token.startswith('Bearer '):
        token = token.split(' ', 1)[1].strip()
    
    try:
        with DatabaseConnection() as db:
            # Buscar token no banco
            db.cursor.execute('''
                SELECT id, nome, ativo, expires_at, created_by
                FROM api_tokens
                WHERE token = %s
            ''', (token,))
            
            token_data = db.cursor.fetchone()
            
            if not token_data:
                return None
            
            token_id, token_nome, ativo, expires_at, created_by = token_data
            
            # Verificar se está ativo
            if not ativo:
                return None
            
            # Verificar expiração
            if expires_at:
                expires_at_utc = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at
                if datetime.now(timezone.utc) > expires_at_utc:
                    return None
            
            return token_data
            
    except Exception as e:
        print(f"❌ Erro ao validar token de API: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_token_permission(token_id, endpoint, method):
    """
    Verifica se um token tem permissão para acessar um endpoint específico.
    Retorna True se tiver permissão, False caso contrário.
    """
    try:
        with DatabaseConnection() as db:
            # Buscar permissões do token
            db.cursor.execute('''
                SELECT endpoint, method
                FROM api_token_permissions
                WHERE token_id = %s
            ''', (token_id,))
            
            permissions = db.cursor.fetchall()
            
            if not permissions:
                return False
            
            # Normalizar endpoint e método
            endpoint = endpoint.strip()
            method = method.strip().upper()
            
            # Verificar cada permissão
            for perm_endpoint, perm_method in permissions:
                perm_endpoint = perm_endpoint.strip()
                perm_method = perm_method.strip().upper() if perm_method else '*'
                
                # Wildcard no final (ex: /api/v1/*)
                if perm_endpoint.endswith('*'):
                    base_path = perm_endpoint[:-1]
                    if endpoint.startswith(base_path):
                        if perm_method == '*' or perm_method == method:
                            return True
                
                # Wildcard no início (ex: */atividades)
                elif perm_endpoint.startswith('*'):
                    suffix_path = perm_endpoint[1:]
                    if endpoint.endswith(suffix_path):
                        if perm_method == '*' or perm_method == method:
                            return True
                
                # Comparação exata
                elif perm_endpoint == endpoint:
                    if perm_method == '*' or perm_method == method:
                        return True
                
                # Comparação parcial (para rotas com parâmetros)
                elif endpoint.startswith(perm_endpoint.rstrip('/')):
                    if perm_method == '*' or perm_method == method:
                        return True
            
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar permissão: {e}")
        import traceback
        traceback.print_exc()
        return False

def api_token_required(f):
    """
    Decorator para rotas protegidas por token de API.
    Valida o token e verifica permissões por endpoint.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Obter token do header
        token = request.headers.get('Authorization') or request.headers.get('X-API-Token')
        
        if not token:
            return jsonify({'message': 'Token de API não fornecido!'}), 401
        
        # Validar token
        token_data = validate_api_token(token)
        
        if not token_data:
            return jsonify({'message': 'Token de API inválido ou expirado!'}), 401
        
        token_id, token_nome, ativo, expires_at, created_by = token_data
        
        # Verificar permissões
        endpoint = request.path
        method = request.method
        
        has_permission = check_token_permission(token_id, endpoint, method)
        
        if not has_permission:
            return jsonify({
                'message': 'Token sem permissão para este endpoint!',
                'endpoint': endpoint,
                'method': method
            }), 403
        
        # Atualizar último uso
        try:
            with DatabaseConnection() as db:
                db.cursor.execute('''
                    UPDATE api_tokens
                    SET last_used_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (token_id,))
        except Exception as e:
            print(f"⚠️ Erro ao atualizar last_used_at: {e}")
        
        # Passar dados do token para a função
        return f(token_data, *args, **kwargs)
    
    return decorated

def hybrid_token_required(f):
    """
    Decorator híbrido que aceita tanto JWT quanto API Token.
    Útil para endpoints internos que podem ser acessados de ambas as formas.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401
        
        # Tentar JWT primeiro
        if token.startswith('Bearer '):
            jwt_token = token.split(' ')[1]
            user_id = verify_jwt_token(jwt_token)
            
            if user_id:
                try:
                    with DatabaseConnection() as db:
                        db.cursor.execute('''
                            SELECT id, nome, email, ativo, departamento_id
                            FROM usuarios
                            WHERE id = %s
                        ''', (user_id,))
                        user = db.cursor.fetchone()
                        
                        if user and user[3]:  # Se existe e está ativo
                            return f(user, *args, **kwargs)
                except Exception as e:
                    print(f"⚠️ Erro ao buscar usuário: {e}")
        
        # Tentar API Token
        token_data = validate_api_token(token)
        
        if token_data:
            token_id, token_nome, ativo, expires_at, created_by = token_data
            
            # Verificar permissões
            endpoint = request.path
            method = request.method
            
            has_permission = check_token_permission(token_id, endpoint, method)
            
            if has_permission:
                # Atualizar último uso
                try:
                    with DatabaseConnection() as db:
                        db.cursor.execute('''
                            UPDATE api_tokens
                            SET last_used_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        ''', (token_id,))
                except Exception as e:
                    print(f"⚠️ Erro ao atualizar last_used_at: {e}")
                
                return f(token_data, *args, **kwargs)
        
        return jsonify({'message': 'Token inválido ou sem permissão!'}), 401
    
    return decorated
