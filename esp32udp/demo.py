import time
from main import *

from espwconst import *

def run():
    paz.deinit()
    palt.deinit()
    palt.init(duty=ALT_MIN)
    paz.init(duty=AZ_MAX)
    time.sleep(1)
    r = AZ_MAX-AZ_MIN
    pause = .2
    while True :
        for i in range(r+1):
            if i > int(r/2):
                palt.duty(ALT_MAX - int((ALT_MAX-ALT_MIN)/r*i))
            else:
                palt.duty(ALT_MIN + int((ALT_MAX-ALT_MIN)/r*i))
            paz.duty(AZ_MAX - int((AZ_MAX-AZ_MIN)/r*i))
            time.sleep(pause)
    paz.deinit()
    palt.deinit()

