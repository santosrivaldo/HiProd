# HiProd Agent - Executável Único Integrado

## 📦 Visão Geral

O HiProd Agent agora é um **executável único (.exe)** que integra todos os componentes:

1. **lock_screen.py** - Tela de bloqueio e interface gráfica
2. **agent.py** - Monitoramento de atividades
3. **face_detection.py** - Detecção facial e rastreamento de presença

## 🔄 Fluxo de Execução

```
HiProd-Agent.exe (main.py)
    │
    ├─> lock_screen.main()
    │       │
    │       ├─> Interface gráfica de bloqueio
    │       ├─> Integração com Bitrix24 Timeman
    │       └─> Quando expediente abre:
    │               │
    │               └─> agent.main() (thread separada)
    │                       │
    │                       ├─> Monitoramento de atividades
    │                       ├─> Envio para API
    │                       └─> face_detection (automático)
    │                               │
    │                               └─> Verificação de presença a cada 1 minuto
    │                               └─> Rastreamento de tempo de presença
```

## 📁 Estrutura de Arquivos

```
agent/
├── main.py                 # Ponto de entrada único
├── lock_screen.py          # Interface gráfica e gerenciamento
├── agent.py                # Monitoramento de atividades
├── face_detection.py       # Detecção facial
├── hiprod-agent.spec       # Configuração do PyInstaller
├── build.py                # Script de build
└── requirements.txt        # Dependências
```

## 🛠️ Como Compilar

### Método 1: Automático (Recomendado)

```bash
# Windows
cd agent
build.bat
```

### Método 2: Manual

```bash
cd agent

# 1. Criar/ativar ambiente virtual
python setup.py

# 2. Compilar
python build.py
```

### Resultado

Após o build, você encontrará:

```
agent/
├── dist/
│   └── HiProd-Agent.exe    # Executável único
└── release/
    ├── HiProd-Agent.exe    # Executável para distribuição
    ├── config.example      # Arquivo de configuração exemplo
    └── README.txt          # Instruções
```

## ✨ Funcionalidades Integradas

### 1. Tela de Bloqueio (lock_screen.py)
- ✅ Interface gráfica estilo Windows
- ✅ Suporte a múltiplos monitores
- ✅ Integração com Bitrix24 Timeman
- ✅ Botão flutuante para controle
- ✅ Gerenciamento de expediente

### 2. Monitoramento (agent.py)
- ✅ Captura de janelas ativas
- ✅ Captura de URLs e páginas web
- ✅ Detecção de aplicações
- ✅ Envio automático para API
- ✅ Fila offline para resiliência
- ✅ **Integração automática com detecção facial**

### 3. Detecção Facial (face_detection.py)
- ✅ Verificação de presença a cada 1 minuto
- ✅ Rastreamento de tempo de presença
- ✅ Integração automática com agent
- ✅ Dados incluídos nos registros de atividades

## 🔧 Configuração

### Arquivo .env (ou config)

Crie um arquivo `.env` na mesma pasta do executável:

```env
# API
API_URL=http://192.241.155.236:8010

# Credenciais do agente
USER_NAME=connect
USER_PASSWORD=sua_senha

# Monitoramento
MONITOR_INTERVAL=10
IDLE_THRESHOLD=600
```

## 📊 Dados Coletados

Cada registro de atividade inclui:

```json
{
    "usuario_monitorado_id": 123,
    "ociosidade": 0,
    "active_window": "Título da Janela",
    "url": "https://exemplo.com",
    "page_title": "Título da Página",
    "domain": "exemplo.com",
    "application": "Chrome",
    "horario": "2024-01-01T10:00:00-03:00",
    "face_presence_time": 3600  // Tempo em segundos (novo!)
}
```

## 🚀 Distribuição

O executável é **standalone**:
- ✅ Não requer Python instalado
- ✅ Todas as dependências incluídas
- ✅ OpenCV e haarcascade incluídos
- ✅ Arquivo único (onefile)
- ✅ Pronto para distribuição

## 📝 Notas Importantes

1. **Câmera**: O sistema de detecção facial requer uma câmera conectada
2. **Primeira execução**: Pode demorar um pouco na primeira vez (extração de arquivos)
3. **Antivírus**: Alguns antivírus podem detectar como falso positivo (comum com PyInstaller)
4. **Permissões**: Pode precisar de permissões de administrador para algumas funcionalidades

## 🐛 Solução de Problemas

### Executável não inicia
- Verifique se todas as dependências estão instaladas no ambiente de build
- Execute com console habilitado para ver erros (altere `console=False` para `console=True` no spec)

### Detecção facial não funciona
- Verifique se a câmera está conectada e funcionando
- O arquivo haarcascade é incluído automaticamente no build

### Erro de módulo não encontrado
- Adicione o módulo em `hiddenimports` no arquivo `hiprod-agent.spec`
- Execute o build novamente

## 📞 Suporte

Para mais informações, consulte:
- `BUILD.md` - Guia detalhado de build
- `README.md` - Documentação geral
- Logs em `build/HiProd-Agent/warn-HiProd-Agent.txt`

