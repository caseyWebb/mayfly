from digitalio import Direction
from pins import buzzer
import time

buzzer.direction = Direction.OUTPUT


def beep_confirm():
    beep_morse(".")


def beep_success():
    beep_morse("..")


def beep_done():
    beep_morse("...")


def beep_error():
    beep_morse("---")


def beep_morse(sequence):
    for symbol in sequence:
        if symbol == ".":
            buzzer.value = True
            time.sleep(0.1)
        elif symbol == "-":
            buzzer.value = True
            time.sleep(0.3)
        buzzer.value = False
        time.sleep(0.1)
