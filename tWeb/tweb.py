#!/usr/bin/python3
# encoding: utf-8
"""
Tiny web server to store params recived from GET requests.
"""
import sys
import argparse
import logging

from http.server import *
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os, sqlite3, re
import json

lg = logging.getLogger(__file__)
args = None
VMAS = 580
DEF_RANGE = 7 # in days!!!

def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='count', default=0, dest="verbose_count",
                        help="increases log verbosity for each occurence up to 3 times, default - critical")
    parser.add_argument('--log_file', dest="log_file", help="logging file. default - stderr")
    parser.add_argument('--hostname', dest="hostname", default='', help="web hostname (ip address). default ''")
    parser.add_argument('--port', dest="port", default=8088, help="web port. default 8088")
    parser.add_argument('--datadir', dest='datadir', default='./', help="diredtory to store data. default: './'")
    parser.add_argument('--dir', dest="dir", default='./', help="directory to store params. default: './'")

    args = parser.parse_args()

    loggerConfig(level=args.verbose_count, log_file=args.log_file)
    httpd = HTTPServer((args.hostname, args.port), tHandler)
    httpd.timeout = 10
    httpd.serve_forever()

class tHandler(BaseHTTPRequestHandler):
    server_version = "BaseHTTP/0.9"
    sys_version = "Pantofle/0.42"
    code = 200
    def show_favicon_ico(self, parsedpath=None):
        #ico = open('%s/favicon.ico' % args.datadir, 'rb').read()
        #self.do_HEAD('image/png', len(ico), 43200)
        #self.wfile.write(icoa)
        self.code=404

    def show_graph(self, data):
        lg.debug("Graph for %s" % data)
        txt = ''
        content_type = 'text/text'
        age = None
        refreshtime = 450
        try:
            parsedurl = urlparse(self.path)
            params = parse_qs(parsedurl.query)
            if parsedurl.query:
                lg.debug("Params: %s" % ("%s" % parsedurl.query))
            if data[0] in ('dygraph.js', 'jquery.min.js', 'moment.min.js', 'daterangepicker.min.js',
                           'dygraph.css', 'daterangepicker.css'):
                age = 43200
                txt = open('%s/templates/%s' % (args.datadir, data[0]), 'r').read()
                if data[0].endswith('.css'):
                    content_type = 'text/css'
                else:
                    content_type = 'text/javascript'
            elif data[0] == 'favicon.ico':
                self.show_favicon_ico()
            else:
                (startdate, enddate, default_range) = self.get_range(params)
                lg.debug("Start date: %s End date: %s Default: %s" % (startdate, enddate, default_range))
                if len(data) > 1 and data[1].endswith('.csv'):
                    dbh = get_dbh(data[0])
                    content_type = 'text/csv'
                    res = dbh.execute("""select *, datetime(timedate, 'localtime') as tztime from data
                                         where timedate >= datetime(?, 'localtime') and
                                               timedate <= datetime(datetime(?, 'localtime'), '1 day')
                                      order by timedate""", (startdate, enddate))
                    rows = res.fetchall()
                    for row in rows:
                        txt = txt + "%(tztime)s,%(temperature)s,%(humidity)s,%(pressure)s,%(voltage)s\n" % row
                    dbh.close()
                else:
                    dbh = get_dbh(data[0])
                    # rename?
                    if 'rename' in params.keys():
                        newname = params['rename'][0]
                        dbh.execute("insert or replace into params values (?, ?)", ('name', newname))
                        dbh.commit()
                        refreshtime=0
                        lg.info("Rename to '%s'" % newname)
                    res = dbh.execute("""select case when params.value is NULL then '__new__' else params.value end as name,
                                                data.*, datetime(data.timedate, 'localtime') as tztime
                                         from data
                                         left join params on params.name='name'
                                         order by timedate desc limit 1""")
                    row = res.fetchone()
                    row['id'] = data[0]
                    row['refreshtime'] = refreshtime
                    row['url'] = parsedurl.path
                    row['startdate'] = startdate
                    row['enddate'] = enddate
                    lg.debug(row)
                    tmpl = open('%s/templates/graph.tmpl' % args.datadir, 'r').read()
                    if not default_range:
                        row['daterange'] = "daterange=%(startdate)s+-+%(enddate)s" % row
                    else:
                        row['daterange'] = ''
                    txt = tmpl % row
                    content_type = 'text/html'
                    dbh.close()
        except Exception as e:
            lg.error(e)
            self.code = 404
            txt = 'Error'
        btxt = bytearray(txt, 'UTF-8')
        self.do_HEAD(content_type, len(btxt), age)
        self.wfile.write(btxt)

    def get_range(self, params):
        daterange = None
        default = True
        try:
            lg.debug("Daterange: %s" % params['daterange'])
            r = re.match('(\d{4}-\d\d-\d\d).-.(\d{4}-\d\d-\d\d)', params['daterange'][0])
            daterange = r.groups()
            default = False
        except Exception as e:
            lg.info('Daterange error %s' % e)
            daterange = None

        if not daterange :
            lg.debug("Use default date range")
            now = datetime.now()
            start = now - relativedelta(days=DEF_RANGE)
            daterange =(start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'))
        return daterange + (default,)

    def do_HEAD(self, content_type="text/text", content_length=None, age=None):
        self.send_response(self.code)
        self.send_header("Content-Type", content_type)
        if content_length :
            self.send_header("Content-Length", content_length)
        if age :
            self.send_header("Cache-Control", "max-age=%s" % age)
        self.end_headers()

    def do_POST(self):
        parsedurl = urlparse(self.path)
        parsedpath = parsedurl.path.split('/')
        parsedpath.pop(0)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        lg.info("Post path: %s, length: %s" % (parsedpath, content_length))

        if parsedpath[0] != 'id':
            lg.warning('Bad POST request: %s' % self.path)
            self.code = 400
            self.do_HEAD()
            return

        jdata = json.loads(post_data)
        lg.info("Post last data: %s" % jdata['measures'][-1])
        dbh = get_dbh(parsedpath[1], True)
        c = dbh.cursor()
        for m in jdata['measures']:
            vals = m.split(',')
            vals.insert(1, self.client_address[0])
            vals[5] = float(vals[5]) / VMAS
            c.execute('insert or replace into data values(?,?,?,?,?,?,?)', vals)
        dbh.commit()
        dbh.close()
        self.do_HEAD()
        self.wfile.write(b'OK.')

    def do_GET(self):
        parsedurl = urlparse(self.path)
        parsedpath = parsedurl.path.split('/')
        parsedpath.pop(0)

        try:
            if parsedpath[0]:
                method = 'show_' + parsedpath[0].replace('.', '_')
                parsedpath.pop(0)
                result = getattr(self, method)(parsedpath)
            else :
                raise Exception("Empty path.")
        except Exception as e:
            lg.debug(str(e))
            lg.error("GET error: %s" % e )
            self.code = 404
            self.do_HEAD()
            self.wfile.write(b'Error')
        self.wfile.flush()
        self.connection.close()

def get_dbh(name, create=False):
    fname = '%s/%s.sqlite3' % (args.datadir, name)
    if os.path.isfile(fname) :
        dbh = sqlite3.connect(fname)
    elif create:
        dbh = sqlite3.connect(fname)
        c = dbh.cursor()
        c.execute("""CREATE TABLE data ( timedate text primary key, ip text,
                                        temperature real, humidity real,
                                        pressure real, voltage real,
                                        message text)""")
        c.execute("CREATE TABLE params (name text primary key, value text)")
        dbh.commit()
    dbh.row_factory = dict_factory
    return dbh

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def loggerConfig(level=0, log_file=None):
    lg.setLevel({1: 'ERROR', 2: 'WARNING', 3: 'INFO'}.get(level, 'DEBUG') if level else 'CRITICAL')
    try: fh = open(log_file, 'a')
    except: fh = sys.stderr
    ch = logging.StreamHandler(fh)
    formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d %(threadName)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    lg.addHandler(ch)

if __name__ == '__main__':
    main()

# vim: ai ts=4 sts=4 et sw=4 ft=python
