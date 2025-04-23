idf_component_register(
                    SRCS "eink_bridge.c" "led.c" "wifi.c" "eink_display.c"
                    INCLUDE_DIRS "."
                    REQUIRES esp_wifi nvs_flash esp_event esp_netif esp_driver_gpio esp_driver_spi wpa_supplicant
)
