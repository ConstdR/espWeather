import esp
import network
import machine
import time
import socket
import re

CONNECT_WAIT = 10
CFG_NAME = '_config'
HTTP_RESPONSE = b"""\
HTTP/1.0 200 OK
Content-Length: %d

%s
"""

pin21 = machine.Pin(21, machine.Pin.OUT)
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
        pin21.value( not pin21.value())
    print("AP active: %s %s" % (ap.config('essid'), ap.ifconfig()))
    pin21.on()

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
            html = web_page()
        else:
            html = web_page(res['essid'], res['pswd'], res['srv'],
                            res['port'],res['message'])
        response = HTTP_RESPONSE % (len(html), html)
        conn.send(response)
        conn.close()

def process_request(request):
    req = request.decode().split('\n')[0].strip().split(' ')
    fields = ('essid', 'pswd', 'srv', 'port')
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
    count = 0
    for k in fields:
        if k in resdict.keys():
            count += 1
    if count != len(fields):
        resdict = None
    else:
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
            find_servers(resdict['srv'], resdict['port'])
            try:
                fh = open(CFG_NAME, 'w')
                fh.write(resdict['essid'] + '\n')
                fh.write(resdict['pswd'] + '\n')
                fh.write(resdict['srv'] + ':' + resdict['port'] + '\n')
                fh.close()
                resdict['message'] += ' Settings stored. Please restart.'
            except Exception as e:
                resdict['message'] += ' Settings storing error. %s' % e
                print(e)
        wlan.active(False)

    print("Res dict: %s" % resdict)
    return resdict

def find_servers(ip, port):
    try:
        m = re.match("(.*\.)\d*$", ip).group(1)
        print("Network: %s" % m)
        for i in range(1,256):
            cip = "%s%s" % (m, i)
            print("Current IP: %s" % cip)
    except Exception as e:
        print("Find server error: %s" % str(e))

def web_page(essid='essid', pswd='password', server='192.168.1.5', port='8088', message=''):
  html = """<html><body><h1>ESP: %s </h1>""" % ap.config('essid')
  html += """<form action="/" method="get">
<p>ESSID:<input name="essid" type=text value="%s"></p>
<p>Password:<input name="pswd" type=text value="%s"></p>
<p>Server IP:<input name="srv" type=text value="%s"></p>
<p>Server Port:<input name="port" type=text value="%s"></p>
<p><input type="submit" value="Submit"></p>
</form>
<hr>
%s
""" % (essid, pswd, server, port, message)
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

def run():
    print("Run AP.")
    start_ap()
    start_httpd()

    return (None, None)
