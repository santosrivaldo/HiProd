# HiProd Agent - Instalação como Serviço Windows

O HiProd Agent pode ser instalado como serviço do Windows para iniciar automaticamente com o sistema e rodar o agent na sessão do usuário logado (com interface gráfica: botão flutuante, tela de bloqueio).

## Requisitos

- Windows (serviço não disponível em Linux/macOS)
- Para instalação **sem Python**: use os executáveis da pasta `release` (`HiProd-Agent.exe` e `HiProd-Agent-Service.exe` na mesma pasta)
- Para instalação **com Python**: pywin32 (`pip install pywin32`)
- Executar os comandos de instalação/remoção **como Administrador**

## Instalação

### Opção 1: Sem Python (apenas .exe)

1. Coloque na mesma pasta: `HiProd-Agent.exe` e `HiProd-Agent-Service.exe` (e o `.env` se já configurou).
2. Abra o **Prompt de Comando** ou **PowerShell como Administrador** nessa pasta.
3. Execute: `HiProd-Agent-Service.exe install`
4. Para iniciar: `net start HiProdAgent` ou `HiProd-Agent-Service.exe start`

### Opção 2: Script em lote (com ou sem Python)

1. Clique com o botão direito em `install_service.bat`
2. Escolha **Executar como administrador**
3. Se existir `HiProd-Agent-Service.exe` na pasta, o script usa o exe (sem Python). Caso contrário, usa Python e instala pywin32 se necessário.

### Opção 3: Linha de comando (com Python)

Abra o **Prompt de Comando** ou **PowerShell como Administrador** na pasta do agent e execute:

```cmd
pip install pywin32
python agent_service.py install
```

## Comandos do serviço

Com **Python** (na pasta do agent):

| Comando | Descrição |
|--------|------------|
| `python agent_service.py install` | Instala o serviço (como Admin) |
| `python agent_service.py remove`  | Remove o serviço (como Admin) |
| `python agent_service.py start`   | Inicia o serviço |
| `python agent_service.py stop`   | Para o serviço |
| `python agent_service.py debug`  | Testa início do agent na sessão do usuário (sem instalar serviço) |

Sem **Python** (usando o .exe na pasta com `HiProd-Agent.exe` e `HiProd-Agent-Service.exe`):

| Comando | Descrição |
|--------|------------|
| `HiProd-Agent-Service.exe install` | Instala o serviço (como Admin) |
| `HiProd-Agent-Service.exe remove`  | Remove o serviço (como Admin) |
| `HiProd-Agent-Service.exe start`   | Inicia o serviço |
| `HiProd-Agent-Service.exe stop`   | Para o serviço |
| `HiProd-Agent-Service.exe debug`  | Testa início do agent na sessão do usuário (sem instalar serviço) |

Ou use o Windows:

- **services.msc** → procure por "HiProd Agent" → botão Iniciar/Parar
- Ou no prompt (como Admin): `net start HiProdAgent` / `net stop HiProdAgent`

## Comportamento

- O serviço inicia com o Windows e fica em execução em segundo plano.
- Quando há um usuário logado na estação, o serviço inicia o HiProd Agent **na sessão desse usuário**, para que o botão flutuante e a tela de bloqueio apareçam normalmente.
- Se ninguém estiver logado, o serviço continua rodando e tenta iniciar o agent a cada 30 segundos até que alguém faça logon.
- O arquivo `.env` e o executável do agent (`HiProd-Agent.exe` ou `main.py`) devem estar na mesma pasta do instalador do serviço (`agent_service.py` ou `HiProd-Agent-Service.exe`).

## Desinstalação

1. Clique com o botão direito em `uninstall_service.bat` → **Executar como administrador**  
   **ou**
2. Como Admin: `python agent_service.py remove` (com Python) ou `HiProd-Agent-Service.exe remove` (sem Python)

## Solução de problemas

- **"Acesso negado" ao instalar/remover**  
  Execute sempre como Administrador.

- **Serviço instalado mas o agent não aparece**  
  Verifique se há usuário logado na máquina. O agent só é iniciado na sessão ativa (console). Teste com: `python agent_service.py debug` (sem ser serviço) para ver se o agent sobe na sua sessão.

- **pywin32 não encontrado**  
  Execute: `pip install pywin32` no mesmo ambiente em que roda o `agent_service.py`.
