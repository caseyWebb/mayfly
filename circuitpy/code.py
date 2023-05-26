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


def init():
    # We don't use the second LDO, disable it to save power
    ldo2.disable()

    print("Initializing WiFi...", end=" ")
    init_wifi()
    print("Done!")

    print("Setting time...", end=" ")
    set_time()
    print("Done!")

    print("Starting ULP...", end=" ")
    ulp.start()
    print("Done!")


def update():
    # print("pH:", sensors.pH)
    # print("DO:", sensors.DO)
    print("Air temp:", sensors.air_temp)
    print("Water temp:", sensors.water_temp)
    print("Modified:", sensors.modified)
    
    ulp.resume()

    # print("Updating display...", end=" ")
    # Display().update(datetime.now())
    # print("Done!")

def main():
    if alarm.wake_alarm == None:
        print("No wake alarm, initializing...")
        init()
    else:
        print("ULP requested wake up at", datetime.now())
        update()

    print("Entering deep sleep at", datetime.now())
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)

main()