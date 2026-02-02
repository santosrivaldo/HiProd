# Endpoint `/usuarios-monitorados` - Autenticação Condicional

## 📋 Comportamento

O endpoint `GET /usuarios-monitorados` tem comportamento diferente dependendo dos parâmetros:

### 1. Verificação de Existência (SEM Autenticação)

**URL:** `GET /usuarios-monitorados?nome=NOME_USUARIO`

**Autenticação:** ❌ **NÃO REQUERIDA**

**Comportamento:**
- Busca usuário monitorado pelo nome
- Se encontrar: retorna dados do usuário
- Se encontrar inativo: reativa automaticamente
- Se não encontrar: cria novo usuário automaticamente

**Uso:** Agent verifica se usuário existe antes de enviar atividades

**Exemplo:**
```bash
curl "http://192.241.155.236:8010/usuarios-monitorados?nome=rivaldo.santos"
```

### 2. Listar Todos (COM Autenticação)

**URL:** `GET /usuarios-monitorados`

**Autenticação:** ✅ **REQUERIDA** (JWT Token ou X-User-Name)

**Comportamento:**
- Lista todos os usuários monitorados ativos
- Requer autenticação para segurança

**Uso:** Interface web para listar usuários

**Exemplo:**
```bash
# Com JWT Token
curl -H "Authorization: Bearer <jwt_token>" \
     "http://192.241.155.236:8010/usuarios-monitorados"

# Com X-User-Name (modo agente)
curl -H "X-User-Name: nome_usuario" \
     "http://192.241.155.236:8010/usuarios-monitorados"
```

## 🔒 Segurança

### Por que verificação não requer autenticação?

1. **Necessário para o Agent**: O agent precisa verificar se o usuário existe antes de poder enviar atividades
2. **Operação Segura**: Apenas busca/cria usuário monitorado, não expõe dados sensíveis
3. **Criação Controlada**: Apenas cria usuário monitorado básico, sem permissões especiais

### Por que listar todos requer autenticação?

1. **Dados Sensíveis**: Lista todos os usuários monitorados
2. **Controle de Acesso**: Apenas usuários autenticados podem ver a lista completa
3. **Auditoria**: Permite rastrear quem acessou a lista

## 📝 Resumo

| Operação | URL | Autenticação | Uso |
|----------|-----|--------------|-----|
| Verificar/Criar | `/usuarios-monitorados?nome=X` | ❌ Não | Agent |
| Listar Todos | `/usuarios-monitorados` | ✅ Sim | Interface Web |

## ✅ Benefícios

- ✅ Agent pode verificar/criar usuário sem precisar de token
- ✅ Lista completa protegida por autenticação
- ✅ Criação automática de usuários monitorados
- ✅ Reativação automática de usuários inativos

