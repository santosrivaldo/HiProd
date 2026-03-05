# HiProd Agent (C)

Versão do agente HiProd em C: envia atividade (janela ativa, ociosidade) e opcionalmente frames de tela para a API, identificando-se pelo nome do usuário Windows.

## Requisitos

- **Windows**: Visual Studio Build Tools ou MinGW-w64, e [libcurl](https://curl.se/windows/) (OpenSSL).
- **Linux**: `build-essential`, `libcurl4-openssl-dev`.

## Configuração

- Crie um ficheiro `.env` na mesma pasta do executável (ou use variáveis de ambiente):
  - `API_URL` – URL base da API (ex.: `https://hiprod.grupohi.com.br`)
  - `MONITOR_INTERVAL` – intervalo em segundos entre envios de atividade (padrão: 10)
  - `SCREEN_FRAME_INTERVAL` – intervalo para captura/envio de frames (padrão: 1)
  - `REQUEST_TIMEOUT` – timeout HTTP em segundos (padrão: 30)
  - `SSL_VERIFY` – `true` ou `false` (padrão: true)

O agente usa o **nome do usuário do Windows** (ou `USER` no Linux) para o header `X-User-Name` e para buscar/criar o usuário monitorado na API.

## Build no Windows (sem CMake)

Na pasta do agente, execute:

```batch
cd agent\c
build.bat
```

O script usa `gcc` se estiver no PATH (por exemplo após instalar [MSYS2](https://www.msys2.org/) e `pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-curl`). Se não tiver `gcc`, o script mostra instruções.

## Build com CMake

Se tiver o CMake instalado (ex.: `winget install Kitware.CMake`):

```bash
cd agent/c
cmake -B build
cmake --build build
```

O executável ficará em `build/hiprod_agent_c.exe` (ou `hiprod_agent_c` no Linux).

## Build com Makefile (Linux)

```bash
cd agent/c
# Ajuste CURL_CFLAGS e CURL_LIBS se necessário (ex.: pkg-config)
make
./hiprod_agent_c
```

## Build no Windows (MinGW + libcurl)

1. Instale [MSYS2](https://www.msys2.org/), depois: `pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-curl`
2. No shell MinGW64:
```bash
cd agent/c
gcc -O2 -o hiprod_agent_c.exe main.c config.c http.c api.c screen_capture.c windows_utils.c -I. -lcurl -lcurl
```

(Em muitos sistemas MinGW o link é apenas `-lcurl`.)

## Funcionalidades

- **Atividade**: a cada `MONITOR_INTERVAL` segundos envia `POST /api/atividade` com:
  - `usuario_monitorado_id` (obtido via `GET /api/usuarios-monitorados?nome=...`)
  - `ociosidade`, `active_window`, `horario`, `url`, `page_title`, `domain`, `application`
- **Screen frames**: a cada `SCREEN_FRAME_INTERVAL` segundos tenta capturar o ecrã e enviar `POST /api/screen-frames` (multipart). **Por defeito não há encoder JPEG**; a captura GDI está implementada mas a codificação JPEG requer libjpeg (opcional). Sem JPEG, o agente não envia frames (apenas atividade).

## Captura de tela com JPEG (opcional)

Para enviar frames de tela é necessário codificar em JPEG. Opções:

1. **Com libjpeg**: defina `ENABLE_JPEG_ENCODE` e implemente `hiprod_rgb_to_jpeg()` em `jpeg_encode.c` usando libjpeg, e ligue com `-ljpeg`. O `screen_capture.c` já prepara os dados RGB (BGR do GDI).
2. **Sem libjpeg**: o agente compila e corre normalmente; apenas não envia frames (continua a enviar atividade).

## Compatibilidade com a API

- `GET /api/usuarios-monitorados?nome=...` com header `X-User-Name` → retorna `{"id": N, "created": true/false}`.
- `POST /api/atividade` com JSON e `X-User-Name`.
- `POST /api/screen-frames` com multipart: `usuario_monitorado_id`, `captured_at`, e ficheiros `frames` (JPEG).

Compatível com o backend HiProd usado pelo agente Python.
