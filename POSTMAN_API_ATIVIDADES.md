# Guia de Teste - Endpoint API Atividades no Postman

## Endpoint: Buscar Atividades por Usuário e Período

### Configuração da Requisição

#### 1. Método e URL
- **Método:** `POST`
- **URL:** `http://localhost:8000/api/atividades`
  - Para produção: `http://seu-servidor:8000/api/atividades`

#### 2. Headers (Aba Headers)

Adicione os seguintes headers:

| Key | Value |
|-----|-------|
| `Authorization` | `Bearer SEU_TOKEN_AQUI` |
| `Content-Type` | `application/json` |

**OU** use o header alternativo:

| Key | Value |
|-----|-------|
| `X-API-Token` | `SEU_TOKEN_AQUI` |

#### 3. Body (Aba Body)

Selecione **raw** e **JSON**, depois cole o seguinte JSON:

```json
{
  "usuario": "nome_do_usuario",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Exemplos de Body:**

**Exemplo 1 - Buscar por nome de usuário:**
```json
{
  "usuario": "João Silva",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

**Exemplo 2 - Buscar por ID do usuário:**
```json
{
  "usuario": 123,
  "time": {
    "inicio": "2024-01-15T08:00:00Z",
    "fim": "2024-01-15T18:00:00Z"
  }
}
```

**Exemplo 3 - Período de hoje:**
```json
{
  "usuario": "admin",
  "time": {
    "inicio": "2024-01-20T00:00:00Z",
    "fim": "2024-01-20T23:59:59Z"
  }
}
```

#### 4. Configuração Completa no Postman

**Passo a passo:**

1. Abra o Postman
2. Clique em **New** → **HTTP Request**
3. Selecione o método **POST**
4. Digite a URL: `http://localhost:8000/api/atividades`
5. Vá para a aba **Headers**
6. Adicione:
   - Key: `Authorization`, Value: `Bearer SEU_TOKEN_AQUI`
   - Key: `Content-Type`, Value: `application/json`
7. Vá para a aba **Body**
8. Selecione **raw** e escolha **JSON** no dropdown
9. Cole o JSON do exemplo acima
10. Clique em **Send**

### Como Obter um Token de API

1. Faça login no sistema normalmente
2. Acesse a página **Tokens API** no menu
3. Clique em **Criar Novo Token**
4. Preencha:
   - Nome: "Token para Postman"
   - Descrição: "Token para testes no Postman"
   - Expira em: (opcional, deixe vazio para não expirar)
   - Permissões: Adicione `/api/atividades` com método `POST`
5. Clique em **Criar Token**
6. **COPIE O TOKEN** (ele só será exibido uma vez!)
7. Use esse token no header `Authorization: Bearer <token>`

### Respostas Esperadas

#### Sucesso (200 OK)
```json
{
  "usuario": "João Silva",
  "periodo": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  },
  "total_atividades": 150,
  "atividades": [
    {
      "id": 1,
      "usuario_monitorado_id": 123,
      "usuario_monitorado_nome": "João Silva",
      "cargo": "Desenvolvedor",
      "active_window": "Visual Studio Code",
      "titulo_janela": "app.py - Visual Studio Code",
      "categoria": "productive",
      "produtividade": "productive",
      "horario": "2024-01-15T10:30:00",
      "ociosidade": 0,
      "duracao": 300,
      "domain": null,
      "application": "VS Code",
      "ip_address": "192.168.1.100",
      "user_agent": "...",
      "has_screenshot": false,
      "screenshot_size": null,
      "face_presence_time": 300,
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ]
}
```

#### Erro 400 - Dados Inválidos
```json
{
  "message": "Campo \"usuario\" é obrigatório!"
}
```

#### Erro 401 - Token Não Fornecido
```json
{
  "message": "Token de API não fornecido!"
}
```

#### Erro 403 - Token Sem Permissão
```json
{
  "message": "Token sem permissão para este endpoint!",
  "endpoint": "/api/atividades",
  "method": "POST"
}
```

#### Erro 404 - Usuário Não Encontrado
```json
{
  "message": "Usuário \"nome_inexistente\" não encontrado!"
}
```

#### Erro 405 - Method Not Allowed
Se você receber este erro, verifique:

1. **Você está usando POST?** (não GET)
2. **A URL está correta?** `http://localhost:8000/api/atividades`
3. **O servidor foi reiniciado?** Após adicionar a rota, reinicie o Flask

**Solução:**
- No Postman, certifique-se de que o método está como **POST**
- Verifique se a URL não tem barra no final: `/api/atividades` (não `/api/atividades/`)
- Reinicie o servidor Flask se acabou de adicionar a rota

### Variáveis de Ambiente no Postman (Opcional)

Para facilitar os testes, você pode criar variáveis de ambiente:

1. Clique no ícone de **engrenagem** (⚙️) no canto superior direito
2. Clique em **Add**
3. Nome: `HiProd API`
4. Adicione variáveis:
   - `base_url`: `http://localhost:8000`
   - `api_token`: `SEU_TOKEN_AQUI`
5. Salve

Depois, use nas requisições:
- URL: `{{base_url}}/api/atividades`
- Header Authorization: `Bearer {{api_token}}`

### Collection do Postman (JSON)

Você pode importar esta collection diretamente no Postman:

```json
{
  "info": {
    "name": "HiProd API - Atividades",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Buscar Atividades por Usuário e Período",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{api_token}}",
            "type": "text"
          },
          {
            "key": "Content-Type",
            "value": "application/json",
            "type": "text"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"usuario\": \"nome_do_usuario\",\n  \"time\": {\n    \"inicio\": \"2024-01-01T00:00:00Z\",\n    \"fim\": \"2024-01-31T23:59:59Z\"\n  }\n}",
          "options": {
            "raw": {
              "language": "json"
            }
          }
        },
        "url": {
          "raw": "{{base_url}}/api/atividades",
          "host": ["{{base_url}}"],
          "path": ["api", "atividades"]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "api_token",
      "value": "SEU_TOKEN_AQUI"
    }
  ]
}
```

### Dicas de Teste

1. **Primeiro teste:** Use um período amplo (ex: último mês) para ver se retorna dados
2. **Teste com usuário inexistente:** Para verificar tratamento de erro
3. **Teste sem token:** Para verificar autenticação
4. **Teste com token sem permissão:** Crie um token sem a permissão `/api/atividades`
5. **Teste com datas inválidas:** Para verificar validação

### Formato de Data

As datas devem estar no formato **ISO 8601**:
- `2024-01-01T00:00:00Z` (UTC)
- `2024-01-01T00:00:00-03:00` (com timezone)
- `2024-01-01T00:00:00` (sem timezone, será interpretado como UTC)

### Exemplo de Requisição cURL

Se preferir testar via terminal:

```bash
curl -X POST http://localhost:8000/api/atividades \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "nome_do_usuario",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

