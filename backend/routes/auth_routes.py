
import uuid
import bcrypt
import jwt
import secrets
import urllib.parse
import requests
from flask import Blueprint, request, jsonify, redirect
from ..auth import generate_jwt_token, token_required, find_user_by_email_or_sso, create_usuario_from_sso_email
from ..database import DatabaseConnection
from ..config import Config
from ..utils import format_datetime_brasilia

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    # Registro desabilitado - apenas usuários cadastrados podem acessar
    return jsonify({'message': 'Registro de novos usuários está desabilitado. Contate o administrador.'}), 403


# ========== SSO (prioridade): nome = parte local do e-mail (ex: rivaldo.santos = rivaldo.santos@grupohi.com.br) ==========

@auth_bp.route('/sso/login', methods=['POST'])
def sso_login():
    """
    Login via SSO por e-mail. O usuário é identificado pelo e-mail corporativo.
    Regra: rivaldo.santos@grupohi.com.br corresponde ao usuário com nome 'rivaldo.santos' ou email igual.
    Body: { "email": "rivaldo.santos@grupohi.com.br" } ou { "email": "...", "id_token": "..." } para validação futura.
    """
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        if not email or '@' not in email:
            return jsonify({'message': 'E-mail é obrigatório para login SSO.'}), 400

        usuario = find_user_by_email_or_sso(email)
        if not usuario:
            usuario = create_usuario_from_sso_email(email)
        if not usuario:
            print(f"❌ SSO: usuário não encontrado para e-mail: {email}")
            return jsonify({'message': 'Usuário não encontrado. Cadastre-se no painel ou use o e-mail corporativo (ex: nome@grupohi.com.br).'}), 401

        # Atualizar último login e email se estava só por nome
        try:
            with DatabaseConnection() as db:
                db.cursor.execute(
                    'UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP, email = COALESCE(NULLIF(TRIM(email), \'\'), %s) WHERE id = %s;',
                    (email, usuario[0])
                )
        except Exception as e:
            print(f"⚠️ SSO: erro ao atualizar último login: {e}")

        token = generate_jwt_token(usuario[0])
        response_data = {
            'usuario_id': str(usuario[0]),
            'usuario': usuario[1],
            'token': token,
            'perfil': (usuario[5] if len(usuario) > 5 else 'colaborador') or 'colaborador'
        }
        print(f"🎉 Login SSO realizado: {usuario[1]} ({email})")
        return jsonify(response_data), 200
    except Exception as e:
        print(f"❌ Erro no login SSO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno no login SSO.'}), 500


def _sso_microsoft_authorization_url():
    """Gera URL para redirecionar o usuário ao login Microsoft."""
    client_id = (Config.SSO_MICROSOFT_CLIENT_ID or '').strip()
    redirect_uri = (Config.SSO_REDIRECT_URI or '').strip()
    tenant = (Config.SSO_MICROSOFT_TENANT or 'common').strip()
    if not client_id or not redirect_uri:
        return None
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'response_mode': 'query',
        'scope': 'openid email profile',
    }
    if tenant:
        params['tenant'] = tenant
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)


@auth_bp.route('/sso/url', methods=['GET'])
def sso_url():
    """Retorna a URL para iniciar o fluxo SSO (Microsoft). Se não configurado, retorna 404."""
    if not getattr(Config, 'SSO_ENABLED', True):
        return jsonify({'message': 'SSO desabilitado.'}), 404
    url = _sso_microsoft_authorization_url()
    if not url:
        return jsonify({'message': 'SSO Microsoft não configurado. Defina SSO_MICROSOFT_CLIENT_ID e SSO_REDIRECT_URI.'}), 404
    return jsonify({'url': url}), 200


@auth_bp.route('/sso/callback', methods=['GET'])
def sso_callback():
    """Callback OAuth2: troca o code por tokens e obtém o e-mail do usuário; emite JWT e redireciona ao frontend."""
    code = request.args.get('code')
    error = request.args.get('error')
    if error:
        print(f"❌ SSO callback error: {error}")
        front_url = request.args.get('state') or _frontend_url()
        return redirect(f"{front_url}?sso_error=1")
    if not code:
        return jsonify({'message': 'Código de autorização não recebido.'}), 400

    client_id = (Config.SSO_MICROSOFT_CLIENT_ID or '').strip()
    client_secret = (Config.SSO_MICROSOFT_CLIENT_SECRET or '').strip()
    redirect_uri = (Config.SSO_REDIRECT_URI or '').strip()
    tenant = (Config.SSO_MICROSOFT_TENANT or 'common').strip()
    if not client_id or not client_secret or not redirect_uri:
        return jsonify({'message': 'SSO não configurado.'}), 500

    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    scope = "openid email profile"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
        'scope': scope,
    }
    try:
        r = requests.post(token_url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=15)
        if not r.ok:
            err_body = r.text[:500] if r.text else ''
            try:
                err_json = r.json()
                err_desc = err_json.get('error_description', err_json.get('error', err_body))
            except Exception:
                err_desc = err_body
            print(f"❌ SSO token exchange failed: {r.status_code} - {err_desc}")
            print(f"   [Dica] redirect_uri no .env deve ser EXATAMENTE igual ao configurado no Azure (incl. barra final).")
            front_url = _frontend_url()
            return redirect(f"{front_url}?sso_error=1")
        data = r.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ SSO token exchange failed: {e}")
        if hasattr(e, 'response') and e.response is not None and getattr(e.response, 'text', None):
            print(f"   Response: {e.response.text[:300]}")
        front_url = _frontend_url()
        return redirect(f"{front_url}?sso_error=1")

    id_token = data.get('id_token')
    email = None
    if id_token:
        try:
            payload_jwt = jwt.decode(id_token, options={"verify_signature": False})
            email = (payload_jwt.get('email') or payload_jwt.get('preferred_username') or '').strip()
        except Exception:
            pass
    if not email or '@' not in email:
        print("❌ SSO: não foi possível obter e-mail do token.")
        front_url = _frontend_url()
        return redirect(f"{front_url}?sso_error=1")

    usuario = find_user_by_email_or_sso(email)
    if not usuario:
        usuario = create_usuario_from_sso_email(email)
    if not usuario:
        print(f"❌ SSO: usuário não encontrado para: {email}")
        front_url = _frontend_url()
        return redirect(f"{front_url}?sso_error=2")  # usuário não cadastrado

    try:
        with DatabaseConnection() as db:
            db.cursor.execute(
                'UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP, email = COALESCE(NULLIF(TRIM(email), \'\'), %s) WHERE id = %s;',
                (email, usuario[0])
            )
    except Exception:
        pass

    token = generate_jwt_token(usuario[0])
    front_url = _frontend_url()
    return redirect(f"{front_url}/auth/callback?token={urllib.parse.quote(token)}")


def _frontend_url():
    """URL base do frontend para redirecionamento pós-SSO."""
    url = (getattr(Config, 'FRONTEND_URL', None) or '').strip()
    if url:
        return url.rstrip('/')
    return (request.headers.get('X-Frontend-URL') or request.args.get('frontend_url') or '').split('?')[0].rstrip('/') or request.host_url.rstrip('/')


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        print(f"📝 Tentativa de login recebida: {data.get('nome', 'N/A') if data else 'Dados vazios'}")

        if not data or 'nome' not in data or 'senha' not in data:
            print("❌ Dados de login incompletos")
            return jsonify({'message': 'Nome de usuário e senha são obrigatórios!'}), 400

        nome = data['nome'].strip()
        senha = data['senha']

        if not nome or not senha:
            print("❌ Nome ou senha vazios")
            return jsonify({'message': 'Nome de usuário e senha não podem estar vazios!'}), 400

        with DatabaseConnection() as db:
            # Buscar usuário
            db.cursor.execute("SELECT id, nome, senha, email, departamento_id, ativo, COALESCE(perfil, 'colaborador') FROM usuarios WHERE nome = %s AND ativo = TRUE;", (nome,))
            usuario = db.cursor.fetchone()

            if not usuario:
                print(f"❌ Usuário não encontrado: {nome}")
                return jsonify({'message': 'Credenciais inválidas!'}), 401

            print(f"✅ Usuário encontrado: {usuario[1]} (ID: {usuario[0]})")

            # Verificar senha
            senha_hash = usuario[2]
            
            # Se a senha ainda não está hasheada (primeira vez ou dados de teste)
            if not isinstance(senha_hash, str) or not senha_hash.startswith('$2b$'):
                print("🔧 Senha não está hasheada, criando hash...")
                # Criar hash da senha fornecida para comparação
                senha_hash_novo = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Atualizar no banco
                db.cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s;", (senha_hash_novo, usuario[0]))
                senha_hash = senha_hash_novo
                print("✅ Hash da senha atualizado no banco")

            # Verificar senha
            try:
                senha_valida = bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
                
                if not senha_valida:
                    print(f"❌ Senha inválida para usuário: {nome}")
                    return jsonify({'message': 'Credenciais inválidas!'}), 401
                    
                print(f"✅ Login bem-sucedido para: {nome}")
                
            except Exception as verify_error:
                print(f"❌ Erro ao verificar senha: {verify_error}")
                return jsonify({'message': 'Erro interno do servidor. Tente novamente.'}), 500

            # Atualizar último login
            try:
                db.cursor.execute("UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP WHERE id = %s;", (usuario[0],))
            except Exception as update_error:
                print(f"⚠️ Erro ao atualizar último login: {update_error}")

            # Gerar token
            token = generate_jwt_token(usuario[0])

            response_data = {
                'usuario_id': str(usuario[0]),
                'usuario': usuario[1],
                'token': token,
                'perfil': (usuario[6] if len(usuario) > 6 else 'colaborador') or 'colaborador'
            }

            print(f"🎉 Login realizado com sucesso: {nome}")
            return jsonify(response_data), 200
            
    except Exception as e:
        print(f"❌ Erro crítico no login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor'}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    # current_user: id, nome, email, ativo, departamento_id, perfil
    return jsonify({
        'usuario_id': str(current_user[0]),
        'usuario': current_user[1],
        'perfil': (current_user[5] if len(current_user) > 5 else 'colaborador') or 'colaborador',
        'created_at': format_datetime_brasilia(current_user[6]) if len(current_user) > 6 and current_user[6] else None
    }), 200

@auth_bp.route('/verify-token', methods=['POST', 'OPTIONS'])
def verify_token_route():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    try:
        data = request.get_json()
        print(f"🔍 Verificação de token recebida: {bool(data)}")
        
        if not data:
            return jsonify({'valid': False, 'error': 'Dados não fornecidos'}), 200

        token = data.get('token')

        if not token:
            return jsonify({'valid': False, 'error': 'Token não fornecido'}), 200

        # Decodifica o token JWT
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        usuario_id = payload.get('user_id')

        if not usuario_id:
            return jsonify({'valid': False, 'error': 'Token mal formado'}), 200

        # Verifica se o usuário ainda existe
        with DatabaseConnection() as db:
            db.cursor.execute("SELECT nome, COALESCE(perfil, 'colaborador') FROM usuarios WHERE id = %s AND ativo = TRUE", (uuid.UUID(usuario_id),))
            result = db.cursor.fetchone()

            if result:
                print(f"✅ Token válido para usuário: {result[0]}")
                return jsonify({
                    'valid': True,
                    'usuario_id': usuario_id,
                    'usuario': result[0],
                    'perfil': (result[1] or 'colaborador')
                }), 200
            else:
                print(f"❌ Usuário não encontrado para token: {usuario_id}")
                return jsonify({'valid': False, 'error': 'Usuário não encontrado'}), 200

    except jwt.ExpiredSignatureError:
        print("❌ Token expirado")
        return jsonify({'valid': False, 'error': 'Token expirado'}), 200
    except jwt.InvalidTokenError:
        print("❌ Token inválido")
        return jsonify({'valid': False, 'error': 'Token inválido'}), 200
    except Exception as e:
        print(f"❌ Erro ao verificar token: {e}")
        return jsonify({'valid': False, 'error': f'Erro interno: {str(e)}'}), 200
