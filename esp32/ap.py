import esp
import network
import machine
import time
import socket
import re
import main
from espwconst import *

CONNECT_WAIT = 10
CFG_NAME = '_config'
HTTP_RESPONSE = b"""\
HTTP/1.0 200 OK
Content-Length: %d

%s
"""

ap = None
_hextobyte_cache = None

def start_ap():
    """
        Start WiFi Access POINT with default ISSID like ESP_XXXXXX and no password.
    """
    global ap
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    while ap.active() == False:
        time.sleep(1)
    print("AP active: %s %s" % (ap.config('essid'), ap.ifconfig()))

def start_httpd():
    """
        Stupid httpd
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        print('Got a connection from %s' % str(addr))
        request = conn.recv(1024)
        res = process_request(request)
        if not res:
            cfg = get_config()
            if cfg is not None:
                html = web_page(*cfg)
            else:
                html = web_page()
        else:
            html = web_page(res['essid'], res['pswd'], res['srv'],
                            res['port'], res['tz'], res['latitude'], res['action'], res['message'])
        response = HTTP_RESPONSE % (len(html), html)
        conn.send(response)
        conn.close()

def az(duty):
    main.paz.deinit()
    main.paz.init(duty=duty)

def az_min():
    az(AZ_MIN)
    print ("AZ_MIN")
def az_mid():
    az(round((AZ_MAX+AZ_MIN)/2))
    print ("AZ_MID")
def az_max():
    az(AZ_MAX)
    print ("AZ_MAX")

def alt(duty):
    main.palt.deinit()
    main.palt.init(duty=duty)

def alt_min():
    alt(ALT_MIN)
    print ("ALT_MIN")
def alt_mid():
    alt(round((ALT_MAX+ALT_MIN)/2))
    print ("ALT_MID")
def alt_max():
    alt(ALT_MAX)
    print ("ALT_MAX")

def action(act):
    switch = {
        'az_min': az_min,
        'az_mid': az_mid,
        'az_max': az_max,
        'alt_min': alt_min,
        'alt_mid': alt_mid,
        'alt_max': alt_max
    }
    func = switch.get(act)
    try:
        return func()
    except Exception as e:
        print(e)

def process_request(request):
    print("Req decode: %s" % request.decode().split('\n')[0].strip().split(' '))
    req = request.decode().split('\n')[0].strip().split(' ')
    fields = ('essid', 'pswd', 'srv', 'port', 'tz', 'latitude', 'action')
    get = '' if len(req) < 3 else req[1]
    lst = get.split('?')
    get = '' if len(lst) < 2 else lst[1]
    print('Request = %s' % get)
    lst = get.split('&')
    resdict = {}
    for part in lst:
        try:
            pair = part.split('=')
            resdict[pair[0]]=unquote(pair[1]).decode()
        except:
            pass
    print("Res dict: %s" % resdict)
    count = 0
    for k in fields:
        if k in resdict.keys():
            count += 1
    if count != len(fields):
        resdict = None
    else:
        if resdict['action']:
            print("Action: %s" % resdict['action'])
            action(resdict['action'])

        # check wifi connection
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(resdict['essid'], resdict['pswd'])
        print('Connecting...')
        for i in range(CONNECT_WAIT):
            time.sleep(1)
            print("%s ..." % (i), end='\r')
            if wlan.isconnected():
                break
        if not wlan.isconnected():
            resdict['message'] = "%s connection failed!" % resdict['essid']
        else:
            resdict['message'] = "%s connected." % resdict['essid']
            # store credentials
            # find_servers(resdict['srv'], resdict['port'])  # maybe later
            try:
                fh = open(CFG_NAME, 'w')
                fh.write(resdict['essid'] + '\n')
                fh.write(resdict['pswd'] + '\n')
                fh.write(resdict['srv'] + ':' + resdict['port'] + '\n')
                fh.write(resdict['tz'] + '\n')
                fh.write(resdict['latitude'] + '\n')
                fh.close()
                resdict['message'] += ' Settings stored. Please restart.'
            except Exception as e:
                resdict['message'] += ' Settings storing error. %s' % e
                print(e)
        wlan.active(False)

    return resdict

def find_servers(ip, port): 
    # TODO
    try:
        m = re.match("(.*\.)\d*$", ip).group(1)
        print("Network: %s" % m)
        for i in range(1,256):
            cip = "%s%s" % (m, i)
            print("Current IP: %s" % cip)
    except Exception as e:
        print("Find server error: %s" % str(e))

def web_page(essid='essid', pswd='password', server='192.168.1.5', port='8088', tz='1', latitude='50', action="", message=''):
  html = """<html><body><h1>%s</h1>""" % ap.config('essid')
  html += """<form action="/" method="get">
<p>ESSID:<input name="essid" type=text value="%s"></p>
<p>Password:<input name="pswd" type=text value="%s"></p>
<p>Server IP:<input name="srv" type=text value="%s"></p>
<p>Server Port:<input name="port" type=text value="%s"></p>
<p>Time: UTC + <input name="tz" type=text value="%s"></p>
<p>Latitude: <input name="latitude" type=text value="%s"></p>
<p>Action: %s
<br>
Azimuth:<input name="action" type="radio" value="az_min">min
<input name="action" type="radio" value="az_mid" checked>middle
<input name="action" type="radio" value="az_max">max
<br>
Altitude:<input name="action" type="radio" value="alt_min">min
<input name="action" type="radio" value="alt_mid">middle
<input name="action" type="radio" value="alt_max">max
</p>
<p><input type="submit" value="Submit"></p>
</form>
<hr>
%s
""" % (essid, pswd, server, port, tz, latitude, action, message)
  html += """</body></html>""" 
  return html

def unquote(string):
    """unquote('abc%20de+f') -> b'abc de f'."""
    global _hextobyte_cache

    # Note: strings are encoded as UTF-8. This is only an issue if it contains
    # unescaped non-ASCII characters, which URIs should not.
    if not string:
        return b''

    if isinstance(string, str):
        string = string.replace('+', ' ')
        string = string.encode('utf-8')

    bits = string.split(b'%')
    if len(bits) == 1:
        return string

    res = [bits[0]]
    append = res.append

    # Build cache for hex to char mapping on-the-fly only for codes
    # that are actually used
    if _hextobyte_cache is None:
        _hextobyte_cache = {}

    for item in bits[1:]:
        try:
            code = item[:2]
            char = _hextobyte_cache.get(code)
            if char is None:
                char = _hextobyte_cache[code] = bytes([int(code, 16)])
            append(char)
            append(item[2:])
        except KeyError:
            append(b'%')
            append(item)

    return b''.join(res)

def get_config():
    try:
        fh = open(CFG_NAME, 'r')
        essid = fh.readline() # skip essid
        pswd = fh.readline() # skip pswd
        (host, port) = fh.readline().strip().split(':')
        tz = float(fh.readline().strip())
        longitude = float(fh.readline().strip())
        if tz == '': tz=TZ
        if longitude == '' : longitude=ALT_LONGITUDE
        fh.close()
        return (essid, pswd, host, port, tz, longitude, '', 'Existing Config.')
    except Exception as e:
        print("Error getting config: %s" % e)

def run():
    print("Run AP.")
    start_ap()
    start_httpd()

    return (None, None)
