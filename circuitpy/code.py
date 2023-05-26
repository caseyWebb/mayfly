from adafruit_datetime import datetime
import adafruit_ntp
import alarm
from display import Display
import ldo2 as ldo2
import rtc
from secrets import WIFI_SSID, WIFI_PASS, TZ_OFFSET
from sensors import Sensors
import socketpool
import supervisor
from ulp import ULP
import wifi

DEBUG = True

# Auto-reload and the ULP is a bad time. Use serial communication or hardware to reset.
supervisor.runtime.autoreload = False

ulp = ULP()
sensors = Sensors(ulp.shared_memory)

def init_wifi():
    wifi.radio.connect(WIFI_SSID, WIFI_PASS)


def set_time():
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime

def log(*args, **kwargs):
    if DEBUG: print(*args, **kwargs)

def init():
    # We don't use the second LDO, disable it to save power
    ldo2.disable()

    log("Initializing WiFi...", end=" ")
    init_wifi()
    log("Done!")

    log("Setting time...", end=" ")
    set_time()
    log("Done!")

    log("Starting ULP...", end=" ")
    ulp.start()
    log("Done!")


def update():
    if DEBUG:
        log("pH:", sensors.pH)
        log("DO:", sensors.DO)
        log("Air temp:", sensors.air_temp)
        log("Water temp:", sensors.water_temp)
        log("Modified:", sensors.modified)
        ulp.resume()
    else:
        Display().update(datetime.now())

def main():
    if alarm.wake_alarm == None:
        log("No wake alarm, initializing...")
        init()
    else:
        log("ULP requested wake up at", datetime.now())
        update()

    log("Entering deep sleep at", datetime.now())
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)

main()