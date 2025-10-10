import os
import sys
import psycopg2
from flask import Flask, request, abort
from flask_cors import CORS
from backend.config import Config
from backend.database import init_connection_pool
from backend.models import init_db, drop_all_tables
from backend.routes.auth_routes import auth_bp
from backend.routes.activity_routes import activity_bp
from backend.routes.user_routes import user_bp
from backend.routes.department_routes import department_bp
from backend.routes.tag_routes import tag_bp
from backend.routes.category_routes import category_bp
from backend.routes.escala_routes import escala_bp
from backend.routes.legacy_routes import legacy_bp

app = Flask(__name__)
CORS(app)

# Middleware para detectar e logar tentativas SSL
@app.before_request
def log_requests():
    # Log detalhado da requisição
    print(f"📥 {request.method} {request.path} de {request.remote_addr}")
    print(f"   Headers: {dict(request.headers)}")
    print(f"   Secure: {request.is_secure}")
    print(f"   Scheme: {request.scheme}")

# Handler para erros SSL/TLS (conexões malformadas)
@app.errorhandler(400)
def handle_ssl_error(error):
    print(f"🚫 Erro 400 - Possível tentativa SSL de {request.remote_addr}")
    return {"error": "Este servidor aceita apenas HTTP", "message": "Use http:// em vez de https://"}, 400

# Configuração JWT
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = Config.JWT_ACCESS_TOKEN_EXPIRES

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(user_bp)
app.register_blueprint(department_bp)
app.register_blueprint(tag_bp)
app.register_blueprint(category_bp)
app.register_blueprint(escala_bp)
app.register_blueprint(legacy_bp)

if __name__ == '__main__':
    try:
        # Aviso apenas (não falhar) se .env não existe
        if not os.path.exists('.env'):
            print("⚠️ .env não encontrado; usando variáveis de ambiente atuais.")

        # Garantir que temos string de conexão
        if not Config.DATABASE_URL:
            print("❌ Configuração de banco ausente. Defina DATABASE_URL ou as variáveis DB_HOST/DB_USER/DB_PASSWORD/DB_NAME/DB_PORT.")
            sys.exit(1)

        # Reset opcional
        if len(sys.argv) > 1 and sys.argv[1] == '--reset':
            print("🔄 Modo reset ativado - Excluindo e recriando banco...")
            drop_all_tables()
            init_db()
            print("✅ Banco de dados resetado com sucesso!")
        else:
            init_db()
            print("✅ Banco de dados inicializado com sucesso!")

        # Inicializar pool de conexões
        init_connection_pool()

        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_PORT', '8000'))
        debug = os.getenv('FLASK_DEBUG', '0') == '1'

        print(f"🚀 Servidor rodando em http://{host}:{port}")
        print(f"🔌 Pool de conexões ativo com {Config.MIN_CONNECTIONS}-{Config.MAX_CONNECTIONS} conexões")

        app.run(host=host, port=port, debug=debug)

    except psycopg2.OperationalError as e:
        print(f"❌ Erro de conexão com o banco PostgreSQL: {e}")
        print("\n📋 Checklist:")
        print("1. Variáveis de ambiente do banco (ou DATABASE_URL) estão corretas?")
        print("2. Serviço do Postgres acessível (em Docker, host 'db')?")
        print("3. Banco existe e credenciais válidas?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)