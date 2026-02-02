# Backend HiProd

Sistema de monitoramento de produtividade - Backend API

## 🚀 Início Rápido

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env

# 3. Inicializar banco de dados
python app.py

# 4. Servidor rodando em http://localhost:8000
```

## 📚 Documentação Completa

Consulte [DOCUMENTACAO.md](./DOCUMENTACAO.md) para documentação completa.

## 🔑 Autenticação

### JWT (Usuários do Sistema)
```bash
POST /login
{
  "nome": "usuario",
  "senha": "senha123"
}
```

### API Token (Integrações Externas)
```bash
# Criar token via interface web ou:
POST /api-tokens
Authorization: Bearer <jwt_token>
{
  "nome": "Token Integração",
  "permissions": [...]
}
```

## 📡 Endpoints Principais

- **Autenticação:** `/login`, `/register`, `/profile`
- **Atividades:** `/atividades`, `/atividade`
- **Usuários:** `/usuarios`, `/usuarios-monitorados`
- **API V1:** `/api/v1/atividades`, `/api/v1/usuarios`, `/api/v1/estatisticas`
- **Tokens:** `/api-tokens`

## 🛠️ Tecnologias

- Python 3.8+
- Flask
- PostgreSQL
- JWT
- psycopg2

## 📖 Mais Informações

- [Documentação Completa](./DOCUMENTACAO.md)
- [Sistema de Tokens](./DOCUMENTACAO.md#sistema-de-tokens-de-api)
- [Endpoints da API](./DOCUMENTACAO.md#endpoints-da-api)

