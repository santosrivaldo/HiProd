# Configuração de SSO no HiProd

Este documento descreve como configurar o **Single Sign-On (SSO)** no sistema HiProd, com prioridade para login por e-mail corporativo e opção de integração com **Microsoft Entra (Azure AD)**.

---

## 1. Visão geral

- **SSO é a prioridade** na tela de login: o usuário pode entrar com **e-mail corporativo** (sem senha) ou com **Microsoft**.
- A identificação segue a regra: **nome do usuário = parte local do e-mail**.
  - Exemplo: usuário cadastrado com **nome** `rivaldo.santos` corresponde ao e-mail **rivaldo.santos@grupohi.com.br**.
- O login tradicional (usuário + senha) continua disponível como alternativa.

---

## 2. Regra de identificação (nome = e-mail)

| Cadastro no sistema     | E-mail para login SSO           |
|-------------------------|----------------------------------|
| Nome: `rivaldo.santos`  | `rivaldo.santos@grupohi.com.br` |
| Nome: `maria.silva`     | `maria.silva@grupohi.com.br`    |

- O sistema busca o usuário por:
  1. **E-mail** exatamente igual ao informado; ou
  2. **Nome** igual à parte antes do `@` quando o domínio for o configurado (ex.: `grupohi.com.br`).

O domínio corporativo é definido pela variável **`SSO_EMAIL_DOMAIN`** (padrão: `grupohi.com.br`).

---

## 3. Variáveis de ambiente

Configure no arquivo **`.env`** na raiz do projeto (backend).

| Variável | Obrigatória | Descrição | Exemplo |
|----------|-------------|-----------|---------|
| `SSO_EMAIL_DOMAIN` | Não | Domínio do e-mail corporativo (parte após o `@`) | `grupohi.com.br` |
| `SSO_ENABLED` | Não | Habilitar SSO (`true` ou `false`) | `true` |
| `SSO_MICROSOFT_CLIENT_ID` | Para Microsoft | Application (client) ID do app no Azure | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `SSO_MICROSOFT_CLIENT_SECRET` | Para Microsoft | Client secret do app no Azure | `abc123...` |
| `SSO_MICROSOFT_TENANT` | Não | Tenant ID do Azure AD (`common` para multi-tenant) | `common` ou `seu-tenant-id` |
| `SSO_REDIRECT_URI` | Para Microsoft | URL de callback do backend (onde a Microsoft redireciona após o login) | `https://hiprod.grupohi.com.br/api/sso/callback` |
| `FRONTEND_URL` | Para Microsoft | URL do frontend (para redirecionar com o token após o SSO) | `https://hiprod.grupohi.com.br` |

**Exemplo mínimo (apenas login por e-mail, sem Microsoft):**

```env
SSO_EMAIL_DOMAIN=grupohi.com.br
SSO_ENABLED=true
```

**Exemplo completo (com Microsoft Entra):**

```env
SSO_EMAIL_DOMAIN=grupohi.com.br
SSO_ENABLED=true
SSO_MICROSOFT_CLIENT_ID=seu-client-id
SSO_MICROSOFT_CLIENT_SECRET=seu-client-secret
SSO_MICROSOFT_TENANT=common
SSO_REDIRECT_URI=https://hiprod.grupohi.com.br/api/sso/callback
FRONTEND_URL=https://hiprod.grupohi.com.br
```

---

## 4. Modo 1: Login apenas com e-mail (sem Microsoft)

Não é necessário configurar Azure. O usuário informa o **e-mail corporativo** na tela de login e o sistema valida contra os usuários cadastrados.

### O que configurar

- No `.env`: `SSO_EMAIL_DOMAIN` e `SSO_ENABLED=true` (ou omitir, que o padrão já é esse).

### Cadastro de usuários

- Crie o usuário no painel com **nome** = parte local do e-mail (ex.: `rivaldo.santos`).
- Se não informar o campo **e-mail** ao criar o usuário, o sistema preenche automaticamente com `nome@SSO_EMAIL_DOMAIN` (ex.: `rivaldo.santos@grupohi.com.br`).

### Fluxo para o usuário

1. Na tela de login, em **"Ou use seu e-mail corporativo"**, informar o e-mail (ex.: `rivaldo.santos@grupohi.com.br`).
2. Clicar em **"Entrar com e-mail"**.
3. Se existir usuário com esse e-mail ou com nome `rivaldo.santos`, o login é concluído sem senha.

---

## 5. Modo 2: Microsoft Entra (Azure AD)

Com a integração Microsoft, o usuário clica em **"Entrar com SSO (Microsoft)"**, é redirecionado para o login da Microsoft e, após autenticar, volta ao HiProd já logado.

### 5.1 Registrar o aplicativo no Azure

1. Acesse o [Portal do Azure](https://portal.azure.com) e vá em **Microsoft Entra ID** (Azure Active Directory).
2. **Registros de aplicativo** → **Novo registro**.
3. Defina:
   - **Nome**: ex. `HiProd SSO`.
   - **Tipos de conta**: conforme sua necessidade (ex. "Contas somente neste diretório organizacional").
   - **URI de redirecionamento**: escolha **Web** e informe a URL do callback do **backend**:
     - Produção: `https://hiprod.grupohi.com.br/api/sso/callback`
     - Desenvolvimento (se o backend estiver em outra porta): `http://localhost:8010/sso/callback`
4. Clique em **Registrar**.

### 5.2 Obter Client ID e Client Secret

- **Application (client) ID**: na página do app, em **Visão geral** → copie o valor e use em `SSO_MICROSOFT_CLIENT_ID`.
- **Client secret**:
  1. No menu do app, **Certificados e segredos**.
  2. **Novo segredo do cliente** → descrição (ex. "HiProd") e validade.
  3. Copie o **Valor** assim que for exibido (não é mostrado de novo) e use em `SSO_MICROSOFT_CLIENT_SECRET`.

### 5.3 Configurar permissões (tokens OpenID)

1. No app registrado, **Permissões de API**.
2. **Adicionar uma permissão** → **Microsoft Graph** (ou **OpenID Connect**) → **Permissões delegadas**.
3. Inclua: **openid**, **email**, **profile** (ou o equivalente no fluxo OpenID que o backend usa).
4. Salve e, se solicitado, **Conceder consentimento de administrador**.

### 5.4 Variáveis no servidor

No `.env` do backend:

```env
SSO_MICROSOFT_CLIENT_ID=<Application (client) ID>
SSO_MICROSOFT_CLIENT_SECRET=<Valor do segredo criado>
SSO_MICROSOFT_TENANT=common
SSO_REDIRECT_URI=https://hiprod.grupohi.com.br/api/sso/callback
FRONTEND_URL=https://hiprod.grupohi.com.br
```

- **SSO_REDIRECT_URI** deve ser **exatamente** a mesma URL configurada no Azure (incluindo protocolo e path).
- **FRONTEND_URL** é a URL onde o usuário usa o HiProd no navegador; após o callback, o backend redireciona para `FRONTEND_URL/auth/callback?token=...`.

### 5.5 Fluxo para o usuário

1. Clicar em **"Entrar com SSO (Microsoft)"**.
2. Ser redirecionado para a tela de login da Microsoft.
3. Após login na Microsoft, voltar ao HiProd na rota `/auth/callback` com o token; o frontend valida o token e redireciona para o dashboard.

O usuário precisa existir no HiProd com **nome** ou **e-mail** compatível com o e-mail retornado pela Microsoft (mesma regra nome = parte local do e-mail).

---

## 6. Cadastro de usuários para SSO

- **Recomendado**: criar usuários com **nome** = parte local do e-mail corporativo (ex.: `rivaldo.santos`).
- Deixar o campo **e-mail** em branco ao criar: o sistema grava automaticamente `nome@SSO_EMAIL_DOMAIN`.
- Ou informar o e-mail completo; o login SSO funciona tanto por nome quanto por e-mail.

Usuários já existentes só com **nome** (ex.: `rivaldo.santos`) também funcionam: o sistema associa ao e-mail `rivaldo.santos@grupohi.com.br` na primeira vez que o login SSO for feito (e pode atualizar o campo e-mail no banco).

---

## 7. Frontend e callback

- A rota **`/auth/callback`** no frontend recebe o token após o login Microsoft (`?token=...`), valida com o backend (`/verify-token`) e redireciona para a página inicial.
- Em produção, o frontend e o backend costumam estar no mesmo domínio (ex.: `hiprod.grupohi.com.br`), com o backend em `/api`. Ajuste `FRONTEND_URL` e `SSO_REDIRECT_URI` conforme sua implantação.
- Em desenvolvimento local, use por exemplo:
  - Backend: `http://localhost:8010`
  - Frontend: `http://localhost:5173`
  - `SSO_REDIRECT_URI=http://localhost:8010/sso/callback`
  - `FRONTEND_URL=http://localhost:5173`

---

## 8. Endpoints relacionados ao SSO

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/sso/login` | Login por e-mail (body: `{ "email": "usuario@dominio.com" }`). |
| GET | `/sso/url` | Retorna a URL para redirecionar ao login Microsoft (se configurado). |
| GET | `/sso/callback` | Callback OAuth2 da Microsoft; redireciona ao frontend com `?token=...`. |

---

## 9. Desabilitar SSO

No `.env`:

```env
SSO_ENABLED=false
```

A tela de login deixará de exibir as opções SSO como prioridade e o botão "Entrar com SSO (Microsoft)" não será oferecido (ou a chamada a `/sso/url` retornará 404).

---

## 10. Resolução de problemas

### 401 Unauthorized na troca do code (token exchange)

Se aparecer no log do backend:

```text
❌ SSO token exchange failed: 401 Client Error: Unauthorized for url: https://login.microsoftonline.com/.../oauth2/v2.0/token
```

As causas mais comuns são:

1. **`redirect_uri` diferente**  
   O valor de `SSO_REDIRECT_URI` no `.env` tem que ser **exatamente** igual ao configurado no Azure (Registros de aplicativo → seu app → Autenticação → URIs de redirecionamento):
   - Mesmo esquema (`https` vs `http`)
   - Mesmo host e porta
   - Com ou sem barra final: use o **mesmo** nos dois (ex.: `https://hiprod.grupohi.com.br/api/sso/callback` em ambos).
   - Se o backend estiver atrás de um proxy (Nginx, etc.), a URL que a Microsoft chama é a **pública** (a que o usuário usa no navegador ao voltar do login). Essa deve ser a mesma no Azure e no `.env`.

2. **Client secret incorreto ou expirado**  
   - No Azure: Certificados e segredos → confira se o segredo está ativo e não expirado.  
   - Gere um novo segredo e atualize `SSO_MICROSOFT_CLIENT_SECRET` no `.env` (sem espaços ao copiar).

3. **Client ID incorreto**  
   - Confira em Azure → Visão geral do app → "Application (client) ID" e compare com `SSO_MICROSOFT_CLIENT_ID`.

4. **Tenant**  
   - Se usar tenant específico, `SSO_MICROSOFT_TENANT` deve ser o ID do tenant (ex.: `406d13ff-6f7e-4d46-9651-584bc014ed17`). Para contas de qualquer tenant, use `common`.

Após alterar o `.env`, reinicie o backend e tente o login SSO de novo. O backend agora grava no log a mensagem de erro retornada pela Microsoft (`error_description`), o que ajuda a identificar qual desses pontos está falhando.

---

| Problema | Verificação |
|----------|-------------|
| "Usuário não encontrado" no login por e-mail | Confirme que existe usuário com **nome** igual à parte antes do `@` ou com **e-mail** igual. Domínio deve bater com `SSO_EMAIL_DOMAIN` quando for busca por nome. |
| Botão Microsoft não aparece ou dá 404 | Confirme `SSO_MICROSOFT_CLIENT_ID` e `SSO_REDIRECT_URI` no `.env` e que `SSO_ENABLED=true`. |
| **401 na troca do code** | Veja a subseção **401 Unauthorized na troca do code** acima. |
| Erro após login na Microsoft (callback) | Verifique se `SSO_REDIRECT_URI` no Azure é **idêntica** à do `.env` (incluindo `/api` se for o caso). Confirme `FRONTEND_URL` para o redirecionamento pós-login. |
| "Usuário não cadastrado" após Microsoft | O e-mail retornado pela Microsoft deve corresponder a um usuário no HiProd (nome ou e-mail). Cadastre o usuário com nome = parte local do e-mail. |

---

## Resumo rápido

1. **Só e-mail**: defina `SSO_EMAIL_DOMAIN` (e opcionalmente `SSO_ENABLED=true`). Cadastre usuários com nome = parte local do e-mail.
2. **Com Microsoft**: registre o app no Azure, configure redirect URI, crie o client secret e preencha todas as variáveis `SSO_MICROSOFT_*`, `SSO_REDIRECT_URI` e `FRONTEND_URL`.
3. Usuários: **nome** = parte antes do `@` (ex.: rivaldo.santos = rivaldo.santos@grupohi.com.br).
