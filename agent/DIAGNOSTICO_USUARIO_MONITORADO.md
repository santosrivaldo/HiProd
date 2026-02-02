# Diagnóstico - Erro ao Criar Usuário Monitorado

## 🔍 Problema

Erro: `Expecting value: line 2 column 1 (char 1)` ao tentar criar/buscar usuário monitorado.

## ✅ Melhorias Aplicadas

1. **Logs Detalhados**: Agora mostra sempre:
   - Status code da resposta
   - Content-Type
   - Tamanho da resposta
   - Conteúdo completo da resposta em caso de erro

2. **Validação**: Verifica se o nome do usuário está presente antes de fazer requisição

3. **Tratamento de Erros**: Trata especificamente:
   - Status 401 (autenticação)
   - Status 500 (erro interno)
   - Respostas vazias
   - JSON malformado

## 🔧 Como Diagnosticar

### 1. Verificar Logs do Agent

Após recompilar e executar, os logs mostrarão:
```
[INFO] Buscando/criando usuário monitorado: NOME_USUARIO
[INFO] URL: https://hiprod.grupohi.com.br/usuarios-monitorados
[INFO] Params: nome=NOME_USUARIO
[INFO] Headers: X-User-Name=NOME_USUARIO
[INFO] Status code: XXX
[INFO] Content-Type: XXX
[INFO] Response length: XXX bytes
```

### 2. Verificar Logs do Backend

No backend, verifique se aparece:
```
✅ Usuário monitorado encontrado: NOME_USUARIO (ID: X)
```
ou
```
🔧 Criando novo usuário monitorado: NOME_USUARIO
✅ Usuário monitorado criado: NOME_USUARIO (ID: X)
```

### 3. Possíveis Causas

#### A. Resposta Vazia
**Sintoma**: `Response length: 0 bytes`
**Causa**: Backend não está retornando resposta
**Solução**: Verificar logs do backend para erros

#### B. HTML em vez de JSON
**Sintoma**: `Content-Type: text/html` ou resposta começa com `<!DOCTYPE`
**Causa**: Backend retornando página de erro HTML
**Solução**: Verificar se o endpoint está correto e se há erros no backend

#### C. Erro 500
**Sintoma**: `Status code: 500`
**Causa**: Erro interno no backend
**Solução**: Verificar logs do backend para exceções

#### D. Erro 401
**Sintoma**: `Status code: 401`
**Causa**: Header `X-User-Name` não está sendo enviado ou não está sendo aceito
**Solução**: Verificar se o header está sendo enviado corretamente

## 🚀 Próximos Passos

1. **Recompilar o executável**:
   ```bash
   python build.py
   ```

2. **Executar e verificar logs**:
   - Os logs agora mostram todas as informações necessárias
   - Verifique o status code e conteúdo da resposta

3. **Verificar backend**:
   - Verifique se o endpoint `/usuarios-monitorados` está funcionando
   - Teste manualmente com curl ou Postman:
     ```bash
     curl -H "X-User-Name: NOME_USUARIO" \
          "https://hiprod.grupohi.com.br/usuarios-monitorados?nome=NOME_USUARIO"
     ```

## 📝 Teste Manual

Para testar o endpoint diretamente:

```bash
# Windows PowerShell
$headers = @{
    "X-User-Name" = "NOME_USUARIO_WINDOWS"
    "Content-Type" = "application/json"
}
Invoke-RestMethod -Uri "https://hiprod.grupohi.com.br/usuarios-monitorados?nome=NOME_USUARIO_WINDOWS" -Headers $headers -Method Get
```

## 🔍 Verificações no Backend

1. Verificar se a tabela `usuarios_monitorados` existe
2. Verificar se há escala padrão "Comercial Padrão" na tabela `escalas_trabalho`
3. Verificar logs do Flask para erros de SQL ou exceções

## ✅ Checklist

- [ ] Agent recompilado com as melhorias
- [ ] Logs do agent mostram informações detalhadas
- [ ] Logs do backend verificados
- [ ] Endpoint testado manualmente
- [ ] Tabela `usuarios_monitorados` existe e está acessível
- [ ] Escala padrão existe no banco de dados

