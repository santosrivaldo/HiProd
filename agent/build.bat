@echo off
echo 🚀 HiProd Agent - Build para Executável
echo ========================================
echo.

REM Verificar se estamos no diretório correto
if not exist "agent.py" (
    echo ❌ Erro: Execute este script no diretório do agent
    echo Certifique-se de estar em: agent\
    pause
    exit /b 1
)

REM Verificar se o venv existe
if not exist "venv" (
    echo ⚠️  Ambiente virtual não encontrado!
    echo Executando setup primeiro...
    echo.
    python setup.py
    if errorlevel 1 (
        echo ❌ Erro no setup
        pause
        exit /b 1
    )
    echo.
)

REM Ativar venv e executar build
echo 🔄 Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo 🔄 Iniciando build...
python build.py

if errorlevel 1 (
    echo.
    echo ❌ Erro no build
    pause
    exit /b 1
)

echo.
echo 🎉 Build concluído!
echo 📦 Verifique a pasta 'release' para os arquivos
echo.
pause
