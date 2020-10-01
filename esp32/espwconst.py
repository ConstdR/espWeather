import machine
import ubinascii

MY_ID = str(ubinascii.hexlify(machine.unique_id()), 'utf-8')

AP_PIN = 35 # ground this pin to activate AP mode on reset
CFG_NAME = '_config' # store wifi ssid/pswd and tWeb ip:port
CONNECT_WAIT = 10 # wait seconds to connect
TS_NAME = '_timestamp' # timestamp for ntp
NTP_SYNC_PERIOD = 43200  # 12 hours
LVL_PIN = 34 # 500k/500k to power middle node to check power level
LVL_LOWPWR = 1800 # low power level ~= 3.15V
LED_PIN = 21
DEEP_SLEEP = 60000 # 900000 == 15 min
FAKE_SLEEP = 0 # 1 -- no really go to deep sleep (for debug only)
URL = "http://%s/?id=%s&t=%s&h=%s&p=%s&v=%s&m=%s"
I2CSCL_PIN = 22
I2CSDA_PIN = 23
I2C_FREQ = 10000
