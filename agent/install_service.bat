@echo off
REM Instala o HiProd Agent como servico do Windows.
REM Execute como Administrador (clique direito -> Executar como administrador).

cd /d "%~dp0"

if exist "HiProd-Agent-Service.exe" (
    echo Usando executavel do servico (instalacao sem Python).
    echo Instalando servico HiProd Agent...
    HiProd-Agent-Service.exe install
) else (
    echo Verificando se pywin32 esta instalado...
    python -c "import win32serviceutil" 2>nul
    if errorlevel 1 (
        echo Instalando pywin32...
        pip install pywin32
    )
    echo.
    echo Instalando servico HiProd Agent...
    python agent_service.py install
)

if errorlevel 1 (
    echo.
    echo ERRO: Execute este script como Administrador.
    echo Clique direito em install_service.bat -^> Executar como administrador
    pause
    exit /b 1
)

echo.
echo Servico instalado. Para iniciar: net start HiProdAgent
if exist "HiProd-Agent-Service.exe" (
    echo Ou: HiProd-Agent-Service.exe start
) else (
    echo Ou use: python agent_service.py start
)
echo.
pause
