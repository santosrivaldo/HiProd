# Como Importar a Collection no Postman

## 📥 Passo a Passo Completo

### 1. Abrir o Postman

Abra o aplicativo Postman no seu computador.

### 2. Importar a Collection

1. Clique no botão **"Import"** no canto superior esquerdo
2. Na janela que abrir, você tem 3 opções:
   - **Opção A:** Arraste o arquivo `HiProd_API_Collection.postman_collection.json` para a área de importação
   - **Opção B:** Clique em **"Upload Files"** e selecione o arquivo
   - **Opção C:** Clique em **"Link"** e cole a URL do arquivo (se estiver em repositório)

3. Clique em **"Import"**

### 3. Importar o Environment

1. Clique no ícone de **engrenagem** (⚙️) no canto superior direito
2. Clique em **"Import"**
3. Selecione o arquivo `HiProd_API_Environment.postman_environment.json`
4. Clique em **"Import"**

### 4. Selecionar o Environment

1. No canto superior direito, clique no dropdown de environments
2. Selecione **"HiProd API - Environment"**

### 5. Configurar Variáveis

1. Clique no ícone de **olho** (👁️) ao lado do dropdown de environments
2. Clique em **"Edit"** ao lado do environment "HiProd API - Environment"
3. Configure as variáveis:

   | Variável | Valor | Descrição |
   |----------|-------|-----------|
   | `base_url` | `https://hiprod.grupohi.com.br` | URL de produção |
   | `base_url_local` | `http://localhost:8000` | URL de desenvolvimento |
   | `jwt_token` | (deixe vazio) | Será preenchido após login |
   | `api_token` | (deixe vazio) | Token de API (obtido na página Tokens API) |

4. Clique em **"Save"**

### 6. Testar a Importação

1. Expanda a pasta **"🔐 Autenticação"**
2. Execute a requisição **"Login"**
3. Copie o `token` da resposta
4. Cole no environment na variável `jwt_token`
5. Execute outras requisições para testar

## ✅ Verificação

Após importar, você deve ver:

- ✅ Collection "HiProd API - Collection Completa" na barra lateral
- ✅ Environment "HiProd API - Environment" no dropdown
- ✅ Variáveis configuráveis no environment

## 📋 Estrutura da Collection

A collection está organizada em pastas:

1. **🔐 Autenticação** - Login e verificação de token
2. **🌐 API V1 - Externa** - Endpoints para integrações externas
3. **📊 Atividades** - Gerenciamento de atividades
4. **👥 Usuários** - Gerenciamento de usuários
5. **🏢 Departamentos** - Gerenciamento de departamentos
6. **🏷️ Tags** - Gerenciamento de tags
7. **📁 Categorias** - Gerenciamento de categorias
8. **⏰ Escalas** - Gerenciamento de escalas
9. **🔑 Tokens de API** - Gerenciamento de tokens
10. **👤 Presença Facial** - Verificações de presença

## 🔑 Obter Tokens

### Token JWT (para usuários)

1. Execute a requisição **"Autenticação > Login"**
2. Copie o `token` da resposta
3. Cole em `jwt_token` no environment

### Token de API (para integrações)

1. Faça login no sistema web
2. Acesse "Tokens API" no menu
3. Crie um novo token com permissões para `/api/v1/*`
4. Copie o token (será exibido apenas uma vez)
5. Cole em `api_token` no environment

## 🐛 Problemas Comuns

### Collection não aparece após importar

- Verifique se o arquivo JSON está válido
- Tente fechar e reabrir o Postman
- Verifique se não há erros na importação

### Variáveis não funcionam

- Certifique-se de que o environment está selecionado
- Verifique se as variáveis estão escritas corretamente: `{{base_url}}`
- Recarregue o environment

### Erro 404 nos endpoints V1

- Verifique se a URL está correta: `/api/v1/health` (não `API/v1?health`)
- Reinicie o servidor Flask após adicionar endpoints
- Consulte `TROUBLESHOOTING_404_V1.md`

## 📚 Próximos Passos

1. Importe a collection e o environment
2. Configure as variáveis
3. Faça login para obter token JWT
4. Teste os endpoints
5. Crie um token de API para testar endpoints V1
6. Consulte a documentação em `API_V1_DOCUMENTACAO.md`

