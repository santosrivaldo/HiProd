# Importar Tags via CSV

## 📋 Visão Geral

O sistema permite importar múltiplas tags de uma vez através de um arquivo CSV. Isso facilita a criação em massa de tags e suas palavras-chave associadas.

## 🔗 Endpoint

```
POST /tags/import-csv
```

**Autenticação:** JWT Token (requerido)

**Content-Type:** `multipart/form-data`

## 📝 Formato do CSV

### Colunas Obrigatórias

- **nome** (obrigatório): Nome da tag
- **produtividade** (obrigatório): Deve ser `productive`, `nonproductive` ou `neutral`

### Colunas Opcionais

- **descricao**: Descrição da tag
- **cor**: Cor em hexadecimal (ex: `#6B7280`). Padrão: `#6B7280`
- **departamento_id**: ID numérico do departamento
- **departamento_nome**: Nome do departamento (alternativa a `departamento_id`)
- **tier**: Nível de prioridade (1-5). Padrão: `3`
- **palavras_chave**: Palavras-chave separadas por vírgula ou ponto-e-vírgula
- **ativo**: `true` ou `false`. Padrão: `true`

## 📄 Exemplo de CSV

```csv
nome,descricao,cor,produtividade,departamento_nome,tier,palavras_chave,ativo
Google,Google Search e serviços,#4285F4,productive,TI,1,"google,search,busca,chrome",true
Facebook,Redes Sociais Facebook,#1877F2,nonproductive,Geral,3,"facebook,rede social,fb",true
YouTube,Plataforma de vídeos,#FF0000,neutral,Geral,2,"youtube,video,yt",true
Microsoft Teams,Comunicação corporativa,#6264A7,productive,TI,1,"teams,microsoft,comunicação",true
```

## 🚀 Como Usar

### Via cURL

```bash
curl -X POST http://localhost:8000/tags/import-csv \
  -H "Authorization: Bearer <seu_jwt_token>" \
  -F "file=@tags_exemplo.csv"
```

### Via Python (requests)

```python
import requests

# Autenticar primeiro
response = requests.post('http://localhost:8000/login', json={
    'nome': 'usuario',
    'senha': 'senha123'
})
token = response.json()['token']

# Importar CSV
with open('tags_exemplo.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/tags/import-csv',
        headers={'Authorization': f'Bearer {token}'},
        files={'file': ('tags_exemplo.csv', f, 'text/csv')}
    )

resultado = response.json()
print(f"Tags criadas: {resultado['tags_criadas']}")
print(f"Tags atualizadas: {resultado['tags_atualizadas']}")
print(f"Tags ignoradas: {resultado['tags_ignoradas']}")
```

### Via JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/tags/import-csv', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('Tags criadas:', data.tags_criadas);
  console.log('Tags atualizadas:', data.tags_atualizadas);
  console.log('Tags ignoradas:', data.tags_ignoradas);
  if (data.erros) {
    console.error('Erros:', data.erros);
  }
});
```

## 📊 Resposta

### Sucesso

```json
{
  "message": "Importação concluída!",
  "tags_criadas": 8,
  "tags_atualizadas": 2,
  "tags_ignoradas": 0,
  "total_processadas": 10
}
```

### Com Erros

```json
{
  "message": "Importação concluída! (5 erros encontrados)",
  "tags_criadas": 5,
  "tags_atualizadas": 0,
  "tags_ignoradas": 5,
  "total_processadas": 10,
  "erros": [
    "Linha 3: Produtividade inválida (deve ser: productive, nonproductive ou neutral)",
    "Linha 7: Departamento \"Marketing\" não encontrado",
    "Linha 9: Nome é obrigatório"
  ],
  "erros_total": 5
}
```

## ⚠️ Regras de Importação

1. **Tags Duplicadas**: Se uma tag com o mesmo nome e departamento já existe, ela será **atualizada** em vez de criada.

2. **Validação de Produtividade**: Deve ser exatamente uma das opções:
   - `productive`
   - `nonproductive`
   - `neutral`

3. **Validação de Tier**: Deve ser um número entre 1 e 5. Valores inválidos serão substituídos por 3 (padrão).

4. **Departamento**: 
   - Se `departamento_id` for fornecido, será usado diretamente
   - Se `departamento_nome` for fornecido, será buscado no banco
   - Se nenhum for fornecido, a tag será global (sem departamento)

5. **Palavras-chave**: 
   - Podem ser separadas por vírgula (`,`) ou ponto-e-vírgula (`;`)
   - Exemplo: `"palavra1,palavra2,palavra3"` ou `"palavra1;palavra2;palavra3"`
   - Palavras-chave existentes serão removidas e substituídas pelas novas

6. **Encoding**: O arquivo deve estar em UTF-8. O sistema remove automaticamente o BOM se presente.

## 🔍 Exemplo Completo

### Arquivo CSV (`tags_exemplo.csv`)

```csv
nome,descricao,cor,produtividade,departamento_nome,tier,palavras_chave,ativo
Google,Google Search,#4285F4,productive,TI,1,"google,search,busca",true
Facebook,Redes Sociais,#1877F2,nonproductive,Geral,3,"facebook,rede social",true
YouTube,Vídeos,#FF0000,neutral,Geral,2,"youtube,video",true
```

### Requisição

```bash
curl -X POST http://localhost:8000/tags/import-csv \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "file=@tags_exemplo.csv"
```

### Resposta

```json
{
  "message": "Importação concluída!",
  "tags_criadas": 3,
  "tags_atualizadas": 0,
  "tags_ignoradas": 0,
  "total_processadas": 3
}
```

## 🐛 Troubleshooting

### Erro: "Arquivo CSV não fornecido!"

**Causa:** O campo `file` não foi enviado na requisição.

**Solução:** Certifique-se de enviar o arquivo com o nome de campo `file`.

### Erro: "CSV deve conter as colunas: nome, produtividade"

**Causa:** O CSV não tem as colunas obrigatórias.

**Solução:** Verifique se o CSV tem pelo menos as colunas `nome` e `produtividade`.

### Erro: "Produtividade inválida"

**Causa:** O valor de produtividade não é exatamente `productive`, `nonproductive` ou `neutral`.

**Solução:** Verifique se os valores estão escritos corretamente (case-insensitive, mas deve ser exato).

### Erro: "Departamento 'X' não encontrado"

**Causa:** O nome do departamento fornecido não existe no banco.

**Solução:** 
- Verifique se o departamento existe: `GET /departamentos`
- Use `departamento_id` em vez de `departamento_nome` se souber o ID
- Crie o departamento antes de importar as tags

## 📝 Notas

- O arquivo CSV pode ter até 50 erros reportados na resposta
- Tags duplicadas (mesmo nome e departamento) serão atualizadas
- Palavras-chave existentes são removidas e substituídas pelas novas
- O sistema suporta arquivos CSV com ou sem BOM (Byte Order Mark)

## 📄 Arquivo de Exemplo

Um arquivo de exemplo está disponível em: `backend/exemplos/tags_exemplo.csv`

