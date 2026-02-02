# Troubleshooting - Erro 405 Method Not Allowed

## Problema
Ao tentar acessar o endpoint `/api/atividades`, você recebe:
```
405 Method Not Allowed
The method is not allowed for the requested URL.
```

## Soluções

### 1. Verificar o Método HTTP
**Certifique-se de estar usando POST, não GET!**

No Postman:
- ✅ Método: **POST**
- ❌ NÃO use GET

### 2. Verificar a URL Completa
A URL correta é:
```
http://localhost:8000/api/atividades
```

**NÃO use:**
- ❌ `http://localhost:8000/atividades` (sem `/api`)
- ❌ `http://localhost:8000/api/atividades/` (com barra no final pode causar problemas)

### 3. Verificar Headers
Certifique-se de ter:
```
Authorization: Bearer SEU_TOKEN_AQUI
Content-Type: application/json
```

### 4. Verificar Body
O body deve estar em formato JSON:
```json
{
  "usuario": "nome_do_usuario",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

### 5. Reiniciar o Servidor Flask
Se você acabou de adicionar a rota, reinicie o servidor:

```bash
# Pare o servidor (Ctrl+C)
# Inicie novamente
python app.py
```

### 6. Verificar Logs do Servidor
Verifique os logs do servidor Flask. Você deve ver algo como:
```
📥 POST /api/atividades de 127.0.0.1
```

Se não aparecer, a requisição não está chegando ao servidor.

### 7. Testar com cURL
Teste diretamente com cURL para isolar o problema:

```bash
curl -X POST http://localhost:8000/api/atividades \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "admin",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

### 8. Verificar Permissões do Token
Certifique-se de que o token tem permissão para:
- Endpoint: `/api/atividades`
- Método: `POST`

### 9. Verificar se o Servidor Está Rodando
Certifique-se de que o servidor Flask está rodando na porta correta:
```
🚀 Servidor rodando em http://0.0.0.0:8000
```

### 10. Verificar CORS (se testando de outro domínio)
Se estiver testando de um navegador ou outro domínio, pode ser necessário configurar CORS. O endpoint já trata OPTIONS, mas verifique se o servidor está configurado corretamente.

## Checklist Rápido

- [ ] Método é **POST** (não GET)
- [ ] URL está correta: `http://localhost:8000/api/atividades`
- [ ] Header `Authorization: Bearer TOKEN` está presente
- [ ] Header `Content-Type: application/json` está presente
- [ ] Body está em formato JSON válido
- [ ] Servidor Flask está rodando
- [ ] Token tem permissão para `/api/atividades` (POST)
- [ ] Servidor foi reiniciado após adicionar a rota

## Exemplo Correto no Postman

1. **Método:** POST
2. **URL:** `http://localhost:8000/api/atividades`
3. **Headers:**
   - `Authorization`: `Bearer seu_token_aqui`
   - `Content-Type`: `application/json`
4. **Body (raw, JSON):**
```json
{
  "usuario": "admin",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

## Se Nada Funcionar

1. Verifique os logs do servidor Flask para ver se a requisição está chegando
2. Teste com cURL para isolar problemas do Postman
3. Verifique se há outras rotas conflitantes
4. Verifique se o blueprint está registrado corretamente no `app.py`

