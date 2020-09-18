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
import os, sqlite3

lg = logging.getLogger(__file__)
args = None

def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='count', default=0, dest="verbose_count", 
                        help="increases log verbosity for each occurence up to 3 times, default - critical")
    parser.add_argument('--log_file', dest="log_file", help="logging file. default - stderr")
    parser.add_argument('--hostname', dest="hostname", default='', help="web hostname (ip address). default ''")
    parser.add_argument('--port', dest="port", default=8088, help="web port. default 8088")
    parser.add_argument('--datadir', dest='datadir', default='./', help="diredtory to store data. default: './'")
    parser.add_argument('--timezone', dest='timezone', default='+2', help="timezone in hours i.e: +2 or -8 and etc. default: '+2'")
    parser.add_argument('--dir', dest="dir", default='./', help="directory to store params. default: './'")

    args = parser.parse_args()

    loggerConfig(level=args.verbose_count, log_file=args.log_file)
    httpd = HTTPServer((args.hostname, args.port), tHandler)
    httpd.serve_forever()

class tHandler(BaseHTTPRequestHandler):
    code = 200
    def show_favicon_ico(self, data):
        self.do_HEAD('text/text')
        self.wfile.write(b'')

    def show_graph(self, data):
        lg.debug("Graph for %s" % data)
        txt = ''
        content_type = 'text/text'
        try:
            if data[0] in ('dygraph.js', 'dygraph.css'):
                txt = open('%s/templates/%s' % (args.datadir, data[0]), 'r').read()
                if data[0].endswith('.css'):
                    content_type = 'text/css'
                else:
                    content_type = 'text/javascript'
            elif len(data) > 1 and data[1].endswith('.csv'):
                dbh = get_dbh(data[0])
                content_type = 'text/csv'
                res = dbh.execute("select *, datetime(timedate, '%s hours') as tztime from data order by timedate"
                                   % args.timezone)
                rows = res.fetchall()
                for row in rows:
                    txt = txt + "%(tztime)s,%(ip)s,%(temperature)s,%(humidity)s,%(pressure)s,%(voltage)s\n" % row 
                dbh.close()
            else:
                dbh = get_dbh(data[0])
                res = dbh.execute("select *, datetime(timedate, '%s hours') as tztime from data order by timedate desc limit 1"
                                  % args.timezone )
                row = res.fetchone()
                row['id'] = data[0]
                lg.debug(row)
                tmpl = open('%s/templates/graph.tmpl' % args.datadir, 'r').read()
                txt = tmpl % row
                content_type = 'text/html'
                dbh.close()
        except Exception as e:
            lg.error(str(e))
            self.code = 400
            txt = 'Error'
        btxt = bytearray(txt, 'UTF-8')
        self.do_HEAD(content_type, len(btxt))
        self.wfile.write(btxt)

    def do_HEAD(self, content_type="text/text", content_length=None):
        self.send_response(self.code)
        self.send_header("Content-type", content_type)
        if content_length :
            self.send_header("Content_length", content_length)
        self.end_headers()

    def do_GET(self):
        parsedurl = urlparse(self.path)
        parsedpath = parsedurl.path.split('/')
        parsedpath.pop(0)
        lg.debug("parsedurl:")
        lg.debug(parsedpath)

        try:
            method = 'show_' + parsedpath[0].replace('.', '_')
            parsedpath.pop(0)
            result = getattr(self, method)(parsedpath)
        except Exception as e:
            lg.debug(e)
            try:
                params = parse_qs(parsedurl.query)
                client_ip = self.client_address[0]
                lg.debug((client_ip, params))
                self.code = 200

                if 'id' in params.keys():
                    remoteid = params['id'][0]
                    temp = params['t'][0] if 't' in params.keys() else '0'
                    humidity = params['h'][0] if 'h' in params.keys() else '0'
                    pressure = params['p'][0] if 'p' in params.keys() else '0'
                    voltage = params['v'][0] if 'v' in params.keys() else '0'
                    message = params['m'][0] if 'm' in params.keys() else ''
                    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    dbh = get_dbh(remoteid)
                    c = dbh.cursor()
                    c.execute('insert or replace into data values(?,?,?,?,?,?,?)',
                              (timestamp, client_ip, temp, humidity, pressure, voltage, message))
                    dbh.commit()
                    dbh.close()
                else:
                    lg.debug("No id key found")
                    self.code = 400
            except Exception as e:
                lg.error("GET error: %s" % e )
                self.code = 500

            self.do_HEAD()
            self.wfile.write(b'OK.')

def get_dbh(name):
    fname = '%s/%s.sqlite3' % (args.datadir, name)
    if os.path.isfile(fname) :
        dbh = sqlite3.connect(fname)
    else:
        dbh = sqlite3.connect(fname)
        c = dbh.cursor()
        c.execute("""
                    CREATE TABLE data ( timedate text primary key, ip text,
                                        temperature real, humidity real,
                                        pressure real, voltage real,
                                        message text);
                  """)
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
