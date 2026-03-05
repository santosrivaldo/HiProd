cmake_minimum_required(VERSION 3.10)
project(hiprod_agent_c C)

set(CMAKE_C_STANDARD 11)

find_package(CURL REQUIRED)

add_executable(hiprod_agent_c
  main.c
  config.c
  http.c
  api.c
  screen_capture.c
)

if(WIN32)
  target_sources(hiprod_agent_c PRIVATE windows_utils.c)
  target_compile_definitions(hiprod_agent_c PRIVATE _WIN32_WINNT=0x0600)
  target_link_libraries(hiprod_agent_c PRIVATE CURL::libcurl)
else()
  target_link_libraries(hiprod_agent_c PRIVATE CURL::libcurl)
  # windows_utils.c compila vazio em não-Windows (apenas stubs)
  target_sources(hiprod_agent_c PRIVATE windows_utils.c)
endif()

# Opcional: captura de tela com JPEG (requer libjpeg)
# option(ENABLE_JPEG_ENCODE "Build with screen capture JPEG encoding (libjpeg)" OFF)
# if(ENABLE_JPEG_ENCODE)
#   find_package(JPEG REQUIRED)
#   target_compile_definitions(hiprod_agent_c PRIVATE ENABLE_JPEG_ENCODE)
#   target_sources(hiprod_agent_c PRIVATE jpeg_encode.c)
#   target_link_libraries(hiprod_agent_c PRIVATE JPEG::JPEG)
# endif()
