#ifndef HIPROD_AGENT_HTTP_H
#define HIPROD_AGENT_HTTP_H

typedef struct hiprod_http_response {
    long code;
    char *body;
    size_t body_len;
} hiprod_http_response_t;

void hiprod_http_response_free(hiprod_http_response_t *r);

int hiprod_http_get(const char *url, const char *header_user_name,
                    int timeout_sec, int ssl_verify,
                    hiprod_http_response_t *out);

int hiprod_http_post_json(const char *url, const char *header_user_name,
                          const char *json_body,
                          int timeout_sec, int ssl_verify,
                          hiprod_http_response_t *out);

int hiprod_http_post_multipart(const char *url, const char *header_user_name,
                               const char *form_usuario_monitorado_id,
                               const char *form_captured_at,
                               const unsigned char **frame_data,
                               const size_t *frame_len,
                               int frame_count,
                               int timeout_sec, int ssl_verify,
                               hiprod_http_response_t *out);

#endif
