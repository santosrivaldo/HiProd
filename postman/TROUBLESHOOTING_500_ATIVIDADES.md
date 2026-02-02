# Troubleshooting - Erro 500 em /api/v1/atividades

## Erro Recebido

```json
{
    "message": "Erro interno do servidor!"
}
```

## Melhorias Implementadas

### 1. ✅ Validação de Datas Melhorada
- Valida se as datas são strings
- Normaliza formato ISO 8601
- Garante timezone UTC
- Valida que início < fim

### 2. ✅ Tratamento de Erros Melhorado
- Logs com traceback completo
- Mensagens de erro mais detalhadas
- Retorna tipo de erro na resposta
- Tratamento de erros por linha de resultado

### 3. ✅ Validação de Dados
- Valida tipos antes de processar
- Converte tipos corretamente (int, bool)
- Continua mesmo se uma linha falhar

## Como Diagnosticar

### 1. Verificar Logs do Servidor

Após fazer a requisição, verifique os logs do servidor Flask. Você deve ver:

```
❌ Erro ao buscar atividades por token: [detalhes do erro]
Traceback (most recent call last):
  [stack trace completo]
```

### 2. Verificar Requisição

Certifique-se de que a requisição está correta:

```bash
POST /api/v1/atividades
Authorization: Bearer SEU_TOKEN_DE_API
Content-Type: application/json

{
  "usuario": "rivaldo.santos",
  "time": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  }
}
```

### 3. Possíveis Causas

#### Causa 1: Formato de Data Inválido
**Erro esperado:**
```json
{
  "message": "Formato de data inválido: ...",
  "exemplo": "Use formato ISO 8601: 2024-01-01T00:00:00Z"
}
```

**Solução:** Use formato ISO 8601:
- ✅ `2024-01-01T00:00:00Z`
- ✅ `2024-01-01T00:00:00+00:00`
- ❌ `2024-01-01` (sem hora)
- ❌ `01/01/2024` (formato brasileiro)

#### Causa 2: Usuário Não Encontrado
**Erro esperado:**
```json
{
  "message": "Usuário \"nome\" não encontrado!"
}
```

**Solução:** 
- Verifique se o usuário existe na tabela `usuarios_monitorados`
- Use o nome exato ou ID do usuário

#### Causa 3: Erro no Banco de Dados
**Erro esperado:** Logs mostram erro SQL

**Solução:**
- Verifique conexão com banco
- Verifique se tabelas existem
- Verifique permissões do banco

#### Causa 4: Erro ao Processar Resultados
**Erro esperado:** Logs mostram "Erro ao processar linha"

**Solução:**
- Verifique estrutura da tabela `atividades`
- Verifique se todas as colunas existem
- O código agora continua mesmo se uma linha falhar

## Teste Passo a Passo

### 1. Teste Básico

```bash
curl -X POST "https://hiprod.grupohi.com.br/api/v1/atividades" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "rivaldo.santos",
    "time": {
      "inicio": "2024-01-01T00:00:00Z",
      "fim": "2024-01-31T23:59:59Z"
    }
  }'
```

### 2. Verificar Resposta

**Sucesso esperado:**
```json
{
  "version": "v1",
  "usuario": "rivaldo.santos",
  "periodo": {
    "inicio": "2024-01-01T00:00:00Z",
    "fim": "2024-01-31T23:59:59Z"
  },
  "total_atividades": 10,
  "atividades": [...]
}
```

**Erro esperado:**
```json
{
  "message": "Erro interno do servidor!",
  "error": "[detalhes do erro]",
  "error_type": "[tipo do erro]"
}
```

### 3. Verificar Logs

Após a requisição, verifique os logs do servidor para ver o erro completo.

## Checklist de Verificação

- [ ] Token de API está correto e tem permissão para `/api/v1/atividades` (POST)
- [ ] URL está correta: `/api/v1/atividades`
- [ ] Método está correto: `POST`
- [ ] Header `Content-Type: application/json` está presente
- [ ] Body contém `usuario` (string)
- [ ] Body contém `time.inicio` (string ISO 8601)
- [ ] Body contém `time.fim` (string ISO 8601)
- [ ] Usuário existe na tabela `usuarios_monitorados`
- [ ] Datas estão no formato correto (ISO 8601)
- [ ] Data de início é anterior à data de fim

## Próximos Passos

1. ✅ Faça a requisição novamente
2. ✅ Verifique os logs do servidor Flask
3. ✅ Os logs agora mostram o erro completo com traceback
4. ✅ Compartilhe os logs se o problema persistir

## Melhorias Aplicadas

- ✅ Validação de datas mais robusta
- ✅ Tratamento de erros melhorado
- ✅ Logs mais detalhados
- ✅ Mensagens de erro mais informativas
- ✅ Tratamento de erros por linha (continua mesmo se uma falhar)

