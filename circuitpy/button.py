from digitalio import Direction, Pull
import time


def wait_for_confirmation(btn, timeout=5):
    btn.direction = Direction.INPUT
    btn.pull = Pull.UP
    start = time.monotonic()
    while True:
        if time.monotonic() - start > timeout:
            raise TimeoutError("Timed out waiting for confirmation!")
        elif not btn.value:
            return True


def wait_for_selection(btn1, btn2, timeout=10):
    btn1.direction = Direction.INPUT
    btn2.direction = Direction.INPUT
    btn1.pull = Pull.UP
    btn2.pull = Pull.UP
    start = time.monotonic()
    while True:
        if time.monotonic() - start > timeout:
            raise TimeoutError("Timed out waiting for selection!")
        elif not btn1.value:
            return btn1
        elif not btn2.value:
            return btn2
