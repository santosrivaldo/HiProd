# Configuração HTTPS - HiProd

## 🔒 Problema: Mixed Content Error

Quando a aplicação é servida via HTTPS, o navegador bloqueia conexões WebSocket inseguras (ws://). O Vite precisa usar WebSocket seguro (wss://) ou ter o HMR desabilitado em produção.

## ✅ Soluções Implementadas

### 1. Detecção Automática de HTTPS

O Vite agora detecta automaticamente se está rodando em HTTPS e configura o HMR adequadamente.

### 2. Configuração de Variáveis de Ambiente

Para forçar HTTPS, defina:

```bash
# .env ou variáveis de ambiente
VITE_HTTPS=1
# OU
HTTPS=1
# OU (automático em produção)
NODE_ENV=production
```

### 3. HMR Desabilitado em Produção HTTPS

Em produção HTTPS, o HMR (Hot Module Replacement) é automaticamente desabilitado para evitar problemas de WebSocket.

## 🚀 Configuração para Produção

### Opção 1: Desabilitar HMR (Recomendado para Produção)

O HMR já está configurado para ser desabilitado automaticamente em produção HTTPS. Não é necessário fazer nada adicional.

### Opção 2: Usar WSS (WebSocket Seguro)

Se você precisar de HMR em produção (não recomendado), configure:

```bash
VITE_HTTPS=1
VITE_BEHIND_PROXY=1
VITE_PUBLIC_HOST=hiprod.grupohi.com.br
```

## 📝 Verificações

### 1. Verificar se está em HTTPS

No console do navegador, verifique:
```javascript
console.log(window.location.protocol) // Deve ser "https:"
```

### 2. Verificar WebSocket

O Vite não deve tentar conectar via `ws://` se a página estiver em HTTPS.

### 3. Verificar API

A API deve usar a mesma origem (same-origin) em produção:
```javascript
// Em produção HTTPS, usa: https://hiprod.grupohi.com.br/api
// Em desenvolvimento, usa: http://localhost:8010
```

## 🔧 Troubleshooting

### Erro: "Mixed Content: The page at 'https://...' was loaded over HTTPS, but attempted to connect to the insecure WebSocket endpoint 'ws://...'"

**Solução:**
1. Certifique-se de que `VITE_HTTPS=1` está definido OU
2. O HMR será automaticamente desabilitado em produção
3. Reinicie o servidor Vite

### Erro: "Failed to construct 'WebSocket': An insecure WebSocket connection may not be initiated from a page loaded over HTTPS"

**Solução:**
- O HMR está desabilitado automaticamente em produção HTTPS
- Se precisar de HMR, configure WSS manualmente (não recomendado)

### Erro: "Connection timeout" na porta 5000

**Solução:**
- Em produção HTTPS, não use a porta 5000 diretamente
- Use o proxy reverso (Nginx) que roteia para a aplicação
- A API deve usar `/api` (same-origin)

## 📋 Checklist de Produção HTTPS

- [ ] Aplicação servida via HTTPS
- [ ] HMR desabilitado (automático em produção)
- [ ] API usando same-origin (`/api`)
- [ ] Sem tentativas de conexão WebSocket inseguro
- [ ] Variáveis de ambiente configuradas corretamente

## 🔗 Arquivos Modificados

- `vite.config.js` - Configuração de HMR e HTTPS
- `src/contexts/AuthContext.jsx` - Correção de URL da API
- `src/hooks/useIntersectionObserver.js` - Correção de importação do React

