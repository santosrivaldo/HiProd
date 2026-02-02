# Corrigir Problemas de React e WebSocket

## 🔧 Problemas Identificados

1. **WebSocket Inseguro**: Tentando conectar `ws://` em página HTTPS
2. **Múltiplas Cópias do React**: Erro "Cannot read properties of null (reading 'useState')"

## ✅ Correções Aplicadas

### 1. WebSocket (HMR)
- ✅ HMR desabilitado completamente em HTTPS
- ✅ Configuração atualizada no `vite.config.js`

### 2. React
- ✅ Configuração de `dedupe` melhorada
- ✅ Aliases explícitos para React
- ✅ Hook `useIntersectionObserver` atualizado para usar `React.*` diretamente
- ✅ `optimizeDeps.force: true` para forçar re-otimização

## 🚀 Passos para Aplicar as Correções

### Passo 1: Parar o Servidor Vite

Pressione `Ctrl+C` no terminal onde o Vite está rodando.

### Passo 2: Limpar Cache do Vite

```powershell
# Windows PowerShell
Remove-Item -Recurse -Force node_modules\.vite -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
```

### Passo 3: Limpar node_modules e Reinstalar

```powershell
# Windows PowerShell
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue

# Reinstalar
npm install
```

### Passo 4: Verificar Versões do React

```powershell
npm list react react-dom
```

Deve mostrar apenas uma versão de cada.

### Passo 5: Reiniciar o Servidor

```powershell
npm run dev
```

## 🔍 Verificações

### Verificar se HMR está Desabilitado

Após reiniciar, verifique no console do navegador:
- ❌ **NÃO deve aparecer**: `Mixed Content: The page at 'https://...' was loaded over HTTPS, but attempted to connect to the insecure WebSocket`
- ✅ **Deve aparecer**: Apenas logs normais do Vite

### Verificar se React está Funcionando

Após reiniciar, verifique no console do navegador:
- ❌ **NÃO deve aparecer**: `Invalid hook call` ou `Cannot read properties of null (reading 'useState')`
- ✅ **Deve funcionar**: Componente `ActivityManagement` carrega sem erros

## 🐛 Se o Problema Persistir

### 1. Verificar Múltiplas Instalações do React

```powershell
# Windows PowerShell
Get-ChildItem -Path node_modules -Filter react -Recurse -Directory | Select-Object FullName
```

Deve haver apenas:
- `node_modules/react`
- `node_modules/react-dom/node_modules/react` (se houver)

### 2. Verificar package.json

Certifique-se de que há apenas uma versão do React:

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}
```

### 3. Verificar vite.config.js

Certifique-se de que as configurações estão corretas:
- `dedupe: ['react', 'react-dom', 'react/jsx-runtime']`
- `optimizeDeps.force: true`
- `hmr: IS_HTTPS ? false : hmrConfig`

### 4. Limpar Cache do Navegador

1. Abra DevTools (F12)
2. Clique com botão direito no botão de atualizar
3. Selecione "Esvaziar cache e atualizar forçadamente"

### 5. Verificar se está em HTTPS

O Vite detecta automaticamente HTTPS em produção. Se estiver em desenvolvimento local com HTTP, o HMR funcionará normalmente.

## 📝 Notas

- **HMR em Produção**: O HMR (Hot Module Replacement) não é necessário em produção e foi desabilitado para evitar problemas de WebSocket
- **React Único**: As configurações garantem que há apenas uma cópia do React carregada
- **Cache**: Sempre limpe o cache após mudanças significativas no `vite.config.js`

## ✅ Checklist

- [ ] Servidor Vite parado
- [ ] Cache do Vite limpo (`node_modules/.vite`)
- [ ] `node_modules` removido e reinstalado
- [ ] Versões do React verificadas (apenas uma)
- [ ] Servidor reiniciado
- [ ] Console do navegador verificado (sem erros de WebSocket)
- [ ] Componente `ActivityManagement` carrega sem erros
- [ ] Cache do navegador limpo (se necessário)

