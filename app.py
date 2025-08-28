from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.pool
import uuid
from datetime import datetime, timedelta
from datetime import timezone
import psycopg2.extras
from dotenv import load_dotenv
import os
import jwt
import bcrypt
from functools import wraps
import threading
import time

# Carregar variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuração JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Pool de conexões global
connection_pool = None
pool_lock = threading.Lock()

# Função para criar o pool de conexões
def create_connection_pool():
    global connection_pool
    database_url = os.getenv('DATABASE_URL')

    # Configurações do pool
    min_connections = 2
    max_connections = 20

    if database_url:
        print(f"🔌 Criando pool de conexões com DATABASE_URL... (min: {min_connections}, max: {max_connections})")
        try:
            # Modificar URL para usar connection pooler do Neon se disponível
            if '.neon.tech' in database_url and '-pooler' not in database_url:
                pooled_url = database_url.replace('.neon.tech', '-pooler.neon.tech')
                print("🔄 Usando Neon connection pooler...")
            else:
                pooled_url = database_url

            return psycopg2.pool.ThreadedConnectionPool(
                min_connections, max_connections, pooled_url
            )
        except psycopg2.OperationalError as e:
            print(f"❌ Erro ao criar pool com DATABASE_URL: {e}")
            print("🔄 Tentando com URL original...")
            return psycopg2.pool.ThreadedConnectionPool(
                min_connections, max_connections, database_url
            )
    else:
        # Fallback para variáveis individuais
        print(f"🔌 Criando pool com variáveis individuais... (min: {min_connections}, max: {max_connections})")
        try:
            return psycopg2.pool.ThreadedConnectionPool(
                min_connections, max_connections,
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT", 5432)
            )
        except psycopg2.OperationalError as e:
            print(f"❌ Erro ao criar pool com variáveis individuais: {e}")
            raise e

# Context manager para obter conexões do pool
class DatabaseConnection:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        global connection_pool
        with pool_lock:
            if connection_pool is None:
                connection_pool = create_connection_pool()

            try:
                self.conn = connection_pool.getconn()
                if self.conn:
                    # Registrar adaptador UUID para esta conexão
                    psycopg2.extras.register_uuid(conn_or_curs=self.conn)
                    self.cursor = self.conn.cursor()
                    # Testar a conexão
                    self.cursor.execute('SELECT 1;')
                    self.cursor.fetchone()
                    return self
                else:
                    raise psycopg2.OperationalError("Não foi possível obter conexão do pool")
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"⚠️ Erro ao obter conexão do pool: {e}")
                if self.conn:
                    try:
                        connection_pool.putconn(self.conn, close=True)
                    except:
                        pass
                # Tentar recriar o pool
                try:
                    connection_pool.closeall()
                    connection_pool = create_connection_pool()
                    self.conn = connection_pool.getconn()
                    psycopg2.extras.register_uuid(conn_or_curs=self.conn)
                    self.cursor = self.conn.cursor()
                    return self
                except Exception as reconnect_error:
                    print(f"❌ Falha na reconexão: {reconnect_error}")
                    raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        global connection_pool
        if self.cursor:
            try:
                self.cursor.close()
            except:
                pass

        if self.conn and connection_pool:
            try:
                if exc_type:
                    self.conn.rollback()
                else:
                    self.conn.commit()
                connection_pool.putconn(self.conn)
            except Exception as e:
                print(f"⚠️ Erro ao retornar conexão para o pool: {e}")
                try:
                    connection_pool.putconn(self.conn, close=True)
                except:
                    pass

# Função para obter conexão simples (para compatibilidade)
def get_db_connection():
    global connection_pool
    with pool_lock:
        if connection_pool is None:
            connection_pool = create_connection_pool()
        return connection_pool.getconn()

# Função para gerar token JWT
def generate_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.now(timezone.utc) + app.config['JWT_ACCESS_TOKEN_EXPIRES']
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

# Função para classificar atividade automaticamente usando tags
def classify_activity_with_tags(active_window, ociosidade, user_department_id=None, activity_id=None):
    try:
        print(f"🏷️ Classificando com tags - window: {active_window}, dept_id: {user_department_id}")

        with DatabaseConnection() as db:
            # Buscar tags ativas - primeiro do departamento específico, depois globais
            if user_department_id:
                db.cursor.execute('''
                SELECT t.id, t.nome, t.produtividade, tk.palavra_chave, tk.peso
                FROM tags t
                JOIN tag_palavras_chave tk ON t.id = tk.tag_id
                WHERE t.ativo = TRUE AND (t.departamento_id = %s OR t.departamento_id IS NULL)
                ORDER BY t.departamento_id NULLS LAST, tk.peso DESC;
                ''', (user_department_id,))
            else:
                # Buscar apenas tags globais
                db.cursor.execute('''
                SELECT t.id, t.nome, t.produtividade, tk.palavra_chave, tk.peso
                FROM tags t
                JOIN tag_palavras_chave tk ON t.id = tk.tag_id
                WHERE t.ativo = TRUE AND t.departamento_id IS NULL
                ORDER BY tk.peso DESC;
                ''')

            tag_matches = db.cursor.fetchall()
            matched_tags = []

            for tag_match in tag_matches:
                # Verificar se temos todos os campos necessários
                if len(tag_match) < 5:
                    continue
                tag_id, tag_nome, tag_produtividade, palavra_chave, peso = tag_match
                # Verificar se a palavra-chave está presente no título da janela (case insensitive)
                if palavra_chave.lower() in active_window.lower():
                    # Calcular confidence baseado no peso e na proporção da palavra-chave
                    confidence = peso * (len(palavra_chave) / len(active_window)) * 100
                    matched_tags.append({
                        'tag_id': tag_id,
                        'nome': tag_nome,
                        'produtividade': tag_produtividade,
                        'confidence': confidence,
                        'palavra_chave': palavra_chave,
                        'peso': peso
                    })

                    print(f"🎯 Match encontrado: '{palavra_chave}' -> Tag '{tag_nome}' (confidence: {confidence:.2f}, peso: {peso})")

            # Se temos múltiplas tags, escolher a de maior peso (menor tier/maior prioridade)
            if matched_tags:
                # Ordenar por peso DESC (maior peso = maior prioridade)
                best_match = max(matched_tags, key=lambda x: x['peso'])
                print(f"🏷️ Melhor match por peso: '{best_match['nome']}' (peso: {best_match['peso']}, produtividade: {best_match['produtividade']})")

                # Se temos um ID da atividade, salvar apenas a melhor associação
                if activity_id:
                    with DatabaseConnection() as db_save:
                        db_save.cursor.execute('''
                        INSERT INTO atividade_tags (atividade_id, tag_id, confidence)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (atividade_id, tag_id) DO UPDATE SET confidence = EXCLUDED.confidence;
                        ''', (activity_id, best_match['tag_id'], best_match['confidence']))

                # A categoria agora será o nome da tag
                return best_match['nome'], best_match['produtividade']

    except Exception as e:
        print(f"❌ Erro na classificação com tags: {e}")
        # Retornar fallback em caso de erro
        if ociosidade >= 600:
            return 'Ocioso', 'nonproductive'
        elif ociosidade >= 300:
            return 'Ausente', 'nonproductive'
        else:
            return 'Não Classificado', 'neutral'

    # Fallback para classificação por ociosidade se nenhuma tag foi encontrada
    print(f"🔍 Nenhuma tag encontrada, usando classificação por ociosidade: {ociosidade}")
    if ociosidade >= 600:  # 10 minutos
        return 'Ocioso', 'nonproductive'
    elif ociosidade >= 300:  # 5 minutos
        return 'Ausente', 'nonproductive'
    else:
        return 'Não Classificado', 'neutral'

# Manter função antiga para compatibilidade
def classify_activity(active_window, ociosidade, user_department_id=None):
    return classify_activity_with_tags(active_window, ociosidade, user_department_id)

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

# Função para deletar todas as tabelas
def drop_all_tables():
    try:
        print("🗑️ Excluindo todas as tabelas existentes...")

        with DatabaseConnection() as db:
            # Desabilitar verificações de foreign key temporariamente
            db.cursor.execute("SET session_replication_role = replica;")

            # Listar todas as tabelas do usuário
            db.cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
            """)
            tables = db.cursor.fetchall()

            # Excluir todas as tabelas
            for table in tables:
                table_name = table[0]
                print(f"   Excluindo tabela: {table_name}")
                db.cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")

            # Reabilitar verificações de foreign key
            db.cursor.execute("SET session_replication_role = DEFAULT;")

        print("✅ Todas as tabelas foram excluídas!")

    except Exception as e:
        print(f"❌ Erro ao excluir tabelas: {e}")
        raise

# Função para inicializar as tabelas se não existirem
def init_db():
    try:
        print("🔧 Inicializando estrutura do banco de dados...")

        with DatabaseConnection() as db:
            # 1. Primeiro criar tabela de departamentos
            print("📋 Criando tabela de departamentos...")
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS departamentos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL UNIQUE,
                descricao TEXT,
                cor VARCHAR(7) DEFAULT '#6B7280',
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            print("✅ Tabela departamentos criada")

            # 2. Inserir departamentos padrão
            print("📋 Inserindo departamentos padrão...")
            db.cursor.execute('''
            INSERT INTO departamentos (nome, descricao, cor)
            VALUES
                ('TI', 'Tecnologia da Informação', '#10B981'),
                ('Marketing', 'Marketing e Comunicação', '#3B82F6'),
                ('RH', 'Recursos Humanos', '#F59E0B'),
                ('Financeiro', 'Departamento Financeiro', '#EF4444'),
                ('Vendas', 'Departamento de Vendas', '#8B5CF6'),
                ('Geral', 'Categorias gerais para todos os departamentos', '#6B7280')
            ON CONFLICT (nome) DO NOTHING;
            ''')
            print("✅ Departamentos padrão inseridos")

            # 3. Verificar se tabela usuarios existe e criar com departamento_id
            db.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'usuarios'
                );
            """)
            usuarios_table_exists = db.cursor.fetchone()[0]

            if usuarios_table_exists:
                print("📋 Tabela usuarios já existe, verificando coluna departamento_id...")
                # Verificar se coluna departamento_id existe
                db.cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='usuarios' AND column_name='departamento_id';
                """)

                if not db.cursor.fetchone():
                    print("🔧 Adicionando coluna departamento_id à tabela usuarios...")
                    db.cursor.execute("ALTER TABLE usuarios ADD COLUMN departamento_id INTEGER;")
                    db.cursor.execute("ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_departamento FOREIGN KEY (departamento_id) REFERENCES departamentos(id);")
                    print("✅ Coluna departamento_id adicionada com sucesso!")
                else:
                    print("✅ Coluna departamento_id já existe")
            else:
                print("📋 Criando tabela usuarios com departamento_id...")
                # Criar tabela usuarios do zero com departamento_id
                db.cursor.execute('''
                CREATE TABLE usuarios (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    senha VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    departamento_id INTEGER REFERENCES departamentos(id),
                    ativo BOOLEAN DEFAULT TRUE,
                    ultimo_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                ''')
                print("✅ Tabela usuarios criada com departamento_id")

            # 4. Criar demais tabelas
            print("📋 Criando tabelas auxiliares...")

            # Tabela de usuários monitorados
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios_monitorados (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL UNIQUE,
                departamento_id INTEGER REFERENCES departamentos(id),
                cargo VARCHAR(100),
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''')

            # Tabela de categorias de aplicações
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias_app (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                departamento_id INTEGER REFERENCES departamentos(id),
                tipo_produtividade VARCHAR(20) NOT NULL CHECK (tipo_produtividade IN ('productive', 'nonproductive', 'neutral')),
                cor VARCHAR(7) DEFAULT '#6B7280',
                descricao TEXT,
                is_global BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nome, departamento_id)
            );
            ''')

            # Tabela para regras de classificação automática
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS regras_classificacao (
                id SERIAL PRIMARY KEY,
                pattern VARCHAR(255) NOT NULL,
                categoria_id INTEGER REFERENCES categorias_app(id),
                departamento_id INTEGER REFERENCES departamentos(id),
                tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('window_title', 'application_name')),
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''')

            # Tabela de tags
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                descricao TEXT,
                cor VARCHAR(7) DEFAULT '#6B7280',
                produtividade VARCHAR(20) NOT NULL CHECK (produtividade IN ('productive', 'nonproductive', 'neutral')),
                departamento_id INTEGER REFERENCES departamentos(id),
                tier INTEGER DEFAULT 3 CHECK (tier >= 1 AND tier <= 5),
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nome, departamento_id)
            );
            ''')
            
            # Verificar se coluna tier existe na tabela tags, se não, adicionar
            db.cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='tags' AND column_name='tier';
            """)
            
            if not db.cursor.fetchone():
                print("🔧 Adicionando coluna tier à tabela tags...")
                db.cursor.execute("ALTER TABLE tags ADD COLUMN tier INTEGER DEFAULT 3 CHECK (tier >= 1 AND tier <= 5);")
                print("✅ Coluna tier adicionada com sucesso!")

            # Tabela de palavras-chave das tags
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tag_palavras_chave (
                id SERIAL PRIMARY KEY,
                tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                palavra_chave VARCHAR(255) NOT NULL,
                peso INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tag_id, palavra_chave)
            );
            ''')

            # Tabela para configurações de departamento
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS departamento_configuracoes (
                id SERIAL PRIMARY KEY,
                departamento_id INTEGER REFERENCES departamentos(id),
                configuracao_chave VARCHAR(100) NOT NULL,
                configuracao_valor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(departamento_id, configuracao_chave)
            );
            ''')

            # Tabela de atividades (criar após usuarios_monitorados)
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS atividades (
                id SERIAL PRIMARY KEY,
                usuario_monitorado_id INTEGER NOT NULL,
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
                FOREIGN KEY (usuario_monitorado_id) REFERENCES usuarios_monitorados (id) ON DELETE CASCADE
            );
            ''')

            # Tabela para associar atividades com tags (criar após atividades)
            db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS atividade_tags (
                id SERIAL PRIMARY KEY,
                atividade_id INTEGER REFERENCES atividades(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                confidence FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(atividade_id, tag_id)
            );
            ''')

            print("✅ Todas as tabelas criadas")

            # 5. Criar índices para melhor performance
            print("📋 Criando índices...")
            indices = [
                'CREATE INDEX IF NOT EXISTS idx_atividades_usuario_monitorado_id ON atividades(usuario_monitorado_id);',
                'CREATE INDEX IF NOT EXISTS idx_atividades_horario ON atividades(horario DESC);',
                'CREATE INDEX IF NOT EXISTS idx_atividades_categoria ON atividades(categoria);',
                'CREATE INDEX IF NOT EXISTS idx_usuarios_nome ON usuarios(nome);',
                'CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo);',
                'CREATE INDEX IF NOT EXISTS idx_usuarios_monitorados_nome ON usuarios_monitorados(nome);',
                'CREATE INDEX IF NOT EXISTS idx_departamentos_nome ON departamentos(nome);',
                'CREATE INDEX IF NOT EXISTS idx_categorias_departamento ON categorias_app(departamento_id);',
                'CREATE INDEX IF NOT EXISTS idx_tags_departamento ON tags(departamento_id);',
                'CREATE INDEX IF NOT EXISTS idx_tags_ativo ON tags(ativo);',
                'CREATE INDEX IF NOT EXISTS idx_tag_palavras_chave_tag_id ON tag_palavras_chave(tag_id);',
                'CREATE INDEX IF NOT EXISTS idx_atividade_tags_atividade_id ON atividade_tags(atividade_id);',
                'CREATE INDEX IF NOT EXISTS idx_atividade_tags_tag_id ON atividade_tags(tag_id);'
            ]

            for indice in indices:
                db.cursor.execute(indice)

            # 6. Inserir dados padrão
            print("📋 Inserindo dados padrão...")

            # Inserir tags padrão
            print("📋 Inserindo tags padrão...")
            # Primeiro, verificar se já existem tags para evitar duplicatas
            db.cursor.execute("SELECT COUNT(*) FROM tags;")
            tag_count_result = db.cursor.fetchone()
            tag_count = tag_count_result[0] if tag_count_result else 0

            if tag_count == 0:
                # Inserir tags uma por vez para evitar problemas
                tags_to_insert = [
                    ('Desenvolvimento Web', 'Desenvolvimento de aplicações web', 'productive', 'TI', '#10B981'),
                    ('Banco de Dados', 'Administração e desenvolvimento de bancos de dados', 'productive', 'TI', '#059669'),
                    ('Design UI/UX', 'Design de interfaces e experiência do usuário', 'productive', 'Marketing', '#8B5CF6'),
                    ('Análise de Dados', 'Análise e processamento de dados', 'productive', 'Financeiro', '#3B82F6'),
                    ('Redes Sociais', 'Gerenciamento de mídias sociais', 'productive', 'Marketing', '#EC4899'),
                    ('Entretenimento', 'Atividades de entretenimento e lazer', 'nonproductive', None, '#EF4444'),
                    ('Comunicação', 'Ferramentas de comunicação e colaboração', 'productive', None, '#06B6D4'),
                    ('Navegação Web', 'Navegação geral na internet', 'neutral', None, '#F59E0B')
                ]

                for tag_nome, tag_desc, tag_prod, dept_nome, tag_cor in tags_to_insert:
                    if dept_nome:
                        db.cursor.execute('''
                        INSERT INTO tags (nome, descricao, produtividade, departamento_id, cor)
                        SELECT %s, %s, %s, d.id, %s
                        FROM departamentos d WHERE d.nome = %s
                        ON CONFLICT (nome, departamento_id) DO NOTHING;
                        ''', (tag_nome, tag_desc, tag_prod, tag_cor, dept_nome))
                    else:
                        db.cursor.execute('''
                        INSERT INTO tags (nome, descricao, produtividade, departamento_id, cor)
                        VALUES (%s, %s, %s, NULL, %s)
                        ON CONFLICT (nome, departamento_id) DO NOTHING;
                        ''', (tag_nome, tag_desc, tag_prod, tag_cor))
            else:
                print("⏭️ Tags já existem, pulando inserção...")

            # Inserir palavras-chave para as tags
            db.cursor.execute("SELECT COUNT(*) FROM tag_palavras_chave;")
            keyword_count_result = db.cursor.fetchone()
            keyword_count = keyword_count_result[0] if keyword_count_result else 0

            if keyword_count == 0:
                # Inserir palavras-chave uma por vez
                keywords_data = [
                    ('Desenvolvimento Web', ['Visual Studio Code', 'VS Code', 'GitHub', 'React', 'Node.js', 'Replit'], [5, 5, 4, 4, 4, 5]),
                    ('Banco de Dados', ['pgAdmin', 'PostgreSQL', 'MySQL', 'MongoDB'], [5, 4, 4, 4]),
                    ('Design UI/UX', ['Figma', 'Adobe XD', 'Photoshop'], [5, 5, 4]),
                    ('Análise de Dados', ['Excel', 'Power BI'], [5, 5]),
                    ('Redes Sociais', ['Instagram', 'Facebook', 'LinkedIn'], [4, 4, 4]),
                    ('Entretenimento', ['YouTube', 'Netflix', 'Spotify'], [3, 3, 3]),
                    ('Comunicação', ['WhatsApp', 'Slack', 'Teams', 'Zoom'], [4, 4, 4, 4]),
                    ('Navegação Web', ['Google Chrome', 'Firefox', 'Edge'], [3, 3, 3])
                ]

                for tag_nome, palavras, pesos in keywords_data:
                    db.cursor.execute("SELECT id FROM tags WHERE nome = %s;", (tag_nome,))
                    tag_result = db.cursor.fetchone()
                    if tag_result:
                        tag_id = tag_result[0]
                        for palavra, peso in zip(palavras, pesos):
                            db.cursor.execute('''
                            INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (tag_id, palavra_chave) DO NOTHING;
                            ''', (tag_id, palavra, peso))
            else:
                print("⏭️ Palavras-chave já existem, pulando inserção...")

        print("✅ Todos os dados padrão inseridos")
        print("🎉 Banco de dados inicializado com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante inicialização: {e}")
        raise

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

# Rota para login
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json

        if not data or 'nome' not in data or 'senha' not in data:
            return jsonify({'message': 'Nome de usuário e senha são obrigatórios!'}), 400

        nome = data['nome'].strip()
        senha = data['senha']

        with DatabaseConnection() as db:
            # Buscar usuário
            db.cursor.execute("SELECT * FROM usuarios WHERE nome = %s;", (nome,))
            usuario = db.cursor.fetchone()

            if not usuario:
                return jsonify({'message': 'Credenciais inválidas!'}), 401

            # Verificar senha - lidar com diferentes tipos de dados
            senha_hash = usuario[2]
            if isinstance(senha_hash, bool):
                # Se a senha foi armazenada como boolean, recriar o hash
                senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                # Atualizar no banco com o hash correto
                db.cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s;", (senha_hash, usuario[0]))
            elif isinstance(senha_hash, str):
                # Verificar se é um hash válido
                if not senha_hash.startswith('$2b$'):
                    # Se não é um hash bcrypt válido, criar um novo
                    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    db.cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s;", (senha_hash, usuario[0]))

            # Verificar senha
            try:
                if not bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
                    return jsonify({'message': 'Credenciais inválidas!'}), 401
            except (ValueError, TypeError):
                return jsonify({'message': 'Erro interno do servidor. Tente novamente.'}), 500

            # Gerar token
            token = generate_token(usuario[0])

            return jsonify({
                'usuario_id': str(usuario[0]),
                'usuario': usuario[1],
                'token': token
            }), 200
    except Exception as e:
        print(f"Erro na preparação do login: {e}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

# Rota para obter perfil do usuário (protegida)
@app.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'usuario_id': str(current_user[0]),
        'usuario': current_user[1],
        'created_at': current_user[6].isoformat() if len(current_user) > 6 and current_user[6] else None
    }), 200

# Rota para verificar token
@app.route('/verify-token', methods=['POST'])
def verify_token_route():
    data = request.json
    if not data or 'token' not in data:
        return jsonify({'valid': False}), 400

    user_id = verify_token(data['token'])
    if user_id:
        try:
            with DatabaseConnection() as db:
                db.cursor.execute("SELECT * FROM usuarios WHERE id = %s;", (uuid.UUID(user_id),))
                usuario = db.cursor.fetchone()
                if usuario:
                    return jsonify({
                        'valid': True,
                        'usuario_id': str(usuario[0]),
                        'usuario': usuario[1]
                    }), 200
        except Exception as e:
            print(f"Erro ao verificar token: {e}")

    return jsonify({'valid': False}), 401

# Rota para adicionar atividade (protegida)
@app.route('/atividade', methods=['POST'])
@token_required
def add_activity(current_user):
    try:
        data = request.json
        print(f"📥 Recebendo atividade: {data}")

        # Valida se os dados necessários estão presentes
        if not data:
            print("❌ Nenhum dado JSON recebido")
            return jsonify({'message': 'Dados JSON não fornecidos!'}), 400

        required_fields = ['ociosidade', 'active_window', 'usuario_monitorado_id']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            print(f"❌ Campos obrigatórios ausentes: {missing_fields}")
            return jsonify({
                'message': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}',
                'required_fields': required_fields,
                'received_data': list(data.keys()) if data else []
            }), 400

        usuario_monitorado_id = data['usuario_monitorado_id']

        with DatabaseConnection() as db:
            # Verificar se o usuário monitorado existe
            db.cursor.execute("""
                SELECT id, nome, departamento_id, cargo, ativo, created_at, updated_at
                FROM usuarios_monitorados
                WHERE id = %s AND ativo = TRUE;
            """, (usuario_monitorado_id,))
            usuario_monitorado = db.cursor.fetchone()

            if not usuario_monitorado:
                print(f"❌ Usuário monitorado não encontrado: ID {usuario_monitorado_id}")
                return jsonify({
                    'message': f'Usuário monitorado não encontrado ou inativo! ID: {usuario_monitorado_id}',
                    'suggestion': 'Verifique se o usuário existe ou recrie-o através do endpoint /usuarios-monitorados'
                }), 404

            print(f"✅ Usuário monitorado encontrado: {usuario_monitorado[1]} (ID: {usuario_monitorado[0]})")

            # Obter departamento do usuário monitorado (índice 2 é departamento_id)
            user_department_id = usuario_monitorado[2] if usuario_monitorado and len(usuario_monitorado) > 2 else None

            # Classificar atividade automaticamente
            ociosidade = int(data.get('ociosidade', 0))
            active_window = data['active_window']

            # Extrair informações adicionais
            titulo_janela = data.get('titulo_janela', active_window)
            duracao = data.get('duracao', 0)

            # Obter IP real do agente (considerando proxies)
            ip_address = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
            if ',' in str(ip_address):
                ip_address = ip_address.split(',')[0].strip()

            user_agent = request.headers.get('User-Agent', '')

            # Configurar timezone de São Paulo
            sao_paulo_tz = timezone(timedelta(hours=-3))
            horario_atual = datetime.now(sao_paulo_tz)

            # Salvar atividade temporariamente
            db.cursor.execute('''
                INSERT INTO atividades
                (usuario_monitorado_id, ociosidade, active_window, titulo_janela, categoria, produtividade,
                 horario, duracao, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            ''', (
                usuario_monitorado_id, ociosidade, active_window, titulo_janela,
                'pending', 'neutral', horario_atual,
                duracao, ip_address, user_agent
            ))

            activity_id = db.cursor.fetchone()[0]
            
            # Fazer commit da atividade antes de tentar classificar
            db.conn.commit()

            try:
                categoria, produtividade = classify_activity_with_tags(active_window, ociosidade, user_department_id, activity_id)
                print(f"🏷️ Classificação concluída: {categoria} ({produtividade})")
            except Exception as classify_error:
                print(f"❌ Erro na classificação: {classify_error}")
                # Fallback para classificação básica
                if ociosidade >= 600:
                    categoria, produtividade = 'idle', 'nonproductive'
                elif ociosidade >= 300:
                    categoria, produtividade = 'away', 'nonproductive'
                else:
                    categoria, produtividade = 'unclassified', 'neutral'

            # Atualizar atividade com classificação final
            db.cursor.execute('''
                UPDATE atividades
                SET categoria = %s, produtividade = %s
                WHERE id = %s;
            ''', (categoria, produtividade, activity_id))

            response_data = {
                'message': 'Atividade salva com sucesso!',
                'id': activity_id,
                'categoria': categoria,
                'produtividade': produtividade,
                'usuario_monitorado': usuario_monitorado[1],
                'usuario_monitorado_id': usuario_monitorado_id,
                'horario': horario_atual.isoformat()
            }

            print(f"✅ Atividade salva: ID {activity_id}")
            return jsonify(response_data), 201

    except Exception as e:
        print(f"❌ Erro inesperado ao salvar atividade: {e}")
        return jsonify({
            'message': 'Erro interno do servidor',
            'error': str(e)
        }), 500

# Rota para obter atividades (protegida)
@app.route('/atividades', methods=['GET'])
@token_required
def get_atividades(current_user):
    """Buscar todas as atividades com filtros opcionais"""
    try:
        limite = min(request.args.get('limite', 50, type=int), 100)  # Limitar a 100
        pagina = request.args.get('pagina', 1, type=int)
        offset = (pagina - 1) * limite
        agrupar = request.args.get('agrupar', 'false').lower() == 'true'
        categoria_filter = request.args.get('categoria')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        usuario_monitorado_id = request.args.get('usuario_monitorado_id')

        with DatabaseConnection() as db:
            # Construir a parte WHERE da query
            query_parts = []
            params = []

            if categoria_filter:
                query_parts.append('a.categoria = %s')
                params.append(categoria_filter)

            if data_inicio:
                query_parts.append('a.horario >= %s')
                params.append(data_inicio)

            if data_fim:
                query_parts.append('a.horario <= %s')
                params.append(data_fim)

            if usuario_monitorado_id:
                query_parts.append('a.usuario_monitorado_id = %s')
                params.append(usuario_monitorado_id)

            where_clause = ""
            if query_parts:
                where_clause = "WHERE " + " AND ".join(query_parts)

            # Primeiro, contar o total de registros que atendem aos filtros
            if agrupar:
                count_query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1
                        FROM atividades a
                        LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                        {where_clause}
                        GROUP BY a.usuario_monitorado_id, a.active_window, a.categoria, a.produtividade,
                                 DATE_TRUNC('minute', a.horario)
                    ) as grouped;
                """
            else:
                count_query = f"SELECT COUNT(*) FROM atividades a {where_clause};"

            db.cursor.execute(count_query, params)
            total_count = db.cursor.fetchone()[0]

            if agrupar:
                # Query com agrupamento
                query = f"""
                    SELECT
                        MIN(a.id) as id,
                        a.usuario_monitorado_id,
                        MAX(um.nome) as usuario_monitorado_nome,
                        MAX(um.cargo) as cargo,
                        a.active_window,
                        a.categoria,
                        a.produtividade,
                        MIN(a.horario) as horario,
                        MIN(a.ociosidade) as ociosidade,
                        COUNT(*) as eventos_agrupados,
                        SUM(COALESCE(a.duracao, 10)) as duracao_total
                    FROM atividades a
                    LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                    {where_clause}
                    GROUP BY a.usuario_monitorado_id, a.active_window, a.categoria, a.produtividade,
                             DATE_TRUNC('minute', a.horario)
                    ORDER BY MIN(a.horario) DESC
                    LIMIT %s OFFSET %s;
                """
            else:
                # Query simples sem agrupamento
                query = f"""
                    SELECT
                        a.id,
                        a.usuario_monitorado_id,
                        um.nome as usuario_monitorado_nome,
                        um.cargo,
                        a.active_window,
                        a.categoria,
                        a.produtividade,
                        a.horario,
                        a.ociosidade,
                        1 as eventos_agrupados,
                        COALESCE(a.duracao, 10) as duracao_total
                    FROM atividades a
                    LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                    {where_clause}
                    ORDER BY a.horario DESC
                    LIMIT %s OFFSET %s;
                """

            params.extend([limite, offset])
            db.cursor.execute(query, params)
            rows = db.cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'usuario_monitorado_id': row[1],
                    'usuario_monitorado_nome': row[2],
                    'cargo': row[3],
                    'active_window': row[4],
                    'categoria': row[5] or 'unclassified',
                    'produtividade': row[6] or 'neutral',
                    'horario': row[7].isoformat() if row[7] else None,
                    'ociosidade': row[8] or 0,
                    'eventos_agrupados': row[9] if agrupar else 1,
                    'duracao': row[10] or 10
                })

            # Criar resposta com headers de paginação
            response = jsonify(result)
            response.headers['X-Total-Count'] = str(total_count)
            response.headers['X-Page'] = str(pagina)
            response.headers['X-Per-Page'] = str(limite)
            response.headers['X-Total-Pages'] = str((total_count + limite - 1) // limite)

            return response

    except Exception as e:
        print(f"Erro ao buscar atividades: {e}")
        return jsonify([]), 200

# Rota para obter usuários (protegida)
@app.route('/usuarios', methods=['GET'])
@token_required
def get_users(current_user):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT u.id, u.nome, u.email, u.departamento_id, u.ativo, u.created_at, d.nome as departamento_nome, d.cor as departamento_cor
                FROM usuarios u
                LEFT JOIN departamentos d ON u.departamento_id = d.id
                WHERE u.ativo = TRUE
                ORDER BY u.nome;
            ''')
            usuarios = db.cursor.fetchall()

            result = []
            if usuarios:
                for usuario in usuarios:
                    # Verificar se temos dados suficientes do departamento
                    departamento_info = None
                    if len(usuario) > 6 and usuario[6]:  # departamento_nome existe
                        departamento_info = {
                            'nome': usuario[6],
                            'cor': usuario[7] if len(usuario) > 7 else None
                        }

                    result.append({
                        'usuario_id': str(usuario[0]) if usuario[0] else None,
                        'usuario': usuario[1],
                        'email': usuario[2],
                        'departamento_id': usuario[3],
                        'ativo': usuario[4],
                        'created_at': usuario[5].isoformat() if usuario[5] else None,
                        'departamento': departamento_info
                    })

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de usuários: {e}")
        return jsonify([]), 200

# Rota para obter ou criar usuário monitorado (protegida)
@app.route('/usuarios-monitorados', methods=['GET'])
@token_required
def get_monitored_users(current_user):
    # Verificar se foi passado um nome para buscar/criar usuário específico
    nome_usuario = request.args.get('nome')

    if nome_usuario:
        # Buscar usuário específico ou criar se não existir
        try:
            with DatabaseConnection() as db:
                # Primeiro, tentar encontrar o usuário
                db.cursor.execute('''
                    SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                           d.nome as departamento_nome, d.cor as departamento_cor
                    FROM usuarios_monitorados um
                    LEFT JOIN departamentos d ON um.departamento_id = d.id
                    WHERE um.nome = %s AND um.ativo = TRUE;
                ''', (nome_usuario,))

                usuario_existente = db.cursor.fetchone()

                if usuario_existente:
                    # Usuário existe, retornar seus dados
                    departamento_info = None
                    if len(usuario_existente) > 7 and usuario_existente[7]:
                        departamento_info = {
                            'nome': usuario_existente[7],
                            'cor': usuario_existente[8] if len(usuario_existente) > 8 else None
                        }

                    result = {
                        'id': usuario_existente[0],
                        'nome': usuario_existente[1],
                        'departamento_id': usuario_existente[2] if len(usuario_existente) > 2 else None,
                        'cargo': usuario_existente[3] if len(usuario_existente) > 3 else None,
                        'ativo': usuario_existente[4] if len(usuario_existente) > 4 else True,
                        'created_at': usuario_existente[5].isoformat() if usuario_existente[5] else None,
                        'updated_at': usuario_existente[6].isoformat() if len(usuario_existente) > 6 and usuario_existente[6] else None,
                        'departamento': departamento_info,
                        'created': False
                    }
                    print(f"✅ Usuário monitorado encontrado: {nome_usuario} (ID: {usuario_existente[0]})")
                    return jsonify(result)
                else:
                    # Usuário não existe, criar novo automaticamente
                    print(f"🔧 Criando novo usuário monitorado: {nome_usuario}")
                    db.cursor.execute('''
                        INSERT INTO usuarios_monitorados (nome, cargo)
                        VALUES (%s, 'Usuário')
                        RETURNING id, nome, departamento_id, cargo, ativo, created_at, updated_at;
                    ''', (nome_usuario,))

                    novo_usuario = db.cursor.fetchone()
                    print(f"✅ Usuário monitorado criado: {nome_usuario} (ID: {novo_usuario[0]})")

                    result = {
                        'id': novo_usuario[0],
                        'nome': novo_usuario[1],
                        'departamento_id': novo_usuario[2] if len(novo_usuario) > 2 else None,
                        'cargo': novo_usuario[3] if len(novo_usuario) > 3 else None,
                        'ativo': novo_usuario[4] if len(novo_usuario) > 4 else True,
                        'created_at': novo_usuario[5].isoformat() if novo_usuario[5] else None,
                        'updated_at': novo_usuario[6].isoformat() if len(novo_usuario) > 6 and novo_usuario[6] else None,
                        'departamento': None,
                        'created': True
                    }
                    return jsonify(result)

        except Exception as e:
            print(f"❌ Erro ao buscar/criar usuário monitorado {nome_usuario}: {e}")
            # Retornar um usuário básico para manter o agente funcionando
            return jsonify({
                'id': 0,
                'nome': nome_usuario,
                'departamento_id': None,
                'cargo': 'Usuário',
                'ativo': True,
                'created_at': None,
                'updated_at': None,
                'departamento': None,
                'created': False,
                'error': 'Erro ao processar usuário, usando fallback'
            }), 200

    else:
        # Listar todos os usuários monitorados (comportamento original)
        try:
            with DatabaseConnection() as db:
                db.cursor.execute('''
                    SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                           d.nome as departamento_nome, d.cor as departamento_cor
                    FROM usuarios_monitorados um
                    LEFT JOIN departamentos d ON um.departamento_id = d.id
                    WHERE um.ativo = TRUE
                    ORDER BY um.nome;
                ''')
                usuarios_monitorados = db.cursor.fetchall()

                result = []
                if usuarios_monitorados:
                    for usuario in usuarios_monitorados:
                        try:
                            # Verificar se campos do departamento existem
                            departamento_info = None
                            if len(usuario) > 7 and usuario[7]:
                                departamento_info = {
                                    'nome': usuario[7],
                                    'cor': usuario[8] if len(usuario) > 8 else None
                                }

                            result.append({
                                'id': usuario[0],
                                'nome': usuario[1],
                                'departamento_id': usuario[2] if len(usuario) > 2 else None,
                                'cargo': usuario[3] if len(usuario) > 3 else None,
                                'ativo': usuario[4] if len(usuario) > 4 else True,
                                'created_at': usuario[5].isoformat() if usuario[5] else None,
                                'updated_at': usuario[6].isoformat() if len(usuario) > 6 and usuario[6] else None,
                                'departamento': departamento_info
                            })
                        except (IndexError, AttributeError) as e:
                            print(f"Erro ao processar usuário monitorado: {e}")
                            continue

                return jsonify(result)
        except Exception as e:
            print(f"Erro na consulta de usuários monitorados: {e}")
            return jsonify([]), 200

# Rota para obter departamentos
@app.route('/departamentos', methods=['GET'])
@token_required
def get_departments(current_user):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute("SELECT * FROM departamentos WHERE ativo = TRUE ORDER BY nome;")
            departamentos = db.cursor.fetchall()

            if not departamentos:
                return jsonify([]), 200

            result = []
            for dept in departamentos:
                try:
                    # Verificar se created_at é datetime ou string
                    created_at_value = None
                    if len(dept) > 5 and dept[5]:
                        if hasattr(dept[5], 'isoformat'):
                            created_at_value = dept[5].isoformat()
                        else:
                            created_at_value = str(dept[5])

                    result.append({
                        'id': dept[0],
                        'nome': dept[1],
                        'descricao': dept[2] if len(dept) > 2 and dept[2] else '',
                        'cor': dept[3] if len(dept) > 3 and dept[3] else '#6B7280',
                        'ativo': dept[4] if len(dept) > 4 and dept[4] is not None else True,
                        'created_at': created_at_value
                    })
                except (IndexError, AttributeError) as e:
                    print(f"Erro ao processar departamento: {e}")
                    continue

            return jsonify(result)
    except Exception as e:
        print(f"Erro na consulta de departamentos: {e}")
        return jsonify([]), 200

@app.route('/tags', methods=['GET'])
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

@app.route('/tags', methods=['POST'])
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
            for palavra in palavras_chave:
                if isinstance(palavra, dict):
                    palavra_chave = palavra.get('palavra', '')
                    peso = palavra.get('peso', 1)
                else:
                    palavra_chave = str(palavra)
                    peso = 1

                if palavra_chave.strip():
                    db.cursor.execute('''
                        INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (tag_id, palavra_chave) DO UPDATE SET peso = EXCLUDED.peso;
                    ''', (tag_id, palavra_chave.strip(), peso))

            return jsonify({'message': 'Tag criada com sucesso!', 'id': tag_id}), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Tag já existe para este departamento!'}), 409
    except Exception as e:
        print(f"Erro ao criar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@app.route('/tags/<int:tag_id>', methods=['PUT'])
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
                for palavra in data['palavras_chave']:
                    if isinstance(palavra, dict):
                        palavra_chave = palavra.get('palavra', '')
                        peso = palavra.get('peso', 1)
                    else:
                        palavra_chave = str(palavra)
                        peso = 1

                    if palavra_chave.strip():
                        db.cursor.execute('''
                            INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                            VALUES (%s, %s, %s);
                        ''', (tag_id, palavra_chave.strip(), peso))

            return jsonify({'message': 'Tag atualizada com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@app.route('/tags/<int:tag_id>', methods=['DELETE'])
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

# Rota para criar novo departamento
@app.route('/departamentos', methods=['POST'])
@token_required
def create_department(current_user):
    data = request.json

    if not data or 'nome' not in data:
        return jsonify({'message': 'Nome do departamento é obrigatório!'}), 400

    nome = data['nome'].strip()
    descricao = data.get('descricao', '')
    cor = data.get('cor', '#6B7280')

    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO departamentos (nome, descricao, cor)
                VALUES (%s, %s, %s) RETURNING id;
            ''', (nome, descricao, cor))
            department_id = db.cursor.fetchone()[0]
            return jsonify({
                'message': 'Departamento criado com sucesso!',
                'id': department_id
            }), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Departamento já existe!'}), 409
    except Exception as e:
        print(f"Erro ao criar departamento: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para criar nova categoria
@app.route('/categorias', methods=['POST'])
@token_required
def create_category(current_user):
    data = request.json

    if not data or 'nome' not in data or 'tipo_produtividade' not in data:
        return jsonify({'message': 'Nome e tipo de produtividade são obrigatórios!'}), 400

    nome = data['nome'].strip()
    tipo = data['tipo_produtividade']
    departamento_id = data.get('departamento_id')
    cor = data.get('cor', '#6B7280')
    descricao = data.get('descricao', '')
    is_global = data.get('is_global', False)

    if tipo not in ['productive', 'nonproductive', 'neutral']:
        return jsonify({'message': 'Tipo de produtividade inválido!'}), 400

    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO categorias_app (nome, departamento_id, tipo_produtividade, cor, descricao, is_global)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            ''', (nome, departamento_id, tipo, cor, descricao, is_global))
            category_id = db.cursor.fetchone()[0]
            return jsonify({
                'message': 'Categoria criada com sucesso!',
                'id': category_id
            }), 201
    except psycopg2.IntegrityError:
        return jsonify({'message': 'Categoria já existe para este departamento!'}), 409
    except Exception as e:
        print(f"Erro ao criar categoria: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para obter categorias
@app.route('/categorias', methods=['GET'])
@token_required
def get_categories(current_user):
    departamento_id = request.args.get('departamento_id')

    try:
        with DatabaseConnection() as db:
            if departamento_id:
                # Categorias específicas do departamento + globais
                db.cursor.execute('''
                    SELECT c.*, d.nome as departamento_nome FROM categorias_app c
                    LEFT JOIN departamentos d ON c.departamento_id = d.id
                    WHERE c.departamento_id = %s OR c.is_global = TRUE
                    ORDER BY c.nome;
                ''', (departamento_id,))
            else:
                # Todas as categorias
                db.cursor.execute('''
                    SELECT c.*, d.nome as departamento_nome FROM categorias_app c
                    LEFT JOIN departamentos d ON c.departamento_id = d.id
                    ORDER BY c.nome;
                ''')

            categorias = db.cursor.fetchall()
            result = [{
                'id': cat[0],
                'nome': cat[1],
                'departamento_id': cat[2],
                'tipo_produtividade': cat[3],
                'cor': cat[4],
                'descricao': cat[5],
                'is_global': cat[6],
                'created_at': cat[7].isoformat() if cat[7] else None,
                'departamento_nome': cat[8] if len(cat) > 8 else None
            } for cat in categorias]
            return jsonify(result)
    except Exception as e:
        print(f"Erro ao obter categorias: {e}")
        return jsonify([]), 200

# Rota para atualizar atividade (protegida)
@app.route('/atividades/<int:activity_id>', methods=['PATCH'])
@token_required
def update_activity(current_user, activity_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se a atividade existe
            db.cursor.execute('''
                SELECT id FROM atividades
                WHERE id = %s;
            ''', (activity_id,))

            if not db.cursor.fetchone():
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
                SET {', '.join(update_fields)}
                WHERE id = %s;
            '''
            update_values.append(activity_id)

            db.cursor.execute(query, update_values)
            return jsonify({'message': 'Atividade atualizada com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar atividade: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para excluir atividade (protegida)
@app.route('/atividades/<int:activity_id>', methods=['DELETE'])
@token_required
def delete_activity(current_user, activity_id):
    try:
        with DatabaseConnection() as db:
            # Verificar se a atividade existe
            db.cursor.execute('''
                SELECT id FROM atividades
                WHERE id = %s;
            ''', (activity_id,))

            if not db.cursor.fetchone():
                return jsonify({'message': 'Atividade não encontrada!'}), 404

            # Excluir a atividade
            db.cursor.execute('''
                DELETE FROM atividades
                WHERE id = %s;
            ''', (activity_id,))

            return jsonify({'message': 'Atividade excluída com sucesso!'}), 200
    except Exception as e:
        print(f"Erro ao excluir atividade: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para atualizar departamento do usuário
@app.route('/usuarios/<uuid:usuario_id>/departamento', methods=['PATCH'])
@token_required
def update_user_department(current_user, usuario_id):
    data = request.json

    if not data or 'departamento_id' not in data:
        return jsonify({'message': 'ID do departamento é obrigatório!'}), 400

    departamento_id = data['departamento_id']

    try:
        with DatabaseConnection() as db:
            # Verificar se o departamento existe
            db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (departamento_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Departamento não encontrado!'}), 404

            db.cursor.execute('''
                UPDATE usuarios
                SET departamento_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (departamento_id, usuario_id))

            if db.cursor.rowcount == 0:
                return jsonify({'message': 'Usuário não encontrado!'}), 404

            return jsonify({'message': 'Departamento do usuário atualizado com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar departamento do usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para obter configurações do departamento
@app.route('/departamentos/<int:departamento_id>/configuracoes', methods=['GET'])
@token_required
def get_department_config(current_user, departamento_id):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT configuracao_chave, configuracao_valor
                FROM departamento_configuracoes
                WHERE departamento_id = %s;
            ''', (departamento_id,))

            configs = db.cursor.fetchall()
            result = {config[0]: config[1] for config in configs}
            return jsonify(result)
    except Exception as e:
        print(f"Erro ao obter configurações do departamento: {e}")
        return jsonify({}), 200

# Rota para definir configuração do departamento
@app.route('/departamentos/<int:departamento_id>/configuracoes', methods=['POST'])
@token_required
def set_department_config(current_user, departamento_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Configurações não fornecidas!'}), 400

    try:
        with DatabaseConnection() as db:
            for chave, valor in data.items():
                db.cursor.execute('''
                    INSERT INTO departamento_configuracoes (departamento_id, configuracao_chave, configuracao_valor)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (departamento_id, configuracao_chave)
                    DO UPDATE SET configuracao_valor = EXCLUDED.configuracao_valor;
                ''', (departamento_id, chave, str(valor)))

            return jsonify({'message': 'Configurações atualizadas com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rotas para gerenciamento de usuários monitorados
@app.route('/usuarios-monitorados', methods=['POST'])
@token_required
def create_monitored_user(current_user):
    data = request.json

    if not data or 'nome' not in data:
        return jsonify({'message': 'Nome é obrigatório!'}), 400

    nome = data['nome'].strip()
    cargo = data.get('cargo', 'Usuário')
    departamento_id = data.get('departamento_id')

    try:
        with DatabaseConnection() as db:
            if departamento_id is not None:
                try:
                    dept_id = int(departamento_id)
                    # Verificar se o departamento existe e está ativo
                    db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (dept_id,))
                    if not db.cursor.fetchone():
                        return jsonify({'message': 'Departamento não encontrado ou inativo!'}), 400
                except ValueError:
                    return jsonify({'message': 'ID de departamento inválido!'}), 400
            else:
                dept_id = None

            db.cursor.execute('''
                INSERT INTO usuarios_monitorados (nome, cargo, departamento_id)
                VALUES (%s, %s, %s)
                RETURNING id, nome, cargo, departamento_id, ativo, created_at, updated_at;
            ''', (nome, cargo, dept_id))

            usuario = db.cursor.fetchone()
            return jsonify({
                'message': 'Usuário monitorado criado com sucesso!',
                'id': usuario[0],
                'nome': usuario[1],
                'cargo': usuario[2],
                'departamento_id': usuario[3],
                'ativo': usuario[4],
                'created_at': usuario[5].isoformat() if usuario[5] else None,
                'updated_at': usuario[6].isoformat() if usuario[6] else None
            }), 201

    except psycopg2.IntegrityError:
        return jsonify({'message': 'Usuário monitorado já existe!'}), 409
    except Exception as e:
        print(f"Erro ao criar usuário monitorado: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@app.route('/usuarios-monitorados/<int:user_id>', methods=['PUT'])
@token_required
def update_monitored_user(current_user, user_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se o usuário existe
            db.cursor.execute('SELECT id FROM usuarios_monitorados WHERE id = %s;', (user_id,))
            if not db.cursor.fetchone():
                return jsonify({'message': 'Usuário monitorado não encontrado!'}), 404

            update_fields = []
            update_values = []

            if 'nome' in data:
                update_fields.append('nome = %s')
                update_values.append(data['nome'])
            if 'cargo' in data:
                update_fields.append('cargo = %s')
                update_values.append(data['cargo'])
            if 'departamento_id' in data:
                dept_id = data.get('departamento_id')
                if dept_id is not None:
                    try:
                        dept_id = int(dept_id)
                        # Verificar se o departamento existe e está ativo
                        db.cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (dept_id,))
                        if not db.cursor.fetchone():
                            return jsonify({'message': 'Departamento não encontrado ou inativo!'}), 404
                    except ValueError:
                        return jsonify({'message': 'ID de departamento inválido!'}), 400
                else:
                    dept_id = None # Permitir definir departamento_id como NULL
                update_fields.append('departamento_id = %s')
                update_values.append(dept_id)
            if 'ativo' in data:
                update_fields.append('ativo = %s')
                update_values.append(data['ativo'])

            if not update_fields:
                return jsonify({'message': 'Nenhum campo válido para atualizar!'}), 400

            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            update_values.append(user_id)

            db.cursor.execute(f'''
                UPDATE usuarios_monitorados SET {', '.join(update_fields)}
                WHERE id = %s;
            ''', update_values)

            return jsonify({'message': 'Usuário monitorado atualizado com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar usuário monitorado: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para obter tags de uma atividade específica
@app.route('/atividades/<int:activity_id>/tags', methods=['GET'])
@token_required
def get_activity_tags(current_user, activity_id):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT t.id, t.nome, t.descricao, t.cor, t.produtividade,
                       at.confidence, d.nome as departamento_nome
                FROM atividade_tags at
                JOIN tags t ON at.tag_id = t.id
                LEFT JOIN departamentos d ON t.departamento_id = d.id
                WHERE at.atividade_id = %s
                ORDER BY at.confidence DESC;
            ''', (activity_id,))

            tags = db.cursor.fetchall()
            result = []

            for tag in tags:
                result.append({
                    'id': tag[0],
                    'nome': tag[1],
                    'descricao': tag[2],
                    'cor': tag[3],
                    'produtividade': tag[4],
                    'confidence': float(tag[5]) if tag[5] else 0.0,
                    'departamento_nome': tag[6]
                })

            return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar tags da atividade: {e}")
        return jsonify([]), 200

# Estatísticas avançadas
@app.route('/estatisticas', methods=['GET'])
@token_required
def get_statistics(current_user):
    usuario_monitorado_id = request.args.get('usuario_monitorado_id')

    if not usuario_monitorado_id:
        return jsonify({'message': 'usuario_monitorado_id é obrigatório!'}), 400

    try:
        with DatabaseConnection() as db:
            # Estatísticas por categoria
            db.cursor.execute('''
                SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
                       SUM(duracao) as tempo_total
                FROM atividades
                WHERE usuario_monitorado_id = %s
                GROUP BY categoria
                ORDER BY total DESC;
            ''', (usuario_monitorado_id,))

            stats_por_categoria = db.cursor.fetchall()

            # Produtividade por dia da semana
            db.cursor.execute('''
                SELECT EXTRACT(DOW FROM horario) as dia_semana,
                       produtividade,
                       COUNT(*) as total
                FROM atividades
                WHERE usuario_monitorado_id = %s
                GROUP BY EXTRACT(DOW FROM horario), produtividade
                ORDER BY dia_semana;
            ''', (usuario_monitorado_id,))

            produtividade_semanal = db.cursor.fetchall()

            # Total de atividades hoje
            db.cursor.execute('''
                SELECT COUNT(*)
                FROM atividades
                WHERE usuario_monitorado_id = %s
                AND DATE(horario) = CURRENT_DATE;
            ''', (usuario_monitorado_id,))

            atividades_hoje = db.cursor.fetchone()[0]

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
    except Exception as e:
        print(f"Erro ao obter estatísticas: {e}")
        return jsonify({}), 200

# Rota legacy para compatibilidade (será removida)
@app.route('/usuario', methods=['GET'])
def get_user_legacy():
    return jsonify({'message': 'Esta rota foi descontinuada. Use /login para autenticação.'}), 410

if __name__ == '__main__':
    import sys

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

        # Verificar se deve excluir todas as tabelas
        if len(sys.argv) > 1 and sys.argv[1] == '--reset':
            print("🔄 Modo reset ativado - Excluindo e recriando banco...")
            drop_all_tables()
            init_db()
            print("✅ Banco de dados resetado com sucesso!")
        else:
            init_db()  # Inicializa o banco de dados
            print("✅ Banco de dados inicializado com sucesso!")

        # Criar pool inicial
        with pool_lock:
            connection_pool = create_connection_pool()

        print(f"🚀 Servidor rodando em http://0.0.0.0:5000")
        print(f"🔌 Pool de conexões ativo com {connection_pool.minconn}-{connection_pool.maxconn} conexões")

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