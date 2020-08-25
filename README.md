Here we go with weather sensor based on ESP32 SoC.

Board powered by Li-Ion 18650 battery on 3.3V pin.

BME280 sensor connection: SDA - Pin 23, SCL - Pin 22

AP-configuration mode starts automatically, if no config file found or by reset board with lowered Pin 15. 
At this mode you can connect to WiFi AP with name like ESP_XXXXX w/o password and set your local WiFi credentials and IP:PORT of the server where to send data.

Pin 34 reads adc from 470kOm/470kOm devider between 3.3V and GND pin.

tWeb.py -- simple web server to store data recieved from ESP32 modules. Format: CSV. GET requests expected with mandatory 'id' param. File name determined by id field. Columns are:
- UTC time
- IP
- temperature (t)
- humidity (h)
- pressure (p) in hPa-950
- Battery (v) relative value, must be recalculated


*Hints.*
Using Adafruit MicroPython Tool (ampy)

Put files to ESP32

# ~/.local/bin/ampy -p /dev/ttyUSB0 put boot.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put ap.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put main.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put BME280.py 

Connect to board on USB:

# screen /dev/ttyUSB0 115200

Run web to get measures (better under screen/tmux):

# cd tWeb
# ./tweb.py -vvvv
