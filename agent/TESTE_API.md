# Teste de Integração - Agente e API

## ✅ Alterações Implementadas

### 1. **Agente (agent.py)**
- ✅ Removida autenticação por token JWT
- ✅ Removida função `login()`
- ✅ Função `get_headers()` agora inclui o nome do usuário no header `X-User-Name`
- ✅ Todas as requisições HTTP incluem o nome do usuário do Windows

### 2. **API (backend)**
- ✅ Criado novo decorator `@agent_required` em `backend/auth.py`
- ✅ Decorator aceita token JWT OU nome do usuário no header `X-User-Name`
- ✅ Endpoints atualizados para usar `@agent_required`:
  - `/atividade` (POST) - Receber atividades
  - `/face-presence-check` (POST) - Verificação facial
  - `/usuarios-monitorados` (GET) - Buscar/criar usuário monitorado

## 🔍 Como Funciona

### Modo Agente (sem autenticação):
1. Agente obtém nome do usuário do Windows: `get_logged_user()`
2. Envia no header: `X-User-Name: nome_do_usuario`
3. API identifica pelo header e processa a requisição

### Modo Normal (com token):
1. Cliente envia token JWT no header: `Authorization: Bearer <token>`
2. API valida token e processa a requisição

## 📋 Endpoints Testados

### 1. GET `/usuarios-monitorados?nome=UsuarioWindows`
**Header enviado:**
```
X-User-Name: UsuarioWindows
Content-Type: application/json
```

**Comportamento:**
- Se usuário existe: retorna dados do usuário
- Se usuário não existe: cria automaticamente e retorna dados

### 2. POST `/atividade`
**Header enviado:**
```
X-User-Name: UsuarioWindows
Content-Type: application/json
```

**Body:**
```json
{
  "usuario_monitorado_id": 123,
  "active_window": "Chrome",
  "ociosidade": 0,
  ...
}
```

### 3. POST `/face-presence-check`
**Header enviado:**
```
X-User-Name: UsuarioWindows
Content-Type: application/json
```

**Body:**
```json
{
  "usuario_monitorado_id": 123,
  "face_detected": true,
  "presence_time": 300
}
```

## 🧪 Como Testar

### Teste 1: Verificar se agente envia header correto
```python
# No agent.py, função get_headers()
headers = get_headers("UsuarioTeste")
# Deve retornar: {'Content-Type': 'application/json', 'X-User-Name': 'UsuarioTeste'}
```

### Teste 2: Testar endpoint sem token
```bash
curl -X GET "http://localhost:8010/usuarios-monitorados?nome=UsuarioTeste" \
  -H "X-User-Name: UsuarioTeste" \
  -H "Content-Type: application/json"
```

### Teste 3: Testar endpoint com token (deve continuar funcionando)
```bash
curl -X GET "http://localhost:8010/usuarios-monitorados?nome=UsuarioTeste" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

## ⚠️ Observações

1. **Compatibilidade**: A API continua aceitando tokens JWT para outros clientes
2. **Segurança**: O header `X-User-Name` identifica o usuário, mas não autentica
3. **Criação automática**: Usuários são criados automaticamente se não existirem
4. **Validação**: A API valida se o usuário monitorado existe antes de salvar atividades

## ✅ Status

- [x] Agente configurado para enviar nome do usuário
- [x] API configurada para aceitar nome do usuário
- [x] Decorator `@agent_required` criado
- [x] Endpoints atualizados
- [x] Compatibilidade com token mantida

## 🚀 Próximos Passos

1. Testar agente em ambiente real
2. Verificar logs da API para confirmar recebimento
3. Validar criação automática de usuários
4. Testar envio de atividades

