#!/usr/bin/env python3

'''
MQTT/UDP listen and store data
'''

# will work even if package is not installed
import argparse
import logging
import configparser
import re
import sqlite3
import json
import os

import mqttudp.engine as me

lg = logging.getLogger(__file__)
args = None
cfg = None

last = {}

def main():
    global args, cfg
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', default='config.cfg',
                    help="Config file. Default: config.cfg")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    cfg = config['listener']
    logging.basicConfig(level=cfg['debug'])

    me.listen(recv_packet)

def recv_packet(pkt):
    global last
    if pkt.ptype != me.PacketType.Publish:
        # not publish msg
        return
    if last.__contains__(pkt.topic) and last[pkt.topic] == pkt.value:
        # duplicate
        return
    last[pkt.topic] = pkt.value
    lg.debug( pkt.topic+"="+pkt.value+ "\t\t" + str(pkt.addr) )

    r = re.match(r'weather/+(.*)', pkt.topic)
    if r and r.group(1):
        lg.debug("Weather id: %s" % r.group(1))
        try:
            store(r.group(1), pkt.value, str(pkt.addr))
        except Exception as e:
            lg.error("Store error: %s" % e)

def store(wid, data, ip):
    ddata  = json.loads(data)
    ddata['ip'] = ip
    lg.debug("JSON: %s" % ddata)
    dbname = cfg['dbdir']+'/'+wid+'.sqlite3'
    if not os.path.isfile(dbname):
        dbh = sqlite3.connect(dbname)
        c = dbh.cursor()
        c.execute("""CREATE TABLE data ( timedate text primary key, ip text,
                                        temperature real, humidity real,
                                        pressure real, voltage int, voltagesun int,
                                        azimuth int, altitude int,
                                        wake int, message text)""")
        c.execute("CREATE TABLE params (name text primary key, value text)")
        dbh.commit()
        dbh.close()
        lg.debug("SQLITE created for id %s" % wid)
    dbh = sqlite3.connect(dbname)
    c = dbh.cursor()
    c.execute("""insert or replace into data (timedate, ip, temperature, humidity,
                        pressure, voltage, voltagesun, azimuth, altitude,
                        wake, message) 
                        values (:ts, :ip, :t, :h,
                        :p, :v, :vs, :az, :alt, 
                        :w, :m)""", ddata)
    dbh.commit()
    dbh.close()
    return

if __name__ == "__main__":
    main()
