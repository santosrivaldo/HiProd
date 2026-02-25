@echo off
chcp 65001 >nul
REM Adiciona o HiProd Agent para iniciar quando o usuário fizer logon no Windows.
REM NÃO precisa ser Administrador.

cd /d "%~dp0"

set "EXE=%~dp0HiProd-Agent.exe"
if not exist "%EXE%" (
    echo HiProd-Agent.exe nao encontrado nesta pasta: %~dp0
    echo Coloque este script na mesma pasta do HiProd-Agent.exe e execute novamente.
    pause
    exit /b 1
)

for %%I in ("%EXE%") do set "CAMINHO=%%~fI"
REM Valor no registro: caminho entre aspas (para pastas com espacos)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v HiProdAgent /t REG_SZ /d "\"%CAMINHO%\"" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo [OK] HiProd Agent configurado para iniciar com o Windows.
    echo     O agent sera iniciado quando voce fizer logon.
    echo     Para remover: execute iniciar_com_windows_desinstalar.bat
) else (
    echo Erro ao gravar no registro. Tente executar como Administrador.
)
echo.
pause
