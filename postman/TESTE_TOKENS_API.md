# Teste de Tokens de API - Checklist

## Endpoints para Testar

### 1. ✅ Listar Tokens (GET)
```bash
GET /api-tokens
Authorization: Bearer JWT_TOKEN
```

**Esperado:** Lista de todos os tokens

### 2. ✅ Criar Token (POST)
```bash
POST /api-tokens
Authorization: Bearer JWT_TOKEN
Content-Type: application/json

{
  "nome": "Token Teste",
  "descricao": "Token para testes",
  "expires_days": null,
  "permissions": [
    {
      "endpoint": "/api/v1/usuarios",
      "method": "GET"
    }
  ]
}
```

**Esperado:** Token criado com sucesso e token retornado

### 3. ✅ Atualizar Token (PUT)
```bash
PUT /api-tokens/{token_id}
Authorization: Bearer JWT_TOKEN
Content-Type: application/json

{
  "nome": "Token Atualizado",
  "descricao": "Nova descrição",
  "ativo": true,
  "permissions": [
    {
      "endpoint": "/api/v1/usuarios",
      "method": "GET"
    },
    {
      "endpoint": "/api/v1/atividades",
      "method": "POST"
    }
  ]
}
```

**Esperado:** Token atualizado com sucesso

### 4. ✅ Ativar/Desativar Token (POST)
```bash
POST /api-tokens/{token_id}/toggle
Authorization: Bearer JWT_TOKEN
```

**Esperado:** Status do token alterado

### 5. ✅ Excluir Token (DELETE)
```bash
DELETE /api-tokens/{token_id}
Authorization: Bearer JWT_TOKEN
```

**Esperado:** Token excluído com sucesso

### 6. ✅ Listar Endpoints Disponíveis (GET)
```bash
GET /api-tokens/endpoints
Authorization: Bearer JWT_TOKEN
```

**Esperado:** Lista de endpoints disponíveis

## Problemas Corrigidos

### 1. ✅ Validação de expires_days
- Agora valida se é um número inteiro positivo
- Retorna erro 400 se inválido

### 2. ✅ Tratamento de Erros
- Logs com traceback completo
- Mensagens de erro mais detalhadas
- Retorna erro específico na resposta

### 3. ✅ Validação de Permissões
- Valida se endpoint é string não vazia
- Normaliza método HTTP (uppercase)
- Continua mesmo se uma permissão falhar

### 4. ✅ Query SQL Segura
- Corrigida construção de UPDATE query
- Validação de parâmetros antes de executar

## Como Testar

### 1. Teste de Criação
```bash
curl -X POST "https://hiprod.grupohi.com.br/api-tokens" \
  -H "Authorization: Bearer SEU_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Token Teste V1",
    "descricao": "Token para testar API V1",
    "permissions": [
      {
        "endpoint": "/api/v1/usuarios",
        "method": "GET"
      },
      {
        "endpoint": "/api/v1/atividades",
        "method": "POST"
      }
    ]
  }'
```

### 2. Teste de Atualização
```bash
curl -X PUT "https://hiprod.grupohi.com.br/api-tokens/1" \
  -H "Authorization: Bearer SEU_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Token Atualizado",
    "ativo": true,
    "permissions": [
      {
        "endpoint": "/api/v1/usuarios",
        "method": "GET"
      }
    ]
  }'
```

### 3. Teste de Exclusão
```bash
curl -X DELETE "https://hiprod.grupohi.com.br/api-tokens/1" \
  -H "Authorization: Bearer SEU_JWT_TOKEN"
```

## Verificar Logs

Após cada operação, verifique os logs do servidor Flask. Você deve ver:

**Sucesso:**
- Nenhum erro nos logs
- Operação concluída

**Erro:**
```
❌ Erro ao criar token: [detalhes do erro]
Traceback (most recent call last):
  ...
```

## Checklist de Verificação

- [ ] Criar token funciona sem erro 500
- [ ] Atualizar token funciona sem erro 500
- [ ] Excluir token funciona sem erro 500
- [ ] Ativar/Desativar token funciona sem erro 500
- [ ] Listar tokens funciona sem erro 500
- [ ] Validação de expires_days funciona
- [ ] Validação de permissões funciona
- [ ] Logs mostram erros detalhados (se houver)
- [ ] Mensagens de erro são claras

## Próximos Passos

1. Teste cada endpoint individualmente
2. Verifique os logs do servidor
3. Se houver erro 500, os logs agora mostrarão o traceback completo
4. Compartilhe os logs se o problema persistir

