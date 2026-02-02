# Troubleshooting - Erro 404 nos Endpoints V1

## Problema
Ao tentar acessar os endpoints V1, você recebe:
```
404 Not Found
The requested URL was not found on the server.
```

## Soluções

### 1. Verificar a URL Correta

A URL deve ser exatamente:
```
https://hiprod.grupohi.com.br/api/v1/health
```

**❌ URLs Incorretas:**
- `API/v1?health` (maiúsculas, sem barra, com ?)
- `api/v1/health` (sem barra inicial)
- `/API/v1/health` (maiúsculas)
- `api/v1?health` (com ? em vez de /)

**✅ URL Correta:**
- `https://hiprod.grupohi.com.br/api/v1/health`
- `http://localhost:8000/api/v1/health` (desenvolvimento)

### 2. Reiniciar o Servidor Flask

**IMPORTANTE:** Após adicionar novos endpoints, você DEVE reiniciar o servidor Flask!

```bash
# Pare o servidor (Ctrl+C)
# Inicie novamente
python app.py
```

### 3. Verificar se o Blueprint Está Registrado

Verifique os logs do servidor ao iniciar. Você deve ver algo como:
```
🚀 Servidor rodando em http://0.0.0.0:8000
```

Se houver erros de importação ou registro, eles aparecerão nos logs.

### 4. Verificar Rotas Registradas

Você pode verificar as rotas registradas adicionando este código temporariamente no `app.py`:

```python
# Após registrar todos os blueprints
with app.app_context():
    print("\n📋 Rotas registradas:")
    for rule in app.url_map.iter_rules():
        print(f"   {rule.methods} {rule.rule}")
```

### 5. Testar com cURL

Teste diretamente com cURL para isolar o problema:

```bash
# Health check (sem autenticação)
curl -X GET https://hiprod.grupohi.com.br/api/v1/health

# Com token de API
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

### 6. Verificar Logs do Servidor

Quando você faz uma requisição, verifique os logs do servidor Flask. Você deve ver:

```
📥 GET /api/v1/health de 127.0.0.1
```

Se não aparecer, a requisição não está chegando ao servidor.

### 7. Verificar Nginx/Proxy (se aplicável)

Se estiver usando Nginx ou outro proxy reverso, verifique se as rotas `/api/v1/*` estão configuradas corretamente.

### 8. Verificar Porta do Servidor

Certifique-se de que está acessando a porta correta:
- Desenvolvimento: `http://localhost:8000`
- Produção: `https://hiprod.grupohi.com.br` (porta padrão 80/443)

## ✅ Checklist Rápido

- [ ] URL está correta: `/api/v1/health` (não `API/v1?health`)
- [ ] Servidor Flask foi reiniciado após adicionar endpoints
- [ ] Blueprint está registrado no `app.py`
- [ ] Não há erros nos logs do servidor
- [ ] Porta do servidor está correta
- [ ] Testou com cURL para isolar problemas do Postman

## 🔍 URLs Corretas dos Endpoints V1

| Endpoint | URL Completa |
|----------|--------------|
| Health Check | `https://hiprod.grupohi.com.br/api/v1/health` |
| Atividades | `https://hiprod.grupohi.com.br/api/v1/atividades` |
| Usuários | `https://hiprod.grupohi.com.br/api/v1/usuarios` |
| Estatísticas | `https://hiprod.grupohi.com.br/api/v1/estatisticas` |

## 📝 Exemplo Correto no Postman

1. **Método:** GET
2. **URL:** `https://hiprod.grupohi.com.br/api/v1/health`
   - ✅ Com `https://`
   - ✅ Com `/api/v1/` (minúsculas, com barras)
   - ✅ Com `/health` no final
3. **Headers:** Nenhum necessário para health check
4. **Body:** Nenhum

## 🐛 Se Nada Funcionar

1. Verifique se o arquivo `backend/routes/api_v1_routes.py` existe
2. Verifique se o import está correto no `app.py`
3. Verifique se não há erros de sintaxe no código
4. Verifique os logs completos do servidor Flask
5. Teste com um endpoint simples primeiro (health check)

