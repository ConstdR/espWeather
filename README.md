
Put files to ESP32

# ~/.local/bin/ampy -p /dev/ttyUSB0 put boot.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put ap.py 
# ~/.local/bin/ampy -p /dev/ttyUSB0 put main.py 

Connect to board on USB:

# screen /dev/ttyUSB0 115200

Run web to get measures (better under screen/tmux):

# cd tWeb
# ./tweb.py -vvvv
