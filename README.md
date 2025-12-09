
# Activity Tracker

Um sistema completo de rastreamento de atividades com interface React e backend Flask.

## 📋 Visão Geral

O Activity Tracker é uma aplicação web que permite monitorar e gerenciar atividades de usuários com funcionalidades de:

- Dashboard com estatísticas em tempo real
- Gerenciamento de atividades
- Sistema de tags e categorias
- Gerenciamento de usuários
- Tema claro/escuro
- Autenticação JWT

## 🛠️ Tecnologias Utilizadas

### Frontend
- React 18
- Vite
- Tailwind CSS
- Heroicons
- Recharts (para gráficos)
- Axios (para requisições HTTP)

### Backend
- Flask
- PostgreSQL
- JWT para autenticação
- bcrypt para hash de senhas
- psycopg2 para conexão com PostgreSQL

## 🚀 Instalação e Configuração

### 1. Configuração do Banco de Dados

Primeiro, configure suas variáveis de ambiente:

```bash
# Copie o arquivo de exemplo
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais do banco:

```env
# Configuração do Banco de Dados
DATABASE_URL=postgresql://username:password@host:port/database_name

# Configuração JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# Configuração do ambiente
FLASK_ENV=development
```

### 2. Instalação das Dependências

#### Backend (Python)
```bash
# As dependências Python serão instaladas automaticamente pelo Replit
# Ou manualmente com:
pip install -r requirements.txt
```

#### Frontend (Node.js)
```bash
npm install
```

### 3. Inicialização do Banco de Dados

Execute o script para criar as tabelas:

```bash
python setup_database.py
```

Ou inicie o backend com reset do banco:

```bash
python app.py --reset
```

## ▶️ Como Executar

### Opção 1: Usando os Workflows do Replit (Recomendado)

1. **Frontend**: Clique no botão "Run" (executa o workflow "Start Frontend")
2. **Backend**: Selecione o workflow "Start Backend" no dropdown

### Opção 2: Execução Manual

#### Iniciar o Backend
```bash
python app.py
```

#### Iniciar o Frontend
```bash
npm run dev
```

### Portas de Acesso

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

## 🐳 Docker (API + Postgres)

Suba a API e o banco com Docker Compose. O processo:
- Sobe o Postgres (db)
- A API aguarda o banco ficar saudável
- Executa a inicialização/migração (init_db)
- Inicia a API em 0.0.0.0:8000

### ⚠️ IMPORTANTE: Configuração de Segurança

**Antes de executar o Docker Compose, você DEVE criar um arquivo `.env` com as variáveis de ambiente:**

```bash
# Criar arquivo .env na raiz do projeto
cat > .env << EOF
# Banco de Dados - OBRIGATÓRIO: Use senhas fortes!
DB_USER=hiprod_user
DB_PASSWORD=SUA_SENHA_FORTE_AQUI_ALTERE_ISTO
DB_NAME=hiprod
DB_HOST=db
DB_PORT=5432

# Segurança JWT - OBRIGATÓRIO: Use uma chave secreta forte!
JWT_SECRET_KEY=SUA_CHAVE_SECRETA_FORTE_AQUI_ALTERE_ISTO
EOF
```

**⚠️ NUNCA use valores padrão em produção!**

### Executar Docker Compose

```bash
docker compose up --build
```

### Variáveis Obrigatórias

O docker-compose **NÃO** aceita valores padrão por segurança. Você DEVE definir:

- `DB_USER` - Usuário do banco de dados
- `DB_PASSWORD` - Senha forte do banco (mínimo 16 caracteres)
- `JWT_SECRET_KEY` - Chave secreta para JWT (mínimo 32 caracteres)

### Variáveis Opcionais

- `DB_NAME` - Nome do banco (padrão: `hiprod`)
- `DB_HOST` - Host do banco (padrão: `db` no Docker)
- `DB_PORT` - Porta do banco (padrão: `5432`)

### Segurança Implementada

✅ **Banco de dados não exposto externamente** - Apenas acessível via rede interna do Docker  
✅ **Senhas obrigatórias** - Não aceita valores padrão  
✅ **Rede isolada** - Serviços se comunicam apenas dentro da rede Docker  
✅ **Restart automático** - Serviços reiniciam automaticamente em caso de falha

A API ficará disponível em http://localhost:8010. O banco de dados **NÃO** está exposto externamente por segurança.

## 👤 Login Inicial

Após a primeira execução, será criado um usuário administrador padrão:

- **Usuário**: `admin`
- **Senha**: `admin123`

⚠️ **Importante**: Altere estas credenciais após o primeiro login!

## 📁 Estrutura do Projeto

```
├── backend/                 # Backend Flask
│   ├── routes/             # Rotas da API
│   ├── models.py           # Modelos do banco
│   ├── database.py         # Configuração do banco
│   └── auth.py             # Autenticação
├── src/                    # Frontend React
│   ├── components/         # Componentes React
│   ├── contexts/           # Contextos (Auth, Theme)
│   ├── services/           # Serviços API
│   └── utils/              # Utilitários
├── app.py                  # Aplicação principal Flask
├── requirements.txt        # Dependências Python
├── package.json            # Dependências Node.js
└── .env.example            # Exemplo de variáveis de ambiente
```

## 🔧 Comandos Úteis

### Desenvolvimento

```bash
# Reset completo do banco de dados
python app.py --reset

# Executar apenas o backend
python app.py

# Executar apenas o frontend
npm run dev

# Build do frontend para produção
npm run build
```

### Banco de Dados

```bash
# Criar/recriar tabelas
python setup_database.py

# Conectar ao PostgreSQL (se local)
psql -h localhost -U username -d database_name
```

## 🐛 Solução de Problemas

### Erro de Conexão com Banco
1. Verifique se o arquivo `.env` está configurado corretamente
2. Confirme se o banco PostgreSQL está acessível
3. Teste a conexão manualmente

### Erro "Module not found"
```bash
# Reinstale as dependências
npm install
pip install -r requirements.txt
```

### Problemas de CORS
- O backend já está configurado com CORS habilitado
- Verifique se ambos os serviços estão rodando nas portas corretas

## 📊 Funcionalidades

### Dashboard
- Estatísticas de atividades
- Gráficos de produtividade
- Métricas em tempo real

### Gerenciamento de Atividades
- Visualização de todas as atividades
- Filtros por data, usuário e categoria
- Exportação de dados

### Sistema de Tags
- Criação e edição de tags
- Associação com atividades
- Filtros por tags

### Gerenciamento de Usuários
- CRUD completo de usuários
- Controle de permissões
- Histórico de login

## 🔒 Segurança

- Autenticação JWT
- Senhas criptografadas com bcrypt
- Validação de entrada em todas as rotas
- Proteção contra SQL injection

## 🚀 Deploy

Para deploy em produção no Replit:

1. Configure as variáveis de ambiente de produção
2. Use o workflow de deployment do Replit
3. Certifique-se de que o banco PostgreSQL está acessível externamente

## 📝 Licença

Este projeto é de uso interno e educacional.

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

---

**Desenvolvido com ❤️ usando React + Flask**
