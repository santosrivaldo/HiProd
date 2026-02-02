# Troubleshooting - Token de API Inválido

## Erro: "Token de API inválido!"

### Problema
Ao tentar usar um token de API, você recebe:
```json
{
  "message": "Token de API inválido!"
}
```

## Causas Comuns e Soluções

### 1. ❌ URL Incorreta

**Problema:** Você está usando a URL errada.

**❌ URL Incorreta:**
```
POST /v1/atividades
```

**✅ URL Correta:**
```
POST /api/v1/atividades
```

**Solução:**
- Use sempre o prefixo `/api/v1/` antes do endpoint
- URLs corretas:
  - `https://hiprod.grupohi.com.br/api/v1/atividades`
  - `https://hiprod.grupohi.com.br/api/v1/usuarios`
  - `https://hiprod.grupohi.com.br/api/v1/estatisticas`
  - `https://hiprod.grupohi.com.br/api/v1/health`

### 2. ❌ Token com Espaços ou Caracteres Especiais

**Problema:** O token pode ter espaços, tabs ou quebras de linha invisíveis.

**Exemplo de token com problema:**
```
zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L	-	
```
(Note os tabs e espaços no final)

**Solução:**
1. Copie o token novamente da página "Tokens API"
2. Remova todos os espaços antes e depois
3. Certifique-se de que não há quebras de linha
4. Use o token completo, sem modificações

**Token correto:**
```
zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L
```

### 3. ❌ Header Incorreto

**Problema:** O token não está sendo enviado corretamente no header.

**❌ Formato Incorreto:**
```
Authorization: zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L
```

**✅ Formato Correto:**
```
Authorization: Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L
```

**Ou alternativamente:**
```
X-API-Token: zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L
```

### 4. ❌ Token Não Existe no Banco

**Problema:** O token pode não ter sido criado corretamente ou foi deletado.

**Solução:**
1. Acesse a página "Tokens API" no sistema
2. Verifique se o token existe na lista
3. Se não existir, crie um novo token
4. ⚠️ **IMPORTANTE:** O token é exibido apenas UMA VEZ na criação. Se você não copiou, precisará criar um novo.

### 5. ❌ Token Desativado

**Problema:** O token pode estar desativado.

**Erro esperado:**
```json
{
  "message": "Token de API desativado!"
}
```

**Solução:**
1. Acesse a página "Tokens API"
2. Encontre o token na lista
3. Clique em "Ativar" se estiver desativado

### 6. ❌ Token Expirado

**Problema:** O token pode ter expirado.

**Erro esperado:**
```json
{
  "message": "Token de API expirado!"
}
```

**Solução:**
1. Verifique a data de expiração do token
2. Se expirado, crie um novo token
3. Ou atualize o token para remover a expiração

## Exemplo Correto de Requisição

### cURL
```bash
curl -X POST "https://hiprod.grupohi.com.br/api/v1/atividades" \
  -H "Authorization: Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "rivaldo.santos",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

### JavaScript (fetch)
```javascript
fetch('https://hiprod.grupohi.com.br/api/v1/atividades', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    usuario: 'rivaldo.santos',
    time: {
      inicio: '2024-01-01T00:00:00Z',
      fim: '2024-01-31T23:59:59Z'
    }
  })
})
```

### Python (requests)
```python
import requests

url = "https://hiprod.grupohi.com.br/api/v1/atividades"
headers = {
    "Authorization": "Bearer zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L",
    "Content-Type": "application/json"
}
data = {
    "usuario": "rivaldo.santos",
    "time": {
        "inicio": "2024-01-01T00:00:00Z",
        "fim": "2024-01-31T23:59:59Z"
    }
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Checklist de Verificação

Antes de reportar um problema, verifique:

- [ ] URL está correta: `/api/v1/atividades` (não `/v1/atividades`)
- [ ] Token não tem espaços ou caracteres especiais
- [ ] Header está no formato correto: `Authorization: Bearer TOKEN`
- [ ] Token existe na página "Tokens API"
- [ ] Token está ativo (não desativado)
- [ ] Token não expirou
- [ ] Token tem permissão para o endpoint (`/api/v1/atividades` com método `POST`)
- [ ] Método HTTP está correto (POST para `/atividades` e `/estatisticas`, GET para `/usuarios`)

## Como Obter um Novo Token

1. Faça login no sistema web
2. Acesse "Tokens API" no menu
3. Clique em "Criar Token"
4. Preencha:
   - **Nome:** Nome descritivo (ex: "Token para Integração V1")
   - **Descrição:** Descrição opcional
   - **Expiração:** Opcional (deixe vazio para não expirar)
   - **Permissões:** Adicione pelo menos:
     ```json
     {
       "endpoint": "/api/v1/atividades",
       "method": "POST"
     }
     ```
5. Clique em "Criar"
6. **⚠️ COPIE O TOKEN IMEDIATAMENTE** - Ele será exibido apenas uma vez!

## Verificar Token no Banco de Dados

Se você tem acesso ao banco de dados, pode verificar:

```sql
-- Ver todos os tokens ativos
SELECT id, nome, ativo, expires_at, created_at, last_used_at
FROM api_tokens
WHERE ativo = TRUE
ORDER BY created_at DESC;

-- Verificar se um token específico existe
SELECT id, nome, ativo, expires_at
FROM api_tokens
WHERE token = 'zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L';

-- Ver permissões de um token
SELECT atp.endpoint, atp.method
FROM api_token_permissions atp
JOIN api_tokens at ON atp.token_id = at.id
WHERE at.token = 'zXyYPMfFvCZ9r0eGB9qmXRrj7PKzK0KtqQShYwk2QZdamt4MH00Heu9dhjeeHK8L';
```

## Logs do Servidor

Se o problema persistir, verifique os logs do servidor Flask. Você deve ver:

```
❌ Token de API não encontrado. Primeiros 10 caracteres: zXyYPMfFvC...
   Endpoint: /api/v1/atividades
   Método: POST
   Total de tokens ativos no banco: X
```

Isso ajuda a identificar se:
- O token está sendo recebido corretamente
- O endpoint está correto
- Há tokens no banco de dados

## Próximos Passos

Se após verificar todos os itens acima o problema persistir:

1. Crie um novo token
2. Teste com o novo token
3. Verifique os logs do servidor
4. Entre em contato com o suporte técnico fornecendo:
   - URL completa usada
   - Primeiros 10 caracteres do token (não o token completo por segurança)
   - Mensagem de erro completa
   - Logs do servidor (se disponível)

