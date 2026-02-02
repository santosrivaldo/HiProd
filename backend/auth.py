
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
    """Decorator para rotas protegidas - aceita JWT ou Token de API"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization') or request.headers.get('X-API-Token')
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401

        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
        except IndexError:
            return jsonify({'message': 'Formato de token inválido!'}), 401

        # Tentar primeiro como token de API
        try:
            token_clean = token.strip()
            with DatabaseConnection() as db:
                db.cursor.execute('''
                    SELECT id, nome, ativo, expires_at, created_by
                    FROM api_tokens
                    WHERE token = %s
                ''', (token_clean,))
                
                api_token_data = db.cursor.fetchone()
                
                if api_token_data:
                    token_id, token_nome, ativo, expires_at, created_by = api_token_data
                    
                    # Verificar se token está ativo
                    if not ativo:
                        return jsonify({'message': 'Token de API desativado!'}), 403
                    
                    # Verificar expiração
                    if expires_at:
                        expires_at_utc = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at
                        if datetime.now(timezone.utc) > expires_at_utc:
                            return jsonify({'message': 'Token de API expirado!'}), 403
                    
                    # Verificar permissões
                    endpoint = request.path
                    method = request.method
                    
                    db.cursor.execute('''
                        SELECT endpoint, method
                        FROM api_token_permissions
                        WHERE token_id = %s
                    ''', (token_id,))
                    
                    permissions = db.cursor.fetchall()
                    
                    if not permissions:
                        return jsonify({'message': 'Token sem permissões configuradas!'}), 403
                    
                    # Verificar se o token tem permissão para este endpoint
                    has_permission = False
                    for perm_endpoint, perm_method in permissions:
                        # Normalizar endpoint e permissão
                        perm_endpoint = perm_endpoint.strip() if perm_endpoint else ''
                        perm_method = perm_method.strip().upper() if perm_method else '*'
                        
                        # Suporte a wildcards (ex: /atividades/*)
                        if perm_endpoint.endswith('*'):
                            base_path = perm_endpoint[:-1]
                            if endpoint.startswith(base_path) and (perm_method == '*' or perm_method == method):
                                has_permission = True
                                break
                        # Suporte a wildcards no início (ex: */atividades)
                        elif perm_endpoint.startswith('*'):
                            suffix_path = perm_endpoint[1:]
                            if endpoint.endswith(suffix_path) and (perm_method == '*' or perm_method == method):
                                has_permission = True
                                break
                        # Suporte a padrões com parâmetros (ex: /atividades/<id>)
                        elif '<' in perm_endpoint and '>' in perm_endpoint:
                            # Converter padrão Flask para comparação
                            pattern_parts = perm_endpoint.split('/')
                            endpoint_parts = endpoint.split('/')
                            
                            if len(pattern_parts) == len(endpoint_parts):
                                matches = True
                                for p_part, e_part in zip(pattern_parts, endpoint_parts):
                                    # Se a parte do padrão não é um parâmetro, deve ser exata
                                    if p_part and not (p_part.startswith('<') and p_part.endswith('>')):
                                        if p_part != e_part:
                                            matches = False
                                            break
                                
                                if matches and (perm_method == '*' or perm_method == method):
                                    has_permission = True
                                    break
                        # Comparação exata
                        elif perm_endpoint == endpoint and (perm_method == '*' or perm_method == method):
                            has_permission = True
                            break
                        # Comparação sem parâmetros (ex: /atividades/123 vs /atividades/<id>)
                        elif perm_endpoint in endpoint and (perm_method == '*' or perm_method == method):
                            # Verificar se o endpoint começa com a permissão (para rotas com parâmetros)
                            if endpoint.startswith(perm_endpoint.rstrip('/')) or endpoint.startswith(perm_endpoint + '/'):
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
                    
                    # Criar um objeto current_user simulado para compatibilidade
                    # (None, nome, None, None, None, True) - similar ao formato de current_user
                    current_user = (None, f'api_token_{token_id}', None, None, None, True)
                    return f(current_user, *args, **kwargs)
        except Exception as api_error:
            # Se falhar (token não encontrado ou erro de banco), tentar como JWT
            # Apenas logar se for um erro inesperado (não "token não encontrado")
            if 'api_tokens' in str(api_error).lower() or 'database' in str(api_error).lower():
                print(f"⚠️ Erro ao verificar token de API (tentando JWT): {api_error}")
            # Continuar para tentar JWT
        
        # Tentar como JWT token
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
    """
    Gerar um token de API único e seguro.
    Garante que o token seja único no banco de dados.
    """
    max_attempts = 10  # Limite de tentativas para evitar loop infinito
    
    for attempt in range(max_attempts):
        token = secrets.token_urlsafe(32)
        
        # Verificar se o token já existe no banco
        try:
            with DatabaseConnection() as db:
                db.cursor.execute('SELECT id FROM api_tokens WHERE token = %s', (token,))
                if not db.cursor.fetchone():
                    # Token único encontrado
                    return token
        except Exception as e:
            # Se houver erro ao verificar, retornar o token mesmo assim
            # (melhor ter um token do que falhar completamente)
            print(f"⚠️ Erro ao verificar unicidade do token (tentativa {attempt + 1}): {e}")
            if attempt == max_attempts - 1:
                # Última tentativa, retornar mesmo com erro
                return token
    
    # Se chegou aqui, todas as tentativas geraram tokens duplicados (muito improvável)
    # Gerar um token com timestamp para garantir unicidade
    import time
    unique_suffix = str(int(time.time() * 1000000))  # Microsegundos
    return secrets.token_urlsafe(24) + unique_suffix

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
            # Limpar token (remover espaços, tabs, quebras de linha)
            token_original = token
            token = token.strip()
            
            with DatabaseConnection() as db:
                # Log de debug
                print(f"🔍 Validando token de API:")
                print(f"   Token recebido (primeiros 20 chars): {token[:20]}...")
                print(f"   Comprimento do token: {len(token)}")
                print(f"   Endpoint: {request.path}")
                print(f"   Método: {request.method}")
                
                # Buscar token no banco (armazenamos o token em texto plano para comparação)
                # Primeiro, tentar busca exata
                db.cursor.execute('''
                    SELECT id, nome, ativo, expires_at, created_by
                    FROM api_tokens
                    WHERE token = %s
                ''', (token,))
                
                token_data = db.cursor.fetchone()
                
                # Se não encontrou, tentar busca case-insensitive (para debug)
                if not token_data:
                    db.cursor.execute('''
                        SELECT id, nome, ativo, expires_at, created_by, token
                        FROM api_tokens
                        WHERE LOWER(token) = LOWER(%s)
                    ''', (token,))
                    
                    similar_token = db.cursor.fetchone()
                    if similar_token:
                        print(f"⚠️ Token encontrado com case diferente!")
                        print(f"   Token no banco (primeiros 20 chars): {similar_token[5][:20]}...")
                        print(f"   Token recebido (primeiros 20 chars): {token[:20]}...")
                
                # Se ainda não encontrou, fazer diagnósticos mais detalhados
                if not token_data:
                    # Verificar se há tokens que começam com os mesmos caracteres
                    db.cursor.execute('''
                        SELECT id, nome, ativo, LEFT(token, 30) as token_preview, LENGTH(token) as token_length
                        FROM api_tokens
                        WHERE token LIKE %s || '%'
                        ORDER BY created_at DESC
                        LIMIT 5
                    ''', (token[:10],))
                    
                    similar_tokens = db.cursor.fetchall()
                    if similar_tokens:
                        print(f"   ⚠️ Tokens encontrados que começam com '{token[:10]}...':")
                        for similar in similar_tokens:
                            print(f"     - ID: {similar[0]}, Nome: {similar[1]}, Ativo: {similar[2]}, Preview: {similar[3]}..., Length: {similar[4]}")
                    
                    # Listar alguns tokens ativos para comparação
                    db.cursor.execute('''
                        SELECT id, nome, ativo, LEFT(token, 30) as token_preview, LENGTH(token) as token_length
                        FROM api_tokens
                        WHERE ativo = TRUE
                        ORDER BY created_at DESC
                        LIMIT 5
                    ''')
                    sample_tokens = db.cursor.fetchall()
                    print(f"   Tokens ativos no banco (amostra):")
                    for sample in sample_tokens:
                        print(f"     - ID: {sample[0]}, Nome: {sample[1]}, Preview: {sample[3]}..., Length: {sample[4]}")
                    
                    db.cursor.execute('SELECT COUNT(*) FROM api_tokens WHERE ativo = TRUE')
                    total_tokens = db.cursor.fetchone()[0]
                    print(f"   Total de tokens ativos no banco: {total_tokens}")
                    
                    # Verificar se há diferença de case
                    db.cursor.execute('''
                        SELECT id, nome, ativo, token
                        FROM api_tokens
                        WHERE LOWER(TRIM(token)) = LOWER(TRIM(%s))
                    ''', (token,))
                    
                    case_insensitive_match = db.cursor.fetchone()
                    if case_insensitive_match:
                        print(f"   ⚠️ Token encontrado com case diferente!")
                        print(f"     Token no banco: {case_insensitive_match[3][:30]}...")
                        print(f"     Token recebido: {token[:30]}...")
                        print(f"     Diferença de case detectada!")
                    
                    return jsonify({
                        'message': 'Token de API inválido!',
                        'debug': {
                            'token_length': len(token),
                            'token_preview': token[:20] + '...',
                            'endpoint': request.path,
                            'method': request.method,
                            'total_tokens_ativos': total_tokens,
                            'sugestao': 'Verifique se o token está correto e se existe no banco de dados. Use o script verificar_token.sql para diagnosticar.'
                        }
                    }), 401
                
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
                    # Normalizar endpoint e permissão
                    perm_endpoint = perm_endpoint.strip()
                    perm_method = perm_method.strip().upper() if perm_method else '*'
                    
                    # Suporte a wildcards (ex: /atividades/*)
                    if perm_endpoint.endswith('*'):
                        base_path = perm_endpoint[:-1]
                        if endpoint.startswith(base_path) and (perm_method == '*' or perm_method == method):
                            has_permission = True
                            break
                    # Suporte a wildcards no início (ex: */atividades)
                    elif perm_endpoint.startswith('*'):
                        suffix_path = perm_endpoint[1:]
                        if endpoint.endswith(suffix_path) and (perm_method == '*' or perm_method == method):
                            has_permission = True
                            break
                    # Suporte a padrões com parâmetros (ex: /atividades/<id>)
                    elif '<' in perm_endpoint and '>' in perm_endpoint:
                        # Converter padrão Flask para regex
                        import re
                        pattern = perm_endpoint.replace('<int:', '<').replace('<uuid:', '<').replace('<', '').replace('>', '')
                        pattern_parts = pattern.split('/')
                        endpoint_parts = endpoint.split('/')
                        
                        if len(pattern_parts) == len(endpoint_parts):
                            matches = True
                            for p_part, e_part in zip(pattern_parts, endpoint_parts):
                                # Se a parte do padrão não é um parâmetro, deve ser exata
                                if p_part and not p_part.startswith(':'):
                                    if p_part != e_part:
                                        matches = False
                                        break
                            
                            if matches and (perm_method == '*' or perm_method == method):
                                has_permission = True
                                break
                    # Comparação exata
                    elif perm_endpoint == endpoint and (perm_method == '*' or perm_method == method):
                        has_permission = True
                        break
                    # Comparação sem parâmetros (ex: /atividades/123 vs /atividades/<id>)
                    elif perm_endpoint in endpoint and (perm_method == '*' or perm_method == method):
                        # Verificar se o endpoint começa com a permissão (para rotas com parâmetros)
                        if endpoint.startswith(perm_endpoint.rstrip('/')) or endpoint.startswith(perm_endpoint + '/'):
                            has_permission = True
                            break
                
                if not has_permission:
                    # Log de debug para permissões
                    print(f"❌ Token sem permissão!")
                    print(f"   Endpoint solicitado: {endpoint}")
                    print(f"   Método solicitado: {method}")
                    print(f"   Permissões do token:")
                    for perm_endpoint, perm_method in permissions:
                        print(f"     - {perm_endpoint} ({perm_method})")
                    
                    return jsonify({
                        'message': 'Token sem permissão para este endpoint!',
                        'endpoint': endpoint,
                        'method': method,
                        'permissions': [{'endpoint': p[0], 'method': p[1]} for p in permissions]
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
