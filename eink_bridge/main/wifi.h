#ifndef wifi_h_INCLUDED
#define wifi_h_INCLUDED

#include "esp_err.h"
#include "esp_check.h"
#include "esp_netif_ip_addr.h"

typedef struct {
    char *hostname;
    uint8_t ssid[32];
    uint8_t password[64];
} start_wifi_cfg;

typedef struct {
    esp_ip4_addr_t addr;
} start_wifi_result;

esp_err_t wifi_connect(start_wifi_cfg *cfg, start_wifi_result *out);
esp_err_t wifi_disconnect();


#endif // wifi_h_INCLUDED
