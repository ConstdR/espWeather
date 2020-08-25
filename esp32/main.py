import dht
import machine
import time
import urequests

URL = "http://%s/?id=%s&t=%s&h=%s&v=%s"

myID = int.from_bytes(machine.unique_id(), 'big') # 'little' is more correct :)

CFG_NAME = '_config'
led = machine.Pin(21, machine.Pin.OUT)
dht = dht.DHT11(machine.Pin(32))
dhtpower = machine.Pin(12, machine.Pin.OUT)
lvlpin = machine.ADC(machine.Pin(34))
MEASURE_COUNT = 1
MEASURE_TIMEOUT = 1
DEEP_SLEEP = 900000 # 900000 == 15 min

def main():
    while True:
        (t, h, v) = measure()
        url = URL % (get_hostport(), myID, t, h, v)
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

def measure(res = [0, 0, 0]):
    # DHT have more than 2 sec sampling period 
    # https://www.makerguides.com/wp-content/uploads/2019/02/DHT11-Datasheet.pdf
    # so we can do MEASURE_COUNT measures in MEASURE_TIMEOUT sec interval 
    # and take average (but we still give a shit)
    dhtpower.on()
    try:
        lvlpin.width(lvlpin.WIDTH_12BIT)
        lvlpin.atten(lvlpin.ATTN_11DB)
        res[2] = adc_read(lvlpin) / 100.0

        print("lvl: %s" % res[2])
        for i in range(MEASURE_COUNT):
            time.sleep(MEASURE_TIMEOUT)
            dht.measure()
            res[0] = res[0] + dht.temperature()
            res[1] = res[1] + dht.humidity()
        res[0] = res[0] / MEASURE_COUNT
        res[1] = res[1] / MEASURE_COUNT
    except Exception as e:
        print("Measuring error: %s" % e)
    dhtpower.off()

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
