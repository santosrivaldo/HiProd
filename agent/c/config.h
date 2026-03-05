#ifndef HIPROD_AGENT_CONFIG_H
#define HIPROD_AGENT_CONFIG_H

#define HIPROD_AGENT_VERSION "1.0.0"

typedef struct hiprod_config {
    char api_url[512];
    char user_name[128];
    int  monitor_interval_sec;
    int  screen_frame_interval_sec;
    int  request_timeout_sec;
    int  ssl_verify;
} hiprod_config_t;

int  config_load(hiprod_config_t *cfg);
void config_set_defaults(hiprod_config_t *cfg);

#endif
