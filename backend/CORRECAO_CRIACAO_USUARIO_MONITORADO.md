# Correção - Criação de Usuário Monitorado

## 🔍 Problema Identificado

A API não estava criando usuários monitorados quando não existiam porque:

1. **Query buscava apenas usuários ativos**: `WHERE um.nome = %s AND um.ativo = TRUE`
2. **Usuários inativos não eram encontrados**: Se o usuário existisse mas estivesse inativo, não seria encontrado
3. **Erro de duplicação**: Ao tentar criar um usuário que já existe (mesmo inativo), ocorria erro de constraint UNIQUE
4. **Erro silencioso**: O erro não era tratado adequadamente

## ✅ Correções Aplicadas

### 1. Busca Independente do Status Ativo

**Antes:**
```sql
WHERE um.nome = %s AND um.ativo = TRUE;
```

**Depois:**
```sql
WHERE um.nome = %s;
```

Agora busca o usuário independente do status ativo.

### 2. Reativação Automática

Se o usuário for encontrado mas estiver inativo, ele é automaticamente reativado:

```python
if not usuario_existente[4]:  # ativo está no índice 4
    db.cursor.execute('''
        UPDATE usuarios_monitorados
        SET ativo = TRUE, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    ''', (usuario_existente[0],))
```

### 3. Tratamento de Erro de Duplicação

Se ocorrer erro de duplicação ao tentar criar:
1. Busca o usuário existente novamente
2. Reativa se estiver inativo
3. Retorna os dados completos do usuário

```python
except Exception as insert_error:
    if 'unique' in str(insert_error).lower() or 'duplicate' in str(insert_error).lower():
        # Buscar usuário existente
        # Reativar se inativo
        # Retornar dados completos
```

### 4. Logs Melhorados

- Logs detalhados quando usuário é reativado
- Logs quando usuário é encontrado após erro de duplicação
- Traceback completo em caso de erro

## 🔄 Fluxo Corrigido

1. **Buscar usuário** (independente do status ativo)
2. **Se encontrado**:
   - Se ativo: retornar dados
   - Se inativo: reativar e retornar dados
3. **Se não encontrado**:
   - Criar novo usuário
   - Se der erro de duplicação: buscar novamente e reativar se necessário

## 📝 Resultado

Agora a API:
- ✅ Cria usuários quando não existem
- ✅ Reativa usuários inativos automaticamente
- ✅ Trata erros de duplicação corretamente
- ✅ Retorna dados completos em todos os casos

## 🚀 Teste

Para testar, execute o agent e verifique os logs:

```
[INFO] Buscando/criando usuário monitorado: NOME_USUARIO
✅ Usuário monitorado criado: NOME_USUARIO (ID: X)
```

ou

```
[INFO] Buscando/criando usuário monitorado: NOME_USUARIO
🔄 Reativando usuário monitorado: NOME_USUARIO
✅ Usuário monitorado reativado: NOME_USUARIO (ID: X)
```

