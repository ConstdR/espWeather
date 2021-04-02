import machine
import ubinascii

MY_ID = str(ubinascii.hexlify(machine.unique_id()), 'utf-8')

AP_PIN = 35 # ground this pin to activate AP mode on reset
CFG_NAME = '_config' # store wifi ssid/pswd and tWeb ip:port
TS_NAME = '_timestamp' # timestamp for ntp
DATA_FILE = '_data' # measuring storage
DATA_LENGTH = 128 # number of records to store
CONNECT_WAIT = 10 # wait seconds to connect
NTP_SYNC_PERIOD = 10800 # 3 hours
LVL_PIN = 34 # 500k/500k to power middle node to check power level
LVL_LOWPWR = 1880 # low power level ~= 3.15V
LED_PIN = 5
DEEP_SLEEP = 900000 # 900000 == 15 min
FAKE_SLEEP = 0 # 1 -- no really go to deep sleep (for debug only)
I2CSCL_PIN = 22
I2CSDA_PIN = 21
I2C_FREQ = 10000
