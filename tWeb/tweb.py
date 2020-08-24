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
    parser.add_argument('--dir', dest="dir", default='./', help="directory to store params")

    args = parser.parse_args()

    loggerConfig(level=args.verbose_count, log_file=args.log_file)

# 'application' code
#    lg.debug('debug message')
#    lg.info('info message')
#    lg.warning('warn message')
#    lg.error('error message')
#    lg.critical('critical message')
#    print("args:" , args)

    httpd = HTTPServer( ( args.hostname, args.port ) , tHandler )
    httpd.serve_forever()

class tHandler(BaseHTTPRequestHandler):
    def do_HEAD(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "text/text")
        self.end_headers()
    def do_GET(self):
        try:
            params = parse_qs(urlparse(self.path).query)
            client_ip = self.client_address[0]
            lg.debug((client_ip, params))
            code = 200
    
            if 'id' in params.keys():
                remoteid = params['id'][0]
                temp = params['t'][0] if 't' in params.keys() else ''
                humidity = params['h'][0] if 'h' in params.keys() else ''
                voltage = params['v'][0] if 'v' in params.keys() else ''
                timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                row = "%s,%s,%s,%s,%s" % (timestamp, client_ip, temp, humidity, voltage)
                lastrow = None
                try:
                    fr = open("%s/%s.csv" % (args.dir, remoteid), 'r')
                    # Chrome love to re-send requests
                    # get rid of them
                    lastrow = tail(fr) 
                    if lastrow[0] is not None :
                        lastrow = lastrow[0][0].replace(r"\n", " ") 
                    fr.close()
                except Exception as e:
                    lg.error("%s", e)
    
                lg.debug("Lastrow: %s" % lastrow)
                if lastrow is None or lastrow != row:
                    try:
                        fh = open("%s/%s.csv" % (args.dir, remoteid), 'a')
                        fh.write("%s\n" % row)
                        lg.debug(row)
                        fh.close()
                    except Exception as e:
                        lg.critical("%s", e)
                else:
                    lg.debug("Ignoring duplicate row")
            else:
                lg.debug("No id key found")
                code = 400
        except Exception as e:
                lg.error("GET error: %s" % e )
                code = 500
    
        self.do_HEAD(code)
        self.wfile.write(b'OK.')


#############################

def tail(f, n=1, offset=None):
    """Reads a n lines from f with an offset of offset lines.  The return
    value is a tuple in the form ``(lines, has_more)`` where `has_more` is
    an indicator that is `True` if there are more lines in the file.
    https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-similar-to-tail/692616#692616
    """
    avg_line_length = 30
    to_read = n + (offset or 0)

    while 1:
        try:
            f.seek(-(avg_line_length * to_read), 2)
        except IOError:
            # woops.  apparently file is smaller than what we want
            # to step back, go to the beginning instead
            f.seek(0)
        pos = f.tell()
        lines = f.read().splitlines()
        if len(lines) >= to_read or pos == 0:
            return lines[-to_read:offset and -offset or None], \
                   len(lines) > to_read or pos > 0
        avg_line_length *= 1.3

#############################################

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
