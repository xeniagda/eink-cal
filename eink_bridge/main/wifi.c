#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_event.h"

#include "wifi.h"
#include <string.h>

static const char *TAG = "bridge_wifi";

SemaphoreHandle_t wait_for_connect = NULL;
volatile esp_ip4_addr_t ip_addr;
volatile _Bool failed = false;

// TODO: Handle connect errors
void on_wifi_connect(void *event_handler_arg, esp_event_base_t event_base, int32_t event_id, void *event_data) {
    ESP_LOGI(TAG, "WiFi connected");
}

void on_ip_got(void *event_handler_arg, esp_event_base_t event_base, int32_t event_id, void *event_data) {
    ip_event_got_ip_t *data = event_data;
    ip_addr = data->ip_info.ip;
    xSemaphoreGive(wait_for_connect);
}


static void *wifi_fail_disconnect = (void*) 0x1;

void on_wifi_failed(void *event_handler_arg, esp_event_base_t event_base, int32_t event_id, void *event_data) {
    ESP_LOGE(TAG, "WiFi connect failed:");
    if (event_data == wifi_fail_disconnect) {
        ESP_LOGE(TAG, "(disconnected)");
    } else {
        ESP_LOGE(TAG, "(unknown reason?? %p)", event_data);
    }

    failed = true;
    xSemaphoreGive(wait_for_connect);
}

esp_err_t wifi_connect(start_wifi_cfg *cfg, start_wifi_result *out) {
    wait_for_connect = xSemaphoreCreateBinary();
    if (wait_for_connect == NULL) {
        ESP_LOGE(TAG, "could not initialize semaphore");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Initializing wifi system");
    // initialize wifi and netif stuff
    wifi_init_config_t init_cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_wifi_init(&init_cfg), TAG, "esp_wifi_init failed");

    esp_netif_inherent_config_t netif_config = ESP_NETIF_INHERENT_DEFAULT_WIFI_STA();
    esp_netif_t *netif_wifi = esp_netif_create_wifi(WIFI_IF_STA, &netif_config);
    esp_netif_set_hostname(netif_wifi, cfg->hostname);
    esp_wifi_set_default_wifi_sta_handlers();

    ESP_LOGI(TAG, "Setting mode");
    ESP_RETURN_ON_ERROR(esp_wifi_set_storage(WIFI_STORAGE_RAM), TAG, "esp_wifi_set_storage failed");
    ESP_RETURN_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), TAG, "esp_wifi_set_mode failed");

    // register callbacks
    ESP_RETURN_ON_ERROR(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_CONNECTED, on_wifi_connect, NULL), TAG, "esp_event_handler_register failed");
    ESP_RETURN_ON_ERROR(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, on_wifi_failed, (void*) 0x1), TAG, "esp_event_handler_register failed");
    ESP_RETURN_ON_ERROR(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_ip_got, NULL), TAG, "esp_event_handler_register failed");

    ESP_LOGI(TAG, "Starting");
    ESP_RETURN_ON_ERROR(esp_wifi_start(), TAG, "esp_wifi_start failed");

    ESP_LOGI(TAG, "Started WiFi system");

    wifi_config_t wifi_cfg = { .sta = {
        .scan_method = WIFI_ALL_CHANNEL_SCAN,
        .sort_method = WIFI_CONNECT_AP_BY_SIGNAL,
    }};
    memcpy(&wifi_cfg.sta.ssid, &cfg->ssid, 32);
    memcpy(&wifi_cfg.sta.password, &cfg->password, 64);

    ESP_LOGI(TAG, "Connecting to WiFi SSID %s", wifi_cfg.sta.ssid);
    ESP_RETURN_ON_ERROR(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg), TAG, "esp_wifi_set_config failed");
    ESP_RETURN_ON_ERROR(esp_wifi_connect(), TAG, "esp_wifi_connect failed");

    ESP_LOGI(TAG, "Waiting for connection");
    xSemaphoreTake(wait_for_connect, portMAX_DELAY);

    if (failed) {
        return ESP_FAIL;
    }
    out->addr = ip_addr;

    return ESP_OK;
}

esp_err_t wifi_disconnect() {
    ESP_LOGI(TAG, "shutting down wifi");
    return esp_wifi_stop();

}
