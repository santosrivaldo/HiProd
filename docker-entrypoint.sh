#!/usr/bin/env bash
set -euo pipefail

# Default envs
: "${DB_HOST:=db}"
: "${DB_PORT:=5432}"
: "${DB_USER:=postgres}"
: "${DB_PASSWORD:=postgres}"
: "${DB_NAME:=hiprod}"

echo "🔎 Aguardando banco ${DB_HOST}:${DB_PORT}..."
until python - <<'PY'
import psycopg2, os, sys
try:
    psycopg2.connect(host=os.environ['DB_HOST'], port=os.environ['DB_PORT'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], dbname=os.environ['DB_NAME']).close()
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
PY
 do
  echo "⏳ Banco ainda indisponível..."
  sleep 2
done

# Inicializar/migrar banco
echo "🗃️ Aplicando migrações/inicialização"
python - <<'PY'
from backend.models import init_db
from backend.database import init_connection_pool

init_db()
init_connection_pool()
print('✅ Banco pronto!')
PY

# Start app
echo "🚀 Iniciando API..."
exec python app.py
