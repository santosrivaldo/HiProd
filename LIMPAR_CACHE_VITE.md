# Limpar Cache do Vite - Resolver Erro de Múltiplas Cópias do React

## 🐛 Problema

Erro: `Invalid hook call. Hooks can only be called inside of the body of a function component.`

Este erro geralmente ocorre quando há múltiplas cópias do React sendo carregadas.

## ✅ Solução

### 1. Limpar Cache do Vite

**Windows (PowerShell):**
```powershell
cd C:\Projetos\HiProd
Remove-Item -Recurse -Force node_modules\.vite
```

**Linux/Mac:**
```bash
cd /caminho/para/HiProd
rm -rf node_modules/.vite
```

### 2. Limpar node_modules (se necessário)

**Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force node_modules
npm install
```

**Linux/Mac:**
```bash
rm -rf node_modules
npm install
```

### 3. Reiniciar o Servidor de Desenvolvimento

```bash
# Parar o servidor (Ctrl+C)
# Iniciar novamente
npm run dev
```

## 🔍 Verificações

### Verificar se há múltiplas cópias do React

```bash
# Verificar versões instaladas
npm list react react-dom

# Deve mostrar apenas uma versão de cada
```

### Verificar configuração do Vite

O arquivo `vite.config.js` já está configurado com:
- `dedupe: ['react', 'react-dom', 'react/jsx-runtime']`
- `alias` para forçar resolução única do React
- `optimizeDeps.force: true`

## 📝 Alterações Realizadas

1. ✅ Hook `useIntersectionObserver` agora usa importações diretas:
   ```javascript
   import { useState, useEffect, useRef } from 'react'
   ```

2. ✅ Componente `ActivityManagement` não importa `React` explicitamente:
   ```javascript
   import { useState, useEffect, useCallback } from 'react'
   ```

3. ✅ Cache do Vite foi limpo

## 🚀 Próximos Passos

1. Reiniciar o servidor de desenvolvimento
2. Verificar se o erro foi resolvido
3. Se o erro persistir, limpar `node_modules` e reinstalar dependências
