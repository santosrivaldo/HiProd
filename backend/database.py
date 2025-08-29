
import psycopg2
import psycopg2.pool
import psycopg2.extras
import threading
from .config import Config

# Pool de conexões global
connection_pool = None
pool_lock = threading.Lock()

def create_connection_pool():
    """Cria o pool de conexões com o banco"""
    global connection_pool
    
    if Config.DATABASE_URL:
        print(f"🔌 Criando pool de conexões com DATABASE_URL... (min: {Config.MIN_CONNECTIONS}, max: {Config.MAX_CONNECTIONS})")
        try:
            # Modificar URL para usar connection pooler do Neon se disponível
            if '.neon.tech' in Config.DATABASE_URL and '-pooler' not in Config.DATABASE_URL:
                pooled_url = Config.DATABASE_URL.replace('.neon.tech', '-pooler.neon.tech')
                print("🔄 Usando Neon connection pooler...")
            else:
                pooled_url = Config.DATABASE_URL

            return psycopg2.pool.ThreadedConnectionPool(
                Config.MIN_CONNECTIONS, Config.MAX_CONNECTIONS, pooled_url
            )
        except psycopg2.OperationalError as e:
            print(f"❌ Erro ao criar pool com DATABASE_URL: {e}")
            print("🔄 Tentando com URL original...")
            return psycopg2.pool.ThreadedConnectionPool(
                Config.MIN_CONNECTIONS, Config.MAX_CONNECTIONS, Config.DATABASE_URL
            )
    else:
        # Fallback para variáveis individuais
        print(f"🔌 Criando pool com variáveis individuais... (min: {Config.MIN_CONNECTIONS}, max: {Config.MAX_CONNECTIONS})")
        try:
            return psycopg2.pool.ThreadedConnectionPool(
                Config.MIN_CONNECTIONS, Config.MAX_CONNECTIONS,
                dbname=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                host=Config.DB_HOST,
                port=Config.DB_PORT
            )
        except psycopg2.OperationalError as e:
            print(f"❌ Erro ao criar pool com variáveis individuais: {e}")
            raise e

class DatabaseConnection:
    """Context manager para obter conexões do pool"""
    
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

def get_db_connection():
    """Função para obter conexão simples (para compatibilidade)"""
    global connection_pool
    with pool_lock:
        if connection_pool is None:
            connection_pool = create_connection_pool()
        return connection_pool.getconn()

def init_connection_pool():
    """Inicializa o pool de conexões"""
    global connection_pool
    with pool_lock:
        connection_pool = create_connection_pool()
