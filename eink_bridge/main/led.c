#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_err.h"
#include "driver/rtc_io.h"

#include "led.h"

static const char *TAG = "led";

#define CONFIG_LED_PIN_R 33
#define CONFIG_LED_PIN_G 32
#define CONFIG_LED_PIN_B 25

const led_color_t LED_COLOR_RED = { .r = 1, .g = 0, .b = 0 };
const led_color_t LED_COLOR_YELLOW = { .r = 1, .g = 1, .b = 0 };
const led_color_t LED_COLOR_GREEN = { .r = 0, .g = 1, .b = 0 };
const led_color_t LED_COLOR_TEAL = { .r = 0, .g = 1, .b = 1 };
const led_color_t LED_COLOR_BLUE = { .r = 0, .g = 0, .b = 1 };
const led_color_t LED_COLOR_PURPLE = { .r = 1, .g = 0, .b = 1 };
const led_color_t LED_COLOR_WHITE = { .r = 1, .g = 1, .b = 1 };


esp_err_t led_init() {
    ESP_LOGI(TAG, "Initializing LEDs");
    gpio_config_t cfg = {
        .pin_bit_mask = ((uint64_t) 1 << CONFIG_LED_PIN_R) | ((uint64_t) 1 << CONFIG_LED_PIN_G) | ((uint64_t) 1 << CONFIG_LED_PIN_B),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    return gpio_config(&cfg);
}

// to be called before deep sleep
void led_deinit() {
    ESP_LOGI(TAG, "Disabling LEDs");
    gpio_config_t cfg = {
        .pin_bit_mask = ((uint64_t) 1 << CONFIG_LED_PIN_R) | ((uint64_t) 1 << CONFIG_LED_PIN_G) | ((uint64_t) 1 << CONFIG_LED_PIN_B) | ((uint64_t) 1 << 34) | ((uint64_t) 1 << 35),
        .mode = GPIO_MODE_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

void led_set(led_color_t color) {
    ESP_ERROR_CHECK(gpio_set_level(CONFIG_LED_PIN_R, color.r));
    ESP_ERROR_CHECK(gpio_set_level(CONFIG_LED_PIN_G, color.g));
    ESP_ERROR_CHECK(gpio_set_level(CONFIG_LED_PIN_B, color.b));
}

