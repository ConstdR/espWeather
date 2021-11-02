# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(None)
import os, time, machine, _thread, random, json
from espwconst import *

pled = machine.Pin(LED_PIN, machine.Pin.OUT, value=1)
boot_time=time.time()

def do_connect():
    (essid, pswd) = get_credentials()
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(essid, pswd)
        for i in range(CONNECT_WAIT):
            if wlan.isconnected():
                print("Done")
                break
            print("%s ..." % (i), end='\r')
            time.sleep(1)
    
    if wlan.isconnected():
        print('Network config:', wlan.ifconfig())
        return True
    else:
        print('No network')
        return False

def get_credentials():
    """
        Get WiFi credentials from file, or start AP to get it.
    """
    (essid, pswd) = (None,None)
    try:
        appin = machine.Pin(AP_PIN, machine.Pin.IN)
        if not appin.value():
            # force run AP by AP_PIN == 0
            raise Exception("Force AP by low %s pin" % AP_PIN) 
        fh = open(CFG_NAME)
        cfg = json.loads(fh.read())
        fh.close()
        essid = cfg['essid']
        pswd = cfg['pswd']
    except Exception as e:
        print("Error: %s" % e)
        import ap
        ap.run()
        # (essid, pswd) = ap.run()  # ?????
    return(essid, pswd)

def sync_time():
    """
        Sync local time over the NTP once per NTP_SYNC_PERIOD
    """
    doSync = True
    try:
        diff = abs(time.time() - os.stat(TS_NAME)[-1] )
        print("Time: %s Diff: %s" % (time.time(), diff))
        if diff < NTP_SYNC_PERIOD:
            doSync = False
    except:
        pass
    try:
        if doSync:
            print('Sync time')
            import ntptime
            ntptime.settime()
            fh = open(TS_NAME, 'w')
            fh.write(str(ntptime.time()))
            fh.close()
    except Exception as e:
        print("NTP sync error: %s" % e)
    print('Time: %s' % str(time.localtime()))

def pwrchk():
    """
        Check battery powering level is enough
    """
    lvlpin = machine.ADC(machine.Pin(LVL_PIN))
    lvlpin.width(lvlpin.WIDTH_12BIT)
    lvlpin.atten(lvlpin.ATTN_11DB)
    lvl = lvlpin.read()
    print ("Power: %s" % lvl)
    return True if lvl > LVL_LOWPWR else False

def run():
    if pwrchk():
        if (do_connect()) :
            sync_time()
    else:
        print("Low power, no connection")

def blink():
    print("Blinking")
    while True:
        pled.value(0) if pled.value() == 1 else pled.value(1)
        time.sleep(random.random()/10)

_thread.start_new_thread(blink, ()) # bells and whistles

run()
