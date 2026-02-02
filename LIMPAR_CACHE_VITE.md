# Limpar Cache do Vite - Resolver Problemas de React

## 🔧 Problema: Múltiplas Cópias do React

Se você está vendo erros como "Invalid hook call" ou "Cannot read properties of null (reading 'useState')", pode ser devido a múltiplas cópias do React ou cache corrompido do Vite.

## ✅ Solução: Limpar Cache e Reinstalar

### Passo 1: Parar o servidor Vite

Pressione `Ctrl+C` no terminal onde o Vite está rodando.

### Passo 2: Limpar cache do Vite

```bash
# Windows
rmdir /s /q node_modules\.vite
rmdir /s /q dist

# Linux/Mac
rm -rf node_modules/.vite
rm -rf dist
```

### Passo 3: Limpar node_modules e reinstalar

```bash
# Windows
rmdir /s /q node_modules
del package-lock.json

# Linux/Mac
rm -rf node_modules
rm package-lock.json

# Reinstalar
npm install
```

### Passo 4: Verificar versões do React

```bash
npm list react react-dom
```

Certifique-se de que há apenas uma versão de cada.

### Passo 5: Reiniciar o servidor

```bash
npm run dev
```

## 🔍 Verificações Adicionais

### Verificar se há múltiplas instalações do React

```bash
# Windows PowerShell
Get-ChildItem -Path node_modules -Filter react -Recurse -Directory | Select-Object FullName

# Linux/Mac
find node_modules -name react -type d
```

Deve haver apenas:
- `node_modules/react`
- `node_modules/react-dom/node_modules/react` (se houver)

### Verificar package-lock.json

Certifique-se de que `package-lock.json` tem apenas uma versão do React listada.

## 🚨 Se o Problema Persistir

1. **Verificar vite.config.js**: Certifique-se de que `dedupe` está configurado corretamente
2. **Verificar imports**: Todos os arquivos devem importar React da mesma forma
3. **Verificar node_modules**: Pode ser necessário deletar e reinstalar completamente

## 📝 Nota

Após limpar o cache, o primeiro build pode demorar mais, pois o Vite precisa reconstruir tudo.

