#!/bin/bash
# Script de validação de variáveis de ambiente para Docker Compose
# Verifica se as variáveis obrigatórias estão definidas antes de iniciar os containers

set -e

echo "🔍 Verificando variáveis de ambiente obrigatórias..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Verificar se arquivo .env existe
if [ ! -f .env ]; then
    echo -e "${RED}❌ Arquivo .env não encontrado!${NC}"
    echo -e "${YELLOW}📝 Crie um arquivo .env na raiz do projeto com as seguintes variáveis:${NC}"
    echo ""
    echo "DB_USER=seu_usuario"
    echo "DB_PASSWORD=sua_senha_forte"
    echo "JWT_SECRET_KEY=sua_chave_secreta_forte"
    echo ""
    echo "Exemplo completo:"
    echo "cat > .env << 'EOF'"
    echo "DB_USER=hiprod_user"
    echo "DB_PASSWORD=\$(openssl rand -base64 32)"
    echo "DB_NAME=hiprod"
    echo "JWT_SECRET_KEY=\$(openssl rand -hex 32)"
    echo "EOF"
    exit 1
fi

# Carregar variáveis do .env
set -a
source .env
set +a

# Verificar variáveis obrigatórias
check_var() {
    local var_name=$1
    local var_value=${!var_name:-}
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}❌ ${var_name} não está definido no arquivo .env${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    
    # Verificar se não é valor padrão inseguro
    case $var_name in
        DB_PASSWORD)
            if [ "$var_value" = "postgres" ] || [ "$var_value" = "password" ] || [ ${#var_value} -lt 12 ]; then
                echo -e "${YELLOW}⚠️  ${var_name} parece ser uma senha fraca ou muito curta (mínimo 12 caracteres recomendado)${NC}"
            fi
            ;;
        JWT_SECRET_KEY)
            if [ "$var_value" = "change-me" ] || [ "$var_value" = "your-secret-key" ] || [ ${#var_value} -lt 32 ]; then
                echo -e "${YELLOW}⚠️  ${var_name} parece ser uma chave fraca ou muito curta (mínimo 32 caracteres recomendado)${NC}"
            fi
            ;;
    esac
    
    echo -e "${GREEN}✓ ${var_name} está definido${NC}"
    return 0
}

# Verificar variáveis obrigatórias
check_var "DB_USER"
check_var "DB_PASSWORD"
check_var "JWT_SECRET_KEY"

# Verificar variáveis opcionais (com defaults)
if [ -z "${DB_NAME:-}" ]; then
    echo -e "${YELLOW}ℹ️  DB_NAME não definido, usando padrão: hiprod${NC}"
fi

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Todas as variáveis obrigatórias estão definidas!${NC}"
    echo -e "${GREEN}🚀 Você pode executar: docker compose up --build${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Erros encontrados. Corrija o arquivo .env antes de continuar.${NC}"
    exit 1
fi

