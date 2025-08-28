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

        # Buscar tags ativas - primeiro do departamento específico, depois globais
        if user_department_id:
            cursor.execute('''
            SELECT t.id, t.nome, t.produtividade, tk.palavra_chave, tk.peso
            FROM tags t
            JOIN tag_palavras_chave tk ON t.id = tk.tag_id
            WHERE t.ativo = TRUE AND (t.departamento_id = %s OR t.departamento_id IS NULL)
            ORDER BY t.departamento_id NULLS LAST, tk.peso DESC;
            ''', (user_department_id,))
        else:
            # Buscar apenas tags globais
            cursor.execute('''
            SELECT t.id, t.nome, t.produtividade, tk.palavra_chave, tk.peso
            FROM tags t
            JOIN tag_palavras_chave tk ON t.id = tk.tag_id
            WHERE t.ativo = TRUE AND t.departamento_id IS NULL
            ORDER BY tk.peso DESC;
            ''')

        tag_matches = cursor.fetchall()
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
                    'palavra_chave': palavra_chave
                })

                print(f"🎯 Match encontrado: '{palavra_chave}' -> Tag '{tag_nome}' (confidence: {confidence:.2f})")

                # Se temos um ID da atividade, salvar a associação
                if activity_id:
                    cursor.execute('''
                    INSERT INTO atividade_tags (atividade_id, tag_id, confidence)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (atividade_id, tag_id) DO UPDATE SET confidence = EXCLUDED.confidence;
                    ''', (activity_id, tag_id, confidence))

        # Retornar a tag com maior confidence
        if matched_tags:
            best_match = max(matched_tags, key=lambda x: x['confidence'])
            print(f"🏷️ Melhor match: '{best_match['nome']}' ({best_match['produtividade']}) - confidence: {best_match['confidence']:.2f}")
            # A categoria agora será o nome da tag
            return best_match['nome'], best_match['produtividade']

    except Exception as e:
        conn.rollback()
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
        global conn, cursor

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
            # Verificar se a conexão está ativa
            cursor.execute('SELECT 1;')
        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.InternalError):
            # Reconectar se necessário
            conn.rollback()
            conn = get_db_connection()
            cursor = conn.cursor()
        except (psycopg2.errors.InFailedSqlTransaction, psycopg2.ProgrammingError):
            # Rollback da transação falhada
            conn.rollback()

        try:
            # Verificar se o usuário ainda existe
            cursor.execute("SELECT id, nome, senha, email, departamento_id, ativo FROM usuarios WHERE id = %s;", (uuid.UUID(user_id),))
            current_user = cursor.fetchone()
            if not current_user:
                print(f"❌ Usuário não encontrado para token: {user_id}")
                return jsonify({'message': 'Usuário não encontrado!'}), 401
        except (psycopg2.ProgrammingError, psycopg2.errors.InFailedSqlTransaction, psycopg2.Error) as e:
            conn.rollback()
            print(f"Erro ao verificar usuário: {e}")
            # Try to reconnect and verify again
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, nome, senha, email, departamento_id, ativo FROM usuarios WHERE id = %s;", (uuid.UUID(user_id),))
                current_user = cursor.fetchone()
                if not current_user:
                    return jsonify({'message': 'Usuário não encontrado após reconexão!'}), 401
            except Exception as reconnect_error:
                print(f"Erro na reconexão: {reconnect_error}")
                return jsonify({'message': 'Erro interno do servidor!'}), 500

        return f(current_user, *args, **kwargs)
    return decorated

# Função para deletar todas as tabelas
def drop_all_tables():
    global conn, cursor
    try:
        print("🗑️ Excluindo todas as tabelas existentes...")

        # Desabilitar verificações de foreign key temporariamente
        cursor.execute("SET session_replication_role = replica;")

        # Listar todas as tabelas do usuário
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
        """)
        tables = cursor.fetchall()

        # Excluir todas as tabelas
        for table in tables:
            table_name = table[0]
            print(f"   Excluindo tabela: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")

        # Reabilitar verificações de foreign key
        cursor.execute("SET session_replication_role = DEFAULT;")

        conn.commit()
        print("✅ Todas as tabelas foram excluídas!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao excluir tabelas: {e}")
        raise

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

    try:
        print("🔧 Inicializando estrutura do banco de dados...")

        # 1. Primeiro criar tabela de departamentos
        print("📋 Criando tabela de departamentos...")
        cursor.execute('''
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

        # Commit imediatamente após criar departamentos
        conn.commit()
        print("✅ Tabela departamentos criada")

        # 2. Inserir departamentos padrão
        print("📋 Inserindo departamentos padrão...")
        cursor.execute('''
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

        # Commit após inserir departamentos
        conn.commit()
        print("✅ Departamentos padrão inseridos")

        # 3. Verificar se tabela usuarios existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'usuarios'
            );
        """)
        usuarios_table_exists = cursor.fetchone()[0]

        if usuarios_table_exists:
            print("📋 Tabela usuarios já existe, verificando coluna departamento_id...")
            # Verificar se coluna departamento_id existe
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='usuarios' AND column_name='departamento_id';
            """)

            if not cursor.fetchone():
                print("🔧 Adicionando coluna departamento_id à tabela usuarios...")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN departamento_id INTEGER;")
                cursor.execute("ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_departamento FOREIGN KEY (departamento_id) REFERENCES departamentos(id);")
                conn.commit()
                print("✅ Coluna departamento_id adicionada com sucesso!")
            else:
                print("✅ Coluna departamento_id já existe")
        else:
            print("📋 Criando tabela usuarios com departamento_id...")
            # Criar tabela usuarios do zero com departamento_id
            cursor.execute('''
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
            conn.commit()
            print("✅ Tabela usuarios criada com departamento_id")

        # 4. Criar demais tabelas
        print("📋 Criando tabelas auxiliares...")

        # Tabela de usuários monitorados
        cursor.execute('''
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
        cursor.execute('''
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
        cursor.execute('''
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
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            cor VARCHAR(7) DEFAULT '#6B7280',
            produtividade VARCHAR(20) NOT NULL CHECK (produtividade IN ('productive', 'nonproductive', 'neutral')),
            departamento_id INTEGER REFERENCES departamentos(id),
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nome, departamento_id)
        );
        ''')

        # Tabela de palavras-chave das tags
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_palavras_chave (
            id SERIAL PRIMARY KEY,
            tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
            palavra_chave VARCHAR(255) NOT NULL,
            peso INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')

        # Tabela para configurações de departamento
        cursor.execute('''
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
        cursor.execute('''
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
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS atividade_tags (
            id SERIAL PRIMARY KEY,
            atividade_id INTEGER REFERENCES atividades(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
            confidence FLOAT DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(atividade_id, tag_id)
        );
        ''')

        # Commit de todas as tabelas
        conn.commit()
        print("✅ Todas as tabelas criadas")

        # 5. Criar índices para melhor performance
        print("📋 Criando índices...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_usuario_monitorado_id ON atividades(usuario_monitorado_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_horario ON atividades(horario DESC);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_categoria ON atividades(categoria);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_nome ON usuarios(nome);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_monitorados_nome ON usuarios_monitorados(nome);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_departamentos_nome ON departamentos(nome);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_categorias_departamento ON categorias_app(departamento_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_departamento ON tags(departamento_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_ativo ON tags(ativo);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_palavras_chave_tag_id ON tag_palavras_chave(tag_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividade_tags_atividade_id ON atividade_tags(atividade_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividade_tags_tag_id ON atividade_tags(tag_id);')

        # 6. Inserir dados padrão
        print("📋 Inserindo dados padrão...")

        # Categorias globais padrão
        cursor.execute('''
        INSERT INTO categorias_app (nome, tipo_produtividade, cor, descricao, is_global) 
        VALUES 
            ('Sistema', 'neutral', '#6B7280', 'Atividades do sistema operacional', TRUE),
            ('Entretenimento', 'nonproductive', '#EF4444', 'Jogos, vídeos e redes sociais', TRUE),
            ('Navegação Geral', 'neutral', '#F59E0B', 'Navegação web geral', TRUE)
        ON CONFLICT (nome, departamento_id) DO NOTHING;
        ''')

        # Categorias específicas por departamento
        cursor.execute('''
        INSERT INTO categorias_app (nome, departamento_id, tipo_produtividade, cor, descricao) 
        SELECT 'Desenvolvimento', d.id, 'productive', '#10B981', 'Atividades de programação e desenvolvimento'
        FROM departamentos d WHERE d.nome = 'TI'
        UNION ALL
        SELECT 'DevOps', d.id, 'productive', '#059669', 'Atividades de infraestrutura e deploy'
        FROM departamentos d WHERE d.nome = 'TI'
        UNION ALL
        SELECT 'Design Gráfico', d.id, 'productive', '#7C3AED', 'Criação de materiais visuais'
        FROM departamentos d WHERE d.nome = 'Marketing'
        UNION ALL
        SELECT 'Mídias Sociais', d.id, 'productive', '#EC4899', 'Gestão de redes sociais'
        FROM departamentos d WHERE d.nome = 'Marketing'
        UNION ALL
        SELECT 'Recrutamento', d.id, 'productive', '#DC2626', 'Atividades de contratação'
        FROM departamentos d WHERE d.nome = 'RH'
        UNION ALL
        SELECT 'Treinamento', d.id, 'productive', '#EA580C', 'Capacitação de funcionários'
        FROM departamentos d WHERE d.nome = 'RH'
        UNION ALL
        SELECT 'Análise Financeira', d.id, 'productive', '#DC2626', 'Análise de dados financeiros'
        FROM departamentos d WHERE d.nome = 'Financeiro'
        UNION ALL
        SELECT 'Vendas Online', d.id, 'productive', '#8B5CF6', 'Vendas através de plataformas digitais'
        FROM departamentos d WHERE d.nome = 'Vendas'
        ON CONFLICT (nome, departamento_id) DO NOTHING;
        ''')

        # Regras de classificação padrão por departamento
        cursor.execute('''
        INSERT INTO regras_classificacao (pattern, categoria_id, departamento_id, tipo) 
        SELECT 'Visual Studio Code', c.id, c.departamento_id, 'application_name' 
        FROM categorias_app c WHERE c.nome = 'Desenvolvimento' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'IntelliJ', c.id, c.departamento_id, 'application_name' 
        FROM categorias_app c WHERE c.nome = 'Desenvolvimento' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'PyCharm', c.id, c.departamento_id, 'application_name' 
        FROM categorias_app c WHERE c.nome = 'Desenvolvimento' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'Docker', c.id, c.departamento_id, 'application_name' 
        FROM categorias_app c WHERE c.nome = 'DevOps' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'Photoshop', c.id, c.departamento_id, 'application_name' 
        FROM categorias_app c WHERE c.nome = 'Design Gráfico' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'Figma', c.id, c.departamento_id, 'window_title' 
        FROM categorias_app c WHERE c.nome = 'Design Gráfico' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'LinkedIn', c.id, c.departamento_id, 'window_title' 
        FROM categorias_app c WHERE c.nome = 'Recrutamento' AND c.departamento_id IS NOT NULL
        UNION ALL
        SELECT 'Excel', c.id, c.departamento_id, 'application_name' 
        FROM categorias_app c WHERE c.nome = 'Análise Financeira' AND c.departamento_id IS NOT NULL
        ON CONFLICT DO NOTHING;
        ''')

        # Regras globais
        cursor.execute('''
        INSERT INTO regras_classificacao (pattern, categoria_id, tipo) 
        SELECT 'YouTube', id, 'window_title' FROM categorias_app WHERE nome = 'Entretenimento' AND is_global = TRUE
        UNION ALL
        SELECT 'Windows Explorer', id, 'application_name' FROM categorias_app WHERE nome = 'Sistema' AND is_global = TRUE
        UNION ALL
        SELECT 'File Explorer', id, 'application_name' FROM categorias_app WHERE nome = 'Sistema' AND is_global = TRUE
        UNION ALL
        SELECT 'Visual Studio Code', id, 'window_title' FROM categorias_app WHERE nome = 'Sistema' AND is_global = TRUE
        UNION ALL
        SELECT 'Google Chrome', id, 'window_title' FROM categorias_app WHERE nome = 'Navegação Geral' AND is_global = TRUE
        UNION ALL
        SELECT 'WhatsApp', id, 'window_title' FROM categorias_app WHERE nome = 'Entretenimento' AND is_global = TRUE
        UNION ALL
        SELECT 'Replit', id, 'window_title' FROM categorias_app WHERE nome = 'Sistema' AND is_global = TRUE
        ON CONFLICT DO NOTHING;
        ''')

        # Inserir tags padrão
        print("📋 Inserindo tags padrão...")
        cursor.execute('''
        INSERT INTO tags (nome, descricao, produtividade, departamento_id, cor) 
        SELECT 'Desenvolvimento Web', 'Desenvolvimento de aplicações web', 'productive', d.id, '#10B981'
        FROM departamentos d WHERE d.nome = 'TI'
        UNION ALL
        SELECT 'Banco de Dados', 'Administração e desenvolvimento de bancos de dados', 'productive', d.id, '#059669'
        FROM departamentos d WHERE d.nome = 'TI'
        UNION ALL
        SELECT 'Design UI/UX', 'Design de interfaces e experiência do usuário', 'productive', d.id, '#8B5CF6'
        FROM departamentos d WHERE d.nome = 'Marketing'
        UNION ALL
        SELECT 'Análise de Dados', 'Análise e processamento de dados', 'productive', d.id, '#3B82F6'
        FROM departamentos d WHERE d.nome = 'Financeiro'
        UNION ALL
        SELECT 'Redes Sociais', 'Gerenciamento de mídias sociais', 'productive', d.id, '#EC4899'
        FROM departamentos d WHERE d.nome = 'Marketing'
        UNION ALL
        SELECT 'Entretenimento', 'Atividades de entretenimento e lazer', 'nonproductive', NULL, '#EF4444'
        UNION ALL
        SELECT 'Comunicação', 'Ferramentas de comunicação e colaboração', 'productive', NULL, '#06B6D4'
        UNION ALL
        SELECT 'Navegação Web', 'Navegação geral na internet', 'neutral', NULL, '#F59E0B'
        ON CONFLICT (nome, departamento_id) DO NOTHING;
        ''')

        # Inserir palavras-chave para as tags
        cursor.execute('''
        INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
        SELECT t.id, 'Visual Studio Code', 5 FROM tags t WHERE t.nome = 'Desenvolvimento Web'
        UNION ALL
        SELECT t.id, 'VS Code', 5 FROM tags t WHERE t.nome = 'Desenvolvimento Web'
        UNION ALL
        SELECT t.id, 'GitHub', 4 FROM tags t WHERE t.nome = 'Desenvolvimento Web'
        UNION ALL
        SELECT t.id, 'React', 4 FROM tags t WHERE t.nome = 'Desenvolvimento Web'
        UNION ALL
        SELECT t.id, 'Node.js', 4 FROM tags t WHERE t.nome = 'Desenvolvimento Web'
        UNION ALL
        SELECT t.id, 'Replit', 5 FROM tags t WHERE t.nome = 'Desenvolvimento Web'
        UNION ALL
        SELECT t.id, 'pgAdmin', 5 FROM tags t WHERE t.nome = 'Banco de Dados'
        UNION ALL
        SELECT t.id, 'PostgreSQL', 4 FROM tags t WHERE t.nome = 'Banco de Dados'
        UNION ALL
        SELECT t.id, 'MySQL', 4 FROM tags t WHERE t.nome = 'Banco de Dados'
        UNION ALL
        SELECT t.id, 'MongoDB', 4 FROM tags t WHERE t.nome = 'Banco de Dados'
        UNION ALL
        SELECT t.id, 'Figma', 5 FROM tags t WHERE t.nome = 'Design UI/UX'
        UNION ALL
        SELECT t.id, 'Adobe XD', 5 FROM tags t WHERE t.nome = 'Design UI/UX'
        UNION ALL
        SELECT t.id, 'Photoshop', 4 FROM tags t WHERE t.nome = 'Design UI/UX'
        UNION ALL
        SELECT t.id, 'Excel', 5 FROM tags t WHERE t.nome = 'Análise de Dados'
        UNION ALL
        SELECT t.id, 'Power BI', 5 FROM tags t WHERE t.nome = 'Análise de Dados'
        UNION ALL
        SELECT t.id, 'Instagram', 4 FROM tags t WHERE t.nome = 'Redes Sociais'
        UNION ALL
        SELECT t.id, 'Facebook', 4 FROM tags t WHERE t.nome = 'Redes Sociais'
        UNION ALL
        SELECT t.id, 'LinkedIn', 4 FROM tags t WHERE t.nome = 'Redes Sociais'
        UNION ALL
        SELECT t.id, 'YouTube', 3 FROM tags t WHERE t.nome = 'Entretenimento'
        UNION ALL
        SELECT t.id, 'Netflix', 3 FROM tags t WHERE t.nome = 'Entretenimento'
        UNION ALL
        SELECT t.id, 'Spotify', 3 FROM tags t WHERE t.nome = 'Entretenimento'
        UNION ALL
        SELECT t.id, 'WhatsApp', 4 FROM tags t WHERE t.nome = 'Comunicação'
        UNION ALL
        SELECT t.id, 'Slack', 4 FROM tags t WHERE t.nome = 'Comunicação'
        UNION ALL
        SELECT t.id, 'Teams', 4 FROM tags t WHERE t.nome = 'Comunicação'
        UNION ALL
        SELECT t.id, 'Zoom', 4 FROM tags t WHERE t.nome = 'Comunicação'
        UNION ALL
        SELECT t.id, 'Google Chrome', 3 FROM tags t WHERE t.nome = 'Navegação Web'
        UNION ALL
        SELECT t.id, 'Firefox', 3 FROM tags t WHERE t.nome = 'Navegação Web'
        UNION ALL
        SELECT t.id, 'Edge', 3 FROM tags t WHERE t.nome = 'Navegação Web'
        ON CONFLICT DO NOTHING;
        ''')

        # Não inserir usuários monitorados de demonstração
        # Os usuários serão criados automaticamente conforme necessário

        # Commit final de todos os dados
        conn.commit()
        print("✅ Todos os dados padrão inseridos")
        print("🎉 Banco de dados inicializado com sucesso!")

    except Exception as e:
        conn.rollback()
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
        (new_user_id, nome, hashed_password.decode('utf-8'))
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
    global conn, cursor

    try:
        # Verificar se a conexão está ativa e fazer rollback se necessário
        try:
            cursor.execute('SELECT 1;')
        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.InternalError):
            # Reconectar se necessário
            conn.rollback()
            conn = get_db_connection()
            cursor = conn.cursor()
        except psycopg2.errors.InFailedSqlTransaction:
            # Rollback da transação falhada
            conn.rollback()

        data = request.json

        if not data or 'nome' not in data or 'senha' not in data:
            return jsonify({'message': 'Nome de usuário e senha são obrigatórios!'}), 400

        nome = data['nome'].strip()
        senha = data['senha']

        # Buscar usuário
        cursor.execute("SELECT * FROM usuarios WHERE nome = %s;", (nome,))
        usuario = cursor.fetchone()
    except Exception as e:
        conn.rollback()
        print(f"Erro na preparação do login: {e}")
        return jsonify({'message': 'Erro interno do servidor'}), 500

    if not usuario:
        return jsonify({'message': 'Credenciais inválidas!'}), 401

    # Verificar senha - lidar com diferentes tipos de dados
    senha_hash = usuario[2]
    if isinstance(senha_hash, bool):
        # Se a senha foi armazenada como boolean, recriar o hash
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Atualizar no banco com o hash correto
        cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s;", (senha_hash, usuario[0]))
        conn.commit()
    elif isinstance(senha_hash, str):
        # Verificar se é um hash válido
        if not senha_hash.startswith('$2b$'):
            # Se não é um hash bcrypt válido, criar um novo
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s;", (senha_hash, usuario[0]))
            conn.commit()

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

        # Verificar se o usuário monitorado existe
        cursor.execute("""
            SELECT id, nome, departamento_id, cargo, ativo, created_at, updated_at 
            FROM usuarios_monitorados 
            WHERE id = %s AND ativo = TRUE;
        """, (usuario_monitorado_id,))
        usuario_monitorado = cursor.fetchone()
        if not usuario_monitorado:
            print(f"❌ Usuário monitorado não encontrado: ID {usuario_monitorado_id}")

            # Listar usuários existentes para debug
            cursor.execute("SELECT id, nome FROM usuarios_monitorados WHERE ativo = TRUE;")
            usuarios_existentes = cursor.fetchall()
            print(f"🔍 Usuários monitorados existentes: {usuarios_existentes}")

            return jsonify({
                'message': f'Usuário monitorado não encontrado ou inativo! ID: {usuario_monitorado_id}',
                'suggestion': 'Verifique se o usuário existe ou recrie-o através do endpoint /usuarios-monitorados'
            }), 404

        print(f"✅ Usuário monitorado encontrado: {usuario_monitorado[1]} (ID: {usuario_monitorado[0]})")
        print(f"🔍 Debug - usuário monitorado tuple: {usuario_monitorado}")
        print(f"🔍 Debug - length do tuple: {len(usuario_monitorado)}")

        # Obter departamento do usuário monitorado (índice 2 é departamento_id)
        user_department_id = usuario_monitorado[2] if usuario_monitorado and len(usuario_monitorado) > 2 else None
        print(f"🔍 Debug - departamento_id extraído: {user_department_id}")

        # Classificar atividade automaticamente
        ociosidade = int(data.get('ociosidade', 0))
        active_window = data['active_window']
        print(f"🏷️ Iniciando classificação - window: {active_window}, ociosidade: {ociosidade}, dept: {user_department_id}")

        # Primeiro salvar a atividade para obter o ID
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
        cursor.execute('''
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

        activity_id = cursor.fetchone()[0]

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
            print(f"🏷️ Classificação fallback: {categoria} ({produtividade})")

        # Atualizar atividade com classificação final
        cursor.execute('''
            UPDATE atividades 
            SET categoria = %s, produtividade = %s
            WHERE id = %s;
        ''', (categoria, produtividade, activity_id))

        print(f"🏷️ Atividade classificada: {categoria} ({produtividade})")


        conn.commit()

        response_data = {
            'message': 'Atividade salva com sucesso!',
            'id': activity_id,
            'categoria': categoria,
            'produtividade': produtividade,
            'usuario_monitorado': usuario_monitorado[1],  # Nome do usuário monitorado
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
        limite = request.args.get('limite', 50, type=int)
        pagina = request.args.get('pagina', 1, type=int)
        offset = (pagina - 1) * limite
        agrupar = request.args.get('agrupar', 'false').lower() == 'true'
        categoria_filter = request.args.get('categoria')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        usuario_monitorado_id = request.args.get('usuario_monitorado_id')

        cursor = conn.cursor()

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

        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        if agrupar:
            # Query com agrupamento
            query = f"""
                SELECT 
                    MIN(a.id) as id,
                    a.usuario_monitorado_id,
                    um.nome as usuario_monitorado_nome,
                    um.cargo,
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
        cursor.execute(query, params)
        rows = cursor.fetchall()

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
        return jsonify([]), 500

# Rota para obter todas as atividades (admin - para compatibilidade)
@app.route('/atividades/all', methods=['GET'])
@token_required
def get_all_activities(current_user):
    cursor.execute('''
        SELECT a.*, um.nome as usuario_monitorado_nome, um.cargo, d.nome as departamento_nome
        FROM atividades a 
        JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
        LEFT JOIN departamentos d ON um.departamento_id = d.id
        ORDER BY a.horario DESC;
    ''')
    atividades = cursor.fetchall()
    result = [{
        'id': atividade[0], 
        'usuario_monitorado_id': atividade[1], 
        'ociosidade': atividade[2], 
        'active_window': atividade[3], 
        'horario': atividade[7].isoformat() if atividade[7] else None,
        'usuario_monitorado_nome': atividade[11],
        'cargo': atividade[12],
        'departamento_nome': atividade[13]
    } for atividade in atividades]
    return jsonify(result)

# Rota para obter usuários (protegida)
@app.route('/usuarios', methods=['GET'])
@token_required
def get_users(current_user):
    global conn, cursor

    try:
        # Verificar se a conexão está ativa
        cursor.execute('SELECT 1;')
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        # Reconectar se necessário
        conn = get_db_connection()
        cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT u.id, u.nome, u.email, u.departamento_id, u.created_at, d.nome as departamento_nome, d.cor as departamento_cor
            FROM usuarios u
            LEFT JOIN departamentos d ON u.departamento_id = d.id
            WHERE u.ativo = TRUE
            ORDER BY u.nome;
        ''')
        usuarios = cursor.fetchall()

        result = []
        if usuarios:
            for usuario in usuarios:
                result.append({
                    'usuario_id': str(usuario[0]), 
                    'usuario': usuario[1],
                    'email': usuario[2],
                    'departamento_id': usuario[3],
                    'created_at': usuario[4].isoformat() if usuario[4] else None,
                    'departamento': {
                        'nome': usuario[5],
                        'cor': usuario[6]
                    } if usuario[5] else None
                })

        return jsonify(result)
    except psycopg2.Error as e:
        print(f"Erro na consulta de usuários: {e}")
        return jsonify([]), 200  # Return empty array instead of error

# Rota para obter ou criar usuário monitorado (protegida)
@app.route('/usuarios-monitorados', methods=['GET'])
@token_required
def get_monitored_users(current_user):
    global conn, cursor

    try:
        # Verificar se a conexão está ativa
        cursor.execute('SELECT 1;')
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        # Reconectar se necessário
        conn = get_db_connection()
        cursor = conn.cursor()

    # Verificar se foi passado um nome para buscar/criar usuário específico
    nome_usuario = request.args.get('nome')

    if nome_usuario:
        # Buscar usuário específico ou criar se não existir (sempre sem erro)
        try:
            # Primeiro, tentar encontrar o usuário
            cursor.execute('''
                SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                       d.nome as departamento_nome, d.cor as departamento_cor
                FROM usuarios_monitorados um
                LEFT JOIN departamentos d ON um.departamento_id = d.id
                WHERE um.nome = %s AND um.ativo = TRUE;
            ''', (nome_usuario,))

            usuario_existente = cursor.fetchone()

            if usuario_existente:
                # Usuário existe, retornar seus dados
                # Processar dados do usuário existente com segurança
                created_at_value = None
                updated_at_value = None

                if len(usuario_existente) > 5 and usuario_existente[5]:
                    if hasattr(usuario_existente[5], 'isoformat'):
                        created_at_value = usuario_existente[5].isoformat()
                    else:
                        created_at_value = str(usuario_existente[5])

                if len(usuario_existente) > 6 and usuario_existente[6]:
                    if hasattr(usuario_existente[6], 'isoformat'):
                        updated_at_value = usuario_existente[6].isoformat()
                    else:
                        updated_at_value = str(usuario_existente[6])

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
                    'created_at': created_at_value,
                    'updated_at': updated_at_value,
                    'departamento': departamento_info,
                    'created': False
                }
                print(f"✅ Usuário monitorado encontrado: {nome_usuario} (ID: {usuario_existente[0]})")
                return jsonify(result)
            else:
                # Usuário não existe, criar novo automaticamente
                print(f"🔧 Criando novo usuário monitorado: {nome_usuario}")
                try:
                    cursor.execute('''
                        INSERT INTO usuarios_monitorados (nome, cargo) 
                        VALUES (%s, 'Usuário') 
                        RETURNING id, nome, departamento_id, cargo, ativo, created_at, updated_at;
                    ''', (nome_usuario,))

                    novo_usuario = cursor.fetchone()
                    conn.commit()
                    print(f"✅ Usuário monitorado criado: {nome_usuario} (ID: {novo_usuario[0]})")

                    # Processar dados do novo usuário com segurança
                    created_at_value = None
                    updated_at_value = None

                    if len(novo_usuario) > 5 and novo_usuario[5]:
                        if hasattr(novo_usuario[5], 'isoformat'):
                            created_at_value = novo_usuario[5].isoformat()
                        else:
                            created_at_value = str(novo_usuario[5])

                    if len(novo_usuario) > 6 and novo_usuario[6]:
                        if hasattr(novo_usuario[6], 'isoformat'):
                            updated_at_value = novo_usuario[6].isoformat()
                        else:
                            updated_at_value = str(novo_usuario[6])

                    result = {
                        'id': novo_usuario[0], 
                        'nome': novo_usuario[1],
                        'departamento_id': novo_usuario[2] if len(novo_usuario) > 2 else None,
                        'cargo': novo_usuario[3] if len(novo_usuario) > 3 else None,
                        'ativo': novo_usuario[4] if len(novo_usuario) > 4 else True,
                        'created_at': created_at_value,
                        'updated_at': updated_at_value,
                        'departamento': None,
                        'created': True
                    }
                    return jsonify(result)
                except psycopg2.IntegrityError:
                    # Se houve erro de integridade (usuário já existe), fazer uma nova consulta
                    conn.rollback()
                    print(f"⚠️ Conflito de integridade ao criar {nome_usuario}, buscando novamente...")
                    cursor.execute('''
                        SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                               d.nome as departamento_nome, d.cor as departamento_cor
                        FROM usuarios_monitorados um
                        LEFT JOIN departamentos d ON um.departamento_id = d.id
                        WHERE um.nome = %s AND um.ativo = TRUE;
                    ''', (nome_usuario,))

                    usuario_encontrado = cursor.fetchone()
                    if usuario_encontrado:
                        result = {
                            'id': usuario_encontrado[0], 
                            'nome': usuario_encontrado[1],
                            'departamento_id': usuario_encontrado[2] if len(usuario_encontrado) > 2 else None,
                            'cargo': usuario_encontrado[3] if len(usuario_encontrado) > 3 else None,
                            'ativo': usuario_encontrado[4] if len(usuario_encontrado) > 4 else True,
                            'created_at': usuario_encontrado[5].isoformat() if usuario_encontrado[5] else None,
                            'updated_at': usuario_encontrado[6].isoformat() if len(usuario_encontrado) > 6 and usuario_encontrado[6] else None,
                            'departamento': {
                                'nome': usuario_encontrado[7],
                                'cor': usuario_encontrado[8] if len(usuario_encontrado) > 8 else None
                            } if len(usuario_encontrado) > 7 and usuario_encontrado[7] else None,
                            'created': False
                        }
                        return jsonify(result)

        except Exception as e:
            conn.rollback()
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
            cursor.execute('''
                SELECT um.id, um.nome, um.departamento_id, um.cargo, um.ativo, um.created_at, um.updated_at,
                       d.nome as departamento_nome, d.cor as departamento_cor
                FROM usuarios_monitorados um
                LEFT JOIN departamentos d ON um.departamento_id = d.id
                WHERE um.ativo = TRUE
                ORDER BY um.nome;
            ''')
            usuarios_monitorados = cursor.fetchall()

            result = []
            if usuarios_monitorados:
                for usuario in usuarios_monitorados:
                    try:
                        # Verificar se os campos datetime existem e são válidos
                        created_at_value = None
                        if len(usuario) > 5 and usuario[5]:
                            if hasattr(usuario[5], 'isoformat'):
                                created_at_value = usuario[5].isoformat()
                            else:
                                created_at_value = str(usuario[5])

                        if len(usuario) > 6 and usuario[6]:
                            if hasattr(usuario[6], 'isoformat'):
                                updated_at_value = usuario[6].isoformat()
                            else:
                                updated_at_value = str(usuario[6])

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
                            'created_at': created_at_value,
                            'updated_at': updated_at_value,
                            'departamento': departamento_info
                        })
                    except (IndexError, AttributeError) as e:
                        print(f"Erro ao processar usuário monitorado: {e}")
                        continue

            return jsonify(result)
        except psycopg2.Error as e:
            print(f"Erro na consulta de usuários monitorados: {e}")
            return jsonify([]), 200

# Rota para obter departamentos
@app.route('/departamentos', methods=['GET'])
@token_required
def get_departments(current_user):
    global conn, cursor

    try:
        # Verificar e reconectar se necessário
        try:
            cursor.execute('SELECT 1;')
        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.InternalError):
            conn.rollback()
            conn = get_db_connection()
            cursor = conn.cursor()
        except (psycopg2.errors.InFailedSqlTransaction, psycopg2.ProgrammingError):
            conn.rollback()

        cursor.execute("SELECT * FROM departamentos WHERE ativo = TRUE ORDER BY nome;")
        departamentos = cursor.fetchall()

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
    except (psycopg2.Error, psycopg2.ProgrammingError) as e:
        conn.rollback()
        print(f"Erro na consulta de departamentos: {e}")
        # Try to reconnect
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            return jsonify([]), 200
        except:
            return jsonify([]), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro inesperado em departamentos: {e}")
        return jsonify([]), 200

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
        cursor.execute('''
            INSERT INTO departamentos (nome, descricao, cor) 
            VALUES (%s, %s, %s) RETURNING id;
        ''', (nome, descricao, cor))
        department_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({
            'message': 'Departamento criado com sucesso!',
            'id': department_id
        }), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'message': 'Departamento já existe!'}), 409

# Rota para obter categorias
@app.route('/categorias', methods=['GET'])
@token_required
def get_categories(current_user):
    departamento_id = request.args.get('departamento_id')

    if departamento_id:
        # Categorias específicas do departamento + globais
        cursor.execute('''
            SELECT c.*, d.nome as departamento_nome FROM categorias_app c
            LEFT JOIN departamentos d ON c.departamento_id = d.id
            WHERE c.departamento_id = %s OR c.is_global = TRUE
            ORDER BY c.nome;
        ''', (departamento_id,))
    else:
        # Todas as categorias
        cursor.execute('''
            SELECT c.*, d.nome as departamento_nome FROM categorias_app c
            LEFT JOIN departamentos d ON c.departamento_id = d.id
            ORDER BY c.nome;
        ''')

    categorias = cursor.fetchall()
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
        cursor.execute('''
            INSERT INTO categorias_app (nome, departamento_id, tipo_produtividade, cor, descricao, is_global) 
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (nome, departamento_id, tipo, cor, descricao, is_global))
        category_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({
            'message': 'Categoria criada com sucesso!',
            'id': category_id
        }), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'message': 'Categoria já existe para este departamento!'}), 409

# Rota para atualizar atividade (protegida)
@app.route('/atividades/<int:activity_id>', methods=['PATCH'])
@token_required
def update_activity(current_user, activity_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    # Verificar se a atividade existe
    cursor.execute('''
        SELECT id FROM atividades 
        WHERE id = %s;
    ''', (activity_id,))

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
        SET {', '.join(update_fields)}
        WHERE id = %s;
    '''
    update_values.append(activity_id)

    cursor.execute(query, update_values)
    conn.commit()

    return jsonify({'message': 'Atividade atualizada com sucesso!'}), 200

# Rota para excluir atividade (protegida)
@app.route('/atividades/<int:activity_id>', methods=['DELETE'])
@token_required
def delete_activity(current_user, activity_id):
    # Verificar se a atividade existe
    cursor.execute('''
        SELECT id FROM atividades 
        WHERE id = %s;
    ''', (activity_id,))

    if not cursor.fetchone():
        return jsonify({'message': 'Atividade não encontrada!'}), 404

    # Excluir a atividade
    cursor.execute('''
        DELETE FROM atividades 
        WHERE id = %s;
    ''', (activity_id,))

    conn.commit()

    return jsonify({'message': 'Atividade excluída com sucesso!'}), 200

# Rota para atualizar departamento do usuário
@app.route('/usuarios/<usuario_id>/departamento', methods=['PATCH'])
@token_required
def update_user_department(current_user, usuario_id):
    data = request.json

    if not data or 'departamento_id' not in data:
        return jsonify({'message': 'ID do departamento é obrigatório!'}), 400

    departamento_id = data['departamento_id']

    # Verificar se o departamento existe
    cursor.execute("SELECT id FROM departamentos WHERE id = %s AND ativo = TRUE;", (departamento_id,))
    if not cursor.fetchone():
        return jsonify({'message': 'Departamento não encontrado!'}), 404

    try:
        cursor.execute('''
            UPDATE usuarios 
            SET departamento_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        ''', (departamento_id, uuid.UUID(usuario_id)))

        if cursor.rowcount == 0:
            return jsonify({'message': 'Usuário não encontrado!'}), 404

        conn.commit()
        return jsonify({'message': 'Departamento do usuário atualizado com sucesso!'}), 200

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro ao atualizar departamento do usuário: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para obter configurações do departamento
@app.route('/departamentos/<int:departamento_id>/configuracoes', methods=['GET'])
@token_required
def get_department_config(current_user, departamento_id):
    cursor.execute('''
        SELECT configuracao_chave, configuracao_valor 
        FROM departamento_configuracoes 
        WHERE departamento_id = %s;
    ''', (departamento_id,))

    configs = cursor.fetchall()
    result = {config[0]: config[1] for config in configs}
    return jsonify(result)

# Rota para definir configuração do departamento
@app.route('/departamentos/<int:departamento_id>/configuracoes', methods=['POST'])
@token_required
def set_department_config(current_user, departamento_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Configurações não fornecidas!'}), 400

    try:
        for chave, valor in data.items():
            cursor.execute('''
                INSERT INTO departamento_configuracoes (departamento_id, configuracao_chave, configuracao_valor)
                VALUES (%s, %s, %s)
                ON CONFLICT (departamento_id, configuracao_chave)
                DO UPDATE SET configuracao_valor = EXCLUDED.configuracao_valor;
            ''', (departamento_id, chave, str(valor)))

        conn.commit()
        return jsonify({'message': 'Configurações atualizadas com sucesso!'}), 200

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro ao salvar configurações: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rotas para gerenciamento de Tags

@app.route('/tags', methods=['GET'])
@token_required
def get_tags(current_user):
    departamento_id = request.args.get('departamento_id')
    ativo = request.args.get('ativo', 'true').lower() == 'true'

    try:
        if departamento_id:
            cursor.execute('''
                SELECT t.*, d.nome as departamento_nome
                FROM tags t
                LEFT JOIN departamentos d ON t.departamento_id = d.id
                WHERE (t.departamento_id = %s OR t.departamento_id IS NULL) AND t.ativo = %s
                ORDER BY t.nome;
            ''', (departamento_id, ativo))
        else:
            cursor.execute('''
                SELECT t.*, d.nome as departamento_nome
                FROM tags t
                LEFT JOIN departamentos d ON t.departamento_id = d.id
                WHERE t.ativo = %s
                ORDER BY t.nome;
            ''', (ativo,))

        tags = cursor.fetchall()
        result = []

        for tag in tags:
            # Buscar palavras-chave da tag
            cursor.execute('''
                SELECT palavra_chave, peso
                FROM tag_palavras_chave
                WHERE tag_id = %s
                ORDER BY peso DESC;
            ''', (tag[0],))
            palavras_chave = cursor.fetchall()

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
                'departamento_nome': tag[9] if len(tag) > 9 else None,
                'palavras_chave': [{'palavra': p[0], 'peso': p[1]} for p in palavras_chave]
            })

        return jsonify(result)
    except (psycopg2.Error, psycopg2.ProgrammingError) as e:
        conn.rollback()
        print(f"Erro ao buscar tags: {e}")
        return jsonify([]), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro inesperado ao buscar tags: {e}")
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

    if produtividade not in ['productive', 'nonproductive', 'neutral']:
        return jsonify({'message': 'Produtividade inválida!'}), 400

    try:
        # Criar tag
        cursor.execute('''
            INSERT INTO tags (nome, descricao, cor, produtividade, departamento_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        ''', (nome, descricao, cor, produtividade, departamento_id))

        tag_id = cursor.fetchone()[0]

        # Adicionar palavras-chave
        for palavra in palavras_chave:
            if isinstance(palavra, dict):
                palavra_chave = palavra.get('palavra', '')
                peso = palavra.get('peso', 1)
            else:
                palavra_chave = str(palavra)
                peso = 1

            if palavra_chave.strip():
                cursor.execute('''
                    INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                    VALUES (%s, %s, %s);
                ''', (tag_id, palavra_chave.strip(), peso))

        conn.commit()
        return jsonify({'message': 'Tag criada com sucesso!', 'id': tag_id}), 201

    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'message': 'Tag já existe para este departamento!'}), 409
    except Exception as e:
        conn.rollback()
        print(f"Erro ao criar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@app.route('/tags/<int:tag_id>', methods=['PUT'])
@token_required
def update_tag(current_user, tag_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        # Verificar se a tag existe
        cursor.execute('SELECT id FROM tags WHERE id = %s;', (tag_id,))
        if not cursor.fetchone():
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
            tier_value = data['tier']
            if tier_value < 1 or tier_value > 5:
                return jsonify({'message': 'Tier deve estar entre 1 e 5!'}), 400
            update_fields.append('tier = %s')
            update_values.append(tier_value)

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        update_values.append(tag_id)

        cursor.execute(f'''
            UPDATE tags SET {', '.join(update_fields)}
            WHERE id = %s;
        ''', update_values)

        # Atualizar palavras-chave se fornecidas
        if 'palavras_chave' in data:
            # Remover palavras-chave existentes
            cursor.execute('DELETE FROM tag_palavras_chave WHERE tag_id = %s;', (tag_id,))

            # Adicionar novas palavras-chave
            for palavra in data['palavras_chave']:
                if isinstance(palavra, dict):
                    palavra_chave = palavra.get('palavra', '')
                    peso = palavra.get('peso', 1)
                else:
                    palavra_chave = str(palavra)
                    peso = 1

                if palavra_chave.strip():
                    cursor.execute('''
                        INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                        VALUES (%s, %s, %s);
                    ''', (tag_id, palavra_chave.strip(), peso))

        conn.commit()
        return jsonify({'message': 'Tag atualizada com sucesso!'}), 200

    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar tag: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@app.route('/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def delete_tag(current_user, tag_id):
    try:
        # Verificar se a tag existe
        cursor.execute('SELECT id FROM tags WHERE id = %s;', (tag_id,))
        if not cursor.fetchone():
            return jsonify({'message': 'Tag não encontrada!'}), 404

        # Deletar tag (as palavras-chave serão deletadas em cascata)
        cursor.execute('DELETE FROM tags WHERE id = %s;', (tag_id,))
        conn.commit()

        return jsonify({'message': 'Tag deletada com sucesso!'}), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar tag: {e}")
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
        cursor.execute('''
            INSERT INTO usuarios_monitorados (nome, cargo, departamento_id)
            VALUES (%s, %s, %s)
            RETURNING id, nome, cargo, departamento_id, ativo, created_at;
        ''', (nome, cargo, departamento_id))

        usuario = cursor.fetchone()
        conn.commit()

        return jsonify({
            'message': 'Usuário monitorado criado com sucesso!',
            'id': usuario[0],
            'nome': usuario[1],
            'cargo': usuario[2],
            'departamento_id': usuario[3],
            'ativo': usuario[4],
            'created_at': usuario[5].isoformat() if usuario[5] else None
        }), 201

    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'message': 'Usuário monitorado já existe!'}), 409
    except Exception as e:
        conn.rollback()
        print(f"Erro ao criar usuário monitorado: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@app.route('/usuarios-monitorados/<int:user_id>', methods=['PUT'])
@token_required
def update_monitored_user(current_user, user_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        # Verificar se o usuário existe
        cursor.execute('SELECT id FROM usuarios_monitorados WHERE id = %s;', (user_id,))
        if not cursor.fetchone():
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
            update_fields.append('departamento_id = %s')
            update_values.append(data['departamento_id'])
        if 'ativo' in data:
            update_fields.append('ativo = %s')
            update_values.append(data['ativo'])

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        update_values.append(user_id)

        cursor.execute(f'''
            UPDATE usuarios_monitorados SET {', '.join(update_fields)}
            WHERE id = %s;
        ''', update_values)

        conn.commit()
        return jsonify({'message': 'Usuário monitorado atualizado com sucesso!'}), 200

    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar usuário monitorado: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

# Rota para obter tags de uma atividade específica
@app.route('/atividades/<int:activity_id>/tags', methods=['GET'])
@token_required
def get_activity_tags(current_user, activity_id):
    try:
        cursor.execute('''
            SELECT t.id, t.nome, t.descricao, t.cor, t.produtividade, 
                   at.confidence, d.nome as departamento_nome
            FROM atividade_tags at
            JOIN tags t ON at.tag_id = t.id
            LEFT JOIN departamentos d ON t.departamento_id = d.id
            WHERE at.atividade_id = %s
            ORDER BY at.confidence DESC;
        ''', (activity_id,))

        tags = cursor.fetchall()
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

    # Estatísticas por categoria
    cursor.execute('''
        SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
               SUM(duracao) as tempo_total
        FROM atividades 
        WHERE usuario_monitorado_id = %s 
        GROUP BY categoria 
        ORDER BY total DESC;
    ''', (usuario_monitorado_id,))

    stats_por_categoria = cursor.fetchall()

    # Produtividade por dia da semana
    cursor.execute('''
        SELECT EXTRACT(DOW FROM horario) as dia_semana, 
               produtividade,
               COUNT(*) as total
        FROM atividades 
        WHERE usuario_monitorado_id = %s 
        GROUP BY EXTRACT(DOW FROM horario), produtividade 
        ORDER BY dia_semana;
    ''', (usuario_monitorado_id,))

    produtividade_semanal = cursor.fetchall()

    # Total de atividades hoje
    cursor.execute('''
        SELECT COUNT(*) 
        FROM atividades 
        WHERE usuario_monitorado_id = %s 
        AND DATE(horario) = CURRENT_DATE;
    ''', (usuario_monitorado_id,))

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
            print("🚀 Servidor rodando em http://0.0.0.0:5000")
        else:
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