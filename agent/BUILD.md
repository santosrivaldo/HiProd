# HiProd Agent - Build para Executável

Este guia explica como transformar o HiProd Agent Python em um executável (.exe) standalone.

## 📋 Pré-requisitos

- Python 3.8+ instalado
- Windows (para gerar .exe)
- Conexão com internet (para download de dependências)

## 🚀 Processo de Build

### Método 1: Automático (Recomendado)

```batch
# No diretório agent/
build.bat
```

Este script fará tudo automaticamente:
1. Verificar/criar ambiente virtual
2. Instalar dependências
3. Compilar executável
4. Criar pacote de distribuição

### Método 2: Manual

1. **Setup do ambiente:**
   ```bash
   python setup.py
   ```

2. **Ativar ambiente virtual:**
   ```batch
   # Windows
   venv\Scripts\activate.bat
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Build do executável:**
   ```bash
   python build.py
   ```

## 📦 Resultado

Após o build bem-sucedido, você encontrará:

```
agent/
├── release/
│   ├── HiProd-Agent.exe    # Executável principal
│   ├── config.example      # Exemplo de configuração
│   └── README.txt          # Instruções de uso
├── dist/                   # Arquivos de build do PyInstaller
└── build/                  # Arquivos temporários
```

## ⚙️ Configuração do Executável

1. **Copie `config.example` para `.env`**
2. **Configure as variáveis:**
   ```env
   API_URL=http://localhost:8010
   USER_NAME=seu_usuario
   USER_PASSWORD=sua_senha
   SCREENSHOT_ENABLED=true
   ```

## 🎯 Distribuição

O executável gerado é **standalone** e pode ser distribuído sem Python instalado:

- ✅ **Não requer Python** no computador de destino
- ✅ **Todas as dependências incluídas**
- ✅ **Arquivo único** (onefile)
- ✅ **Ícone personalizado** (se disponível)

## 📏 Tamanho Esperado

- **Executável**: ~15-25 MB
- **Com compressão UPX**: ~8-15 MB

## 🔧 Personalização

### Modificar o ícone:
1. Coloque um arquivo `icon.ico` no diretório `agent/`
2. Execute o build novamente

### Ajustar configurações do PyInstaller:
1. Edite `hiprod-agent.spec`
2. Modifique parâmetros como:
   - `console=False` (para executar sem console)
   - `upx=False` (desabilitar compressão)
   - Adicionar/remover `hiddenimports`

### Incluir arquivos adicionais:
1. Edite a seção `datas` em `hiprod-agent.spec`
2. Adicione tuplas `('origem', 'destino')`

## 🐛 Solução de Problemas

### Erro: "PyInstaller não encontrado"
```bash
pip install pyinstaller
```

### Erro: "Módulo não encontrado" no executável
1. Adicione o módulo em `hiddenimports` no arquivo `.spec`
2. Ou use `--hidden-import=modulo` no comando PyInstaller

### Executável muito grande
1. Habilite compressão UPX: `upx=True`
2. Exclua módulos desnecessários na seção `excludes`
3. Use `--exclude-module=modulo` para módulos específicos

### Erro de antivírus
- Executáveis PyInstaller podem ser detectados como falso positivo
- Adicione exceção no antivírus
- Considere assinar digitalmente o executável

## 📝 Logs de Build

Os logs detalhados são salvos durante o build:
- **PyInstaller**: `build/HiProd-Agent/warn-HiProd-Agent.txt`
- **Console**: Output direto no terminal

## 🔄 Atualizações

Para atualizar o executável:
1. Modifique o código fonte (`agent.py`)
2. Execute `build.bat` novamente
3. Distribua o novo executável da pasta `release/`

## 📞 Suporte

- **Documentação**: README.md principal do projeto
- **Issues**: GitHub do projeto HiProd
- **Build específico**: Verifique logs em `build/`
