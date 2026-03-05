#include "http.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <curl/curl.h>

struct memory {
    char *data;
    size_t size;
};

static size_t write_cb(void *ptr, size_t size, size_t nmemb, void *user) {
    size_t total = size * nmemb;
    struct memory *m = (struct memory *)user;
    char *p = realloc(m->data, m->size + total + 1);
    if (!p) return 0;
    m->data = p;
    memcpy(m->data + m->size, ptr, total);
    m->size += total;
    m->data[m->size] = '\0';
    return total;
}

static struct curl_slist *build_headers(const char *header_user_name, int add_content_json) {
    char hbuf[256];
    snprintf(hbuf, sizeof(hbuf), "X-User-Name: %s", header_user_name ? header_user_name : "");
    struct curl_slist *h = curl_slist_append(NULL, hbuf);
    h = curl_slist_append(h, "Accept: application/json");
    if (add_content_json)
        h = curl_slist_append(h, "Content-Type: application/json");
    return h;
}

static void set_common_opts(CURL *c, int timeout_sec, int ssl_verify, struct memory *mem) {
    curl_easy_setopt(c, CURLOPT_TIMEOUT, (long)timeout_sec);
    curl_easy_setopt(c, CURLOPT_SSL_VERIFYPEER, ssl_verify ? 1L : 0L);
    curl_easy_setopt(c, CURLOPT_SSL_VERIFYHOST, ssl_verify ? 2L : 0L);
    curl_easy_setopt(c, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(c, CURLOPT_WRITEDATA, mem);
}

void hiprod_http_response_free(hiprod_http_response_t *r) {
    if (r && r->body) {
        free(r->body);
        r->body = NULL;
        r->body_len = 0;
    }
}

int hiprod_http_get(const char *url, const char *header_user_name,
                    int timeout_sec, int ssl_verify,
                    hiprod_http_response_t *out) {
    if (!url || !out) return -1;
    out->code = 0;
    out->body = NULL;
    out->body_len = 0;

    CURL *c = curl_easy_init();
    if (!c) return -1;

    struct memory mem = { NULL, 0 };
    set_common_opts(c, timeout_sec, ssl_verify, &mem);
    struct curl_slist *headers = build_headers(header_user_name, 0);
    curl_easy_setopt(c, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(c, CURLOPT_URL, url);
    curl_easy_setopt(c, CURLOPT_HTTPGET, 1L);

    CURLcode res = curl_easy_perform(c);
    curl_slist_free_all(headers);
    if (res != CURLE_OK) {
        curl_easy_cleanup(c);
        free(mem.data);
        return -1;
    }
    curl_easy_getinfo(c, CURLINFO_RESPONSE_CODE, &out->code);
    out->body = mem.data;
    out->body_len = mem.size;
    curl_easy_cleanup(c);
    return 0;
}

int hiprod_http_post_json(const char *url, const char *header_user_name,
                          const char *json_body,
                          int timeout_sec, int ssl_verify,
                          hiprod_http_response_t *out) {
    if (!url || !out) return -1;
    out->code = 0;
    out->body = NULL;
    out->body_len = 0;

    CURL *c = curl_easy_init();
    if (!c) return -1;

    struct memory mem = { NULL, 0 };
    set_common_opts(c, timeout_sec, ssl_verify, &mem);
    struct curl_slist *headers = build_headers(header_user_name, 1);
    curl_easy_setopt(c, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(c, CURLOPT_URL, url);
    curl_easy_setopt(c, CURLOPT_POSTFIELDS, json_body);
    curl_easy_setopt(c, CURLOPT_POST, 1L);

    CURLcode res = curl_easy_perform(c);
    curl_slist_free_all(headers);
    if (res != CURLE_OK) {
        curl_easy_cleanup(c);
        free(mem.data);
        return -1;
    }
    curl_easy_getinfo(c, CURLINFO_RESPONSE_CODE, &out->code);
    out->body = mem.data;
    out->body_len = mem.size;
    curl_easy_cleanup(c);
    return 0;
}

int hiprod_http_post_multipart(const char *url, const char *header_user_name,
                               const char *form_usuario_monitorado_id,
                               const char *form_captured_at,
                               const unsigned char **frame_data,
                               const size_t *frame_len,
                               int frame_count,
                               int timeout_sec, int ssl_verify,
                               hiprod_http_response_t *out) {
    if (!url || !out || !form_usuario_monitorado_id || !form_captured_at ||
        !frame_data || !frame_len || frame_count <= 0)
        return -1;
    out->code = 0;
    out->body = NULL;
    out->body_len = 0;

    CURL *c = curl_easy_init();
    if (!c) return -1;

    curl_mime *mime = curl_mime_init(c);
    if (!mime) { curl_easy_cleanup(c); return -1; }

    curl_mimepart *part = curl_mime_addpart(mime);
    curl_mime_name(part, "usuario_monitorado_id");
    curl_mime_data(part, form_usuario_monitorado_id, CURL_ZERO_TERMINATED);
    part = curl_mime_addpart(mime);
    curl_mime_name(part, "captured_at");
    curl_mime_data(part, form_captured_at, CURL_ZERO_TERMINATED);

    for (int i = 0; i < frame_count; i++) {
        char fname[32];
        snprintf(fname, sizeof(fname), "frame_%d.jpg", i);
        part = curl_mime_addpart(mime);
        curl_mime_name(part, "frames");
        curl_mime_data(part, (const char *)frame_data[i], frame_len[i]);
        curl_mime_filename(part, fname);
        curl_mime_type(part, "image/jpeg");
    }

    struct memory mem = { NULL, 0 };
    set_common_opts(c, timeout_sec, ssl_verify, &mem);
    struct curl_slist *headers = build_headers(header_user_name, 0);
    curl_easy_setopt(c, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(c, CURLOPT_URL, url);
    curl_easy_setopt(c, CURLOPT_MIMEPOST, mime);

    CURLcode res = curl_easy_perform(c);
    curl_slist_free_all(headers);
    curl_mime_free(mime);
    if (res != CURLE_OK) {
        curl_easy_cleanup(c);
        free(mem.data);
        return -1;
    }
    curl_easy_getinfo(c, CURLINFO_RESPONSE_CODE, &out->code);
    out->body = mem.data;
    out->body_len = mem.size;
    curl_easy_cleanup(c);
    return 0;
}
