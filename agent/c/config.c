#include "config.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

static void trim(char *s) {
    char *p = s;
    while (*p == ' ' || *p == '\t') p++;
    if (p != s) memmove(s, p, strlen(p) + 1);
    p = s + strlen(s);
    while (p > s && (p[-1] == ' ' || p[-1] == '\t' || p[-1] == '\r' || p[-1] == '\n')) *--p = '\0';
}

static int parse_env_file(const char *path, hiprod_config_t *cfg) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char line[512];
    while (fgets(line, sizeof(line), f)) {
        trim(line);
        if (!line[0] || line[0] == '#') continue;
        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        char *key = line;
        char *val = eq + 1;
        trim(key);
        trim(val);
        if (strcmp(key, "API_URL") == 0 && val[0]) {
            strncpy(cfg->api_url, val, sizeof(cfg->api_url) - 1);
            cfg->api_url[sizeof(cfg->api_url) - 1] = '\0';
        } else if (strcmp(key, "MONITOR_INTERVAL") == 0 && val[0]) {
            cfg->monitor_interval_sec = atoi(val);
            if (cfg->monitor_interval_sec <= 0) cfg->monitor_interval_sec = 10;
        } else if (strcmp(key, "SCREEN_FRAME_INTERVAL") == 0 && val[0]) {
            cfg->screen_frame_interval_sec = atoi(val);
            if (cfg->screen_frame_interval_sec <= 0) cfg->screen_frame_interval_sec = 1;
        } else if (strcmp(key, "REQUEST_TIMEOUT") == 0 && val[0]) {
            cfg->request_timeout_sec = atoi(val);
            if (cfg->request_timeout_sec <= 0) cfg->request_timeout_sec = 30;
        } else if (strcmp(key, "SSL_VERIFY") == 0) {
            cfg->ssl_verify = (strcmp(val, "false") != 0 && strcmp(val, "0") != 0);
        }
    }
    fclose(f);
    return 1;
}

void config_set_defaults(hiprod_config_t *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    strncpy(cfg->api_url, "https://hiprod.grupohi.com.br", sizeof(cfg->api_url) - 1);
    cfg->monitor_interval_sec = 10;
    cfg->screen_frame_interval_sec = 1;
    cfg->request_timeout_sec = 30;
    cfg->ssl_verify = 1;
}

int config_load(hiprod_config_t *cfg) {
    config_set_defaults(cfg);

    const char *env_url = getenv("API_URL");
    if (env_url && env_url[0]) {
        strncpy(cfg->api_url, env_url, sizeof(cfg->api_url) - 1);
        cfg->api_url[sizeof(cfg->api_url) - 1] = '\0';
    }

    char env_path[1024];
    char dir_buf[1024];
    const char *dir = ".";
#ifdef _WIN32
    if (GetModuleFileNameA(NULL, dir_buf, sizeof(dir_buf))) {
        char *slash = strrchr(dir_buf, '\\');
        if (slash) { *slash = '\0'; dir = dir_buf; }
    }
#endif
    snprintf(env_path, sizeof(env_path), "%s/.env", dir);
    parse_env_file(env_path, cfg);

    snprintf(env_path, sizeof(env_path), "%s/config.example", dir);
    if (!cfg->api_url[0]) parse_env_file(env_path, cfg);

#ifdef _WIN32
    DWORD n = sizeof(cfg->user_name);
    if (GetUserNameA(cfg->user_name, &n))
        cfg->user_name[n] = '\0';
    else
        strncpy(cfg->user_name, "user", sizeof(cfg->user_name) - 1);
#else
    const char *u = getenv("USER");
    if (u) strncpy(cfg->user_name, u, sizeof(cfg->user_name) - 1);
    else strncpy(cfg->user_name, "user", sizeof(cfg->user_name) - 1);
#endif
    return 0;
}
