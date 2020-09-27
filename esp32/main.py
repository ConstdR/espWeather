import BME280
import machine
import time
import urequests
import gc

URL = "http://%s/?id=%s&t=%s&h=%s&p=%s&v=%s&m=%s"

myID = int.from_bytes(machine.unique_id(), 'big') # 'little' is more correct :)

CFG_NAME = '_config'
pled = machine.Pin(21)
led = machine.PWM(pled, freq=50, duty=0)

lvlpin = machine.ADC(machine.Pin(34))
MEASURE_COUNT = 1
MEASURE_TIMEOUT = 1
DEEP_SLEEP = 900000 # 900000 == 15 min
FAKE_SLEEP = 0 # 1 -- no really go to deep sleep

def main():
    wdt = machine.WDT(timeout=int(DEEP_SLEEP+DEEP_SLEEP/2))
    while True:
        (t, h, p, v, msg) = measure()
        message = 'WakeReason:%s' % machine.wake_reason() + ( ',' + msg if msg else '' ) 
        url = URL % (get_hostport(), myID, t, h, p, v, message)
        print("Get: %s" % url)
        try:
            res = urequests.get(url)
            print(res.text)
        except Exception as e:
            print("Exception: %s" % (e))
            pass
        blink() # bells and whistles
        print('Deepsleep for %s sec.' % str(DEEP_SLEEP/1000))
        gc.collect()
        wdt.feed()
        if FAKE_SLEEP :
            print("Fake sleep")
            blink() # bells and whistles
            time.sleep(DEEP_SLEEP/1000 - 3)
        else:
            machine.deepsleep(DEEP_SLEEP)
        blink() # bells and whistles

def measure(res = [0, 0, 0, 0, '']):
    try:
        i2c = machine.I2C(scl=Pin(22), sda=Pin(23), freq=10000)
        bme = BME280.BME280(i2c=i2c)
        lvlpin.width(lvlpin.WIDTH_12BIT)
        lvlpin.atten(lvlpin.ATTN_11DB)
        res = ( bme.temperature, bme.humidity, bme.pressure, adc_read(lvlpin), '')
        print("Measuring: %s", res)
    except Exception as e:
        res[4]="MeasuringError"
        print(str(e))
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
    for i in range(6):
        led.duty(20) if led.duty() == 0 else led.duty(0)
        time.sleep(.5)

main()
