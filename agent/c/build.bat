@echo off
setlocal
cd /d "%~dp0"

set EXE=hiprod_agent_c.exe
set SRCS=main.c config.c http.c api.c screen_capture.c windows_utils.c
set CFLAGS=-O2 -Wall -std=c11 -D_WIN32_WINNT=0x0600

:: Procurar gcc (MinGW)
set GCC=
where gcc >nul 2>&1 && set GCC=gcc
if not defined GCC (
    if exist "C:\msys64\mingw64\bin\gcc.exe" set "GCC=C:\msys64\mingw64\bin\gcc.exe"
    if exist "C:\msys64\ucrt64\bin\gcc.exe"    set "GCC=C:\msys64\ucrt64\bin\gcc.exe"
    if exist "C:\MinGW\bin\gcc.exe"            set "GCC=C:\MinGW\bin\gcc.exe"
)

if not defined GCC (
    echo.
    echo [ERRO] Nao encontrado: gcc. Para compilar sem CMake:
    echo.
    echo  1. Instale o MSYS2: https://www.msys2.org/
    echo  2. Abra "MSYS2 MinGW 64-bit" e rode:
    echo     pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-curl
    echo  3. Nesse terminal, va ate a pasta do agente e rode:
    echo     gcc -O2 -Wall -std=c11 -o hiprod_agent_c.exe main.c config.c http.c api.c screen_capture.c windows_utils.c -I. -lcurl
    echo.
    echo  Ou instale o CMake e use: cmake -B build ^&^& cmake --build build
    echo     winget install Kitware.CMake
    echo.
    exit /b 1
)

:: Incluir/lib curl: tentar pkg-config (em MSYS2) ou caminhos comuns
set CURL_CFLAGS=
set CURL_LIBS=-lcurl
where pkg-config >nul 2>&1 && (
    for /f "delims=" %%i in ('pkg-config --cflags libcurl 2^>nul') do set CURL_CFLAGS=%%i
    for /f "delims=" %%i in ('pkg-config --libs libcurl 2^>nul') do set CURL_LIBS=%%i
)
if not defined CURL_CFLAGS set CURL_CFLAGS=-IC:\msys64\mingw64\include
if not defined CURL_LIBS   set CURL_LIBS=-lcurl

echo Compilando com: %GCC%
"%GCC%" %CFLAGS% %CURL_CFLAGS% -o %EXE% %SRCS% %CURL_LIBS%
if errorlevel 1 (
    echo.
    echo Se der erro de "curl/curl.h" ou "-lcurl", instale o libcurl no MSYS2:
    echo   pacman -S mingw-w64-x86_64-curl
    echo E execute este build.bat no terminal "MSYS2 MinGW 64-bit".
    exit /b 1
)

echo.
echo OK: %EXE% gerado. Execute com: .\%EXE%
exit /b 0
