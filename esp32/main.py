import BME280
import machine
import time
import urequests

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
        message = 'WakeReason:%s' % machine.wake_reason() + ( ' ' + msg if msg else '' )
        dat = update_data([t, h, p, v, message])
        try:
            print("Post my_id: %s Length:%s" % (MY_ID, len(dat)))
            res = urequests.post('http://%s/id/%s' % (get_hostport(), MY_ID), 
                                json={'measures':dat})
        except Exception as e:
            print("POST exception: %s" % str(e))

        print('Deepsleep for %s sec.' % str(DEEP_SLEEP/1000))
        if FAKE_SLEEP :
            sleeptime = float(DEEP_SLEEP/100000)
            print("Fake sleep for %s" % sleeptime)
            blink() # bells and whistles
            time.sleep(sleeptime)
        else:
            wdt.feed()
            machine.deepsleep(DEEP_SLEEP)

def update_data(d):
    open(DATA_FILE, 'a').close()
    data = [line.strip() for line in open(DATA_FILE, 'r')]
    tstump = '%s-%.2d-%.2d %.2d:%.2d:%.2d' % time.localtime()[0:6]
    print("Timestamp: %s" % tstump)
    d.insert(0, tstump)
    s = ','.join([str(e) for e in d ])
    data.append(s)
    if len(data) > DATA_LENGTH:
        data.pop(0)
    with open(DATA_FILE,'w') as f:
        f.write('\n'.join(data))
    return data

def measure(res = [0, 0, 0, 0, '']):
    try:
        lvlpin = machine.ADC(machine.Pin(LVL_PIN))
        lvlpin.width(lvlpin.WIDTH_12BIT)
        lvlpin.atten(lvlpin.ATTN_11DB)
        res[3] = adc_read(lvlpin)
        res[4] = 'Low power.' if res[3] < LVL_LOWPWR else ''
        i2c = machine.I2C(scl=machine.Pin(I2CSCL_PIN), sda=machine.Pin(I2CSDA_PIN), freq=I2C_FREQ)
        bme = BME280.BME280(i2c=i2c)
        res = (bme.temperature, bme.humidity, bme.pressure, res[3], res[4])
    except Exception as e:
        res[4]= res[4] + "Measuring Error."
        print("Measurin Error: %s" % str(e))
    print("Measuring: %s" % str(res))
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
        time.sleep(.2)

main()
