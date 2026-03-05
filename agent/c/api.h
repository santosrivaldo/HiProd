#ifndef HIPROD_AGENT_API_H
#define HIPROD_AGENT_API_H

#include "config.h"

/* Retorna ID do usuário monitorado (busca/cria via API) ou 0 em erro */
int api_get_usuario_monitorado_id(const hiprod_config_t *cfg, const char *user_name);

/* Envia atividade. Retorna 0 em sucesso, -1 em falha */
int api_send_activity(const hiprod_config_t *cfg, int usuario_monitorado_id,
                      int ociosidade, const char *active_window,
                      const char *url, const char *page_title,
                      const char *domain, const char *application,
                      const char *horario_iso);

/* Envia screen frames (multipart). frame_data/frame_len arrays de frame_count elementos. */
int api_send_screen_frames(const hiprod_config_t *cfg, int usuario_monitorado_id,
                           const unsigned char **frame_data, const size_t *frame_len,
                           int frame_count, const char *captured_at_iso);

#endif
