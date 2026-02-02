# Verificação de Build - Detecção Facial

## ✅ Status da Verificação Facial no Build

### 1. Código de Detecção Facial

**Localização:** Integrado em `agent.py` (linhas 98-470)

O código de detecção facial está **integrado diretamente** no `agent.py`, não em um arquivo separado. Isso significa que:
- ✅ O código está sempre incluído no build
- ✅ Não há dependência de arquivo externo `face_detection.py` para o funcionamento
- ⚠️ O `build.py` verifica se `face_detection.py` existe, mas isso é apenas uma verificação opcional

### 2. Arquivo .spec do PyInstaller

**Arquivo:** `hiprod-agent.spec`

O arquivo `.spec` está **corretamente configurado** para incluir:

#### ✅ OpenCV (cv2)
- **Linha 107:** `'cv2'` nos hiddenimports
- **Linha 108:** `'cv2.data'` para dados do OpenCV
- **Linha 109:** `'numpy'` (dependência do OpenCV)

#### ✅ Haarcascades
- **Linhas 28-45:** Coleta automática de todos os arquivos `.xml` do diretório haarcascades
- **Linhas 75-80:** Inclusão do haarcascade em múltiplos locais (raiz e data/)
- **Linha 44:** Inclusão do diretório completo como backup

#### ✅ DLLs do OpenCV (Windows)
- **Linhas 52-62:** Coleta automática de DLLs do OpenCV
- **Linha 87:** Inclusão das DLLs nos binaries

### 3. Verificação no Build

O `build.py` verifica se `face_detection.py` existe (linha 85-97), mas isso é apenas uma verificação de arquivo. O código funcional está em `agent.py`.

### 4. Funcionalidade no Agent

**Localização:** `agent.py` linha 2427-2459

A verificação facial é executada:
- ✅ A cada 1 minuto (FACE_CHECK_INTERVAL)
- ✅ Apenas se `FACE_DETECTION_AVAILABLE = True`
- ✅ Usa `check_face_presence_silent()` quando executável
- ✅ Envia dados para API via `enviar_face_presence_check()`

## 🔍 Como Verificar se Está Funcionando

### 1. Verificar Logs do Build

Ao executar `build.py`, você deve ver mensagens como:

```
[SPEC] OpenCV encontrado em: ...
[SPEC] Haarcascade encontrado: ...
[SPEC] Incluindo arquivo OpenCV: haarcascade_frontalface_default.xml
[SPEC] DLL do OpenCV encontrada: ...
```

### 2. Verificar Executável

Após o build, execute o executável e verifique os logs:

```
[INFO] ✓ OpenCV (cv2) carregado com sucesso - Detecção facial disponível
```

Se aparecer:
```
[WARN] OpenCV não encontrado ou não disponível
[WARN] Verificação facial desabilitada.
```

Significa que o OpenCV não foi incluído corretamente no build.

### 3. Verificar Funcionamento

Quando o agent estiver rodando, você deve ver logs como:

```
[FACE] ✓ Presença detectada | Tempo total: X.X min
```

ou

```
[FACE] ⚠ Ausente | Tempo acumulado: X.X min
```

## 🐛 Problemas Comuns

### Problema 1: OpenCV não encontrado no build

**Sintoma:**
```
[SPEC] AVISO: Não foi possível localizar OpenCV automaticamente
```

**Solução:**
1. Verificar se `opencv-python` está instalado no venv:
   ```bash
   venv\Scripts\pip list | findstr opencv
   ```
2. Reinstalar OpenCV:
   ```bash
   venv\Scripts\pip install opencv-python
   ```
3. Rebuild:
   ```bash
   python build.py
   ```

### Problema 2: Haarcascade não encontrado

**Sintoma:**
```
[SPEC] AVISO: Haarcascade não encontrado! Detecção facial pode não funcionar.
```

**Solução:**
1. Verificar se OpenCV está instalado corretamente
2. Verificar se `cv2.data.haarcascades` existe:
   ```python
   import cv2
   print(cv2.data.haarcascades)
   ```
3. Se não existir, reinstalar OpenCV

### Problema 3: DLLs não incluídas

**Sintoma:**
Erro ao executar: "DLL load failed" ou "cv2 not found"

**Solução:**
1. Verificar se as DLLs estão sendo coletadas no build
2. Verificar se estão no diretório do executável
3. Adicionar manualmente no `.spec` se necessário

## ✅ Checklist de Verificação

- [ ] `opencv-python` está instalado no venv
- [ ] Build mostra mensagens de OpenCV encontrado
- [ ] Haarcascade está sendo incluído
- [ ] DLLs do OpenCV estão sendo incluídas
- [ ] Executável mostra "OpenCV carregado com sucesso"
- [ ] Logs mostram verificações faciais a cada minuto
- [ ] Dados de presença são enviados para API

## 📝 Notas Importantes

1. **Código Integrado:** O código de detecção facial está em `agent.py`, não em `face_detection.py`
2. **Arquivo face_detection.py:** Existe mas é usado apenas como referência/backup
3. **Build Automático:** O `.spec` coleta automaticamente OpenCV e haarcascades
4. **Fallback:** Se OpenCV não estiver disponível, o agent continua funcionando sem detecção facial

## 🔧 Comandos Úteis

### Verificar OpenCV no venv
```bash
venv\Scripts\python -c "import cv2; print(cv2.__version__); print(cv2.data.haarcascades)"
```

### Testar detecção facial
```bash
venv\Scripts\python -c "from agent import check_face_presence; print(check_face_presence())"
```

### Verificar build
```bash
python build.py
```

### Verificar executável
```bash
dist\HiProd-Agent.exe
# Verificar logs para mensagens de OpenCV
```

