Here we go with weather sensor based on ESP32 SoC.

Board powered by Li-Ion 18650 battery on 3.3V pin.

DHT11 sensor powered by Pin 12, data reading from Pin 32.

AP-configuration mode starts automatically, if no config file found or by reset board with lowered Pin 15. 
At this mode you can connect to WiFi AP with name like ESP_XXXXX w/o password and set your local WiFi credentials and IP:PORT of the server where to send data.

tWeb.py -- simple web server to store data recieved from ESP32 modules. Format: CSV. GET requests expected with mandatory 'id' param. File name determined by id field. Columns are:
- UTC time
- IP
- temperature (t param from GET)
- humidity (h param from GET)


*Hints.*
Using Adafruit MicroPython Tool (ampy)

Put files to ESP32

# ~/.local/bin/ampy -p /dev/ttyUSB0 put boot.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put ap.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put main.py 

Connect to board on USB:

# screen /dev/ttyUSB0 115200

Run web to get measures (better under screen/tmux):

# cd tWeb
# ./tweb.py -vvvv
