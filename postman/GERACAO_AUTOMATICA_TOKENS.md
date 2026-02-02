# Geração Automática de Tokens de API

## ✅ Sistema Implementado

O sistema **gera tokens automaticamente** quando você cria um novo token de API. Você **não precisa informar ou digitar** o token manualmente.

## Como Funciona

### 1. Criação de Token

Quando você cria um token via API ou interface web:

```json
POST /api-tokens
{
  "nome": "Token Teste",
  "descricao": "Descrição",
  "permissions": [...]
}
```

O sistema:
1. ✅ **Gera automaticamente** um token único e seguro
2. ✅ **Verifica** se o token já existe no banco
3. ✅ **Gera um novo** se houver duplicata (muito improvável)
4. ✅ **Retorna o token** na resposta (exibido apenas uma vez)

### 2. Geração do Token

A função `generate_api_token()`:

- Usa `secrets.token_urlsafe(32)` para gerar token seguro
- Gera token de 43 caracteres (URL-safe)
- Verifica unicidade no banco de dados
- Tenta até 10 vezes se houver duplicata
- Adiciona timestamp se necessário para garantir unicidade

### 3. Exemplo de Token Gerado

```
xK9mP2qR7vT4wY8zA1bC3dE5fG6hI0jK2lM4nO6pQ8rS0tU
```

**Características:**
- ✅ 43 caracteres
- ✅ URL-safe (pode ser usado em URLs)
- ✅ Único no banco de dados
- ✅ Criptograficamente seguro

## Fluxo de Criação

```
1. Usuário cria token (informa apenas nome, descrição, permissões)
   ↓
2. Sistema gera token automaticamente
   ↓
3. Sistema verifica se token já existe
   ↓
4. Se não existe: salva no banco
   Se existe: gera novo e verifica novamente
   ↓
5. Sistema retorna token na resposta
   ↓
6. Token é exibido apenas UMA VEZ
```

## Segurança

### ✅ Implementado

- Tokens gerados com `secrets.token_urlsafe()` (criptograficamente seguro)
- Verificação de unicidade no banco
- Tokens não são exibidos novamente após criação
- Tokens podem ser desativados/excluídos

### ⚠️ Importante

- **Copie o token imediatamente** após criação
- O token **não será exibido novamente**
- Se perder o token, crie um novo

## Código de Geração

```python
def generate_api_token():
    """
    Gerar um token de API único e seguro.
    Garante que o token seja único no banco de dados.
    """
    max_attempts = 10
    
    for attempt in range(max_attempts):
        token = secrets.token_urlsafe(32)
        
        # Verificar se o token já existe no banco
        with DatabaseConnection() as db:
            db.cursor.execute('SELECT id FROM api_tokens WHERE token = %s', (token,))
            if not db.cursor.fetchone():
                return token  # Token único encontrado
    
    # Se todas as tentativas geraram duplicatas (muito improvável)
    # Adiciona timestamp para garantir unicidade
    import time
    unique_suffix = str(int(time.time() * 1000000))
    return secrets.token_urlsafe(24) + unique_suffix
```

## Exemplo de Resposta

Quando você cria um token:

```json
{
  "message": "Token criado com sucesso!",
  "token": "xK9mP2qR7vT4wY8zA1bC3dE5fG6hI0jK2lM4nO6pQ8rS0tU",
  "id": 1,
  "nome": "Token Teste"
}
```

**⚠️ IMPORTANTE:** Copie o `token` imediatamente! Ele não será exibido novamente.

## Verificação de Unicidade

O sistema garante que:

1. ✅ Cada token é único no banco de dados
2. ✅ Não há risco de duplicação
3. ✅ Se houver colisão (muito improvável), gera novo token
4. ✅ Máximo de 10 tentativas para evitar loop infinito

## Estatísticas

- **Probabilidade de duplicata:** Praticamente zero
  - `secrets.token_urlsafe(32)` gera ~2^256 possibilidades
  - Chance de colisão é extremamente baixa
  
- **Tentativas:** Máximo 10 tentativas
  - Se todas falharem (muito improvável), adiciona timestamp
  - Garante que sempre retorna um token único

## Conclusão

✅ **O sistema já gera tokens automaticamente**

- Você não precisa informar o token
- O token é gerado automaticamente na criação
- O token é único e seguro
- O token é retornado apenas uma vez na resposta

**Apenas certifique-se de copiar o token quando ele for exibido!**

