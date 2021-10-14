import BME280
import machine
import time
import urequests
from math import cos,pi

from espwconst import *

tz = TZ
longitude = ALT_LONGITUDE

hostport = None

dom = (9, 40, 68, 99, 129, 160, 190, 221, 252, 282, 313, 343)

hours = 0

az_pin = machine.Pin(AZ_PIN, machine.Pin.OUT)
paz =  machine.PWM(az_pin, freq=50)
paz.init() #duty=round((AZ_MAX+AZ_MIN)/2))

alt_pin = machine.Pin(ALT_PIN, machine.Pin.OUT)
palt =  machine.PWM(alt_pin, freq=50)
palt.init() #duty=round((ALT_MAX+ALT_MIN)/2))

lvlpin = machine.ADC(machine.Pin(LVL_PIN))
lvlpin.width(lvlpin.WIDTH_12BIT)
lvlpin.atten(lvlpin.ATTN_11DB)

lvlspin = machine.ADC(machine.Pin(LVL_SUNPIN))
lvlspin.width(lvlspin.WIDTH_12BIT)
lvlspin.atten(lvlspin.ATTN_11DB)


def run():
    global hours
    if FAKE_SLEEP:
        print("No watchdog")
    else:
        wdt = machine.WDT(timeout=int(DEEP_SLEEP+DEEP_SLEEP/2))
    while True:
        tt = time.gmtime()
        hours = tt[3] + tt[4] * (1/60) + tz
        if hours>4 and hours<20:
            if POSITIONING == 'SCAN':
                scan()
            elif POSITIONING == 'ADOPT':
                az = az_adopt()
                time.sleep(1)
                alt = altitude()
                time.sleep(1)
            else:
                az = azimuth()
                time.sleep(1)
                alt = altitude()
                time.sleep(1)
        (t, h, p, v, vs, msg) = measure()
        print("HOSTPORT: %s TZ: %s LONGITUDE: %s" % (hostport, tz, longitude))
        msg = msg + ( ' AZ:%s' % paz.duty() )  + (' ALT:%s' % palt.duty())
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
    global palt
    print("Altitude: ", end="")
    # duty = round(max_alt())
    # duty = round(alt_var())
    duty = round(alt_cos())
    print(duty)
    if hours > 3 and hours < 21:
        palt.duty(duty)
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
    global paz
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
        paz.duty(duty)
        time.sleep(1)
    else:
        print("No AZ")
    return duty

def az_adopt():
    global paz
    print("Azimuth adoptive", end='')
    d=round((AZ_MAX+AZ_MIN)/2)
    try:
        d=int(open("_az", "r").read())
        print(" read:%s"%d, end='')
    except: print(" default", end='')
    paz.duty(d)
    print(" duty: %s" % d)
    olvl=lvl=adc_read(lvlspin)
    count=0
    direction=1
    while True:
        d+=direction
        if d>AZ_MAX: d=AZ_MAX
        if d<AZ_MIN: d=AZ_MIN
        paz.duty(d)
        time.sleep(1)
        lvl=adc_read(lvlspin)
        if lvl<olvl:
            direction=-direction
        olvl=lvl
        count+=1
        print(" Count:%s Delta: %s"%(count, olvl-lvl))
        if (olvl == lvl and lvl > 0 )or count > 10 : break
    try:
        f=open("_az",'w')
        f.write("%s"%d)
        f.close()
    except Exception as e: print("Error: %s" % str(e))
    return d

def scan():
    global paz, palt
    paz.duty(AZ_MIN)
    palt.duty(round((ALT_MAX+ALT_MIN)/2))
    time.sleep(1)

    r = range(AZ_MIN, AZ_MAX+1, round((AZ_MAX+AZ_MIN)/110))
    max_lvl = 0
    max_az = AZ_MIN
    for a in r:
        paz.duty(a)
        time.sleep(.2)
        lvl=adc_read(lvlspin)
        if lvl > max_lvl:
            max_lvl=lvl
            max_az =a
        print("%s,%s" % (a,lvl))
    print("AZ max lvl: %s,%s" % (max_az,max_lvl))
    paz.duty(max_az)

    r = range(ALT_MIN, ALT_MAX+1, round((ALT_MAX+ALT_MIN)/50))
    max_lvl = 0
    max_alt = ALT_MIN
    for a in r:
        palt.duty(a)
        time.sleep(.2)
        lvl=adc_read(lvlspin)
        if lvl > max_lvl:
            max_lvl=lvl
            max_alt =a
        print("%s,%s" % (a,lvl))
    print("ALT max lvl: %s,%s" % (max_alt,max_lvl))
    palt.duty(max_alt)

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
        res[3] = adc_read(lvlpin)
        res[4] = adc_read(lvlspin)
        res[5] = 'Low power.' if res[3] < LVL_LOWPWR else ''
        i2c = machine.SoftI2C(scl=machine.Pin(I2CSCL_PIN), sda=machine.Pin(I2CSDA_PIN), freq=I2C_FREQ)
        bme = BME280.BME280(i2c=i2c)
        res = (bme.temperature, bme.humidity, bme.pressure, res[3], res[4], res[5])
        print("Measuring: %s" % str(res))
    except Exception as e:
        res[5]= res[5] + " Measuring Error."
        print("Measurin Error: %s" % str(e))
    return res

def adc_read(adc):
    # damn stupid averaging adc reading
    count = 5
    val = 0
    for i in range(count):
        val += adc.read()
        time.sleep(.05)
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
