import os
import sys
import psycopg2
from flask import Flask
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
from backend.routes.legacy_routes import legacy_bp

app = Flask(__name__)
CORS(app)

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
app.register_blueprint(legacy_bp)

if __name__ == '__main__':
    try:
        # Verificar se o arquivo .env existe
        if not os.path.exists('.env'):
            print("❌ Arquivo .env não encontrado!")
            print("Copie o arquivo .env.example para .env e configure suas credenciais.")
            exit(1)

        # Verificar variáveis de ambiente essenciais
        if not Config.DATABASE_URL and not all([Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD]):
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

        # Inicializar pool de conexões
        init_connection_pool()

        print(f"🚀 Servidor rodando em http://0.0.0.0:5000")
        print(f"🔌 Pool de conexões ativo com {Config.MIN_CONNECTIONS}-{Config.MAX_CONNECTIONS} conexões")

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