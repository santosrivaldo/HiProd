#include "api.h"
#include "http.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* Parse simples de "id": 123 no JSON (número inteiro) */
static int parse_id_from_json(const char *body) {
    if (!body) return 0;
    const char *p = strstr(body, "\"id\"");
    if (!p) return 0;
    p += 4;
    while (*p == ' ' || *p == '\t' || *p == ':') p++;
    return (int)atoi(p);
}

int api_get_usuario_monitorado_id(const hiprod_config_t *cfg, const char *user_name) {
    char url[768];
    const char *base = cfg->api_url;
    const char *nome = user_name && user_name[0] ? user_name : cfg->user_name;
    snprintf(url, sizeof(url), "%s/api/usuarios-monitorados?nome=%s", base, nome);

    hiprod_http_response_t res = { 0 };
    int r = hiprod_http_get(url, nome, cfg->request_timeout_sec, cfg->ssl_verify, &res);
    if (r != 0) {
        hiprod_http_response_free(&res);
        return 0;
    }
    if (res.code != 200) {
        hiprod_http_response_free(&res);
        return 0;
    }
    int id = parse_id_from_json(res.body);
    hiprod_http_response_free(&res);
    return id;
}

static void escape_json_string(const char *s, char *out, size_t out_len) {
    if (!s || !out || out_len == 0) { if (out) out[0] = '\0'; return; }
    size_t j = 0;
    for (; *s && j < out_len - 1; s++) {
        if (*s == '"' || *s == '\\') { if (j < out_len - 2) out[j++] = '\\'; }
        if (j < out_len - 1) out[j++] = *s;
    }
    out[j] = '\0';
}

int api_send_activity(const hiprod_config_t *cfg, int usuario_monitorado_id,
                      int ociosidade, const char *active_window,
                      const char *url, const char *page_title,
                      const char *domain, const char *application,
                      const char *horario_iso) {
    char json[2048];
    char esc_title[512], esc_url[512], esc_page[512], esc_domain[256], esc_app[256];
    escape_json_string(active_window, esc_title, sizeof(esc_title));
    escape_json_string(url ? url : "", esc_url, sizeof(esc_url));
    escape_json_string(page_title ? page_title : "", esc_page, sizeof(esc_page));
    escape_json_string(domain ? domain : "", esc_domain, sizeof(esc_domain));
    escape_json_string(application ? application : "", esc_app, sizeof(esc_app));

    const char *hor = (horario_iso && horario_iso[0]) ? horario_iso : "2020-01-01T00:00:00";
    int n = snprintf(json, sizeof(json),
        "{\"usuario_monitorado_id\":%d,\"ociosidade\":%d,\"active_window\":\"%s\","
        "\"url\":\"%s\",\"page_title\":\"%s\",\"domain\":\"%s\",\"application\":\"%s\","
        "\"horario\":\"%s\"}",
        usuario_monitorado_id, ociosidade, esc_title,
        esc_url, esc_page, esc_domain, esc_app, hor);
    if (n < 0 || (size_t)n >= sizeof(json)) return -1;

    char post_url[768];
    snprintf(post_url, sizeof(post_url), "%s/api/atividade", cfg->api_url);

    hiprod_http_response_t res = { 0 };
    int ret = hiprod_http_post_json(post_url, cfg->user_name, json,
                                    cfg->request_timeout_sec, cfg->ssl_verify, &res);
    int ok = (ret == 0 && res.code == 201);
    hiprod_http_response_free(&res);
    return ok ? 0 : -1;
}

int api_send_screen_frames(const hiprod_config_t *cfg, int usuario_monitorado_id,
                           const unsigned char **frame_data, const size_t *frame_len,
                           int frame_count, const char *captured_at_iso) {
    char post_url[768];
    char uid_buf[32];
    snprintf(post_url, sizeof(post_url), "%s/api/screen-frames", cfg->api_url);
    snprintf(uid_buf, sizeof(uid_buf), "%d", usuario_monitorado_id);

    hiprod_http_response_t res = { 0 };
    int r = hiprod_http_post_multipart(post_url, cfg->user_name,
                                       uid_buf, captured_at_iso,
                                       frame_data, frame_len, frame_count,
                                       cfg->request_timeout_sec, cfg->ssl_verify, &res);
    int ok = (r == 0 && res.code == 201);
    hiprod_http_response_free(&res);
    return ok ? 0 : -1;
}
