#ifndef led_h_INCLUDED
#define led_h_INCLUDED

typedef struct {
    uint32_t r, g, b;
} led_color_t;

extern const led_color_t LED_COLOR_RED;
extern const led_color_t LED_COLOR_YELLOW;
extern const led_color_t LED_COLOR_GREEN;
extern const led_color_t LED_COLOR_TEAL;
extern const led_color_t LED_COLOR_BLUE;
extern const led_color_t LED_COLOR_PURPLE;
extern const led_color_t LED_COLOR_WHITE;

esp_err_t led_init();
void led_deinit();
void led_set(led_color_t color);

#endif // led_h_INCLUDED
