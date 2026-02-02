# Endpoints Internos Liberados para Tokens de API

## ✅ Implementação Concluída

Os endpoints internos agora aceitam **tanto JWT quanto Token de API** para consultas (GET).

## Como Funciona

O decorator `@token_required` foi atualizado para:

1. **Primeiro tenta validar como Token de API:**
   - Verifica se o token existe no banco
   - Verifica se está ativo
   - Verifica se não expirou
   - Verifica permissões do endpoint
   - Atualiza `last_used_at`

2. **Se não for Token de API, tenta como JWT:**
   - Valida o token JWT
   - Verifica se o usuário existe e está ativo
   - Retorna os dados do usuário

## Endpoints Liberados para Token de API

### ✅ Endpoints de Consulta (GET)

Todos os endpoints de consulta agora aceitam Token de API:

- **GET /atividades** - Listar atividades
- **GET /atividade** - Listar atividades (alternativo)
- **GET /usuarios** - Listar usuários do sistema
- **GET /usuarios-monitorados** - Listar usuários monitorados
- **GET /departamentos** - Listar departamentos
- **GET /tags** - Listar tags
- **GET /categorias** - Listar categorias
- **GET /escalas** - Listar escalas
- **GET /estatisticas** - Obter estatísticas
- **GET /atividades/<id>** - Buscar atividade específica
- **GET /usuarios/<id>** - Buscar usuário específico
- **GET /atividades/<id>/tags** - Listar tags de atividade
- **GET /screenshot/<id>** - Obter screenshot
- **GET /face-presence-stats** - Estatísticas de presença facial
- **GET /usuarios/inativos** - Listar usuários inativos
- **GET /departamentos/<id>/configuracoes** - Configurações do departamento

### ⚠️ Endpoints de Modificação (POST, PUT, DELETE, PATCH)

Endpoints de modificação **continuam exigindo JWT** por segurança:

- POST /atividades
- POST /usuarios
- POST /tags
- PUT /usuarios/<id>
- DELETE /usuarios/<id>
- PATCH /atividades/<id>
- etc.

## Como Configurar Permissões

### 1. Criar Token com Permissões

Acesse "Tokens API" e crie um token com permissões:

```json
{
  "nome": "Token para Consultas",
  "descricao": "Token para consultar dados via API",
  "permissions": [
    {
      "endpoint": "/atividades",
      "method": "GET"
    },
    {
      "endpoint": "/usuarios",
      "method": "GET"
    },
    {
      "endpoint": "/departamentos",
      "method": "GET"
    },
    {
      "endpoint": "/tags",
      "method": "GET"
    }
  ]
}
```

### 2. Usar Wildcards

Você pode usar wildcards para dar acesso a múltiplos endpoints:

```json
{
  "endpoint": "/atividades/*",
  "method": "GET"
}
```

Isso permite acesso a:
- `/atividades/1`
- `/atividades/2`
- `/atividades/123/tags`
- etc.

### 3. Método Wildcard

Para permitir todos os métodos HTTP:

```json
{
  "endpoint": "/atividades",
  "method": "*"
}
```

## Exemplos de Uso

### Exemplo 1: Listar Atividades

```bash
curl -X GET "https://hiprod.grupohi.com.br/atividades" \
  -H "Authorization: Bearer SEU_TOKEN_DE_API" \
  -H "Content-Type: application/json"
```

### Exemplo 2: Listar Usuários

```bash
curl -X GET "https://hiprod.grupohi.com.br/usuarios" \
  -H "Authorization: Bearer SEU_TOKEN_DE_API"
```

### Exemplo 3: Listar Departamentos

```bash
curl -X GET "https://hiprod.grupohi.com.br/departamentos" \
  -H "Authorization: Bearer SEU_TOKEN_DE_API"
```

## Lista Completa de Endpoints Disponíveis

A lista completa está disponível em:

```
GET /api-tokens/endpoints
Authorization: Bearer JWT_TOKEN
```

Retorna todos os endpoints disponíveis para configuração de permissões.

## Segurança

### ✅ Implementado

- Validação de token de API
- Verificação de permissões por endpoint
- Suporte a wildcards
- Atualização de `last_used_at`
- Verificação de expiração

### ⚠️ Limitações

- Endpoints de modificação (POST, PUT, DELETE, PATCH) **ainda exigem JWT**
- Tokens de API não podem criar/editar/excluir dados
- Apenas consultas (GET) são permitidas com Token de API

## Compatibilidade

### ✅ Mantida

- Endpoints continuam funcionando com JWT normalmente
- Não há breaking changes
- Tokens de API são opcionais

### ✅ Novo

- Endpoints de consulta agora também aceitam Token de API
- Maior flexibilidade para integrações externas
- Controle granular de permissões

## Próximos Passos

1. ✅ Crie tokens de API com permissões para os endpoints desejados
2. ✅ Teste os endpoints usando Token de API
3. ✅ Configure permissões específicas conforme necessário

## Notas Importantes

- **Tokens de API são apenas para consulta (GET)**
- **Modificações (POST, PUT, DELETE) ainda exigem JWT**
- **Permissões são verificadas em tempo real**
- **Wildcards facilitam configuração de múltiplos endpoints**

