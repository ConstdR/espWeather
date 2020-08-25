import BME280
import machine
import time
import urequests

URL = "http://%s/?id=%s&t=%s&h=%s&p=%s&v=%s"

myID = int.from_bytes(machine.unique_id(), 'big') # 'little' is more correct :)

CFG_NAME = '_config'
led = machine.Pin(21, machine.Pin.OUT)

i2c = machine.I2C(scl=Pin(22), sda=Pin(23), freq=10000)
bme = BME280.BME280(i2c=i2c)

lvlpin = machine.ADC(machine.Pin(34))
MEASURE_COUNT = 1
MEASURE_TIMEOUT = 1
DEEP_SLEEP = 900000 # 900000 == 15 min

def main():
    while True:
        (t, h, p, v) = measure()
        url = URL % (get_hostport(), myID, t, h, p, v)
        print("Get: %s" % url)
        try:
            res = urequests.get(url)
            print(res.text)
        except Exception as e:
            print("Exception: %s" % (e))
            pass
#        blink() # bells and whistles
        print('Deepsleep for %s sec.' % str(DEEP_SLEEP/1000))
        machine.deepsleep(DEEP_SLEEP)

def measure(res = [0, 0, 0, 0]):
    try:
        lvlpin.width(lvlpin.WIDTH_12BIT)
        lvlpin.atten(lvlpin.ATTN_11DB)
        res = ( bme.temperature, bme.humidity, bme.pressure - 950,
                adc_read(lvlpin) / 100.0 )
        print("Measuring: %s", res)
    except Exception as e:
        print("Measuring error: %s" % e)
    return res

def adc_read(adc):
    # damn stupid averaging adc reading
    count = 5
    val = 0
    for i in range(count):
        val += adc.read()
    return val/count

def get_hostport():
    hostport = None
    try:
        fh = open(CFG_NAME)
        fh.readline() # skip essid
        fh.readline() # skip pswd
        hostport = fh.readline().strip()
        fh.close()
    except Exception as e:
        print("Error getting hostport: %s" % e)
    return hostport

def blink():
    for i in range(5):
        led.value( not led.value())
        time.sleep(.5)

main()
