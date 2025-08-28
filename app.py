
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import uuid
from datetime import datetime, timedelta
from datetime import timezone
import psycopg2.extras
from dotenv import load_dotenv
import os
import jwt
import bcrypt
from functools import wraps

# Carregar variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuração JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Configurando a conexão com o PostgreSQL usando variáveis de ambiente
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

# Registrando o adaptador para UUID
psycopg2.extras.register_uuid()

# Função para gerar token JWT
def generate_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

# Função para verificar token JWT
def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Decorator para rotas protegidas
def token_required(f):
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
        
        # Verificar se o usuário ainda existe
        cursor.execute("SELECT * FROM usuarios WHERE id = %s;", (uuid.UUID(user_id),))
        current_user = cursor.fetchone()
        if not current_user:
            return jsonify({'message': 'Usuário não encontrado!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# Função para inicializar as tabelas se não existirem
def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id UUID PRIMARY KEY,
        nome VARCHAR(100) NOT NULL UNIQUE,
        senha VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS atividades (
        id SERIAL PRIMARY KEY,
        usuario_id UUID NOT NULL,
        ociosidade TEXT NOT NULL,
        active_window TEXT NOT NULL,
        horario TIMESTAMP NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    );
    ''')
    conn.commit()

# Rota para registro de usuário
@app.route('/register', methods=['POST'])
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
    
    # Verificar se o usuário já existe
    cursor.execute("SELECT * FROM usuarios WHERE nome = %s;", (nome,))
    if cursor.fetchone():
        return jsonify({'message': 'Usuário já existe!'}), 409
    
    # Hash da senha
    hashed_password = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    
    # Criar novo usuário
    new_user_id = uuid.uuid4()
    cursor.execute(
        "INSERT INTO usuarios (id, nome, senha) VALUES (%s, %s, %s);",
        (str(new_user_id), nome, hashed_password.decode('utf-8'))
    )
    conn.commit()
    
    # Gerar token
    token = generate_token(new_user_id)
    
    return jsonify({
        'message': 'Usuário criado com sucesso!',
        'usuario_id': str(new_user_id),
        'usuario': nome,
        'token': token
    }), 201

# Rota para login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    
    if not data or 'nome' not in data or 'senha' not in data:
        return jsonify({'message': 'Nome de usuário e senha são obrigatórios!'}), 400
    
    nome = data['nome'].strip()
    senha = data['senha']
    
    # Buscar usuário
    cursor.execute("SELECT * FROM usuarios WHERE nome = %s;", (nome,))
    usuario = cursor.fetchone()
    
    if not usuario:
        return jsonify({'message': 'Credenciais inválidas!'}), 401
    
    # Verificar senha
    if not bcrypt.checkpw(senha.encode('utf-8'), usuario[2].encode('utf-8')):
        return jsonify({'message': 'Credenciais inválidas!'}), 401
    
    # Gerar token
    token = generate_token(usuario[0])
    
    return jsonify({
        'usuario_id': str(usuario[0]),
        'usuario': usuario[1],
        'token': token
    }), 200

# Rota para obter perfil do usuário (protegida)
@app.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'usuario_id': str(current_user[0]),
        'usuario': current_user[1],
        'created_at': current_user[3].isoformat() if current_user[3] else None
    }), 200

# Rota para verificar token
@app.route('/verify-token', methods=['POST'])
def verify_token_route():
    data = request.json
    if not data or 'token' not in data:
        return jsonify({'valid': False}), 400
    
    user_id = verify_token(data['token'])
    if user_id:
        cursor.execute("SELECT * FROM usuarios WHERE id = %s;", (uuid.UUID(user_id),))
        usuario = cursor.fetchone()
        if usuario:
            return jsonify({
                'valid': True,
                'usuario_id': str(usuario[0]),
                'usuario': usuario[1]
            }), 200
    
    return jsonify({'valid': False}), 401

# Rota para adicionar atividade (protegida)
@app.route('/atividade', methods=['POST'])
@token_required
def add_activity(current_user):
    data = request.json
    
    # Valida se os dados necessários estão presentes
    if 'ociosidade' not in data or 'active_window' not in data:
        return jsonify({'message': 'Dados inválidos!'}), 400

    # Adiciona a atividade no PostgreSQL usando o ID do usuário autenticado
    cursor.execute(
        "INSERT INTO atividades (usuario_id, ociosidade, active_window, horario) VALUES (%s, %s, %s, %s);",
        (str(current_user[0]), data['ociosidade'], data['active_window'], datetime.now(timezone.utc))
    )
    conn.commit()
    
    return jsonify({'message': 'Atividade salva com sucesso!'}), 201

# Rota para obter atividades (protegida)
@app.route('/atividades', methods=['GET'])
@token_required
def get_activities(current_user):
    cursor.execute("SELECT * FROM atividades WHERE usuario_id = %s ORDER BY horario DESC;", (current_user[0],))
    atividades = cursor.fetchall()
    result = [{'id': atividade[0], 'usuario_id': str(atividade[1]), 'ociosidade': atividade[2], 'active_window': atividade[3], 'horario': atividade[4]} for atividade in atividades]
    return jsonify(result)

# Rota para obter todas as atividades (admin - para compatibilidade)
@app.route('/atividades/all', methods=['GET'])
@token_required
def get_all_activities(current_user):
    cursor.execute("SELECT * FROM atividades ORDER BY horario DESC;")
    atividades = cursor.fetchall()
    result = [{'id': atividade[0], 'usuario_id': str(atividade[1]), 'ociosidade': atividade[2], 'active_window': atividade[3], 'horario': atividade[4]} for atividade in atividades]
    return jsonify(result)

# Rota para obter usuários (protegida)
@app.route('/usuarios', methods=['GET'])
@token_required
def get_users(current_user):
    cursor.execute("SELECT id, nome, created_at FROM usuarios;")
    usuarios = cursor.fetchall()
    result = [{'usuario_id': str(usuario[0]), 'usuario': usuario[1], 'created_at': usuario[2].isoformat() if usuario[2] else None} for usuario in usuarios]
    return jsonify(result)

# Rota legacy para compatibilidade (será removida)
@app.route('/usuario', methods=['GET'])
def get_user_legacy():
    return jsonify({'message': 'Esta rota foi descontinuada. Use /login para autenticação.'}), 410

if __name__ == '__main__':
    init_db()  # Inicializa o banco de dados
    app.run(host='0.0.0.0', port=5000, debug=True)
