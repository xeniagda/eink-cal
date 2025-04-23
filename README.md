# eink-cal

e-ink calendar based on the *esp32-wroom32* and the waveshare *7.3inch e-Paper HAT (F)*

## file structure

* `./bridge_pcb/`: kicad project for the PCB
* `./eink_bridge/`: esp32-idf project for the WiFi-controller for the display
* `./case.FCStd`: freecad project modelling the 3d-printable chassis for the project
* `./cal_render/`: python code to render the calendar

## needed files

the file `./eink_bridge/main/wifi_creds.h` should be filled in with the following

```c

#ifndef wifi_creds_h_INCLUDED
#define wifi_creds_h_INCLUDED


#define WIFI_SSID "WIFI network SSID here"
#define WIFI_PASSWORD "WIFI network password"
static const char *REMOTE_IP = "IP of computer running cal_render";
static const int REMOTE_PORT = port of the above;

#endif // wifi_creds_h_INCLUDED
```

the file `./cal_render/secrets.toml` contains all calendars to be shown

```toml
[[calendar]]
# hemma
is_caldav = true # true for caldav, false for ical/http
username = "caldav username"
password = "caldav password"
url = "caldav URL"
color1 = "primary color" # one of BLACK, WHITE, BLUE, ORANGE, GREEN, RED, PURPLE
color2 = "secondary color"
```

## credits

font packaged and used is [ultlf](https://github.com/ultlang/ultlf) by emma ultlang. all parts of `./cal_render/ultlf` are re-released under the same SIL open font license.
