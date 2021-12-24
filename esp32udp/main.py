import BME280, json, time, machine
import mqttudp.engine as me
from math import cos,pi

from espwconst import *
import lib

dom = (9, 40, 68, 99, 129, 160, 190, 221, 252, 282, 313, 343)

hours = 0
tstump = ''
vbat = 2000

az_pin = machine.Pin(AZ_PIN, machine.Pin.OUT)
paz =  machine.PWM(az_pin, freq=50)
paz.init() #duty=round((AZ_MAX+AZ_MIN)/2))

alt_pin = machine.Pin(ALT_PIN, machine.Pin.OUT)
palt =  machine.PWM(alt_pin, freq=50)
palt.init() #duty=round((ALT_MAX+ALT_MIN)/2))

lvlpin = machine.ADC(machine.Pin(LVL_PIN))
lvlpin.width(lvlpin.WIDTH_12BIT)
lvlpin.atten(lvlpin.ATTN_11DB)

if LVL_SUNPIN:
    lvlspin = machine.ADC(machine.Pin(LVL_SUNPIN))
    lvlspin.width(lvlspin.WIDTH_12BIT)
    lvlspin.atten(lvlspin.ATTN_11DB)

def run():
    global tstump
    (t, h, p, v, vs, msg) = measure()
    vbat = v
    if FAKE_SLEEP:
        print("No watchdog")
    else:
        wdt = machine.WDT(timeout=int(DEEP_SLEEP+DEEP_SLEEP/2)*1000)
    while True:
        tstump = '%s-%.2d-%.2d %.2d:%.2d:%.2d' % time.localtime()[0:6]
        if POSITIONING != 'NO':
            position()
        (t, h, p, v, vs, msg) = measure()
        print("TZ: %s LONGITUDE: %s" % (cfg['tz'], cfg['longitude']))
        dat = update_data([t, h, p, v, vs, paz.duty(), palt.duty(), machine.wake_reason(), msg])
        try:
            config = { "sleep": DEEP_SLEEP, "fake_sleep": FAKE_SLEEP, "ts_cfg": tstump, "Vsun": LVL_SUNPIN}
            print("Publish config: %s %s" % (MY_ID, config))
            me.send_publish('weather/%s/config' % MY_ID, json.dumps(config))
            dat.reverse()
            print("Publish id: %s Length:%s" % (MY_ID, len(dat)))
            for line in dat:
                me.send_publish('weather/' + MY_ID, json.dumps(to_dict(line)))
        except Exception as e:
            print("Publish exception: %s" % e)

        stime = DEEP_SLEEP - (time.time() - lib.boot_time)
        if stime < 0: stime = 1
        elif stime > DEEP_SLEEP: stime = DEEP_SLEEP

        if FAKE_SLEEP :
            stime = stime/20
            print("Fake sleep for %s sec" % stime)
            time.sleep(stime)
            lib.boot_time = time.time()
        else:
            print('Deepsleep for %s sec.' % stime)
            wdt.feed()
            machine.deepsleep(stime * 1000)
        print()

def to_dict(line):
    names = ['ts', 't', 'h', 'p', 'v', 'vs', 'az', 'alt', 'w', 'm']
    vals = line.split(',')
    d = {}
    for i in range(len(names)):
        try: d[names[i]] = vals[i]
        except: d[names[i]] = ''
    return d

def position():
    global hours
    tt = time.gmtime()
    hours = tt[3] + tt[4] * (1/60) + cfg['tz']
    az = azimuth()
    alt = altitude()

def altitude():
    global palt
    print("Altitude: ", end="")
    duty = round(alt_cos())
    print(duty)
    palt.duty(duty)
    time.sleep(1)
    return duty

def alt_cos():
    duty = ALT_MIN
    alt_max = max_alt()
    if hours > 4 and hours < 20 and vbat > 1200 :
        delta = (alt_max-ALT_MIN)/2
        duty = delta*cos(pi/8*(hours+4))+delta+ALT_MIN
    else:
        duty = max_alt()
    return duty

def max_alt():
    (month, day) = time.gmtime()[1:3]
    d = dom[month - 1] + day
    a = cfg['longitude'] - 11.75
    x = (ALT_MAX - ALT_MIN) / 90
    if d >= 183: d = 366 - d
    a = d*23.5/183+a
    return a*x + ALT_MIN

def azimuth():
    global paz, vbat
    print("Azimuth: ", end='')
    duty = round( ( 6 - (hours)) * AZ_DUTYPERHOUR ) + AZ_MAX
    if hours < 4 or hours > 20 or vbat < 1200 : duty = round((PWMMIN+PWMMAX)/2)
    else:
        duty = round( ( 6 - (hours)) * AZ_DUTYPERHOUR ) + AZ_MAX
        if duty < PWMMIN:
            print("PWMMIN :", end="")
            duty=PWMMIN
        elif duty > PWMMAX :
            print("PWMMAX :", end="")
            duty=PWMMAX
    print(duty)
    paz.duty(duty)
    time.sleep(1)
    return duty

def update_data(d):
    open(DATA_FILE, 'a').close()
    data = [line.strip() for line in open(DATA_FILE, 'r')]
    print("Timestamp: %s" % tstump)
    d.insert(0, tstump)
    s = ','.join([str(e) for e in d ])
    data.append(s)
    if len(data) > DATA_LENGTH: data.pop(0)
    with open(DATA_FILE,'w') as f: f.write('\n'.join(data))
    return data

def measure():
    res = [0]*6
    try:
        res[3] = adc_read(lvlpin)
        res[4] = adc_read(lvlspin) if LVL_SUNPIN else 0
        res[5] = 'Low power.' if res[3] < LVL_LOWPWR else ''
        i2c = machine.SoftI2C(scl=machine.Pin(I2CSCL_PIN), sda=machine.Pin(I2CSDA_PIN), freq=I2C_FREQ)
        bme = BME280.BME280(i2c=i2c)
        res = (bme.temperature, bme.humidity, "%.2f" % bme.pressure, res[3], res[4], res[5])
        print("Measuring: %s" % str(res))
    except Exception as e:
        res[5]= res[5] + " Measuring Error."
        print("Measurin Error: %s" % str(e))
    return res

def adc_read(adc):
    # averaging adc reading
    count = 5
    val = 0
    for i in range(count):
        val += adc.read()
        time.sleep(.05)
    return int(val/count)

if __name__ == '__main__':
    cfg=lib.get_config()
    run()
