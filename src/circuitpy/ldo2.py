import time
import board
from digitalio import DigitalInOut, Direction


def enable():
    ldo2.value = True
    time.sleep(0.035)

def disable():
    ldo2.value = False
    time.sleep(0.035)

ldo2 = DigitalInOut(board.LDO2)
ldo2.direction = Direction.OUTPUT
