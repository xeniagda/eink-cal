#ifndef eink_display_h_INCLUDED
#define eink_display_h_INCLUDED

#include "esp_err.h"

extern const int DISPLAY_WIDTH;
extern const int DISPLAY_HEIGHT;

typedef enum {
    COLOR_BLACK = 0x0,
    COLOR_WHITE = 0x1,
    COLOR_GREEN = 0x2,
    COLOR_BLUE = 0x3,
    COLOR_RED = 0x4,
    COLOR_YELLOW = 0x5,
    COLOR_ORANGE = 0x6,
} __attribute__ ((__packed__)) color;

// returns ESP_FAIL if the color is not valid to be sent to the eink display
esp_err_t color_validate(color c);

typedef struct {
    int gpio_spi_clk;
    int gpio_spi_mosi;
    int gpio_spi_cs;
    int gpio_spi_dc;
    int gpio_reset;
    int gpio_busy;

    int gpio_en; // connected to MOSFET, active high
} display_config;

// powers the display, sets configuration registers
esp_err_t display_initialize(display_config cfg);

// called to start drawing a frame
void display_begin_frame();
// can be called multiple times, total of all nbytes should be DISPLAY_WIDTH * DISPLAY_HEIGHT
// npixels must be even
void display_send_data(color *pixels, size_t npixels);
// refreshes the display. takes roughly 30 seconds to return
void display_end_frame();

// unpowers the display
void display_turn_off();


#endif // eink_display_h_INCLUDED
