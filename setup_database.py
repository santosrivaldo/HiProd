
#!/usr/bin/env python3
"""
Script para inicializar as tabelas no banco de dados externo
Execute este script após configurar o .env com as credenciais do seu banco
"""

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

# Carregar variáveis do arquivo .env
load_dotenv(override=True)

def create_tables():
    # Conectar ao banco
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
    
    cursor = conn.cursor()
    
    print("Criando tabelas...")
    
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
    
    # Tabela de atividades
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
    
    # Verificar e adicionar colunas que podem estar faltando nas tabelas existentes
    try:
        # Adicionar colunas faltantes na tabela usuarios
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS senha VARCHAR(255);")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email VARCHAR(255);")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_login TIMESTAMP;")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        
        # Adicionar colunas faltantes na tabela atividades
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) DEFAULT 'unclassified';")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS produtividade VARCHAR(20) DEFAULT 'neutral';")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS titulo_janela VARCHAR(500);")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS duracao INTEGER DEFAULT 0;")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS ip_address INET;")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS user_agent TEXT;")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        cursor.execute("ALTER TABLE atividades ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        
        # Alterar tipo da coluna ociosidade se necessário
        cursor.execute("ALTER TABLE atividades ALTER COLUMN ociosidade TYPE INTEGER USING ociosidade::integer;")
        cursor.execute("ALTER TABLE atividades ALTER COLUMN ociosidade SET DEFAULT 0;")
        
        print("✅ Colunas verificadas e atualizadas com sucesso!")
        
    except Exception as e:
        print(f"⚠️  Aviso ao adicionar/modificar colunas: {e}")
        print("   Algumas modificações podem não ser necessárias, continuando...")
    
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
    
    # Criar índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_usuario_id ON atividades(usuario_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_horario ON atividades(horario DESC);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_atividades_categoria ON atividades(categoria);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_nome ON usuarios(nome);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo);')
    
    # Inserir dados padrão
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
    cursor.close()
    conn.close()
    
    print("✅ Tabelas criadas com sucesso!")
    print("✅ Dados padrão inseridos!")

if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        print("Verifique suas credenciais no arquivo .env")
