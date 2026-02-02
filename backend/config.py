
import os
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

class Config:
    # Configuração JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    
    # Configuração do banco (compatível com Docker e local)
    DATABASE_URL = os.getenv('DATABASE_URL')
    DB_NAME = os.getenv("DB_NAME", "hiprod")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    # No Docker, o host do serviço do Postgres é 'db'
    DB_HOST = os.getenv("DB_HOST", "db")
    try:
        DB_PORT = int(os.getenv("DB_PORT", "5432"))
    except ValueError:
        DB_PORT = 5432

    # Se DATABASE_URL não estiver definido, montar a partir das variáveis individuais
    if not DATABASE_URL and all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Pool de conexões
    MIN_CONNECTIONS = int(os.getenv('DB_MIN_CONNECTIONS', 2))
    MAX_CONNECTIONS = int(os.getenv('DB_MAX_CONNECTIONS', 20))
    
    # Token de API padrão do sistema (gerado automaticamente)
    SYSTEM_API_TOKEN = None  # Será gerado na primeira inicialização