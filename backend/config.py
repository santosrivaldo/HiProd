
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

    # Pasta para upload de frames de tela (timeline) - legado
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'screen_frames'))

    # Google Drive - armazenamento de imagens (screenshots e timeline)
    GDRIVE_ENABLED = os.getenv('GDRIVE_ENABLED', 'false').lower() == 'true'
    # Tipo de autenticação: 'service_account' ou 'oauth'
    GDRIVE_AUTH_TYPE = os.getenv('GDRIVE_AUTH_TYPE', 'service_account').strip().lower()
    # Caminho para o arquivo JSON da service account (modo service_account)
    GDRIVE_SERVICE_ACCOUNT_FILE = os.getenv('GDRIVE_SERVICE_ACCOUNT_FILE', '').strip()
    # Credenciais OAuth (modo oauth) para usar o Drive da conta rivaldo.santos@...
    GDRIVE_CLIENT_ID = os.getenv('GDRIVE_CLIENT_ID', '').strip()
    GDRIVE_CLIENT_SECRET = os.getenv('GDRIVE_CLIENT_SECRET', '').strip()
    GDRIVE_REFRESH_TOKEN = os.getenv('GDRIVE_REFRESH_TOKEN', '').strip()
    # Pasta raiz onde serão criadas as pastas por usuário (white label por cliente pode usar outra raiz)
    GDRIVE_ROOT_FOLDER_ID = os.getenv('GDRIVE_ROOT_FOLDER_ID', '').strip()
    # Pasta temporária para fila de upload (arquivos são removidos após envio ao Drive)
    GDRIVE_UPLOAD_QUEUE_DIR = os.getenv(
        'GDRIVE_UPLOAD_QUEUE_DIR',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'drive_queue')
    ).strip()
    # Cache compacto por dia no servidor: YYYY-MM-DD/usuario_id/arquivos. De madrugada envia ao Drive e apaga.
    GDRIVE_DAY_CACHE_DIR = os.getenv(
        'GDRIVE_DAY_CACHE_DIR',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'drive_day_cache')
    ).strip()
    # Horário (Brasília) para rodar o job de envio do dia anterior ao Drive (ex: 1 = 01:00)
    GDRIVE_MIDNIGHT_UPLOAD_HOUR = int(os.getenv('GDRIVE_MIDNIGHT_UPLOAD_HOUR', '1'))

    # SSO: domínio de e-mail corporativo (nome do usuário = parte local do e-mail)
    # Ex.: rivaldo.santos -> rivaldo.santos@grupohi.com.br
    SSO_EMAIL_DOMAIN = os.getenv('SSO_EMAIL_DOMAIN', 'grupohi.com.br')
    SSO_ENABLED = os.getenv('SSO_ENABLED', 'true').lower() == 'true'

    # Microsoft Entra (Azure AD) OAuth2
    SSO_MICROSOFT_CLIENT_ID = os.getenv('SSO_MICROSOFT_CLIENT_ID', '')
    SSO_MICROSOFT_CLIENT_SECRET = os.getenv('SSO_MICROSOFT_CLIENT_SECRET', '')
    SSO_MICROSOFT_TENANT = os.getenv('SSO_MICROSOFT_TENANT', 'common')  # common, ou tenant id
    SSO_REDIRECT_URI = os.getenv('SSO_REDIRECT_URI', '')  # ex: https://hiprod.grupohi.com.br/api/sso/callback
    FRONTEND_URL = os.getenv('FRONTEND_URL', '')  # ex: https://hiprod.grupohi.com.br para redirecionar após SSO

    # Bitrix24 – expediente (Timeman): verificar se usuário está ativo antes de enviar atividades
    BITRIX_ENABLED = os.getenv('BITRIX_ENABLED', 'false').lower() == 'true'
    # URL do webhook (ex: https://empresa.bitrix24.com.br/rest/1/SEU_CODIGO) – sem barra no final
    BITRIX_WEBHOOK_URL = (os.getenv('BITRIX_WEBHOOK_URL') or '').strip()