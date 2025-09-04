
import uuid
import bcrypt
from .database import DatabaseConnection

def drop_all_tables():
    """Função para deletar todas as tabelas"""
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

def init_db():
    """Função para inicializar as tabelas se não existirem"""
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
            
            # Adicionar colunas de horário de trabalho se não existirem
            columns_to_add = [
                ('horario_inicio_trabalho', "TIME DEFAULT '09:00:00'"),
                ('horario_fim_trabalho', "TIME DEFAULT '18:00:00'"),
                ('dias_trabalho', "VARCHAR(20) DEFAULT '1,2,3,4,5'"),
                ('monitoramento_ativo', "BOOLEAN DEFAULT TRUE")
            ]
            
            for column_name, column_type in columns_to_add:
                db.cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='usuarios_monitorados' AND column_name='{column_name}';
                """)
                
                if not db.cursor.fetchone():
                    print(f"🔧 Adicionando coluna {column_name} à tabela usuarios_monitorados...")
                    db.cursor.execute(f"ALTER TABLE usuarios_monitorados ADD COLUMN {column_name} {column_type};")
                    print(f"✅ Coluna {column_name} adicionada com sucesso!")

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

            # Inserir usuário admin padrão se não existir
            db.cursor.execute("SELECT COUNT(*) FROM usuarios WHERE nome = 'admin';")
            admin_count_result = db.cursor.fetchone()
            admin_count = admin_count_result[0] if admin_count_result else 0

            if admin_count == 0:
                print("👤 Criando usuário admin padrão...")
                admin_password = "Brasil@1402"  # Mesma senha do agente
                hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
                admin_id = uuid.uuid4()
                
                # Buscar ID do departamento TI
                db.cursor.execute("SELECT id FROM departamentos WHERE nome = 'TI';")
                ti_dept_result = db.cursor.fetchone()
                ti_dept_id = ti_dept_result[0] if ti_dept_result else None

                db.cursor.execute('''
                    INSERT INTO usuarios (id, nome, senha, email, departamento_id)
                    VALUES (%s, %s, %s, %s, %s);
                ''', (admin_id, 'admin', hashed_password.decode('utf-8'), 'admin@empresa.com', ti_dept_id))
                
                print("✅ Usuário admin criado (usuario: admin, senha: Brasil@1402)")
            else:
                print("⏭️ Usuário admin já existe...")

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
