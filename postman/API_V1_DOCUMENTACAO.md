# API V1 - Documentação de Endpoints Externos

## 📋 Visão Geral

A API V1 é uma versão dedicada para **integrações externas** que utilizam **tokens de API** para autenticação. Todos os endpoints estão sob o prefixo `/api/v1/`.

### Características

- ✅ **Apenas Token de API**: Todos os endpoints requerem token de API (não JWT)
- ✅ **CORS Habilitado**: Suporta requisições de outros domínios
- ✅ **Versionamento**: Endpoints versionados para garantir compatibilidade
- ✅ **Permissões Restritivas**: Cada token tem permissões específicas por endpoint
- ✅ **Rastreamento**: Registra último uso automaticamente

## 🔐 Autenticação

Todos os endpoints V1 (exceto `/health`) requerem autenticação via **Token de API**:

```
Authorization: Bearer SEU_TOKEN_DE_API
```

**OU**

```
X-API-Token: SEU_TOKEN_DE_API
```

### Como Obter Token de API

1. Faça login no sistema web
2. Acesse "Tokens API" no menu
3. Crie um novo token com permissões para os endpoints V1 desejados
4. Copie o token (será exibido apenas uma vez)

## 📍 Endpoints Disponíveis

### 1. GET /api/v1/health

**Descrição:** Health check da API (não requer autenticação)

**⚠️ URL CORRETA:** `https://hiprod.grupohi.com.br/api/v1/health`
- ✅ Use `/api/v1/health` (minúsculas, com barras)
- ❌ NÃO use `API/v1?health` (maiúsculas, com `?`)

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

**Resposta (503) - Se banco indisponível:**
```json
{
  "version": "v1",
  "status": "unhealthy",
  "error": "Erro de conexão",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

**Exemplo cURL:**
```bash
curl -X GET https://hiprod.grupohi.com.br/api/v1/health
```

**⚠️ Se receber 404:**
1. Verifique se a URL está exatamente: `/api/v1/health` (minúsculas, com barras)
2. Reinicie o servidor Flask após adicionar os endpoints
3. Verifique os logs do servidor para ver se a requisição está chegando

---

### 2. POST /api/v1/atividades

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

**Parâmetros:**
- `usuario` (obrigatório): Nome ou ID do usuário monitorado
- `time.inicio` (obrigatório): Data/hora de início (ISO 8601)
- `time.fim` (obrigatório): Data/hora de fim (ISO 8601)

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
  "atividades": [
    {
      "id": 1,
      "usuario_monitorado_id": 123,
      "usuario_monitorado_nome": "Rivaldo Santos",
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

**Permissão Necessária:**
- Endpoint: `/api/v1/atividades`
- Método: `POST`

**Exemplo cURL:**
```bash
curl -X POST https://hiprod.grupohi.com.br/api/v1/atividades \
  -H "Authorization: Bearer SEU_TOKEN_DE_API" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "rivaldo.santos",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

---

### 3. GET /api/v1/usuarios

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

**Permissão Necessária:**
- Endpoint: `/api/v1/usuarios`
- Método: `GET`

**Exemplo cURL:**
```bash
curl -X GET https://hiprod.grupohi.com.br/api/v1/usuarios \
  -H "Authorization: Bearer SEU_TOKEN_DE_API"
```

---

### 4. POST /api/v1/estatisticas

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

**Parâmetros:**
- `usuario` (obrigatório): Nome ou ID do usuário monitorado
- `time.inicio` (opcional): Data/hora de início (ISO 8601)
- `time.fim` (opcional): Data/hora de fim (ISO 8601)

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
    },
    {
      "categoria": "neutral",
      "total": 30,
      "media_ociosidade": 10.5,
      "tempo_total": 5000
    },
    {
      "categoria": "nonproductive",
      "total": 20,
      "media_ociosidade": 15.0,
      "tempo_total": 2000
    }
  ]
}
```

**Permissão Necessária:**
- Endpoint: `/api/v1/estatisticas`
- Método: `POST`

**Exemplo cURL:**
```bash
curl -X POST https://hiprod.grupohi.com.br/api/v1/estatisticas \
  -H "Authorization: Bearer SEU_TOKEN_DE_API" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "rivaldo.santos",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

---

## 🔒 Permissões de Token

Para usar os endpoints V1, o token de API deve ter as seguintes permissões:

### Exemplo de Permissões

Ao criar um token, adicione as permissões:

```json
{
  "nome": "Token V1 Completo",
  "permissions": [
    {
      "endpoint": "/api/v1/atividades",
      "method": "POST"
    },
    {
      "endpoint": "/api/v1/usuarios",
      "method": "GET"
    },
    {
      "endpoint": "/api/v1/estatisticas",
      "method": "POST"
    }
  ]
}
```

### Usando Wildcards

Você pode usar wildcards para permitir todos os endpoints V1:

```json
{
  "endpoint": "/api/v1/*",
  "method": "*"
}
```

---

## 📊 Códigos de Resposta

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 400 | Dados inválidos ou faltando |
| 401 | Token não fornecido ou inválido |
| 403 | Token desativado, expirado ou sem permissão |
| 404 | Recurso não encontrado (ex: usuário) |
| 405 | Método HTTP não permitido |
| 500 | Erro interno do servidor |
| 503 | Serviço indisponível (health check) |

---

## 🔍 Exemplos de Integração

### Python

```python
import requests

API_BASE_URL = "https://hiprod.grupohi.com.br/api/v1"
API_TOKEN = "seu_token_de_api_aqui"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Buscar atividades
response = requests.post(
    f"{API_BASE_URL}/atividades",
    json={
        "usuario": "rivaldo.santos",
        "time": {
            "inicio": "2024-01-01T00:00:00Z",
            "fim": "2024-01-31T23:59:59Z"
        }
    },
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Total: {data['total_atividades']} atividades")
    for atividade in data['atividades']:
        print(f"- {atividade['active_window']} em {atividade['horario']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_BASE_URL = 'https://hiprod.grupohi.com.br/api/v1';
const API_TOKEN = 'seu_token_de_api_aqui';

const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json'
};

// Buscar atividades
axios.post(`${API_BASE_URL}/atividades`, {
  usuario: 'rivaldo.santos',
  time: {
    inicio: '2024-01-01T00:00:00Z',
    fim: '2024-01-31T23:59:59Z'
  }
}, { headers })
  .then(response => {
    console.log(`Total: ${response.data.total_atividades} atividades`);
    response.data.atividades.forEach(atividade => {
      console.log(`- ${atividade.active_window} em ${atividade.horario}`);
    });
  })
  .catch(error => {
    console.error('Erro:', error.response?.data || error.message);
  });
```

### PHP

```php
<?php
$apiBaseUrl = 'https://hiprod.grupohi.com.br/api/v1';
$apiToken = 'seu_token_de_api_aqui';

$headers = [
    'Authorization: Bearer ' . $apiToken,
    'Content-Type: application/json'
];

// Buscar atividades
$data = [
    'usuario' => 'rivaldo.santos',
    'time' => [
        'inicio' => '2024-01-01T00:00:00Z',
        'fim' => '2024-01-31T23:59:59Z'
    ]
];

$ch = curl_init($apiBaseUrl . '/atividades');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 200) {
    $result = json_decode($response, true);
    echo "Total: {$result['total_atividades']} atividades\n";
    foreach ($result['atividades'] as $atividade) {
        echo "- {$atividade['active_window']} em {$atividade['horario']}\n";
    }
}
?>
```

---

## ⚠️ Importante

1. **Token de API vs JWT**: Endpoints V1 requerem **Token de API**, não token JWT
2. **Permissões**: Configure as permissões corretas ao criar o token
3. **Versionamento**: Use `/api/v1/` para garantir compatibilidade futura
4. **CORS**: Endpoints suportam requisições de outros domínios
5. **Rate Limiting**: Considere implementar limites de taxa em produção

---

## 📚 Documentação Relacionada

- `../README.md` - Guia geral da collection Postman
- `../EXEMPLOS_ENDPOINTS.md` - Exemplos de todos os endpoints
- `../TROUBLESHOOTING_405.md` - Solução de problemas

