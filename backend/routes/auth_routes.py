
import uuid
import bcrypt
import jwt
from flask import Blueprint, request, jsonify
from ..auth import generate_token, token_required
from ..database import DatabaseConnection
from ..config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json

    if not data or 'nome' not in data or 'senha' not in data:
        return jsonify({'message': 'Nome de usuário e senha são obrigatórios!'}), 400

    nome = data['nome'].strip()
    senha = data['senha']

    if len(nome) < 3:
        return jsonify({'message': 'Nome de usuário deve ter pelo menos 3 caracteres!'}), 400

    if len(senha) < 6:
        return jsonify({'message': 'Senha deve ter pelo menos 6 caracteres!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário já existe
            db.cursor.execute("SELECT * FROM usuarios WHERE nome = %s;", (nome,))
            if db.cursor.fetchone():
                return jsonify({'message': 'Usuário já existe!'}), 409

            # Hash da senha
            hashed_password = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())

            # Criar novo usuário
            new_user_id = uuid.uuid4()
            db.cursor.execute(
                "INSERT INTO usuarios (id, nome, senha) VALUES (%s, %s, %s);",
                (new_user_id, nome, hashed_password.decode('utf-8'))
            )

            # Gerar token
            token = generate_token(new_user_id)

            return jsonify({
                'message': 'Usuário criado com sucesso!',
                'usuario_id': str(new_user_id),
                'usuario': nome,
                'token': token
            }), 201
    except Exception as e:
        print(f"Erro ao registrar usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

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
            db.cursor.execute("SELECT id, nome, senha, email, departamento_id, ativo FROM usuarios WHERE nome = %s AND ativo = TRUE;", (nome,))
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
            token = generate_token(usuario[0])

            response_data = {
                'usuario_id': str(usuario[0]),
                'usuario': usuario[1],
                'token': token
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
    return jsonify({
        'usuario_id': str(current_user[0]),
        'usuario': current_user[1],
        'created_at': current_user[6].isoformat() if len(current_user) > 6 and current_user[6] else None
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
            db.cursor.execute("SELECT nome FROM usuarios WHERE id = %s AND ativo = TRUE", (uuid.UUID(usuario_id),))
            result = db.cursor.fetchone()

            if result:
                print(f"✅ Token válido para usuário: {result[0]}")
                return jsonify({
                    'valid': True,
                    'usuario_id': usuario_id,
                    'usuario': result[0]
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
