#ifndef HIPROD_AGENT_SCREEN_CAPTURE_H
#define HIPROD_AGENT_SCREEN_CAPTURE_H

#include <stddef.h>

/* Estrutura para um frame JPEG em memória (caller libera data) */
typedef struct hiprod_frame {
    unsigned char *data;
    size_t len;
} hiprod_frame_t;

/* Captura um frame do monitor principal (JPEG). Retorna 0 em sucesso, -1 em falha.
 * frames[] e *count: saída; caller deve chamar hiprod_frames_free. */
int hiprod_capture_screen_frames(hiprod_frame_t **frames, int *count);

void hiprod_frames_free(hiprod_frame_t *frames, int count);

#endif
