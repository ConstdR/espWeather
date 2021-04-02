Here we go with weather sensor based on ESP32 SoC.

Board powered by Li-Ion 18650 battery.

BME280 sensor connection: SDA - Pin 21, SCL - Pin 22 (can be configured in espwconst.py)

AP-configuration mode starts automatically, if no config file found or by reset board with lowered Pin 35.
At this mode you can connect to WiFi AP with name like ESP_XXXXX w/o password and set your local WiFi credentials and IP:PORT of the server where to send data.
Time automatically adjusted with NTP server.

Pin 34 reads adc from 220kOm/220kOm devider between + Li-Ion and GND pin.

tWeb.py -- simple web server to store data recieved from ESP32 modules and show current values and history graphs.
Storage format: sqlite3.
Data stored by GET requests from ESP32 with mandatory 'id' param and optinal 't' (temperature), 'h' (humidity), 'p' (pressure),
'v' (voltage), 'm' (message). File name determined by id field 'id'.sqlite3. 'data' table contain columns:
- timedate - UTC time
- ip
- temperature (t)
- humidity (h)
- pressure (p) in hPa
- voltage (v) relative value, must be recalculated to real V. (2420 is near full charge, 1515 -- depleated)
Measurement performs once per 900 seconds (15 min) and most of time ESP spend in deep-sleep mode.

*Hints.*
Using Adafruit MicroPython Tool (ampy)

Put files to ESP32

# ~/.local/bin/ampy -p /dev/ttyUSB0 put boot.py
# ~/.local/bin/ampy -p /dev/ttyUSB0 put ap.py
# ~/.local/bin/ampy -p /dev/ttyUSB0 put main.py
# ~/.local/bin/ampy -p /dev/ttyUSB0 put BME280.py
# ~/.local/bin/ampy -p /dev/ttyUSB0 put espwconst.py

Connect to board on USB:

# screen /dev/ttyUSB0 115200

Run web to get measures (better under screen/tmux):

# cd tWeb
# ./tweb.py -vvvv
