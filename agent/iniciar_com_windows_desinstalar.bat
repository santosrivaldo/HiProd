@echo off
chcp 65001 >nul
REM Remove o HiProd Agent da inicializacao com o Windows.

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v HiProdAgent /f >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] HiProd Agent removido da inicializacao com o Windows.
) else (
    echo Nada a remover ou erro. O agent ja nao estava configurado para iniciar com o Windows.
)
echo.
pause
