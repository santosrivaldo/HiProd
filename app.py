
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

# Função para conectar ao banco de dados
def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        print(f"Tentando conectar com DATABASE_URL...")
        try:
            return psycopg2.connect(database_url)
        except psycopg2.OperationalError as e:
            print(f"Erro na conexão com DATABASE_URL: {e}")
            raise e
    else:
        # Fallback para variáveis individuais
        print(f"Tentando conectar com variáveis individuais...")
        try:
            return psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT", 5432)
            )
        except psycopg2.OperationalError as e:
            print(f"Erro na conexão com variáveis individuais: {e}")
            raise e

# Inicializar conexão global
conn = get_db_connection()
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

# Função para classificar atividade automaticamente
def classify_activity(active_window, ociosidade):
    # Buscar regras de classificação
    cursor.execute('''
    SELECT c.nome, c.tipo_produtividade 
    FROM regras_classificacao r 
    JOIN categorias_app c ON r.categoria_id = c.id 
    WHERE r.ativo = TRUE AND %s ILIKE '%' || r.pattern || '%'
    ORDER BY LENGTH(r.pattern) DESC 
    LIMIT 1;
    ''', (active_window,))
    
    result = cursor.fetchone()
    
    if result:
        categoria, produtividade = result
        return categoria, produtividade
    
    # Classificação baseada em ociosidade
    if ociosidade >= 600:  # 10 minutos
        return 'idle', 'nonproductive'
    elif ociosidade >= 300:  # 5 minutos
        return 'away', 'nonproductive'
    else:
        return 'unclassified', 'neutral'

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
    # Garantir que temos uma conexão ativa
    global conn, cursor
    try:
        cursor.execute('SELECT 1;')
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        conn = get_db_connection()
        cursor = conn.cursor()
    
    # Registrar adaptador para UUID
    psycopg2.extras.register_uuid()
    
    # Tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        nome VARCHAR(100) NOT NULL UNIQUE,
        senha VARCHAR(255) NOT NULL,
        email VARCHAR(255),
        ativo BOOLEAN DEFAULT TRUE,
        ultimo_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Tabela de atividades melhorada
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS atividades (
        id SERIAL PRIMARY KEY,
        usuario_id UUID NOT NULL,
        ociosidade INTEGER NOT NULL DEFAULT 0,
        active_window TEXT NOT NULL,
        titulo_janela VARCHAR(500),
        categoria VARCHAR(100) DEFAULT 'unclassified',
        produtividade VARCHAR(20) DEFAULT 'neutral',
        horario TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        duracao INTEGER DEFAULT 0,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
    );
    ''')

    # Tabela para categorias de aplicações
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categorias_app (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL UNIQUE,
        tipo_produtividade VARCHAR(20) NOT NULL CHECK (tipo_produtividade IN ('productive', 'nonproductive', 'neutral')),
        cor VARCHAR(7) DEFAULT '#6B7280',
        descricao TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Tabela para regras de classificação automática
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS regras_classificacao (
        id SERIAL PRIMARY KEY,
        pattern VARCHAR(255) NOT NULL,
        categoria_id INTEGER REFERENCES categorias_app(id),
        tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('window_title', 'application_name')),
        ativo BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Criar índices para melhor performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_usuario_id ON atividades(usuario_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_horario ON atividades(horario DESC);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_categoria ON atividades(categoria);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_nome ON usuarios(nome);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo);')

    # Inserir categorias padrão
    cursor.execute('''
    INSERT INTO categorias_app (nome, tipo_produtividade, cor, descricao) 
    VALUES 
        ('Desenvolvimento', 'productive', '#10B981', 'Atividades de programação e desenvolvimento'),
        ('Comunicação', 'productive', '#3B82F6', 'E-mails, mensagens e reuniões'),
        ('Navegação', 'neutral', '#F59E0B', 'Navegação web geral'),
        ('Entretenimento', 'nonproductive', '#EF4444', 'Jogos, vídeos e redes sociais'),
        ('Sistema', 'neutral', '#6B7280', 'Atividades do sistema operacional')
    ON CONFLICT (nome) DO NOTHING;
    ''')

    # Inserir regras de classificação padrão
    cursor.execute('''
    INSERT INTO regras_classificacao (pattern, categoria_id, tipo) 
    SELECT 'Visual Studio Code', id, 'application_name' FROM categorias_app WHERE nome = 'Desenvolvimento'
    UNION ALL
    SELECT 'Chrome', id, 'application_name' FROM categorias_app WHERE nome = 'Navegação'
    UNION ALL
    SELECT 'Outlook', id, 'application_name' FROM categorias_app WHERE nome = 'Comunicação'
    UNION ALL
    SELECT 'YouTube', id, 'window_title' FROM categorias_app WHERE nome = 'Entretenimento'
    ON CONFLICT DO NOTHING;
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

    # Classificar atividade automaticamente
    ociosidade = int(data.get('ociosidade', 0))
    active_window = data['active_window']
    categoria, produtividade = classify_activity(active_window, ociosidade)
    
    # Extrair informações adicionais
    titulo_janela = data.get('titulo_janela', active_window)
    duracao = data.get('duracao', 0)
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')

    # Adiciona a atividade no PostgreSQL
    cursor.execute('''
        INSERT INTO atividades 
        (usuario_id, ociosidade, active_window, titulo_janela, categoria, produtividade, 
         horario, duracao, ip_address, user_agent) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
        RETURNING id;
    ''', (
        str(current_user[0]), ociosidade, active_window, titulo_janela, 
        categoria, produtividade, datetime.now(timezone.utc), 
        duracao, ip_address, user_agent
    ))
    
    activity_id = cursor.fetchone()[0]
    conn.commit()
    
    return jsonify({
        'message': 'Atividade salva com sucesso!',
        'id': activity_id,
        'categoria': categoria,
        'produtividade': produtividade
    }), 201

# Rota para obter atividades (protegida)
@app.route('/atividades', methods=['GET'])
@token_required
def get_activities(current_user):
    # Parâmetros de filtro
    limite = request.args.get('limite', 100, type=int)
    categoria = request.args.get('categoria')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Construir query base
    query = '''
        SELECT a.id, a.usuario_id, a.ociosidade, a.active_window, a.titulo_janela,
               a.categoria, a.produtividade, a.horario, a.duracao, a.created_at
        FROM atividades a 
        WHERE a.usuario_id = %s
    '''
    params = [current_user[0]]
    
    # Adicionar filtros
    if categoria:
        query += ' AND a.categoria = %s'
        params.append(categoria)
    
    if data_inicio:
        query += ' AND a.horario >= %s'
        params.append(data_inicio)
    
    if data_fim:
        query += ' AND a.horario <= %s'
        params.append(data_fim)
    
    query += ' ORDER BY a.horario DESC LIMIT %s;'
    params.append(limite)
    
    cursor.execute(query, params)
    atividades = cursor.fetchall()
    
    result = [{
        'id': atividade[0], 
        'usuario_id': str(atividade[1]), 
        'ociosidade': atividade[2], 
        'active_window': atividade[3],
        'titulo_janela': atividade[4],
        'categoria': atividade[5],
        'produtividade': atividade[6],
        'horario': atividade[7].isoformat() if atividade[7] else None,
        'duracao': atividade[8],
        'created_at': atividade[9].isoformat() if atividade[9] else None
    } for atividade in atividades]
    
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

# Rota para obter categorias
@app.route('/categorias', methods=['GET'])
@token_required
def get_categories(current_user):
    cursor.execute("SELECT * FROM categorias_app ORDER BY nome;")
    categorias = cursor.fetchall()
    result = [{
        'id': cat[0], 
        'nome': cat[1], 
        'tipo_produtividade': cat[2], 
        'cor': cat[3], 
        'descricao': cat[4],
        'created_at': cat[5].isoformat() if cat[5] else None
    } for cat in categorias]
    return jsonify(result)

# Rota para criar nova categoria
@app.route('/categorias', methods=['POST'])
@token_required
def create_category(current_user):
    data = request.json
    
    if not data or 'nome' not in data or 'tipo_produtividade' not in data:
        return jsonify({'message': 'Nome e tipo de produtividade são obrigatórios!'}), 400
    
    nome = data['nome'].strip()
    tipo = data['tipo_produtividade']
    cor = data.get('cor', '#6B7280')
    descricao = data.get('descricao', '')
    
    if tipo not in ['productive', 'nonproductive', 'neutral']:
        return jsonify({'message': 'Tipo de produtividade inválido!'}), 400
    
    try:
        cursor.execute('''
            INSERT INTO categorias_app (nome, tipo_produtividade, cor, descricao) 
            VALUES (%s, %s, %s, %s) RETURNING id;
        ''', (nome, tipo, cor, descricao))
        category_id = cursor.fetchone()[0]
        conn.commit()
        
        return jsonify({
            'message': 'Categoria criada com sucesso!',
            'id': category_id
        }), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'message': 'Categoria já existe!'}), 409

# Rota para atualizar atividade (protegida)
@app.route('/atividades/<int:activity_id>', methods=['PATCH'])
@token_required
def update_activity(current_user, activity_id):
    data = request.json
    
    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400
    
    # Verificar se a atividade existe e pertence ao usuário
    cursor.execute('''
        SELECT id FROM atividades 
        WHERE id = %s AND usuario_id = %s;
    ''', (activity_id, current_user[0]))
    
    if not cursor.fetchone():
        return jsonify({'message': 'Atividade não encontrada!'}), 404
    
    # Campos que podem ser atualizados
    update_fields = []
    update_values = []
    
    if 'produtividade' in data:
        if data['produtividade'] not in ['productive', 'nonproductive', 'neutral', 'unclassified']:
            return jsonify({'message': 'Valor de produtividade inválido!'}), 400
        update_fields.append('produtividade = %s')
        update_values.append(data['produtividade'])
    
    if 'categoria' in data:
        update_fields.append('categoria = %s')
        update_values.append(data['categoria'])
    
    if not update_fields:
        return jsonify({'message': 'Nenhum campo para atualizar!'}), 400
    
    # Atualizar a atividade
    query = f'''
        UPDATE atividades 
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND usuario_id = %s;
    '''
    update_values.extend([activity_id, current_user[0]])
    
    cursor.execute(query, update_values)
    conn.commit()
    
    return jsonify({'message': 'Atividade atualizada com sucesso!'}), 200

# Rota para excluir atividade (protegida)
@app.route('/atividades/<int:activity_id>', methods=['DELETE'])
@token_required
def delete_activity(current_user, activity_id):
    # Verificar se a atividade existe e pertence ao usuário
    cursor.execute('''
        SELECT id FROM atividades 
        WHERE id = %s AND usuario_id = %s;
    ''', (activity_id, current_user[0]))
    
    if not cursor.fetchone():
        return jsonify({'message': 'Atividade não encontrada!'}), 404
    
    # Excluir a atividade
    cursor.execute('''
        DELETE FROM atividades 
        WHERE id = %s AND usuario_id = %s;
    ''', (activity_id, current_user[0]))
    
    conn.commit()
    
    return jsonify({'message': 'Atividade excluída com sucesso!'}), 200

# Rota para estatísticas avançadas
@app.route('/estatisticas', methods=['GET'])
@token_required
def get_statistics(current_user):
    # Estatísticas por categoria
    cursor.execute('''
        SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
               SUM(duracao) as tempo_total
        FROM atividades 
        WHERE usuario_id = %s 
        GROUP BY categoria 
        ORDER BY total DESC;
    ''', (current_user[0],))
    
    stats_por_categoria = cursor.fetchall()
    
    # Produtividade por dia da semana
    cursor.execute('''
        SELECT EXTRACT(DOW FROM horario) as dia_semana, 
               produtividade,
               COUNT(*) as total
        FROM atividades 
        WHERE usuario_id = %s 
        GROUP BY EXTRACT(DOW FROM horario), produtividade 
        ORDER BY dia_semana;
    ''', (current_user[0],))
    
    produtividade_semanal = cursor.fetchall()
    
    # Total de atividades hoje
    cursor.execute('''
        SELECT COUNT(*) 
        FROM atividades 
        WHERE usuario_id = %s 
        AND DATE(horario) = CURRENT_DATE;
    ''', (current_user[0],))
    
    atividades_hoje = cursor.fetchone()[0]
    
    return jsonify({
        'categorias': [{
            'categoria': stat[0],
            'total_atividades': stat[1],
            'media_ociosidade': float(stat[2]) if stat[2] else 0,
            'tempo_total': stat[3] if stat[3] else 0
        } for stat in stats_por_categoria],
        'produtividade_semanal': [{
            'dia_semana': int(stat[0]),
            'produtividade': stat[1],
            'total': stat[2]
        } for stat in produtividade_semanal],
        'atividades_hoje': atividades_hoje
    })

# Rota legacy para compatibilidade (será removida)
@app.route('/usuario', methods=['GET'])
def get_user_legacy():
    return jsonify({'message': 'Esta rota foi descontinuada. Use /login para autenticação.'}), 410

if __name__ == '__main__':
    try:
        # Verificar se o arquivo .env existe
        if not os.path.exists('.env'):
            print("❌ Arquivo .env não encontrado!")
            print("Copie o arquivo .env.example para .env e configure suas credenciais.")
            exit(1)
        
        # Verificar variáveis de ambiente essenciais
        database_url = os.getenv('DATABASE_URL')
        if not database_url and not all([os.getenv('DB_HOST'), os.getenv('DB_USER'), os.getenv('DB_PASSWORD')]):
            print("❌ Configurações do banco de dados não encontradas!")
            print("Configure DATABASE_URL ou DB_HOST, DB_USER, DB_PASSWORD no arquivo .env")
            exit(1)
        
        init_db()  # Inicializa o banco de dados
        print("✅ Banco de dados inicializado com sucesso!")
        print(f"🚀 Servidor rodando em http://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except psycopg2.OperationalError as e:
        print(f"❌ Erro de conexão com o banco PostgreSQL: {e}")
        print("\n📋 Checklist de verificação:")
        print("1. Verifique se o arquivo .env existe e está configurado")
        print("2. Confirme se as credenciais (usuário/senha) estão corretas")
        print("3. Verifique se o host e porta estão acessíveis")
        print("4. Confirme se o banco de dados existe")
        exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        exit(1)
