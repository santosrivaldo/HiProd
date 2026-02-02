# Documentação do Backend - HiProd

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Configuração](#configuração)
4. [Estrutura do Projeto](#estrutura-do-projeto)
5. [Autenticação e Autorização](#autenticação-e-autorização)
6. [Banco de Dados](#banco-de-dados)
7. [Endpoints da API](#endpoints-da-api)
8. [Sistema de Tokens de API](#sistema-de-tokens-de-api)
9. [Deploy e Execução](#deploy-e-execução)
10. [Exemplos de Uso](#exemplos-de-uso)

---

## Visão Geral

O HiProd é um sistema de monitoramento de produtividade que rastreia atividades de usuários, categoriza aplicações e gera estatísticas de produtividade. O backend é construído com **Flask** (Python) e utiliza **PostgreSQL** como banco de dados.

### Tecnologias Principais

- **Python 3.8+**
- **Flask** - Framework web
- **PostgreSQL** - Banco de dados relacional
- **JWT** - Autenticação de usuários
- **psycopg2** - Driver PostgreSQL
- **Flask-CORS** - Suporte a CORS

---

## Arquitetura

### Padrão de Arquitetura

O sistema utiliza uma arquitetura em camadas com separação de responsabilidades:

```
┌─────────────────────────────────────┐
│         Flask Application           │
│         (app.py)                    │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                 │
┌──────▼──────┐  ┌───────▼────────┐
│   Routes    │  │   Auth Layer   │
│ (Blueprints)│  │  (Decorators)   │
└──────┬──────┘  └───────┬─────────┘
       │                 │
       └───────┬─────────┘
               │
       ┌───────▼────────┐
       │   Database     │
       │  Connection    │
       │     Pool       │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │   PostgreSQL   │
       │    Database    │
       └────────────────┘
```

### Componentes Principais

1. **app.py** - Aplicação Flask principal
2. **backend/auth.py** - Sistema de autenticação e autorização
3. **backend/models.py** - Modelos e esquema do banco de dados
4. **backend/database.py** - Gerenciamento de conexões
5. **backend/routes/** - Blueprints com endpoints da API
6. **backend/utils.py** - Funções utilitárias

---

## Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# JWT
JWT_SECRET_KEY=your-secret-key-change-this-in-production

# Banco de Dados
DATABASE_URL=postgresql://user:password@host:port/database
# OU use variáveis individuais:
DB_HOST=db
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=hiprod

# Pool de Conexões
DB_MIN_CONNECTIONS=2
DB_MAX_CONNECTIONS=20

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=0
```

### Instalação de Dependências

```bash
pip install -r requirements.txt
```

### Inicialização do Banco de Dados

```bash
# Inicialização normal
python app.py

# Reset completo (apaga todas as tabelas e recria)
python app.py --reset
```

---

## Estrutura do Projeto

```
backend/
├── __init__.py
├── auth.py                 # Autenticação e decorators
├── config.py               # Configurações
├── database.py             # Pool de conexões
├── models.py               # Modelos e schema do banco
├── utils.py                # Funções utilitárias
├── routes/
│   ├── auth_routes.py      # Autenticação (login, register)
│   ├── activity_routes.py  # Atividades de usuários
│   ├── user_routes.py      # Usuários e usuários monitorados
│   ├── department_routes.py # Departamentos
│   ├── tag_routes.py       # Tags
│   ├── category_routes.py  # Categorias
│   ├── escala_routes.py    # Escalas de trabalho
│   ├── token_routes.py     # Gerenciamento de tokens API
│   ├── api_v1_routes.py    # API V1 (endpoints externos)
│   └── legacy_routes.py    # Endpoints legados
└── DOCUMENTACAO.md         # Esta documentação
```

---

## Autenticação e Autorização

### Tipos de Autenticação

O sistema suporta três tipos de autenticação:

#### 1. JWT (JSON Web Token)

Usado para autenticação de usuários do sistema web.

**Decorator:** `@token_required`

**Como usar:**
```python
from backend.auth import token_required

@token_required
def minha_rota(current_user):
    # current_user é uma tupla: (id, nome, email, ativo, departamento_id)
    user_id = current_user[0]
    user_name = current_user[1]
    # ...
```

**Header necessário:**
```
Authorization: Bearer <jwt_token>
```

#### 2. Agent Required

Usado para requisições do agente de monitoramento. Aceita token JWT OU nome do usuário no header.

**Decorator:** `@agent_required`

**Como usar:**
```python
from backend.auth import agent_required

@agent_required
def receber_atividade(current_user):
    # current_user pode ser usuário do sistema ou usuário monitorado
    # ...
```

**Headers aceitos:**
```
Authorization: Bearer <jwt_token>
# OU
X-User-Name: nome_do_usuario_windows
```

#### 3. API Token

Usado para integrações externas. Tokens com permissões específicas por endpoint.

**Decorator:** `@api_token_required`

**Como usar:**
```python
from backend.auth import api_token_required

@api_token_required
def endpoint_externo(token_data):
    # token_data é uma tupla: (token_id, token_nome, ativo, expires_at, created_by)
    token_id = token_data[0]
    # ...
```

**Headers aceitos:**
```
Authorization: <api_token>
# OU
X-API-Token: <api_token>
```

### Geração de Tokens JWT

```python
from backend.auth import generate_jwt_token

# Gerar token para um usuário
token = generate_jwt_token(user_id)
```

### Verificação de Tokens JWT

```python
from backend.auth import verify_jwt_token

# Verificar e obter user_id
user_id = verify_jwt_token(token)
if user_id:
    # Token válido
    pass
```

---

## Banco de Dados

### Schema Principal

#### Tabelas Principais

1. **usuarios** - Usuários do sistema (admin, gestores)
2. **usuarios_monitorados** - Usuários monitorados pelo agente
3. **atividades** - Registros de atividades dos usuários
4. **departamentos** - Departamentos da empresa
5. **tags** - Tags para classificação
6. **categorias** - Categorias de aplicações
7. **escalas** - Escalas de trabalho
8. **api_tokens** - Tokens de API para integrações
9. **api_token_permissions** - Permissões dos tokens

### Pool de Conexões

O sistema utiliza um pool de conexões para melhor performance:

```python
from backend.database import DatabaseConnection

# Uso automático do pool
with DatabaseConnection() as db:
    db.cursor.execute("SELECT * FROM usuarios")
    results = db.cursor.fetchall()
```

**Configuração do Pool:**
- Mínimo: 2 conexões
- Máximo: 20 conexões
- Configurável via variáveis de ambiente

---

## Endpoints da API

### Autenticação

#### POST `/login`
Autentica um usuário e retorna um token JWT.

**Body:**
```json
{
  "nome": "usuario",
  "senha": "senha123"
}
```

**Resposta:**
```json
{
  "usuario_id": "uuid",
  "usuario": "nome",
  "token": "jwt_token"
}
```

#### POST `/register`
Registro de novos usuários (desabilitado por padrão).

#### GET `/profile`
Obtém perfil do usuário autenticado.

**Autenticação:** JWT Token

#### POST `/verify-token`
Verifica se um token JWT é válido.

---

### Atividades

#### GET `/atividades`
Lista atividades com filtros opcionais.

**Query Parameters:**
- `usuario_id` - Filtrar por usuário
- `data_inicio` - Data de início (ISO 8601)
- `data_fim` - Data de fim (ISO 8601)
- `categoria` - Filtrar por categoria
- `limit` - Limite de resultados
- `offset` - Offset para paginação

**Autenticação:** JWT Token ou API Token

#### POST `/atividade`
Cria uma nova atividade (usado pelo agente).

**Body:**
```json
{
  "usuario_monitorado_id": 1,
  "active_window": "Chrome - Google",
  "titulo_janela": "Google",
  "ociosidade": 0,
  "duracao": 10,
  "domain": "google.com",
  "application": "Chrome"
}
```

**Autenticação:** Agent Required (JWT ou X-User-Name)

#### GET `/atividades/<id>`
Obtém uma atividade específica.

#### PATCH `/atividades/<id>`
Atualiza uma atividade.

#### DELETE `/atividades/<id>`
Exclui uma atividade.

---

### Usuários

#### GET `/usuarios`
Lista todos os usuários do sistema.

**Autenticação:** JWT Token ou API Token

#### GET `/usuarios/<id>`
Obtém um usuário específico.

#### POST `/usuarios`
Cria um novo usuário.

#### PUT `/usuarios/<id>`
Atualiza um usuário.

#### DELETE `/usuarios/<id>`
Exclui um usuário.

#### GET `/usuarios-monitorados`
Lista usuários monitorados. Aceita query parameter `nome` para buscar/criar.

**Query Parameters:**
- `nome` - Nome do usuário (opcional)

**Autenticação:** Agent Required ou JWT Token

#### POST `/usuarios-monitorados`
Cria um novo usuário monitorado.

---

### Departamentos

#### GET `/departamentos`
Lista todos os departamentos.

**Autenticação:** JWT Token ou API Token

#### POST `/departamentos`
Cria um novo departamento.

#### GET `/departamentos/<id>/configuracoes`
Obtém configurações de um departamento.

#### POST `/departamentos/<id>/configuracoes`
Atualiza configurações de um departamento.

---

### Tags

#### GET `/tags`
Lista todas as tags.

**Autenticação:** JWT Token ou API Token

#### POST `/tags`
Cria uma nova tag.

#### PUT `/tags/<id>`
Atualiza uma tag.

#### DELETE `/tags/<id>`
Exclui uma tag.

---

### Categorias

#### GET `/categorias`
Lista todas as categorias.

**Autenticação:** JWT Token ou API Token

#### POST `/categorias`
Cria uma nova categoria.

---

### Escalas

#### GET `/escalas`
Lista todas as escalas de trabalho.

**Autenticação:** JWT Token ou API Token

#### POST `/escalas`
Cria uma nova escala.

#### PUT `/escalas/<id>`
Atualiza uma escala.

#### DELETE `/escalas/<id>`
Exclui uma escala.

---

### API V1 - Endpoints Externos

Todos os endpoints V1 requerem **API Token** com permissões específicas.

#### GET `/api/v1/health`
Health check (não requer autenticação).

**Resposta:**
```json
{
  "version": "v1",
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### POST `/api/v1/atividades`
Busca atividades por usuário e período.

**Body:**
```json
{
  "usuario": "nome_ou_id",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Resposta:**
```json
{
  "version": "v1",
  "usuario": "nome",
  "periodo": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  },
  "total_atividades": 100,
  "atividades": [...]
}
```

**Autenticação:** API Token com permissão `/api/v1/atividades` (POST)

#### GET `/api/v1/usuarios`
Lista usuários monitorados.

**Resposta:**
```json
{
  "version": "v1",
  "total_usuarios": 10,
  "usuarios": [...]
}
```

**Autenticação:** API Token com permissão `/api/v1/usuarios` (GET)

#### POST `/api/v1/estatisticas`
Obtém estatísticas de um usuário.

**Body:**
```json
{
  "usuario": "nome_ou_id",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Resposta:**
```json
{
  "version": "v1",
  "usuario": "nome",
  "periodo": {...},
  "total_atividades": 100,
  "categorias": [...]
}
```

**Autenticação:** API Token com permissão `/api/v1/estatisticas` (POST)

---

## Sistema de Tokens de API

### Visão Geral

O sistema de tokens de API permite criar tokens com permissões específicas por endpoint para integrações externas.

### Gerenciamento de Tokens

#### GET `/api-tokens`
Lista todos os tokens de API.

**Autenticação:** JWT Token

**Resposta:**
```json
[
  {
    "id": 1,
    "nome": "Token Integração Externa",
    "descricao": "Token para integração com sistema externo",
    "token": "abc123...",
    "ativo": true,
    "created_by": "uuid",
    "created_by_name": "Admin",
    "created_at": "2024-01-01T00:00:00",
    "last_used_at": "2024-01-15T10:30:00",
    "expires_at": null,
    "permissions": [
      {"endpoint": "/api/v1/atividades", "method": "POST"},
      {"endpoint": "/api/v1/usuarios", "method": "GET"}
    ]
  }
]
```

#### POST `/api-tokens`
Cria um novo token de API.

**Body:**
```json
{
  "nome": "Token Integração",
  "descricao": "Descrição do token",
  "expires_days": 30,
  "permissions": [
    {"endpoint": "/api/v1/atividades", "method": "POST"},
    {"endpoint": "/api/v1/usuarios", "method": "GET"},
    {"endpoint": "/api/v1/*", "method": "*"}
  ]
}
```

**Resposta:**
```json
{
  "message": "Token criado com sucesso!",
  "token": "abc123def456...",
  "id": 1,
  "nome": "Token Integração"
}
```

**⚠️ IMPORTANTE:** O token é retornado apenas uma vez na criação. Guarde-o em local seguro!

#### PUT `/api-tokens/<id>`
Atualiza um token de API.

**Body:**
```json
{
  "nome": "Novo Nome",
  "descricao": "Nova descrição",
  "ativo": true,
  "expires_days": 60,
  "permissions": [...]
}
```

#### DELETE `/api-tokens/<id>`
Exclui um token de API.

#### POST `/api-tokens/<id>/toggle`
Ativa ou desativa um token.

#### GET `/api-tokens/endpoints`
Lista todos os endpoints disponíveis para configuração de permissões.

### Permissões

As permissões suportam:

1. **Endpoints específicos:**
   - `/api/v1/atividades` - Endpoint exato

2. **Wildcards:**
   - `/api/v1/*` - Todos os endpoints que começam com `/api/v1/`
   - `*/atividades` - Todos os endpoints que terminam com `/atividades`

3. **Métodos HTTP:**
   - `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
   - `*` - Todos os métodos

### Geração de Tokens

Os tokens são gerados automaticamente pelo backend usando:
- Timestamp em microsegundos
- Valores aleatórios seguros
- Hash SHA-256
- Tamanho fixo de 64 caracteres

### Validação

Ao usar um token de API:

1. O token é validado no banco de dados
2. Verifica se está ativo
3. Verifica se não expirou
4. Verifica permissões para o endpoint e método solicitado
5. Atualiza `last_used_at`

---

## Deploy e Execução

### Execução Local

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# 3. Inicializar banco de dados
python app.py

# 4. Servidor estará rodando em http://localhost:8000
```

### Execução com Docker

```bash
# Build da imagem
docker build -t hiprod-backend .

# Executar container
docker run -p 8000:8000 --env-file .env hiprod-backend
```

### Variáveis de Ambiente para Produção

```env
# Segurança
JWT_SECRET_KEY=<chave-secreta-forte>
FLASK_DEBUG=0

# Banco de Dados
DATABASE_URL=postgresql://user:password@host:port/database

# Performance
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=50
```

### Logs

O sistema gera logs detalhados no console:

- `📥` - Requisições recebidas
- `✅` - Operações bem-sucedidas
- `❌` - Erros
- `⚠️` - Avisos
- `🔑` - Operações de autenticação

---

## Exemplos de Uso

### Exemplo 1: Login e Obter Token

```python
import requests

# Login
response = requests.post('http://localhost:8000/login', json={
    'nome': 'usuario',
    'senha': 'senha123'
})

data = response.json()
token = data['token']
user_id = data['usuario_id']

# Usar token em requisições
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/usuarios', headers=headers)
```

### Exemplo 2: Criar Token de API

```python
import requests

# Autenticar primeiro
response = requests.post('http://localhost:8000/login', json={
    'nome': 'admin',
    'senha': 'senha123'
})
token = response.json()['token']

# Criar token de API
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:8000/api-tokens', headers=headers, json={
    'nome': 'Token Integração',
    'descricao': 'Token para sistema externo',
    'expires_days': 365,
    'permissions': [
        {'endpoint': '/api/v1/atividades', 'method': 'POST'},
        {'endpoint': '/api/v1/usuarios', 'method': 'GET'}
    ]
})

api_token = response.json()['token']
print(f"Token criado: {api_token}")
```

### Exemplo 3: Usar Token de API

```python
import requests

api_token = "seu_token_aqui"

# Buscar atividades
response = requests.post(
    'http://localhost:8000/api/v1/atividades',
    headers={'Authorization': api_token},
    json={
        'usuario': 'usuario.monitorado',
        'time': {
            'inicio': '2024-01-01T00:00:00Z',
            'fim': '2024-01-31T23:59:59Z'
        }
    }
)

atividades = response.json()
print(f"Total de atividades: {atividades['total_atividades']}")
```

### Exemplo 4: Enviar Atividade (Agente)

```python
import requests

# Modo agente - usar header X-User-Name
response = requests.post(
    'http://localhost:8000/atividade',
    headers={'X-User-Name': 'usuario.windows'},
    json={
        'usuario_monitorado_id': 1,
        'active_window': 'Chrome - Google',
        'titulo_janela': 'Google',
        'ociosidade': 0,
        'duracao': 10,
        'domain': 'google.com',
        'application': 'Chrome'
    }
)
```

### Exemplo 5: Usar Pool de Conexões

```python
from backend.database import DatabaseConnection

# O pool é gerenciado automaticamente
with DatabaseConnection() as db:
    db.cursor.execute("SELECT * FROM usuarios WHERE ativo = %s", (True,))
    usuarios = db.cursor.fetchall()
    
    for usuario in usuarios:
        print(f"Usuário: {usuario[1]}")
```

---

## Troubleshooting

### Erro: "Token de API inválido!"

**Possíveis causas:**
1. Token não existe no banco de dados
2. Token está inativo
3. Token expirado
4. Token não tem permissão para o endpoint

**Solução:**
1. Verificar se o token existe: `SELECT * FROM api_tokens WHERE token = 'seu_token';`
2. Verificar se está ativo: `SELECT ativo FROM api_tokens WHERE token = 'seu_token';`
3. Verificar permissões: `SELECT * FROM api_token_permissions WHERE token_id = X;`

### Erro: "Erro de conexão com o banco PostgreSQL"

**Possíveis causas:**
1. Serviço PostgreSQL não está rodando
2. Credenciais incorretas
3. Host/porta incorretos

**Solução:**
1. Verificar se PostgreSQL está rodando
2. Verificar variáveis de ambiente (DATABASE_URL ou DB_*)
3. Testar conexão: `psql -h host -U user -d database`

### Erro: "Token JWT inválido ou expirado"

**Possíveis causas:**
1. Token expirado (padrão: 7 dias)
2. JWT_SECRET_KEY alterado
3. Token malformado

**Solução:**
1. Fazer login novamente para obter novo token
2. Verificar JWT_SECRET_KEY no .env

---

## Segurança

### Boas Práticas

1. **JWT_SECRET_KEY:** Use uma chave forte e única em produção
2. **Tokens de API:** Configure expiração para tokens de API
3. **Permissões:** Use o princípio do menor privilégio
4. **HTTPS:** Use HTTPS em produção
5. **Validação:** Sempre valide dados de entrada
6. **Logs:** Monitore logs para atividades suspeitas

### Recomendações

- Não exponha tokens de API em logs
- Use variáveis de ambiente para credenciais
- Implemente rate limiting em produção
- Monitore uso de tokens de API
- Revise permissões regularmente

---

## Suporte

Para dúvidas ou problemas:

1. Verifique os logs do servidor
2. Consulte esta documentação
3. Verifique as permissões de tokens
4. Teste endpoints com Postman/curl

---

**Última atualização:** 2024-01-01
**Versão:** 1.0.0

