@echo off
REM Remove o servico HiProd Agent do Windows.
REM Execute como Administrador.

cd /d "%~dp0"

echo Parando servico (se estiver em execucao)...
net stop HiProdAgent 2>nul

echo Removendo servico...
if exist "HiProd-Agent-Service.exe" (
    HiProd-Agent-Service.exe remove
) else (
    python agent_service.py remove
)

if errorlevel 1 (
    echo Execute como Administrador: clique direito -^> Executar como administrador
    pause
    exit /b 1
)

echo Servico removido.
pause
