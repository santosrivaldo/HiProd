@echo off
REM Script de validação de variáveis de ambiente para Docker Compose (Windows)
REM Verifica se as variáveis obrigatórias estão definidas antes de iniciar os containers

echo 🔍 Verificando variáveis de ambiente obrigatórias...
echo.

set ERRORS=0

REM Verificar se arquivo .env existe
if not exist .env (
    echo ❌ Arquivo .env não encontrado!
    echo.
    echo 📝 Crie um arquivo .env na raiz do projeto com as seguintes variáveis:
    echo.
    echo DB_USER=seu_usuario
    echo DB_PASSWORD=sua_senha_forte
    echo JWT_SECRET_KEY=sua_chave_secreta_forte
    echo.
    exit /b 1
)

REM Carregar variáveis do .env (Windows não suporta source, então vamos verificar diretamente)
findstr /C:"DB_USER=" .env >nul 2>&1
if errorlevel 1 (
    echo ❌ DB_USER não está definido no arquivo .env
    set /a ERRORS+=1
) else (
    echo ✓ DB_USER está definido
)

findstr /C:"DB_PASSWORD=" .env >nul 2>&1
if errorlevel 1 (
    echo ❌ DB_PASSWORD não está definido no arquivo .env
    set /a ERRORS+=1
) else (
    echo ✓ DB_PASSWORD está definido
    REM Verificar se não é senha padrão
    findstr /C:"DB_PASSWORD=postgres" .env >nul 2>&1
    if not errorlevel 1 (
        echo ⚠️  DB_PASSWORD parece ser uma senha padrão insegura!
    )
)

findstr /C:"JWT_SECRET_KEY=" .env >nul 2>&1
if errorlevel 1 (
    echo ❌ JWT_SECRET_KEY não está definido no arquivo .env
    set /a ERRORS+=1
) else (
    echo ✓ JWT_SECRET_KEY está definido
    REM Verificar se não é chave padrão
    findstr /C:"JWT_SECRET_KEY=change-me" .env >nul 2>&1
    if not errorlevel 1 (
        echo ⚠️  JWT_SECRET_KEY parece ser uma chave padrão insegura!
    )
)

if %ERRORS%==0 (
    echo.
    echo ✅ Todas as variáveis obrigatórias estão definidas!
    echo 🚀 Você pode executar: docker compose up --build
    exit /b 0
) else (
    echo.
    echo ❌ Erros encontrados. Corrija o arquivo .env antes de continuar.
    exit /b 1
)

