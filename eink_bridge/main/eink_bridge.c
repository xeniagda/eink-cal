#include <stdio.h>
#include <math.h>

#include "esp_err.h"
#include "esp_log.h"
#include "esp_event.h"
#include "esp_random.h"
#include "esp_sleep.h"
#include "driver/gpio.h"

#include "esp_netif.h"
#include "freertos/idf_additions.h"
#include "lwip/inet.h"
#include "nvs_flash.h"

#include "lwip/sockets.h"

#include "led.h"
#include "portmacro.h"
#include "stdint.h"
#include "wifi.h"
#include "wifi_creds.h"
#include "eink_display.h"

static const char *TAG = "eink_bridge";

static const uint64_t SLEEP_TIME_US = 4 * 60 * 60 * 1000000ull; // every 4 hours
static const uint64_t RECONNECT_ATTEMPTS = 5;
static const uint64_t RECONNECT_TIME_MS = 3000;

esp_err_t send_exact(int fd, char *buf, size_t nbytes) {
    while (nbytes > 0) {
        int written = send(fd, buf, nbytes, 0);
        if (written < 0) {
            ESP_LOGE(TAG, "Failed to send: %d", errno);
            return ESP_FAIL;
        }
        nbytes -= written;
        buf += written;
    }
    return ESP_OK;
}

esp_err_t recv_exact(int fd, char *buf, size_t nbytes) {
    while (nbytes > 0) {
        ESP_LOGD("recv_exact", "recving...");
        int recvd = recv(fd, buf, nbytes, 0);
        ESP_LOGD("recv_exact", "got %d bytes", recvd);
        if (recvd < 0) {
            ESP_LOGE(TAG, "Failed to recv: %d", errno);
            return ESP_FAIL;
        }
        if (recvd == 0) {
            ESP_LOGE(TAG, "Connection closed");
            return ESP_FAIL;
        }
        nbytes -= recvd;
        buf += recvd;
    }
    return ESP_OK;
}

float gauss() {
    #define clt_count 10
    float n = 0.;
    for (int i = 0; i < clt_count; i++) {
        // variance 1/12
        float ni = ((float) rand() / (float)RAND_MAX) - 0.5;
        n += ni;
    }
    // n has total variance clt_count/12
    return n / sqrtf(clt_count/12.0);

}

esp_err_t display_fill_pattern() {
    ESP_LOGI(TAG, "Filling display with pattern");

    //color colors = //{ COLOR_BLACK, COLOR_BLUE, COLOR_ORANGE, COLOR_GREEN, COLOR_RED, COLOR_WHITE, COLOR_YELLOW };
    color colors[6] = { COLOR_BLUE, COLOR_GREEN, COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_WHITE };

    const int N_NODES = 40;
    typedef struct {
        float x, y;
        color col1;
        color col2;
    } node;

    node nodes[N_NODES];
    for (int i = 0; i < N_NODES; i++) {
        color col1 = colors[esp_random() % 6];
        color col2 = esp_random() % 2 == 0 ? col1 : colors[rand() % 6];

        nodes[i] = (node) {
            .x = (float) esp_random() / (float)UINT32_MAX * DISPLAY_WIDTH,
            .y = (float) esp_random() / (float)UINT32_MAX * DISPLAY_HEIGHT,
            .col1 = col1,
            .col2 = col2,
        };
    }

    display_begin_frame();

    int block_size = 10000;
    color *current_block = malloc(block_size * sizeof(color));
    int n = 0;

    for (int y = 0; y < DISPLAY_HEIGHT; y++) {
        for (int x = 0; x < DISPLAY_WIDTH; x++) {
            // color col;
            // float xx = x - DISPLAY_WIDTH/2.0;
            // float yy = y - DISPLAY_HEIGHT/2.0;

            // float pi = 3.14159265359;
            // float theta = ((atan2(yy, xx) + pi) / (2 * pi) * 360);
            // theta += gauss() * 360.0/7.0 * 0.3;

            // int ii = (int) (theta * 7 / 360);
            // col = colors[(ii < 0) ? 0 : (ii >= 6) ? 6 : ii];

            float min_dist = INFINITY;
            node *closest;
            node *second_closest;

            for (int i = 0; i < N_NODES; i++) {
                node n = nodes[i];
                float dist = sqrtf((x - n.x) * (x - n.x) + (y - n.y) * (y - n.y));
                if (dist < min_dist) {
                    second_closest = closest;
                    closest = &nodes[i];
                    min_dist = dist;
                }
            }
            // midpoint (lies on line)
            float mx = (closest->x + second_closest->x)/2;
            float my = (closest->y + second_closest->y)/2;

            // vector from p2 to p1 (perpendicular to line)
            float dx = second_closest->x - closest->x;
            float dy = second_closest->y - closest->y;
            // normalize
            float d = sqrtf(dx*dx + dy*dy);
            dx /= d; dy /= d;

            // vector from midpoint to this point
            float ex = x - mx;
            float ey = y - my;

            // project e onto d to get distance from this point to line
            float dist = ex * dx + ey * dy;

            color col = (x + y) % 2 == 0 ? closest->col1 : closest->col2;

            float width_here = 2;// + (float) esp_random() / (float) UINT32_MAX;
            if (dist > -width_here / 2 && dist < width_here / 2) {
                col = COLOR_BLACK;
            }

            current_block[n++] = col;
            if (n == block_size) {
                display_send_data(current_block, n);
                n = 0;
            }
        }
    }
    display_send_data(current_block, n);

    free(current_block);

    ESP_LOGI(TAG, "Sent all data");

    display_end_frame();

    return ESP_OK;
}

void go_to_sleep() {
    ESP_LOGI(TAG, "Entering deep sleep for %" PRIu64 ".%06" PRIu64 " s. Bye!", SLEEP_TIME_US / 1000000, SLEEP_TIME_US % 1000000);

    ESP_LOGV(TAG, "Setting timer");
    esp_sleep_enable_timer_wakeup(SLEEP_TIME_US);

    ESP_LOGV(TAG, "Disabling UART");
    const int UART_TX = 1;
    gpio_config_t cfg = {
        .pin_bit_mask = (uint64_t) 1 << UART_TX,
        .mode = GPIO_MODE_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&cfg));
    // no one can hear us say goodbye :(

    esp_deep_sleep_start();
}

void show_failure() {
    ESP_LOGE(TAG, "FAILURE. Displaying fail pattern");
    led_set(LED_COLOR_RED);
    display_fill_pattern();
    display_turn_off();
    led_deinit();
    go_to_sleep();
}

// led indicator:
// blue: initialized, configuring display
// yellow: connecting to wifi
// blue: connecting to socket
// purple: transferring data
// white: waiting for refresh
// green: done

void app_main(void)
{
    ESP_LOGI(TAG, "initializing");
    ESP_ERROR_CHECK(nvs_flash_init()); // why is this needed?
    ESP_ERROR_CHECK(esp_netif_init()); // to subscribe to wifi events
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(led_init());

    led_set(LED_COLOR_WHITE);

    ESP_LOGI(TAG, "configuring display");
    display_config display_cfg = {
        // rev. 1
        // .gpio_spi_mosi = 17,
        // .gpio_spi_clk = 16,
        // .gpio_spi_cs = 15,
        // .gpio_spi_dc = 14,
        // .gpio_reset = 13,
        // .gpio_busy = 12,

        // .gpio_en = 19,

        // rev. 2
        .gpio_spi_mosi = 17,
        .gpio_spi_clk = 18,
        .gpio_spi_cs = 21,
        .gpio_spi_dc = 13,
        .gpio_reset = 27,
        .gpio_busy = 14,

        .gpio_en = 19,
    };
    ESP_ERROR_CHECK(display_initialize(display_cfg));

    led_set(LED_COLOR_YELLOW);

    ESP_LOGI(TAG, "connecting to wifi");

    start_wifi_cfg wificfg = {
        .hostname = "eink_bridge",
        .ssid = WIFI_SSID,
        .password = WIFI_PASSWORD,
    };
    start_wifi_result wifires;
    if (wifi_connect(&wificfg, &wifires) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to connect to wifi");
        show_failure();
    }

    char ipbuf[20];
    esp_ip4addr_ntoa(&wifires.addr, ipbuf, sizeof ipbuf);
    ESP_LOGI(TAG, "Got DHCP IP: %s", ipbuf);

    led_set(LED_COLOR_GREEN);

    // set up socket
    struct sockaddr addr;
    struct sockaddr_in *addr_in = (struct sockaddr_in *) &addr; // is this UB?
    addr_in->sin_family = AF_INET;
    addr_in->sin_port = htons(REMOTE_PORT);
    addr_in->sin_addr.s_addr = esp_ip4addr_aton(REMOTE_IP);

    int socket_fd = -1;
    for (int i = 1; i <= RECONNECT_ATTEMPTS; i++) {
        ESP_LOGI(TAG, "Connect attempt %i", i);
        socket_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
        if (socket_fd < 0) {
            ESP_LOGE(TAG, "Unable to create socket: errno %d", errno);
            show_failure();
        }
        ESP_LOGI(TAG, "Socket created. Connecting to IP %s", REMOTE_IP);
        if (connect(socket_fd, &addr, sizeof addr) < 0) {
            ESP_LOGE(TAG, "Unable to bind to socket: errno %d", errno);
            if (i == RECONNECT_ATTEMPTS) {
                ESP_LOGE(TAG, "Giving up connecting. Drawing pattern and quitting");
                show_failure();
            }
            vTaskDelay(RECONNECT_TIME_MS / portTICK_PERIOD_MS);
            close(socket_fd);
        } else {
            break;
        }
    }
    ESP_LOGI(TAG, "Connected. Sending handshake");

    ESP_ERROR_CHECK(send_exact(socket_fd, "hii^_^", 6));

    ESP_LOGI(TAG, "Receiving handshake");
    char buf[5];
    ESP_ERROR_CHECK(recv_exact(socket_fd, buf, 5));
    if (strncmp(buf, "hewwo", 5) != 0) {
        esp_system_abort("Incorrect handshake!");
        show_failure();
    }
    ESP_LOGI(TAG, "Hand shaken");

    led_set(LED_COLOR_TEAL);

    #define TRANSACTION_SIZE (800 / 2 * 20)
    color *cols = malloc(TRANSACTION_SIZE);
    display_begin_frame();
    ESP_LOGI(TAG, "Streaming data to screen");
    for (int i = 0; i < DISPLAY_HEIGHT * DISPLAY_WIDTH; i += TRANSACTION_SIZE) {
        ESP_ERROR_CHECK(recv_exact(socket_fd, (char*) cols, TRANSACTION_SIZE));
        display_send_data(cols, TRANSACTION_SIZE);
    }
    ESP_LOGI(TAG, "Closing socket");
    close(socket_fd);
    ESP_LOGI(TAG, "Done. Refreshing screen");
    // led_set(LED_COLOR_WHITE);
    display_end_frame();
    free(cols);

    ESP_LOGI(TAG, "Unpowering screen");
    display_turn_off();
    led_deinit();

    go_to_sleep();
}
