#!/usr/bin/python
# encoding: utf-8

import argparse
import logging
import configparser
import os, re
import sqlite3
import aiohttp_jinja2
import jinja2

from datetime import datetime
from dateutil.relativedelta import relativedelta
from aiohttp import web

from pprint import pprint as pp

DEF_RANGE = 7 # in days!!!

lg = logging.getLogger(__file__)
args = None
cfg = None

def main():
    global args, cfg
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', default='config.cfg',
                    help="Config file. Default: config.cfg")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    cfg = config['default']

    logging.basicConfig(level=cfg['debug'])

    app = web.Application()
    aiohttp_jinja2.setup(app,loader=jinja2.FileSystemLoader('templates'))
    app.add_routes([
                    web.get('/', index),
                    web.get(r'/csv/{id}', csv_get),
                    web.get(r'/graph/{id}', graph),
                    web.post(r'/id/{id}', store),
                    web.get('/favicon.ico', favicon),
                    web.static('/static', 'static'),
                   ])
    web.run_app(app, host=cfg['host'], port=cfg['port'])

async def favicon(request):
    raise web.HTTPFound(location='/static/favicon.ico')

async def store(request):
    sensor_id = request.match_info['id']
    lg.debug("New data from %s" % sensor_id)
    jdata = await request.json()
    first = jdata['measures'][0].split(',')[0]
    last  = jdata['measures'][-1].split(',')[0]
    lg.info("Post %s rows from: %s to %s (UTC)" % (len(jdata['measures']), first, last))
    dbname = cfg['dbdir']+'/'+sensor_id+'.sqlite3'
    dbh = sqlite3.connect(dbname)
    if not os.path.isfile(dbname):
        c = dbh.cursor()
        c.execute("""CREATE TABLE data ( timedate text primary key, ip text,
                                        temperature real, humidity real,
                                        pressure real, voltage real, voltagesun real,
                                        message text)""")
        c.execute("CREATE TABLE params (name text primary key, value text)")
        dbh.commit()
    c = dbh.cursor()
    for m in jdata['measures']:
        vals = m.split(',')
        vals.insert(1, request.remote)
        try:
            c.execute('insert or replace into data values(?,?,?,?,?,?,?,?)', vals)
        except Exception as e:
            lg.error('Insert error: %s' % e)
            lg.error('Data row: %s' % m)

    dbh.commit()
    dbh.close()
    return web.Response(text='OK')

@aiohttp_jinja2.template('graph.html')
async def graph(request):
    sensor_id = request.match_info['id']
    lg.debug("Graph for %s" % sensor_id)
    dbname = cfg['dbdir']+'/'+sensor_id+'.sqlite3'
    if 'rename' in request.query.keys():
        lg.debug("Rename %s to %s" % (sensor_id, request.query['rename']))
        dbh = sqlite3.connect(dbname)
        dbh.execute("insert or replace into params values (?, ?)", ('name', request.query['rename']))
        dbh.commit()
        dbh.close()
        raise web.HTTPFound(location='/graph/' + sensor_id)
    info = brief_data(dbname)
    info['id'] = sensor_id
    (info['startdate'], info['enddate']) = get_range(request)
    info['refreshtime'] = 450
    return info

def get_range(request):
    daterange = None
    try:
        lg.debug("Daterange: %s" % request.query['daterange'])
        r = re.match('(\d{4}-\d\d-\d\d).-.(\d{4}-\d\d-\d\d)', request.query['daterange'])
        daterange = r.groups()
    except Exception as e:
        lg.debug('Daterange error %s' % e)
        daterange = None

    if not daterange :
        lg.debug("Use default date range")
        now = datetime.now()
        start = now - relativedelta(days=DEF_RANGE)
        daterange =(start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'))
    return daterange

@aiohttp_jinja2.template('index.html')
async def index(request):
    lg.debug("Get sensors list")
    sensors = {}
    for name in os.listdir(cfg['dbdir']):
        if name.endswith(".sqlite3"):
            try:
                sensor_id = name.strip('.sqlite3') 
                info = brief_data(cfg['dbdir']+'/'+name)
                sensors[sensor_id] = info
            except:
                lg.error("Bad data in %s" % name)
    return { 'sensors': sensors, 'refreshtime':450 }

async def csv_get(request):
    sensor_id = request.match_info['id']
    lg.debug("Get CSV for %s" % sensor_id)
    (startdate, enddate) = get_range(request)
    dbh = sqlite3.connect(cfg['dbdir']+'/'+sensor_id+'.sqlite3')
    dbh.row_factory = dict_factory
    res = dbh.execute("select max(voltage) as mv, max(voltagesun) as mvs from data")
    maxv = res.fetchone()
    v = 4.2/maxv['mv']
    vs= 6/maxv['mvs']
    res = dbh.execute("""select temperature, humidity, pressure,
                         voltage*? as voltage,
                         voltagesun*? as voltagesun,
                         datetime(timedate, 'localtime') as tztime from data
                         where timedate >= datetime(?, 'localtime') and
                               timedate <= datetime(datetime(?, 'localtime'), '1 day')
                      order by timedate""", (v, vs, startdate, enddate))
    rows = res.fetchall()
    txt=''
    for row in rows:
        txt = txt + "%(tztime)s,%(temperature)s,%(humidity)s,%(pressure)s,%(voltage)s,%(voltagesun)s\n" % row
    dbh.close()
    return web.Response(text=txt, content_type="text/csv")

def brief_data(fname):
    dbh = sqlite3.connect(fname)
    dbh.row_factory = dict_factory
    res = dbh.execute("""select case when params.value is NULL then '__new__' else params.value end as name,
                                round(data.temperature,1) as temperature,
                                cast( round(data.humidity,0) as int) as humidity,
                                cast( round(data.pressure,0) as int) as pressure,
                                data.voltage, data.voltagesun,
                                datetime(data.timedate, 'localtime') as tztime
                           from data
                           left join params on params.name='name'
                          order by timedate desc limit 1""")
    row = res.fetchone()
    res = dbh.execute("select max(voltage) as mv, max(voltagesun) as mvs from data")
    maxv = res.fetchone()
    dbh.close()
    row['v'] = round ( row['voltage'] / maxv['mv'] * 4.2, 2 )
    row['vs']= round ( row['voltagesun'] / maxv['mvs'] * 6, 2 )
    return row

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        sys.exit(0)

# vim: ai ts=4 sts=4 et sw=4 ft=python
