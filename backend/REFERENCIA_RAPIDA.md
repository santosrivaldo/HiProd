# Referência Rápida - Backend HiProd

## 🔐 Autenticação

### Headers

```http
# JWT Token
Authorization: Bearer <jwt_token>

# API Token
Authorization: <api_token>
# OU
X-API-Token: <api_token>

# Agent (Agente de Monitoramento)
X-User-Name: nome_usuario_windows
```

## 📋 Endpoints Principais

### Autenticação

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| POST | `/login` | - | Login e obter JWT |
| GET | `/profile` | JWT | Perfil do usuário |
| POST | `/verify-token` | - | Verificar token |

### Atividades

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| GET | `/atividades` | JWT/API | Listar atividades |
| POST | `/atividade` | Agent | Criar atividade |
| GET | `/atividades/<id>` | JWT/API | Obter atividade |
| PATCH | `/atividades/<id>` | JWT | Atualizar atividade |
| DELETE | `/atividades/<id>` | JWT | Excluir atividade |

### Usuários

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| GET | `/usuarios` | JWT/API | Listar usuários |
| POST | `/usuarios` | JWT | Criar usuário |
| GET | `/usuarios/<id>` | JWT/API | Obter usuário |
| PUT | `/usuarios/<id>` | JWT | Atualizar usuário |
| DELETE | `/usuarios/<id>` | JWT | Excluir usuário |
| GET | `/usuarios-monitorados` | Agent/JWT | Listar usuários monitorados |

### API V1 (Externa)

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| GET | `/api/v1/health` | - | Health check |
| POST | `/api/v1/atividades` | API Token | Buscar atividades |
| GET | `/api/v1/usuarios` | API Token | Listar usuários |
| POST | `/api/v1/estatisticas` | API Token | Estatísticas |

### Tokens de API

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| GET | `/api-tokens` | JWT | Listar tokens |
| POST | `/api-tokens` | JWT | Criar token |
| PUT | `/api-tokens/<id>` | JWT | Atualizar token |
| DELETE | `/api-tokens/<id>` | JWT | Excluir token |
| POST | `/api-tokens/<id>/toggle` | JWT | Ativar/desativar |
| GET | `/api-tokens/endpoints` | JWT | Endpoints disponíveis |

## 🔑 Decorators de Autenticação

```python
# JWT Token (usuários do sistema)
@token_required
def minha_rota(current_user):
    # current_user: (id, nome, email, ativo, departamento_id)
    pass

# Agent (agente de monitoramento)
@agent_required
def receber_atividade(current_user):
    # Aceita JWT ou X-User-Name
    pass

# API Token (integrações externas)
@api_token_required
def endpoint_externo(token_data):
    # token_data: (token_id, token_nome, ativo, expires_at, created_by)
    pass
```

## 📦 Exemplos de Requisições

### Login

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"nome": "usuario", "senha": "senha123"}'
```

### Listar Atividades (JWT)

```bash
curl -X GET http://localhost:8000/atividades \
  -H "Authorization: Bearer <jwt_token>"
```

### Buscar Atividades (API Token)

```bash
curl -X POST http://localhost:8000/api/v1/atividades \
  -H "Authorization: <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "usuario.monitorado",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

### Criar Token de API

```bash
curl -X POST http://localhost:8000/api-tokens \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Token Integração",
    "descricao": "Token para sistema externo",
    "expires_days": 365,
    "permissions": [
      {"endpoint": "/api/v1/atividades", "method": "POST"},
      {"endpoint": "/api/v1/usuarios", "method": "GET"}
    ]
  }'
```

## 🗄️ Banco de Dados

### Tabelas Principais

- `usuarios` - Usuários do sistema
- `usuarios_monitorados` - Usuários monitorados
- `atividades` - Registros de atividades
- `departamentos` - Departamentos
- `tags` - Tags de classificação
- `categorias` - Categorias de apps
- `escalas` - Escalas de trabalho
- `api_tokens` - Tokens de API
- `api_token_permissions` - Permissões dos tokens

### Pool de Conexões

```python
from backend.database import DatabaseConnection

with DatabaseConnection() as db:
    db.cursor.execute("SELECT * FROM usuarios")
    results = db.cursor.fetchall()
```

## ⚙️ Variáveis de Ambiente

```env
# JWT
JWT_SECRET_KEY=your-secret-key

# Banco de Dados
DATABASE_URL=postgresql://user:pass@host:port/db
# OU
DB_HOST=db
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=hiprod

# Pool
DB_MIN_CONNECTIONS=2
DB_MAX_CONNECTIONS=20

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=0
```

## 🐛 Troubleshooting

### Token de API inválido
- Verificar se token existe no banco
- Verificar se está ativo
- Verificar permissões do token

### Erro de conexão com banco
- Verificar se PostgreSQL está rodando
- Verificar credenciais no .env
- Testar conexão: `psql -h host -U user -d database`

### Token JWT expirado
- Fazer login novamente
- Verificar JWT_SECRET_KEY

## 📚 Mais Informação

- [Documentação Completa](./DOCUMENTACAO.md)
- [README](./README.md)

