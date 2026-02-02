# Exemplos Detalhados de Endpoints - HiProd API

Este documento contém exemplos detalhados de cada endpoint da API HiProd.

## 📋 Índice

1. [Autenticação](#autenticação)
2. [Atividades](#atividades)
3. [Usuários](#usuários)
4. [Departamentos](#departamentos)
5. [Tags](#tags)
6. [Categorias](#categorias)
7. [Escalas](#escalas)
8. [Tokens de API](#tokens-de-api)
9. [Presença Facial](#presença-facial)
10. [API V1 - Externa](#api-v1---externa)

---

## 🔐 Autenticação

### POST /login

**Descrição:** Autentica um usuário e retorna token JWT

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "admin",
  "senha": "Brasil@1402"
}
```

**Resposta (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "usuario_id": "87657109-8b9d-406d-a75c-507e555bb182",
  "usuario": "admin"
}
```

**Exemplo cURL:**
```bash
curl -X POST https://hiprod.grupohi.com.br/login \
  -H "Content-Type: application/json" \
  -d '{"nome": "admin", "senha": "Brasil@1402"}'
```

---

### POST /verify-token

**Descrição:** Verifica se um token JWT é válido

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Resposta (200):**
```json
{
  "valid": true,
  "usuario_id": "87657109-8b9d-406d-a75c-507e555bb182",
  "usuario": "admin"
}
```

---

### GET /profile

**Descrição:** Retorna o perfil do usuário autenticado

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Resposta (200):**
```json
{
  "usuario_id": "87657109-8b9d-406d-a75c-507e555bb182",
  "usuario": "admin",
  "email": "admin@empresa.com",
  "departamento_id": 1
}
```

---

## 📊 Atividades

### GET /atividades

**Descrição:** Lista todas as atividades com filtros opcionais

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Query Parameters:**
- `limite` (opcional): Número de resultados (padrão: 50, máximo: 100)
- `pagina` (opcional): Número da página (padrão: 1)
- `agrupar` (opcional): Agrupar por dia/usuário/janela (true/false)
- `data_inicio` (opcional): Data de início (ISO 8601)
- `data_fim` (opcional): Data de fim (ISO 8601)
- `usuario_monitorado_id` (opcional): ID do usuário monitorado
- `categoria` (opcional): Filtrar por categoria

**Exemplo:**
```
GET /atividades?limite=50&pagina=1&agrupar=false&usuario_monitorado_id=1
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "usuario_monitorado_id": 1,
    "usuario_monitorado_nome": "João Silva",
    "cargo": "Desenvolvedor",
    "active_window": "Visual Studio Code",
    "categoria": "productive",
    "produtividade": "productive",
    "horario": "2024-01-15T10:30:00",
    "ociosidade": 0,
    "duracao": 300,
    "domain": null,
    "application": "VS Code"
  }
]
```

---

### POST /api/atividades

**Descrição:** Endpoint EXTERNO - Busca atividades por usuário e período usando token de API

**Headers:**
```
Authorization: Bearer {{api_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "usuario": "rivaldo.santos",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Resposta (200):**
```json
{
  "usuario": "rivaldo.santos",
  "periodo": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  },
  "total_atividades": 150,
  "atividades": [...]
}
```

**⚠️ IMPORTANTE:** Este endpoint requer **Token de API**, não JWT!

---

### POST /atividade

**Descrição:** Cria uma nova atividade (aceita token JWT ou X-User-Name)

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
X-User-Name: UsuarioWindows  # Alternativa para agente
```

**Body:**
```json
{
  "usuario_monitorado_id": 1,
  "ociosidade": 0,
  "active_window": "Visual Studio Code",
  "titulo_janela": "app.py - Visual Studio Code",
  "categoria": "productive",
  "produtividade": "productive",
  "duracao": 300,
  "domain": null,
  "application": "VS Code"
}
```

**Resposta (201):**
```json
{
  "message": "Atividade criada com sucesso!",
  "id": 123
}
```

---

### PATCH /atividades/{id}

**Descrição:** Atualiza uma atividade específica

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "categoria": "productive",
  "produtividade": "productive"
}
```

**Resposta (200):**
```json
{
  "message": "Atividade atualizada com sucesso!"
}
```

---

### DELETE /atividades/{id}

**Descrição:** Exclui uma atividade específica

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
{
  "message": "Atividade excluída com sucesso!"
}
```

---

### GET /estatisticas

**Descrição:** Retorna estatísticas de atividades de um usuário

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Query Parameters:**
- `usuario_monitorado_id` (obrigatório): ID do usuário monitorado

**Exemplo:**
```
GET /estatisticas?usuario_monitorado_id=1
```

**Resposta (200):**
```json
{
  "categorias": [
    {
      "categoria": "productive",
      "total": 100,
      "media_ociosidade": 5,
      "tempo_total": 30000
    }
  ],
  "produtividade_semanal": [...],
  "atividades_hoje": 50
}
```

---

## 👥 Usuários

### GET /usuarios

**Descrição:** Lista todos os usuários do sistema

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "usuario_id": "87657109-8b9d-406d-a75c-507e555bb182",
    "usuario": "admin",
    "email": "admin@empresa.com",
    "departamento_id": 1,
    "ativo": true,
    "departamento": {
      "nome": "TI",
      "cor": "#10B981"
    }
  }
]
```

---

### POST /usuarios

**Descrição:** Cria um novo usuário do sistema

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "novo.usuario",
  "senha": "SenhaSegura123!",
  "email": "novo.usuario@empresa.com",
  "departamento_id": 1
}
```

**Resposta (201):**
```json
{
  "message": "Usuário criado com sucesso!",
  "usuario_id": "..."
}
```

---

### GET /usuarios-monitorados

**Descrição:** Lista todos os usuários monitorados

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "nome": "João Silva",
    "cargo": "Desenvolvedor",
    "departamento_id": 1,
    "ativo": true
  }
]
```

---

### GET /usuarios-monitorados?nome={nome}

**Descrição:** Busca ou cria um usuário monitorado pelo nome

**Headers:**
```
Authorization: Bearer {{jwt_token}}
X-User-Name: UsuarioWindows  # Alternativa para agente
```

**Query Parameters:**
- `nome` (obrigatório): Nome do usuário

**Exemplo:**
```
GET /usuarios-monitorados?nome=UsuarioWindows
```

**Resposta (200):**
```json
{
  "id": 1,
  "nome": "UsuarioWindows",
  "cargo": null,
  "departamento_id": null,
  "ativo": true
}
```

---

### POST /usuarios-monitorados

**Descrição:** Cria um novo usuário monitorado

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "novo.usuario",
  "cargo": "Desenvolvedor",
  "departamento_id": 1
}
```

**Resposta (201):**
```json
{
  "message": "Usuário monitorado criado com sucesso!",
  "id": 123
}
```

---

## 🏢 Departamentos

### GET /departamentos

**Descrição:** Lista todos os departamentos

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "nome": "TI",
    "descricao": "Tecnologia da Informação",
    "cor": "#10B981",
    "ativo": true
  }
]
```

---

### POST /departamentos

**Descrição:** Cria um novo departamento

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "Novo Departamento",
  "descricao": "Descrição do departamento",
  "cor": "#3B82F6"
}
```

**Resposta (201):**
```json
{
  "message": "Departamento criado com sucesso!",
  "id": 123
}
```

---

## 🏷️ Tags

### GET /tags

**Descrição:** Lista todas as tags

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "nome": "Desenvolvimento Web",
    "descricao": "Desenvolvimento de aplicações web",
    "produtividade": "productive",
    "departamento_id": 1,
    "cor": "#10B981",
    "tier": 3,
    "ativo": true
  }
]
```

---

### POST /tags

**Descrição:** Cria uma nova tag

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "Nova Tag",
  "descricao": "Descrição da tag",
  "produtividade": "productive",
  "departamento_id": 1,
  "cor": "#10B981",
  "tier": 3
}
```

**Resposta (201):**
```json
{
  "message": "Tag criada com sucesso!",
  "id": 123
}
```

---

## 📁 Categorias

### GET /categorias

**Descrição:** Lista todas as categorias de aplicações

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "nome": "Desenvolvimento",
    "departamento_id": 1,
    "tipo_produtividade": "productive",
    "cor": "#10B981",
    "descricao": "Aplicações de desenvolvimento",
    "is_global": false
  }
]
```

---

### POST /categorias

**Descrição:** Cria uma nova categoria de aplicação

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "Nova Categoria",
  "departamento_id": 1,
  "tipo_produtividade": "productive",
  "cor": "#10B981",
  "descricao": "Descrição da categoria",
  "is_global": false
}
```

**Resposta (201):**
```json
{
  "message": "Categoria criada com sucesso!",
  "id": 123
}
```

---

## ⏰ Escalas

### GET /escalas

**Descrição:** Lista todas as escalas de trabalho

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "nome": "Comercial Padrão",
    "descricao": "Horário comercial de 8h às 18h",
    "horario_inicio_trabalho": "08:00:00",
    "horario_fim_trabalho": "18:00:00",
    "dias_trabalho": "1,2,3,4,5",
    "ativo": true
  }
]
```

---

### POST /escalas

**Descrição:** Cria uma nova escala de trabalho

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "Nova Escala",
  "descricao": "Descrição da escala",
  "horario_inicio_trabalho": "08:00:00",
  "horario_fim_trabalho": "18:00:00",
  "dias_trabalho": "1,2,3,4,5"
}
```

**Resposta (201):**
```json
{
  "message": "Escala criada com sucesso!",
  "id": 123
}
```

---

## 🔑 Tokens de API

### GET /api-tokens

**Descrição:** Lista todos os tokens de API

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "id": 1,
    "nome": "Token para Integração",
    "descricao": "Token para integração externa",
    "ativo": true,
    "created_by": "...",
    "created_at": "2024-01-15T10:30:00",
    "last_used_at": "2024-01-20T15:00:00",
    "expires_at": null,
    "permissions": [
      {
        "endpoint": "/api/atividades",
        "method": "POST"
      }
    ]
  }
]
```

---

### POST /api-tokens

**Descrição:** Cria um novo token de API

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "Token para Integração",
  "descricao": "Token para integração externa",
  "expires_days": null,
  "permissions": [
    {
      "endpoint": "/api/atividades",
      "method": "POST"
    }
  ]
}
```

**Resposta (201):**
```json
{
  "message": "Token criado com sucesso!",
  "token": "xK9mP2qR7vT4wY8zA1bC3dE5fG6hI0jK1L2M3N4O5P6Q7R8S9T0",
  "id": 1,
  "nome": "Token para Integração"
}
```

**⚠️ IMPORTANTE:** O token será exibido apenas uma vez! Copie imediatamente.

---

### PUT /api-tokens/{id}

**Descrição:** Atualiza um token de API

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Body:**
```json
{
  "nome": "Token Atualizado",
  "descricao": "Nova descrição",
  "ativo": true,
  "permissions": [
    {
      "endpoint": "/api/atividades",
      "method": "POST"
    }
  ]
}
```

**Resposta (200):**
```json
{
  "message": "Token atualizado com sucesso!"
}
```

---

### POST /api-tokens/{id}/toggle

**Descrição:** Ativa ou desativa um token de API

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
{
  "message": "Token ativado com sucesso!",
  "ativo": true
}
```

---

### DELETE /api-tokens/{id}

**Descrição:** Exclui um token de API

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
{
  "message": "Token excluído com sucesso!"
}
```

---

### GET /api-tokens/endpoints

**Descrição:** Lista todos os endpoints disponíveis para configuração de permissões

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Resposta (200):**
```json
[
  {
    "endpoint": "/atividades",
    "method": "GET",
    "description": "Listar atividades"
  },
  {
    "endpoint": "/api/atividades",
    "method": "POST",
    "description": "Buscar atividades por usuário e período (requer token API)"
  }
]
```

---

## 👤 Presença Facial

### POST /face-presence-check

**Descrição:** Registra verificação de presença facial

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
X-User-Name: UsuarioWindows  # Alternativa para agente
```

**Body:**
```json
{
  "usuario_monitorado_id": 1,
  "face_detected": true,
  "presence_time": 300
}
```

**Resposta (201):**
```json
{
  "message": "Verificação de presença facial registrada com sucesso!",
  "id": 123
}
```

---

### GET /face-presence-stats

**Descrição:** Retorna estatísticas de presença facial

**Headers:**
```
Authorization: Bearer {{jwt_token}}
```

**Query Parameters:**
- `usuario_monitorado_id` (obrigatório): ID do usuário monitorado
- `data_inicio` (opcional): Data de início (YYYY-MM-DD)
- `data_fim` (opcional): Data de fim (YYYY-MM-DD)

**Exemplo:**
```
GET /face-presence-stats?usuario_monitorado_id=1&data_inicio=2024-01-01&data_fim=2024-01-31
```

**Resposta (200):**
```json
{
  "total_checks": 100,
  "face_detected_count": 95,
  "face_not_detected_count": 5,
  "total_presence_time": 30000,
  "average_presence_time": 300
}
```

---

## 🌐 API V1 - Externa

### GET /api/v1/health

**Descrição:** Health check da API (não requer autenticação)

**Headers:**
```
Nenhum requerido
```

**Resposta (200):**
```json
{
  "version": "v1",
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

**Exemplo cURL:**
```bash
curl -X GET https://hiprod.grupohi.com.br/api/v1/health
```

---

### POST /api/v1/atividades

**Descrição:** Busca atividades de um usuário em um período específico

**Headers:**
```
Authorization: Bearer SEU_TOKEN_DE_API
Content-Type: application/json
```

**Body:**
```json
{
  "usuario": "rivaldo.santos",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Resposta (200):**
```json
{
  "version": "v1",
  "usuario": "rivaldo.santos",
  "periodo": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  },
  "total_atividades": 150,
  "atividades": [...]
}
```

**Permissão Necessária:** `/api/v1/atividades` (POST)

---

### GET /api/v1/usuarios

**Descrição:** Lista todos os usuários monitorados ativos

**Headers:**
```
Authorization: Bearer SEU_TOKEN_DE_API
```

**Resposta (200):**
```json
{
  "version": "v1",
  "total_usuarios": 10,
  "usuarios": [
    {
      "id": 1,
      "nome": "rivaldo.santos",
      "cargo": "Desenvolvedor",
      "departamento_id": 1,
      "ativo": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ]
}
```

**Permissão Necessária:** `/api/v1/usuarios` (GET)

---

### POST /api/v1/estatisticas

**Descrição:** Obtém estatísticas de atividades de um usuário

**Headers:**
```
Authorization: Bearer SEU_TOKEN_DE_API
Content-Type: application/json
```

**Body:**
```json
{
  "usuario": "rivaldo.santos",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Resposta (200):**
```json
{
  "version": "v1",
  "usuario": "rivaldo.santos",
  "periodo": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  },
  "total_atividades": 150,
  "categorias": [
    {
      "categoria": "productive",
      "total": 100,
      "media_ociosidade": 5.2,
      "tempo_total": 30000
    }
  ]
}
```

**Permissão Necessária:** `/api/v1/estatisticas` (POST)

---

## 📌 Notas Finais

- Todos os endpoints que requerem autenticação precisam do header `Authorization: Bearer {{jwt_token}}`
- Os endpoints **V1** (`/api/v1/*`) requerem **Token de API**, não JWT
- O endpoint `/api/atividades` (legado) também requer Token de API
- Alguns endpoints aceitam `X-User-Name` como alternativa ao token JWT (para o agente)
- Use as variáveis do environment no Postman para facilitar os testes
- Sempre verifique as permissões do token de API antes de usar endpoints externos
- **Recomendado**: Use endpoints V1 (`/api/v1/*`) para novas integrações

