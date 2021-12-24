import time,random
from main import *

from espwconst import *
pause = 2 

def run():
    while True :
        palt.duty(random.randint(78,124))
        time.sleep(pause)
        paz.duty(random.randint(28,124))
        time.sleep(pause)
