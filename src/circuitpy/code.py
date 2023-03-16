from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime
from adafruit_display_text import label
import adafruit_il0373
import adafruit_ntp
import board
import busio
from digitalio import DigitalInOut, Direction
import displayio
import ldo2 as ldo2
import rtc
from secrets import WIFI_SSID, WIFI_PASS, TZ_OFFSET
import socketpool
import time
from ulp.ulp import ULP
import wifi

DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128
BACKGROUND_COLOR = 0xFFFFFF
FOREGROUND_COLOR = 0x000000
FONT = bitmap_font.load_font("/font/UpheavalTT-BRK--28.bdf")
SMALL_FONT = bitmap_font.load_font("/font/UpheavalTT-BRK--16.bdf")

EPD_CS = board.D5
EPD_DC = board.D6


def init_wifi():
    wifi.radio.connect(WIFI_SSID, WIFI_PASS)


def init_display():
    displayio.release_displays()
    spi = busio.SPI(board.SCK, board.MOSI)
    display_bus = displayio.FourWire(
        spi, command=EPD_DC, chip_select=EPD_CS, baudrate=1000000
    )
    return adafruit_il0373.IL0373(
        display_bus,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        rotation=270,
        black_bits_inverted=False,
        color_bits_inverted=False,
        grayscale=True,
        refresh_time=1,
    )


def set_time():
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime


def add_text_to_group(group, text, x, y, font=FONT):
    text_group = displayio.Group(scale=1, x=x, y=y)
    text_area = label.Label(text=text, font=font, color=FOREGROUND_COLOR)
    text_group.append(text_area)
    group.append(text_group)


def update_display(display):
    g = displayio.Group()
    palette = displayio.Palette(1)
    palette[0] = BACKGROUND_COLOR

    background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    t = displayio.TileGrid(background_bitmap, pixel_shader=palette)
    g.append(t)

    add_text_to_group(g, "pH: 7.0", 20, 15)
    add_text_to_group(g, "DO: 50%", 20, 45)
    add_text_to_group(g, "Temp (Air): 25C", 20, 75)
    add_text_to_group(g, "Temp (Water): 25C", 20, 105)

    now = datetime.now()
    updated_at = f'{now.month}/{now.day} {now.hour}:{now.minute:02}'

    add_text_to_group(g, "Last updated:", 160, 15, SMALL_FONT)
    add_text_to_group(g, updated_at, 160, 30, SMALL_FONT)

    display.show(g)
    display.refresh()

def ulp_start():
    ULP().run()

# led = DigitalInOut(board.IO11)
# led.direction = Direction.OUTPUT

# def blink():
#     print("Turning on LED")
#     led.value = True
#     time.sleep(3)
#     print("Turning off LED")
#     led.value = False
#     time.sleep(3)


def loop(display):
    update_display(display)


def main():
    # We don't use the second LDO, so we can disable it to save power
    # ldo2.disable()

    # init_wifi()
    # set_time()
    # display = init_display()
    
    print("starting ulp")
    ulp_start()
    print("started ulp")
    
    while True:
        time.sleep(1)
        print("loop")

    # while True:
        # blink()
        # loop(display)
        



main()
