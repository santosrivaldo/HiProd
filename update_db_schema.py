
#!/usr/bin/env python3
"""
Script para atualizar o schema do banco de dados
Adiciona as colunas 'domain' e 'application' na tabela atividades
"""

import psycopg2
from dotenv import load_dotenv
import os

# Carregar variáveis do arquivo .env
load_dotenv(override=True)

def update_database_schema():
    """Adiciona as novas colunas domain e application se não existirem"""
    try:
        # Configurações do banco
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        if not DATABASE_URL:
            print("❌ DATABASE_URL não encontrada no .env")
            return
        
        # Conectar ao banco
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("🔧 Atualizando schema do banco de dados...")
        
        # Verificar se as colunas já existem
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'atividades' 
            AND column_name IN ('domain', 'application');
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Adicionar coluna domain se não existir
        if 'domain' not in existing_columns:
            print("📋 Adicionando coluna 'domain'...")
            cursor.execute("""
                ALTER TABLE atividades 
                ADD COLUMN domain VARCHAR(255);
            """)
            print("✅ Coluna 'domain' adicionada")
        else:
            print("⏭️ Coluna 'domain' já existe")
        
        # Adicionar coluna application se não existir
        if 'application' not in existing_columns:
            print("📋 Adicionando coluna 'application'...")
            cursor.execute("""
                ALTER TABLE atividades 
                ADD COLUMN application VARCHAR(100);
            """)
            print("✅ Coluna 'application' adicionada")
        else:
            print("⏭️ Coluna 'application' já existe")
        
        # Criar índices para melhor performance
        print("📋 Criando índices...")
        
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_atividades_domain 
                ON atividades(domain);
            """)
            print("✅ Índice para 'domain' criado")
        except:
            print("⏭️ Índice para 'domain' já existe")
        
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_atividades_application 
                ON atividades(application);
            """)
            print("✅ Índice para 'application' criado")
        except:
            print("⏭️ Índice para 'application' já existe")
        
        # Commit das mudanças
        conn.commit()
        cursor.close()
        conn.close()
        
        print("🎉 Schema atualizado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao atualizar schema: {e}")

if __name__ == "__main__":
    update_database_schema()
