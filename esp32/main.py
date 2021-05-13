import BME280
import machine
import time
import urequests
from math import cos,pi

from espwconst import *

az_pin = machine.Pin(AZ_PIN, machine.Pin.OUT)
paz =  machine.PWM(az_pin, freq=50)
paz.init() #duty=round((AZ_MAX+AZ_MIN)/2))

alt_pin = machine.Pin(ALT_PIN, machine.Pin.OUT)
palt =  machine.PWM(alt_pin, freq=50)
palt.init() #duty=round((ALT_MAX+ALT_MIN)/2))

tz = TZ
longitude = ALT_LONGITUDE

hostport = None

dom = (9, 40, 68, 99, 129, 160, 190, 221, 252, 282, 313, 343)

hours = 0

def run():
    global hours
    if FAKE_SLEEP:
        print("No watchdog")
    else:
        wdt = machine.WDT(timeout=int(DEEP_SLEEP+DEEP_SLEEP/2))
    while True:
        (t, h, p, v, vs, msg) = measure()
        tt = time.gmtime()
        hours = tt[3] + tt[4] * (1/60) + tz
        az = azimuth()
        alt = altitude()
        print("HOSTPORT: %s TZ: %s LONGITUDE: %s" % (hostport, tz, longitude))
        msg = msg + ( ' AZ:%s' % az )  + (' ALT:%s' % alt)
        message = 'WakeReason:%s' % machine.wake_reason() + ( msg if msg else '' )
        dat = update_data([t, h, p, v, vs, message])
        try:
            print("Post my_id: %s Length:%s" % (MY_ID, len(dat)))
            res = urequests.post('http://%s/id/%s' % (hostport, MY_ID), 
                                json={'measures':dat})
        except Exception as e:
            print("POST exception: %s" % str(e))

        if FAKE_SLEEP :
            sleeptime = float(DEEP_SLEEP/10000)
            print("Fake sleep for %s sec" % sleeptime)
            time.sleep(sleeptime)
        else:
            print('Deepsleep for %s sec.' % str(DEEP_SLEEP/1000))
            wdt.feed()
            machine.deepsleep(DEEP_SLEEP)
        print()

def altitude():
    print("Altitude: ", end="")
    # duty = round(max_alt())
    # duty = round(alt_var())
    duty = round(alt_cos())
    print(duty)
    if hours > 3 and hours < 21:
        palt.deinit()
        palt.init(duty=duty)
        time.sleep(1)
    else:
        print("No ALT")
    return duty

def alt_var():
    duty = ALT_MIN
    alt_max = max_alt()
    fraction = (alt_max-ALT_MIN)/6
    if hours > 6 and hours < 18:
        if hours < 12:
            duty = (hours-6) * fraction + ALT_MIN
        elif hours > 12:
            duty = alt_max - (hours - 12) * fraction
    if hours < 4 or hours > 20:
        duty = max_alt()
    return duty

def alt_cos():
    duty = ALT_MIN
    alt_max = max_alt()
    if hours > 4 and hours < 20:
        delta = (alt_max-ALT_MIN)/2
        duty = delta*cos(pi/8*(hours+4))+delta+ALT_MIN
    if hours < 4 or hours > 20:
        duty = max_alt()
    return duty

def max_alt():
    (month, day) = time.gmtime()[1:3]
    d = dom[month - 1] + day
    a = longitude - 11.75
    x = (ALT_MAX - ALT_MIN) / 90
    if d >= 183: d = 366 - d
    a = d*23.5/183+a
    return a*x + ALT_MIN
 
def azimuth():
    print("Azimuth: ", end='')
    duty = round( ( 6 - (hours)) * AZ_DUTYPERHOUR ) + AZ_MAX
    if duty < PWMMIN:
        print("PWMMIN :", end="")
        duty=PWMMIN
    elif duty > PWMMAX :
        print("PWMMAX :", end="")
        duty=PWMMAX
    if hours < 4 or hours > 20:
        duty = round((PWMMIN+PWMMAX)/2)
    print(duty)
    if hours > 3 and hours < 21:
        paz.deinit()
        paz.init(duty=duty)
        time.sleep(1) # TODO: calculate sleep time by duty difference, but 1 sec seems to be fine
    else:
        print("No AZ")
    return duty

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

def measure(res = [0, 0, 0, 0, 0, '']):
    try:
        lvlpin = machine.ADC(machine.Pin(LVL_PIN))
        lvlpin.width(lvlpin.WIDTH_12BIT)
        lvlpin.atten(lvlpin.ATTN_11DB)
        res[3] = adc_read(lvlpin)
        lvlspin = machine.ADC(machine.Pin(LVL_SUNPIN))
        lvlspin.width(lvlpin.WIDTH_12BIT)
        lvlspin.atten(lvlpin.ATTN_11DB)
        res[4] = adc_read(lvlspin)
        res[5] = 'Low power.' if res[3] < LVL_LOWPWR else ''
        i2c = machine.SoftI2C(scl=machine.Pin(I2CSCL_PIN), sda=machine.Pin(I2CSDA_PIN), freq=I2C_FREQ)
        bme = BME280.BME280(i2c=i2c)
        res = (bme.temperature, bme.humidity, bme.pressure, res[3], res[4], res[5])
    except Exception as e:
        res[5]= res[5] + "Measuring Error."
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

def get_config():
    global hostport, tz, longitude
    try:
        fh = open(CFG_NAME, 'r')
        fh.readline() # skip essid
        fh.readline() # skip pswd
        hostport = fh.readline().strip()
        tz = float(fh.readline().strip())
        longitude = float(fh.readline().strip())
        if tz == '': tz=TZ
        if longitude == '' : longitude=ALT_LONGITUDE
        fh.close()
    except Exception as e:
        print("Error getting config: %s" % e)

if __name__ == '__main__':
    get_config()
    run()
