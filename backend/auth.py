
import jwt
import bcrypt
import uuid
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
