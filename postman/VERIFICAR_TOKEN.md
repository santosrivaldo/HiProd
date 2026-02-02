# Como Verificar se o Token Está Correto

## Problema: Token não está sendo reconhecido

Se você está recebendo "Token de API inválido!", siga estes passos:

## 1. Verificar o Token no Sistema

1. Acesse o sistema web
2. Vá em "Tokens API"
3. Procure pelo token na lista
4. Verifique:
   - ✅ Token existe?
   - ✅ Token está **ATIVO**?
   - ✅ Token não expirou?
   - ✅ Token tem permissão para `/api/v1/usuarios` (GET)?

## 2. Verificar Permissões do Token

O token precisa ter a permissão exata:

```json
{
  "endpoint": "/api/v1/usuarios",
  "method": "GET"
}
```

**⚠️ IMPORTANTE:**
- O endpoint deve ser exatamente `/api/v1/usuarios` (com `/api/v1/` no início)
- O método deve ser `GET` (maiúsculas)

## 3. Verificar Formato do Header

### ✅ Correto:
```
Authorization: Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L
```

### ❌ Incorreto:
```
Authorization: zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L
```

## 4. Verificar URL

### ✅ URL Correta:
```
GET https://hiprod.grupohi.com.br/api/v1/usuarios
```

### ❌ URLs Incorretas:
```
GET https://hiprod.grupohi.com.br/v1/usuarios
GET https://hiprod.grupohi.com.br/api/usuarios
GET https://hiprod.grupohi.com.br/usuarios
```

## 5. Teste com cURL

Use este comando para testar:

```bash
curl -X GET "https://hiprod.grupohi.com.br/api/v1/usuarios" \
  -H "Authorization: Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L" \
  -H "Content-Type: application/json"
```

## 6. Verificar Logs do Servidor

Após fazer a requisição, verifique os logs do servidor Flask. Você deve ver algo como:

```
🔍 Validando token de API:
   Token recebido (primeiros 20 chars): zXyYPMfFvCZ9r0eGB9qm...
   Comprimento do token: 64
   Endpoint: /api/v1/usuarios
   Método: GET
```

Se o token não for encontrado, você verá:

```
❌ Token de API não encontrado. Primeiros 10 caracteres: zXyYPMfFvC...
   Endpoint: /api/v1/usuarios
   Método: GET
   Tokens ativos no banco (amostra):
     - ID: 1, Nome: Token Teste, Preview: zXyYPMfFvCZ9r0eGB9qm..., Length: 64
   Total de tokens ativos no banco: 1
```

## 7. Possíveis Problemas

### Problema 1: Token não existe no banco
**Solução:** Crie um novo token na página "Tokens API"

### Problema 2: Token está desativado
**Solução:** Ative o token na página "Tokens API"

### Problema 3: Token não tem permissão
**Erro esperado:**
```json
{
  "message": "Token sem permissão para este endpoint!",
  "endpoint": "/api/v1/usuarios",
  "method": "GET",
  "permissions": [
    {
      "endpoint": "/api/v1/atividades",
      "method": "POST"
    }
  ]
}
```

**Solução:** 
1. Edite o token na página "Tokens API"
2. Adicione a permissão:
   - Endpoint: `/api/v1/usuarios`
   - Método: `GET`

### Problema 4: Token tem espaços ou caracteres invisíveis
**Solução:** 
1. Copie o token novamente da página "Tokens API"
2. Certifique-se de não ter espaços antes ou depois
3. O código agora remove espaços automaticamente, mas é melhor garantir

### Problema 5: URL incorreta
**Solução:** Use sempre `/api/v1/usuarios` (não `/v1/usuarios`)

## 8. Como Criar/Atualizar Token com Permissões Corretas

### Criar Novo Token:

1. Acesse "Tokens API"
2. Clique em "Criar Token"
3. Preencha:
   - **Nome:** Token V1 Usuarios
   - **Descrição:** Token para listar usuários via API V1
   - **Expiração:** (opcional, deixe vazio para não expirar)
   - **Permissões:** Adicione:
     ```json
     {
       "endpoint": "/api/v1/usuarios",
       "method": "GET"
     }
     ```
4. Clique em "Criar"
5. **⚠️ COPIE O TOKEN IMEDIATAMENTE** - Ele será exibido apenas uma vez!

### Atualizar Token Existente:

1. Acesse "Tokens API"
2. Encontre o token na lista
3. Clique em "Editar"
4. Adicione/Atualize as permissões:
   ```json
   [
     {
       "endpoint": "/api/v1/usuarios",
       "method": "GET"
     },
     {
       "endpoint": "/api/v1/atividades",
       "method": "POST"
     },
     {
       "endpoint": "/api/v1/estatisticas",
       "method": "POST"
     }
   ]
   ```
5. Clique em "Salvar"

## 9. Verificar no Banco de Dados (SQL)

Se você tem acesso ao banco de dados, pode verificar diretamente:

```sql
-- Verificar se o token existe
SELECT id, nome, ativo, expires_at, created_at, last_used_at
FROM api_tokens
WHERE token = 'zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L';

-- Ver permissões do token
SELECT atp.endpoint, atp.method
FROM api_token_permissions atp
JOIN api_tokens at ON atp.token_id = at.id
WHERE at.token = 'zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L';

-- Ver todos os tokens ativos
SELECT id, nome, ativo, LEFT(token, 20) as token_preview, LENGTH(token) as token_length
FROM api_tokens
WHERE ativo = TRUE
ORDER BY created_at DESC;
```

## 10. Exemplo Completo de Requisição

### Postman:
- **Método:** GET
- **URL:** `https://hiprod.grupohi.com.br/api/v1/usuarios`
- **Headers:**
  - `Authorization`: `Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L`
  - `Content-Type`: `application/json`

### Resposta Esperada (Sucesso):
```json
{
  "version": "v1",
  "total_usuarios": 5,
  "usuarios": [
    {
      "id": 1,
      "nome": "rivaldo.santos",
      "cargo": "Desenvolvedor",
      "departamento_id": 1,
      "ativo": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

## Próximos Passos

1. ✅ Verifique o token no sistema web
2. ✅ Confirme que tem permissão para `/api/v1/usuarios` (GET)
3. ✅ Teste com cURL ou Postman
4. ✅ Verifique os logs do servidor
5. ✅ Se necessário, crie um novo token com as permissões corretas

