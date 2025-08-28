
#!/usr/bin/env python3
"""
Script para testar a conexão com o banco de dados
"""

import psycopg2
from dotenv import load_dotenv
import os

# Forçar recarregamento das variáveis de ambiente
load_dotenv(override=True)

def test_connection():
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL não encontrada no arquivo .env")
            return
        
        print(f"🔍 Testando conexão...")
        print(f"📍 Host extraído da URL: {database_url.split('@')[1].split(':')[0] if '@' in database_url else 'N/A'}")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"📊 Versão do PostgreSQL: {version[0]}")
        
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"❌ Erro de conexão: {e}")
        print("\n🔧 Soluções:")
        print("1. Verifique usuário e senha no painel do Neon")
        print("2. Confirme se o banco de dados existe")
        print("3. Verifique se o IP está liberado (se aplicável)")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    test_connection()
