@echo off
REM Aumenta o tempo que o Windows espera um servico responder ao iniciar (evita Erro 1053).
REM Execute como Administrador (clique direito - Executar como administrador).
echo Aumentando timeout de inicio de servicos para 60 segundos...
reg add "HKLM\SYSTEM\CurrentControlSet\Control" /v ServicesPipeTimeout /t REG_DWORD /d 60000 /f
if %errorlevel% equ 0 (
    echo OK. Reinicie o servico HiProd Agent ou reinicie o PC para aplicar.
) else (
    echo Execute este arquivo como Administrador.
)
pause
