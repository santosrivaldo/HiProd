# HiProd API - Collection Postman

Esta pasta contém a collection completa do Postman com todos os endpoints da API HiProd.

## 📁 Arquivos

- **HiProd_API_Collection.postman_collection.json** - Collection completa com todos os endpoints
- **HiProd_API_Environment.postman_environment.json** - Variáveis de ambiente
- **README.md** - Este arquivo

## 🚀 Como Importar

### 1. Importar Collection

1. Abra o Postman
2. Clique em **Import** (canto superior esquerdo)
3. Arraste o arquivo `HiProd_API_Collection.postman_collection.json` ou clique em **Upload Files**
4. Clique em **Import**

### 2. Importar Environment

1. No Postman, clique no ícone de **engrenagem** (⚙️) no canto superior direito
2. Clique em **Import**
3. Selecione o arquivo `HiProd_API_Environment.postman_environment.json`
4. Clique em **Import**
5. Selecione o environment **"HiProd API - Environment"** no dropdown no canto superior direito

### 3. Configurar Variáveis

Após importar o environment, configure as variáveis:

1. Clique no ícone de **olho** (👁️) no canto superior direito
2. Clique em **Edit** ao lado do environment
3. Configure as variáveis:
   - **base_url**: `https://hiprod.grupohi.com.br` (produção) ou `http://localhost:8000` (desenvolvimento)
   - **jwt_token**: Deixe vazio inicialmente (será preenchido após login)
   - **api_token**: Token de API (obtido na página "Tokens API")

## 📋 Estrutura da Collection

A collection está organizada em pastas:

### 🔐 Autenticação
- **Login** - Autentica usuário e retorna token JWT
- **Verificar Token** - Verifica se token JWT é válido
- **Perfil do Usuário** - Retorna perfil do usuário autenticado

### 📊 Atividades
- **Listar Atividades** - Lista todas as atividades com filtros
- **Buscar Atividades por Usuário e Período** - Endpoint EXTERNO (usa token de API)
- **Criar Atividade** - Cria nova atividade
- **Atualizar Atividade** - Atualiza atividade existente
- **Excluir Atividade** - Exclui atividade
- **Obter Screenshot** - Retorna screenshot de uma atividade
- **Estatísticas** - Estatísticas de atividades

### 👥 Usuários
- **Listar Usuários do Sistema** - Lista usuários do sistema
- **Criar Usuário do Sistema** - Cria novo usuário
- **Listar Usuários Monitorados** - Lista usuários monitorados
- **Buscar/Criar Usuário Monitorado** - Busca ou cria usuário monitorado
- **Criar Usuário Monitorado** - Cria novo usuário monitorado

### 🏢 Departamentos
- **Listar Departamentos** - Lista todos os departamentos
- **Criar Departamento** - Cria novo departamento

### 🏷️ Tags
- **Listar Tags** - Lista todas as tags
- **Criar Tag** - Cria nova tag

### 📁 Categorias
- **Listar Categorias** - Lista todas as categorias
- **Criar Categoria** - Cria nova categoria

### ⏰ Escalas
- **Listar Escalas** - Lista todas as escalas de trabalho
- **Criar Escala** - Cria nova escala

### 🔑 Tokens de API
- **Listar Tokens de API** - Lista todos os tokens
- **Criar Token de API** - Cria novo token com permissões
- **Atualizar Token de API** - Atualiza token existente
- **Ativar/Desativar Token** - Ativa ou desativa token
- **Excluir Token de API** - Exclui token
- **Listar Endpoints Disponíveis** - Lista endpoints para permissões

### 👤 Presença Facial
- **Verificar Presença Facial** - Registra verificação facial
- **Estatísticas de Presença Facial** - Estatísticas de presença

### 🌐 API V1 - Externa
- **Health Check** - Verifica status da API (sem autenticação)
- **Buscar Atividades** - Busca atividades por usuário e período
- **Listar Usuários Monitorados** - Lista usuários monitorados
- **Obter Estatísticas** - Estatísticas de atividades de um usuário

## 🔑 Autenticação

### Token JWT (Para Usuários)

1. Execute a requisição **Login** na pasta **Autenticação**
2. Copie o `token` da resposta
3. Cole no environment na variável `jwt_token`
4. Todas as requisições que usam `{{jwt_token}}` funcionarão automaticamente

### Token de API (Para Integrações)

1. Faça login no sistema web
2. Acesse "Tokens API" no menu
3. Crie um novo token com as permissões necessárias
4. Copie o token (será exibido apenas uma vez)
5. Cole no environment na variável `api_token`
6. Use em requisições que requerem token de API

## 📝 Exemplos de Uso

### 1. Fazer Login e Obter Token

1. Execute **Autenticação > Login**
2. Copie o `token` da resposta
3. Cole em `jwt_token` no environment

### 2. Listar Atividades

1. Certifique-se de que `jwt_token` está configurado
2. Execute **Atividades > Listar Atividades**
3. Ajuste os parâmetros de query se necessário

### 3. Usar Endpoint Externo

1. Certifique-se de que `api_token` está configurado
2. Execute **Atividades > Buscar Atividades por Usuário e Período**
3. Ajuste o body com o usuário e período desejados

## ⚠️ Importante

### Diferença entre Token JWT e Token de API

- **Token JWT**: Usado para autenticação de usuários no sistema
  - Obtido através do endpoint `/login`
  - Usado em requisições que requerem `@token_required`
  - Formato: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

- **Token de API**: Usado para integrações externas
  - Obtido na página "Tokens API" do sistema
  - Usado em endpoints externos (ex: `/api/atividades`)
  - Formato: String aleatória (ex: `xK9mP2qR7vT4wY8zA1bC3dE5fG6hI0j`)

### Endpoints que Aceitam X-User-Name

Alguns endpoints aceitam o header `X-User-Name` como alternativa ao token JWT:
- `/atividade` (POST)
- `/face-presence-check` (POST)
- `/usuarios-monitorados` (GET)

Isso é útil para o agente que não precisa de autenticação JWT.

## 🔧 Configuração de Ambiente

### Produção
```
base_url: https://hiprod.grupohi.com.br
```

### Desenvolvimento
```
base_url: http://localhost:8000
```

## 📚 Documentação Adicional

- `API_V1_DOCUMENTACAO.md` - Documentação completa dos endpoints V1
- `EXEMPLOS_ENDPOINTS.md` - Exemplos detalhados de todos os endpoints
- `../TROUBLESHOOTING_405.md` - Solução de problemas

## 🌐 API V1 - Endpoints Externos

A API V1 (`/api/v1/`) é dedicada para integrações externas usando tokens de API:

- **GET /api/v1/health** - Health check (sem autenticação)
- **POST /api/v1/atividades** - Buscar atividades por usuário e período
- **GET /api/v1/usuarios** - Listar usuários monitorados
- **POST /api/v1/estatisticas** - Obter estatísticas de usuário

Todos os endpoints V1 requerem **Token de API** (não JWT).

Consulte `API_V1_DOCUMENTACAO.md` para documentação completa.

## 🐛 Troubleshooting

### Erro 401 - Unauthorized
- Verifique se o token JWT está configurado corretamente
- Verifique se o token não expirou
- Faça login novamente para obter novo token

### Erro 403 - Forbidden
- Verifique se o token de API tem as permissões necessárias
- Verifique se o token está ativo
- Verifique se o token não expirou

### Erro 405 - Method Not Allowed
- Verifique se está usando o método HTTP correto (GET, POST, PUT, DELETE)
- Verifique a URL do endpoint

### Variáveis Não Funcionam
- Certifique-se de que o environment está selecionado
- Verifique se as variáveis estão configuradas corretamente
- Use `{{variavel}}` para referenciar variáveis

## 📞 Suporte

Para mais informações, consulte a documentação completa da API ou entre em contato com a equipe de desenvolvimento.

