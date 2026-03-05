#include "config.h"
#include "api.h"
#include "screen_capture.h"
#include "windows_utils.h"
#include <curl/curl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

static void get_iso_time(char *buf, size_t buf_len) {
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    if (!tm) { buf[0] = '\0'; return; }
    snprintf(buf, buf_len, "%04d-%02d-%02dT%02d:%02d:%02d",
             tm->tm_year + 1900, tm->tm_mon + 1, tm->tm_mday,
             tm->tm_hour, tm->tm_min, tm->tm_sec);
}

int main(void) {
    hiprod_config_t cfg;
    if (config_load(&cfg) != 0) {
        fprintf(stderr, "[ERROR] Falha ao carregar config\n");
        return 1;
    }

    curl_global_init(CURL_GLOBAL_DEFAULT);

    printf("[HiProd Agent C " HIPROD_AGENT_VERSION "] Usuario: %s | API: %s\n",
           cfg.user_name, cfg.api_url);

    int usuario_id = api_get_usuario_monitorado_id(&cfg, NULL);
    if (usuario_id <= 0) {
        fprintf(stderr, "[ERROR] Nao foi possivel obter ID do usuario monitorado\n");
        curl_global_cleanup();
        return 1;
    }
    printf("[OK] Usuario monitorado ID: %d\n", usuario_id);

    unsigned int cycles = 0;
    unsigned int frame_cycles = 0;
    char horario[64];
    char window_title[512];

    for (;;) {
        get_iso_time(horario, sizeof(horario));
        win_get_foreground_window_title(window_title, sizeof(window_title));
        unsigned int idle_sec = win_get_idle_seconds();

        /* A cada monitor_interval_sec: enviar atividade */
        if (cycles % (unsigned)cfg.monitor_interval_sec == 0) {
            int ociosidade = (int)(idle_sec > 600 ? 100 : (idle_sec / 6));
            if (ociosidade > 100) ociosidade = 100;

            int r = api_send_activity(&cfg, usuario_id, ociosidade,
                                     window_title, "", "", "", "",
                                     horario);
            if (r == 0)
                printf("[OK] Atividade: %s\n", window_title);
            else
                fprintf(stderr, "[WARN] Falha ao enviar atividade\n");
        }

        /* A cada screen_frame_interval_sec: capturar e enviar frames (se houver) */
        if (cfg.screen_frame_interval_sec > 0 && frame_cycles % (unsigned)cfg.screen_frame_interval_sec == 0) {
            hiprod_frame_t *frames = NULL;
            int frame_count = 0;
            if (hiprod_capture_screen_frames(&frames, &frame_count) == 0 && frame_count > 0) {
                const unsigned char **data_ptrs = (const unsigned char **)malloc((size_t)frame_count * sizeof(void *));
                size_t *lens = (size_t *)malloc((size_t)frame_count * sizeof(size_t));
                if (data_ptrs && lens) {
                    for (int i = 0; i < frame_count; i++) {
                        data_ptrs[i] = frames[i].data;
                        lens[i] = frames[i].len;
                    }
                    if (api_send_screen_frames(&cfg, usuario_id, data_ptrs, lens, frame_count, horario) == 0)
                        printf("[FRAMES] %d frame(s) enviado(s)\n", frame_count);
                    free(data_ptrs);
                    free(lens);
                }
                hiprod_frames_free(frames, frame_count);
            }
        }

        frame_cycles++;
        cycles++;

#ifdef _WIN32
        Sleep(1000); /* 1 segundo entre ciclos */
#else
        sleep(1);
#endif
    }

    curl_global_cleanup();
    return 0;
}
