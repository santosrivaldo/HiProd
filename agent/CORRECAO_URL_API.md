# Correção das URLs da API no Agente

## 🐛 Problema

O agente estava fazendo requisições para URLs sem o prefixo `/api`, resultando em respostas HTML do frontend em vez de JSON da API.

**Erro observado:**
```
Content-Type: text/html
Resposta: <!doctype html>...
```

## ✅ Correções Aplicadas

### 1. URL de Usuários Monitorados
**Antes:**
```python
USUARIOS_MONITORADOS_URL = f"{API_BASE_URL}/usuarios-monitorados"
```

**Depois:**
```python
USUARIOS_MONITORADOS_URL = f"{API_BASE_URL}/api/usuarios-monitorados"
```

### 2. URL de Atividades
**Antes:**
```python
ATIVIDADE_URL = f"{API_BASE_URL}/atividade"
```

**Depois:**
```python
ATIVIDADE_URL = f"{API_BASE_URL}/api/atividade"
```

### 3. URL de Face Presence Check
**Antes:**
```python
face_check_url = f"{API_BASE_URL}/face-presence-check"
```

**Depois:**
```python
face_check_url = f"{API_BASE_URL}/api/face-presence-check"
```

## 📋 Endpoints Corretos

| Funcionalidade | Endpoint | Método |
|---------------|----------|--------|
| Buscar/Criar Usuário Monitorado | `/api/usuarios-monitorados?nome=USERNAME` | GET |
| Enviar Atividade | `/api/atividade` | POST |
| Face Presence Check | `/api/face-presence-check` | POST |

## 🚀 Próximos Passos

1. Reiniciar o agente para aplicar as mudanças
2. Verificar os logs para confirmar que as requisições estão sendo feitas corretamente
3. Confirmar que as respostas são JSON e não HTML

## 📝 Nota

Todas as URLs da API devem incluir o prefixo `/api` para serem roteadas corretamente pelo Nginx para o backend Flask, em vez de serem servidas como páginas HTML do frontend.

