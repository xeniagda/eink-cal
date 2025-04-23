#include <stdio.h>

#include "esp_log.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/spi_common.h"
#include "driver/spi_master.h"
#include "portmacro.h"

#include "eink_display.h"

static const char *TAG = "eink_display";
const int DISPLAY_WIDTH = 800;
const int DISPLAY_HEIGHT = 480;

esp_err_t color_validate(color c) {
    if (c < COLOR_BLACK || c > COLOR_ORANGE) {
        return ESP_FAIL;
    }
    return ESP_OK;
}

display_config active_display_cfg;
spi_device_handle_t spi_handle;

#define USER_DC_CMD ((void*) 0xCD)
#define USER_DC_DATA ((void*) 0xDA)


// NOTE: data must point to memory allocated with dma caps
esp_err_t send_data(uint8_t *data, size_t ndata) {
    if (ndata > 0) {
        gpio_set_level(active_display_cfg.gpio_spi_dc, 1);
        spi_transaction_t data_transaction = {
            .cmd = 0,
            .length = 8 * ndata,
            .tx_buffer = data,
        };

        ESP_ERROR_CHECK(spi_device_transmit(spi_handle, &data_transaction));
    }
    return ESP_OK;
}

// NOTE: data must point to memory allocated with dma capability
esp_err_t send_cmd(uint8_t command, uint8_t *data, size_t ndata) {
    ESP_LOGD(TAG, "Sending command 0x%02x with %d bytes data", command, ndata);

    gpio_set_level(active_display_cfg.gpio_spi_dc, 0);
    spi_transaction_t cmd_transaction = {
        .cmd = 0,
        .length = 8,
        .tx_buffer = &command,
    };

    ESP_ERROR_CHECK(spi_device_transmit(spi_handle, &cmd_transaction));

    send_data(data, ndata);

    return ESP_OK;
}

// TODO: Maybe don't do this polling?
void wait_until_not_busy() {
    ESP_LOGV(TAG, "Waiting for display to not be busy");
    int n = 0;
    while (gpio_get_level(active_display_cfg.gpio_busy) == 0) {
        vTaskDelay(1);
        n++;
        if (n == 1) {
            ESP_LOGD(TAG, "Waiting for display to not be busy");
        }
    }
    if (n >= 1) {
        ESP_LOGD(TAG, "Display unbusy in %d ticks", n);
    } else {
        ESP_LOGV(TAG, "Display unbusy in %d ticks", n);
    }
}

void send_startup_sequence();
void refresh();

const int TRANSACTION_SIZE = 800 / 2 * 20; // 20 rows, 24 tranactions to fill screen

esp_err_t display_initialize(display_config cfg) {
    active_display_cfg = cfg;

    ESP_LOGI(TAG, "initializing gpio");
    // initialize gpio
    gpio_config_t gpio_cfg_output = {
        .pin_bit_mask = (1 << cfg.gpio_spi_clk) | (1 << cfg.gpio_spi_dc) | (1 << cfg.gpio_spi_mosi) | (1 << cfg.gpio_spi_cs) | (1 << cfg.gpio_reset) | (1 << cfg.gpio_en),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };

    ESP_ERROR_CHECK(gpio_config(&gpio_cfg_output));
    gpio_config_t gpio_cfg_input = {
        .pin_bit_mask = 1 << cfg.gpio_busy,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&gpio_cfg_input));

    ESP_LOGI(TAG, "powering display");
    ESP_ERROR_CHECK(gpio_set_level(cfg.gpio_en, 1));

    ESP_LOGI(TAG, "gpio done. initilazing spi bus");

    spi_bus_config_t spi_cfg = {
        .mosi_io_num = cfg.gpio_spi_mosi,
        .sclk_io_num = cfg.gpio_spi_clk,
        .max_transfer_sz = TRANSACTION_SIZE,
        .isr_cpu_id = ESP_INTR_CPU_AFFINITY_AUTO,

        .flags = SPICOMMON_BUSFLAG_MASTER,

        .miso_io_num = -1,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
    };

    ESP_ERROR_CHECK(spi_bus_initialize(
        SPI2_HOST,
        &spi_cfg,
        SPI_DMA_CH_AUTO
    ));

    ESP_LOGI(TAG, "spi bus done. initilazing spi device");
    spi_device_interface_config_t dev_cfg = {
        .command_bits = 0,
        .address_bits = 0,
        .dummy_bits = 0,
        .mode = 0,
        .clock_source = SPI_CLK_SRC_DEFAULT,
        .clock_speed_hz = 16000000,
        .spics_io_num = cfg.gpio_spi_cs,
        .queue_size = 1,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &dev_cfg, &spi_handle));

    ESP_LOGI(TAG, "initialize done. sending reset signal");

    gpio_set_level(cfg.gpio_reset, 1);
    vTaskDelay(10 / portTICK_PERIOD_MS);
    gpio_set_level(cfg.gpio_reset, 0);
    vTaskDelay(10 / portTICK_PERIOD_MS);
    gpio_set_level(cfg.gpio_reset, 1);
    vTaskDelay(10 / portTICK_PERIOD_MS);

    wait_until_not_busy();
    ESP_LOGI(TAG, "sent reset signal. configuring display ");

    send_startup_sequence();

    ESP_LOGI(TAG, "display configured. refreshing");

    // refresh();

    ESP_LOGI(TAG, "finished.");
    return ESP_OK;
}

void send_startup_sequence() {
    // uint8_t buffer[24];
    uint8_t *buffer = heap_caps_malloc(24, MALLOC_CAP_DMA);

    // commands stolen from rpi python library
    buffer[0] = 0x49;
    buffer[1] = 0x55;
    buffer[2] = 0x20;
    buffer[3] = 0x08;
    buffer[4] = 0x09;
    buffer[5] = 0x18;
    send_cmd(0xAA, buffer, 6);

    buffer[0] = 0x3F;
    buffer[1] = 0x00;
    buffer[2] = 0x32;
    buffer[3] = 0x2A;
    buffer[4] = 0x0E;
    buffer[5] = 0x2A;
    send_cmd(0x01, buffer, 6);

    buffer[0] = 0x5F;
    buffer[1] = 0x69;
    send_cmd(0x00, buffer, 2);

    buffer[0] = 0x00;
    buffer[1] = 0x54;
    buffer[2] = 0x00;
    buffer[3] = 0x44;
    send_cmd(0x03, buffer, 4);

    buffer[0] = 0x40;
    buffer[1] = 0x1F;
    buffer[2] = 0x1F;
    buffer[3] = 0x2C;
    send_cmd(0x05, buffer, 4);

    buffer[0] = 0x6F;
    buffer[1] = 0x1F;
    buffer[2] = 0x1F;
    buffer[3] = 0x22;
    send_cmd(0x06, buffer, 4);

    buffer[0] = 0x6F;
    buffer[1] = 0x1F;
    buffer[2] = 0x1F;
    buffer[3] = 0x22;
    send_cmd(0x08, buffer, 4);

    buffer[0] = 0x00;
    buffer[1] = 0x04;
    send_cmd(0x13, buffer, 2);

    buffer[0] = 0x3C;
    send_cmd(0x30, buffer, 1);

    buffer[0] = 0x00;
    send_cmd(0x41, buffer, 1);

    // first nibble controls the border color, but also shifts the colormap?
    // 3 is default
    // second nibble seems to do nothing?
    buffer[0] = 0x3F;
    send_cmd(0x50, buffer, 1); // border color?

    buffer[0] = 0x02;
    buffer[1] = 0x00;
    send_cmd(0x60, buffer, 2);

    buffer[0] = 0x03;
    buffer[1] = 0x20;
    buffer[2] = 0x01;
    buffer[3] = 0xE0;
    send_cmd(0x61, buffer, 4);

    buffer[0] = 0x1E;
    send_cmd(0x82, buffer, 1);

    buffer[0] = 0x00;
    send_cmd(0x84, buffer, 1);

    buffer[0] = 0x00;
    send_cmd(0x86, buffer, 1);

    buffer[0] = 0x2F;
    send_cmd(0xE3, buffer, 1);

    buffer[0] = 0x00;
    send_cmd(0xE0, buffer, 1);

    buffer[0] = 0x00;
    send_cmd(0xE6, buffer, 1);

    free(buffer);
}

uint8_t *pixel_buffer;
void display_begin_frame() {
    ESP_LOGI(TAG, "beginning frame");
    send_cmd(0x10, NULL, 0);
    pixel_buffer = heap_caps_malloc(TRANSACTION_SIZE, MALLOC_CAP_DMA);
}

void display_send_data(color *pixels, size_t npixels) {
    ESP_LOGD(TAG, "Sending %d pixels to screen", npixels);

    while (npixels > 0) {
        // two pixels = one byte
        int nbytes = npixels / 2;
        if (nbytes > TRANSACTION_SIZE)
            nbytes = TRANSACTION_SIZE;
        // grab 2*nbytes pixels from the array
        for (int i = 0; i < nbytes; i++) {
            pixel_buffer[i] = pixels[2*i] << 4 | pixels[2*i+1];
        }
        // send the bytes
        send_data(pixel_buffer, nbytes);
        // step forward the pixels array
        pixels += nbytes * 2;
        npixels -= nbytes * 2;
    }
}

void display_end_frame() {
    ESP_LOGI(TAG, "refreshing");
    uint8_t *cmd_buffer = heap_caps_malloc(24, MALLOC_CAP_DMA);

    send_cmd(0x04, cmd_buffer, 0); // power on
    wait_until_not_busy();

    cmd_buffer[0] = 0;
    send_cmd(0x12, cmd_buffer, 1); // display refresh
    wait_until_not_busy();

    cmd_buffer[0] = 0;
    send_cmd(0x02, cmd_buffer, 0); // power off
    wait_until_not_busy();

    free(cmd_buffer);

    free(pixel_buffer);
}

void display_turn_off() {
    ESP_LOGI(TAG, "unpowering display");
    gpio_set_level(active_display_cfg.gpio_en, 0);
}

