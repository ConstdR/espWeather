# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(None)

import os, time, gc
from machine import Pin

AP_PIN = 35
CFG_NAME = '_config'
CONNECT_WAIT = 10
TS_NAME = 'timestamp'
NTP_SYNC_PERIOD = 43200  # 12 hours

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
        appin = Pin(AP_PIN, Pin.IN)
        if not appin.value():
            # force run AP by AP_PIN == 0
            raise Exception("Force AP by low %s pin" % AP_PIN) 
        fh = open(CFG_NAME)
        essid = fh.readline().strip()
        pswd = fh.readline().strip()
        fh.close()
    except Exception as e:
        print("Error: %s" % e)
        import ap
        ap.run()
        # (essid, pswd) = ap.run()  # ?????
    return((essid, pswd))

def sync_time():
    """
        Sync local time over the NTP once per NTP_SYNC_PERIOD
    """
    doSync = True
    try:
        diff = abs( time.time() - os.stat(TS_NAME)[-1] )
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
            fh.write(str(time.time()))
            fh.close()
    except Exception as e:
        print("NTP sync error: %s" % e)
    print('Time: %s' % str(time.localtime()))

def run():
    gc.enable()
    gc.collect()
    if ( do_connect()) :
        sync_time()

run()
