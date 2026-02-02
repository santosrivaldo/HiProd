# Diagnóstico: Token de API Inválido

## Erro Recebido

```json
{
    "debug": {
        "endpoint": "/api/v1/usuarios",
        "method": "GET",
        "token_length": 64,
        "token_preview": "zXyYPMfFvC..."
    },
    "message": "Token de API inválido!"
}
```

## Análise

O erro indica que:
- ✅ URL está correta: `/api/v1/usuarios`
- ✅ Método está correto: `GET`
- ✅ Token tem comprimento correto: 64 caracteres
- ❌ **Token não foi encontrado no banco de dados**

## Possíveis Causas

### 1. Token não existe no banco de dados

**Solução:**
1. Acesse "Tokens API" no sistema web
2. Verifique se o token `zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L` está na lista
3. Se não estiver, o token pode ter sido:
   - Deletado
   - Nunca criado corretamente
   - Criado em outro ambiente/banco

### 2. Token foi copiado incorretamente

**Solução:**
1. Acesse "Tokens API"
2. Se o token estiver na lista, **edite** o token
3. Você não verá o token completo (por segurança), mas pode:
   - Verificar o nome e descrição
   - Verificar as permissões
   - Criar um novo token se necessário

### 3. Token está em outro banco de dados

**Solução:**
- Verifique se está usando o banco de dados correto
- O token pode ter sido criado em desenvolvimento mas você está testando em produção (ou vice-versa)

## Como Diagnosticar

### Opção 1: Verificar no Sistema Web

1. Acesse `https://hiprod.grupohi.com.br/tokens`
2. Faça login
3. Procure pelo token na lista
4. Verifique:
   - Nome do token
   - Se está ativo
   - Permissões configuradas

### Opção 2: Verificar no Banco de Dados (SQL)

Execute o script `verificar_token.sql` no PostgreSQL:

```sql
-- Verificar se o token existe
SELECT 
    id, 
    nome, 
    ativo, 
    expires_at, 
    created_at,
    LENGTH(token) as token_length,
    LEFT(token, 20) as token_preview
FROM api_tokens
WHERE token = 'zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L';
```

**Se retornar vazio:** O token não existe no banco.

**Se retornar resultado:** Verifique:
- `ativo = true`?
- `expires_at` não passou?
- Tem permissão para `/api/v1/usuarios` (GET)?

### Opção 3: Verificar Logs do Servidor

Após fazer a requisição, verifique os logs do servidor Flask. Você deve ver:

```
🔍 Validando token de API:
   Token recebido (primeiros 20 chars): zXyYPMfFvCZ9r0eGB9qm...
   Comprimento do token: 64
   Endpoint: /api/v1/usuarios
   Método: GET
   Tokens ativos no banco (amostra):
     - ID: 1, Nome: Token Teste, Preview: abc123..., Length: 64
   Total de tokens ativos no banco: 1
```

Isso mostra:
- Se há tokens no banco
- Se algum token começa com os mesmos caracteres
- Quantos tokens ativos existem

## Solução: Criar Novo Token

Se o token não existe, crie um novo:

1. Acesse "Tokens API" no sistema
2. Clique em "Criar Token"
3. Preencha:
   - **Nome:** Token V1 - Usuarios
   - **Descrição:** Token para listar usuários via API V1
   - **Expiração:** (deixe vazio para não expirar)
   - **Permissões:** Adicione:
     ```json
     {
       "endpoint": "/api/v1/usuarios",
       "method": "GET"
     }
     ```
4. Clique em "Criar"
5. **⚠️ COPIE O TOKEN IMEDIATAMENTE** - Ele será exibido apenas uma vez!
6. Use o novo token nas requisições

## Verificar Permissões do Token

Mesmo que o token exista, ele precisa ter a permissão correta:

```sql
-- Ver permissões do token
SELECT 
    at.id,
    at.nome,
    at.ativo,
    atp.endpoint,
    atp.method
FROM api_tokens at
LEFT JOIN api_token_permissions atp ON at.id = atp.token_id
WHERE at.token = 'zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L';
```

**Permissão necessária:**
- `endpoint = '/api/v1/usuarios'`
- `method = 'GET'`

## Teste com Novo Token

Após criar um novo token, teste:

```bash
curl -X GET "https://hiprod.grupohi.com.br/api/v1/usuarios" \
  -H "Authorization: Bearer NOVO_TOKEN_AQUI" \
  -H "Content-Type: application/json"
```

## Checklist de Verificação

- [ ] Token existe na página "Tokens API"?
- [ ] Token está ativo?
- [ ] Token não expirou?
- [ ] Token tem permissão para `/api/v1/usuarios` (GET)?
- [ ] URL está correta: `/api/v1/usuarios`?
- [ ] Header está correto: `Authorization: Bearer TOKEN`?
- [ ] Token foi copiado completamente (64 caracteres)?

## Próximos Passos

1. ✅ Verifique o token no sistema web
2. ✅ Execute o script SQL para verificar no banco
3. ✅ Verifique os logs do servidor
4. ✅ Se o token não existir, crie um novo
5. ✅ Teste com o novo token

## Ajuda Adicional

Se o problema persistir após verificar todos os itens acima:

1. Crie um novo token
2. Teste imediatamente após criar
3. Verifique os logs do servidor para mensagens de debug
4. Compartilhe:
   - Logs do servidor
   - Resultado do script SQL
   - Screenshot da página "Tokens API" (sem mostrar o token completo)

