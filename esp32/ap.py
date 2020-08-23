import esp
import network
import machine
import time
import socket

pin21 = machine.Pin(21, machine.Pin.OUT)
ap = None

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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        print('Got a connection from %s' % str(addr))
        request = conn.recv(1024)
        print('Content = %s' % str(request))
        response = web_page()
        conn.send(response)
        conn.close()

def web_page():
  html = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
  <body><h1>ESP: %s </h1>""" % ap.config('essid')
  html += """<form action="/" method="get">
             <p>ESSID:<input name="essid" type=text value="essid"></p>
             <p>Password:<input name="pswd" type=text value="password"></p>
             <p>Server IP:<input name="srv" type=text value="192.168.1.5:8088"></p>
             <p><input type="submit" value="Submit"></p>
             </form>
          """
  html += """</body></html>""" 
  return html

def run():
    print("Run AP.")
    start_ap()
    start_httpd()

    return (None, None)
