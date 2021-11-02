import esp, network, machine, time, socket, re, json

from espwconst import *
import main, lib

CFG_NAME = '_config'
HTTP_RESPONSE = b"""\
HTTP/1.0 200 OK
Content-Length: %d

%s
"""

ap = None

def start_ap():
    "Start WiFi Access POINT with default ISSID like ESP_XXXXXX and no password."
    global ap
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    while ap.active() == False:
        time.sleep(1)
    print("AP active: %s %s" % (ap.config('essid'), ap.ifconfig()))

def start_httpd():
    "Simple httpd"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        print('Got a connection from %s' % str(addr))
        request = conn.recv(1024)
        res = process_request(request)
        if not res:
            cfg = lib.get_config()
            html = web_page(cfg)
        else:
            html = web_page(res)
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

def reset():
    machine.reset()

def action(act):
    switch = {
        'az_min': az_min,
        'az_mid': az_mid,
        'az_max': az_max,
        'alt_min': alt_min,
        'alt_mid': alt_mid,
        'alt_max': alt_max,
        'reset': reset
    }
    func = switch.get(act, az_mid)
    try:
        return func()
    except Exception as e:
        print(e)

def process_request(request):
    print("Req decode: %s" % request.decode().split('\n')[0].strip().split(' '))
    req = request.decode().split('\n')[0].strip().split(' ')
    fields = ('essid', 'pswd', 'tz', 'longitude', 'action')
    get = '' if len(req) < 3 else req[1]
    lst = get.split('?')
    get = '' if len(lst) < 2 else lst[1]
    print('Request = %s' % get)
    lst = get.split('&')
    resdict = {}
    for part in lst:
        try:
            pair = part.split('=')
            resdict[pair[0]]=lib.unquote(pair[1]).decode()
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
            try:
                fh = open(CFG_NAME, 'w')
                fh.write(json.dumps(resdict))
                fh.close()
                resdict['message'] += ' Settings stored. Please restart.'
            except Exception as e:
                resdict['message'] += ' Settings storing error. %s' % e
                print("Store cfg error: %s" % e)
        wlan.active(False)

    return resdict

def web_page(cfg):
    html = """<html><body><h1>%s</h1>""" % ap.config('essid')
    html += """<form action="/" method="get">
<p>ESSID:<input name="essid" type=text value="%(essid)s"></p>
<p>Password:<input name="pswd" type=text value="%(pswd)s"></p>
<p>Time: UTC + <input name="tz" type=text value="%(tz)s"></p>
<p>Latitude: <input name="longitude" type=text value="%(longitude)s"></p>
<p>Action: %(action)s
<br>
Azimuth:<input name="action" type="radio" value="az_min">West
<input name="action" type="radio" value="az_mid" checked>South
<input name="action" type="radio" value="az_max">East
<br>
Altitude:<input name="action" type="radio" value="alt_min">Low
<input name="action" type="radio" value="alt_mid">middle
<input name="action" type="radio" value="alt_max">Zenith
<br>
Reset:<input name="action" type="radio" value="reset">
</p>
<p><input type="submit" value="Submit"></p>
</form>
<hr>
%(message)s
</body></html>
""" % cfg
    return html

def run():
    print("Run AP.")
    start_ap()
    start_httpd()
    return (None, None)
