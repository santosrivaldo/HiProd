# URLs Corretas - Endpoints V1

## ⚠️ Erro Comum

Se você está recebendo **404 Not Found**, verifique se a URL está correta!

## ✅ URLs Corretas

### Health Check
```
GET https://hiprod.grupohi.com.br/api/v1/health
```

### Buscar Atividades
```
POST https://hiprod.grupohi.com.br/api/v1/atividades
```

### Listar Usuários
```
GET https://hiprod.grupohi.com.br/api/v1/usuarios
```

### Obter Estatísticas
```
POST https://hiprod.grupohi.com.br/api/v1/estatisticas
```

## ❌ URLs Incorretas (NÃO Funcionam)

- ❌ `API/v1?health` - Maiúsculas, sem barra inicial, com `?`
- ❌ `api/v1?health` - Sem barra inicial, com `?`
- ❌ `/API/v1/health` - Maiúsculas
- ❌ `api/v1/health` - Sem barra inicial
- ❌ `/api/v1?health` - Com `?` em vez de `/`

## ✅ Formato Correto

```
https://hiprod.grupohi.com.br/api/v1/health
│         │                    │   │  │
│         │                    │   │  └─ Nome do endpoint
│         │                    │   └─ Versão (v1)
│         │                    └─ Prefixo da API externa
│         └─ Domínio do servidor
└─ Protocolo (https ou http)
```

## 📝 Exemplo no Postman

1. **Método:** GET
2. **URL:** `https://hiprod.grupohi.com.br/api/v1/health`
   - ✅ Começa com `https://` ou `http://`
   - ✅ Domínio completo
   - ✅ `/api/v1/` (minúsculas, com barras)
   - ✅ `/health` no final (sem `?`)

## 🔧 Verificação Rápida

1. A URL começa com `http://` ou `https://`? ✅
2. Tem o domínio completo? ✅
3. Tem `/api/v1/` (minúsculas)? ✅
4. Termina com o nome do endpoint? ✅
5. Não tem `?` no lugar de `/`? ✅

## 🚀 Teste Rápido

Copie e cole esta URL exata no Postman:

```
https://hiprod.grupohi.com.br/api/v1/health
```

Se ainda der 404, o servidor precisa ser reiniciado!

