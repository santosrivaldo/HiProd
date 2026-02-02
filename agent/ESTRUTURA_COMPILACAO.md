# Estrutura de Compilação - Arquivo Único

## 📦 Arquitetura do Build

O HiProd Agent é compilado como **um único executável** (.exe) que contém todos os componentes integrados.

## 🔧 Componentes Integrados

### 1. main.py
- **Função**: Ponto de entrada principal
- **Responsabilidade**: Inicializa o sistema completo
- **Dependências**: `lock_screen.py`

### 2. lock_screen.py
- **Função**: Interface gráfica de bloqueio
- **Responsabilidade**: 
  - Tela de bloqueio
  - Integração com Bitrix24 Timeman
  - Inicialização do agent quando expediente é aberto
- **Dependências**: `agent.py`

### 3. agent.py
- **Função**: Monitoramento e envio de dados
- **Responsabilidade**:
  - Monitoramento de atividades (janelas, URLs, aplicações)
  - Envio de dados para API via HTTPS com handshake TLS
  - **Detecção facial integrada** (código completo dentro do arquivo)
  - Rastreamento de presença
- **Dependências**: Nenhuma (tudo integrado)

## ✅ Código Integrado

### Detecção Facial
O código de detecção facial está **completamente integrado** no `agent.py`:
- Classe `FacePresenceTracker`
- Funções `check_face_presence()` e `check_face_presence_silent()`
- Função `get_haarcascade_path()`
- Variável `FACE_DETECTION_AVAILABLE`
- Instância global `_presence_tracker`

**Não há necessidade** do arquivo `face_detection.py` separado.

## 🏗️ Processo de Build

### Arquivo .spec (hiprod-agent.spec)
- **Ponto de entrada**: `main.py`
- **Hidden imports**: 
  - `agent` (contém detecção facial integrada)
  - `lock_screen`
  - `cv2`, `cv2.data`, `numpy` (OpenCV)
- **Dados incluídos**: 
  - Haarcascades do OpenCV
  - DLLs do OpenCV
  - `config.example`

### Build.py
- Verifica apenas: `main.py`, `agent.py`, `lock_screen.py`
- Verifica se `agent.py` contém código de detecção facial
- **Não verifica** `face_detection.py` (não é necessário)

## 📝 Resultado Final

Após a compilação:
- ✅ **Um único executável**: `HiProd-Agent.exe`
- ✅ **Tudo integrado**: lock_screen + agent + detecção facial
- ✅ **Sem dependências externas**: Tudo dentro do .exe
- ✅ **OpenCV incluído**: DLLs e haarcascades embutidos

## 🔍 Verificação

Para verificar se tudo está integrado:

```python
# Verificar se agent.py contém detecção facial
grep -i "FACE_DETECTION_AVAILABLE" agent/agent.py

# Verificar se main.py não importa face_detection
grep -i "import.*face_detection\|from.*face_detection" agent/main.py
```

## 📌 Notas Importantes

1. **face_detection.py**: O arquivo pode existir como referência/documentação, mas **não é usado** no build
2. **Compilação**: O PyInstaller compila tudo em um único executável
3. **OpenCV**: É incluído automaticamente via `hiddenimports` e `binaries`
4. **Haarcascades**: São incluídos via `datas` no arquivo .spec

## 🚀 Build

Para compilar:

```bash
# Windows
build.bat

# Ou manualmente
python build.py
```

O resultado será um único arquivo `HiProd-Agent.exe` com tudo integrado.

