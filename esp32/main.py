import BME280
import machine
import time
import urequests
import gc

from espwconst import *

pled = machine.Pin(LED_PIN)
led = machine.PWM(pled, freq=50, duty=0)

def main():
    if FAKE_SLEEP:
        print("No watchdog")
    else:
        wdt = machine.WDT(timeout=int(DEEP_SLEEP+DEEP_SLEEP/2))
    while True:
        (t, h, p, v, msg) = measure()
        message = 'WakeReason:%s' % machine.wake_reason() + ( ',' + msg if msg else '' ) 
        url = URL % (get_hostport(), MY_ID, t, h, p, v, message)
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
        if FAKE_SLEEP :
            sleeptime = float(DEEP_SLEEP/100000)
            print("Fake sleep for %s" % sleeptime)
            blink() # bells and whistles
            time.sleep(sleeptime)
        else:
            wdt.feed()
            machine.deepsleep(DEEP_SLEEP)
        blink() # bells and whistles

def measure(res = [0, 0, 0, 0, '']):
    try:
        i2c = machine.I2C(scl=machine.Pin(I2CSCL_PIN), sda=machine.Pin(I2CSDA_PIN), freq=I2C_FREQ)
        bme = BME280.BME280(i2c=i2c)
        lvlpin = machine.ADC(machine.Pin(LVL_PIN))
        lvlpin.width(lvlpin.WIDTH_12BIT)
        lvlpin.atten(lvlpin.ATTN_11DB)
        lvl = adc_read(lvlpin)
        msg = 'Low power.' if lvl < LVL_LOWPWR else ''
        res = (bme.temperature, bme.humidity, bme.pressure, adc_read(lvlpin), msg)
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
