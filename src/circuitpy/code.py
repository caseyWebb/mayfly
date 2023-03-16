from adafruit_datetime import datetime
import adafruit_ntp
import alarm
from display import Display
import ldo2 as ldo2
import rtc
from secrets import WIFI_SSID, WIFI_PASS, TZ_OFFSET
import socketpool
from ulp import ULP
import wifi

def init_wifi():
    wifi.radio.connect(WIFI_SSID, WIFI_PASS)


def set_time():
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime


def main():
    # We don't use the second LDO, disable it to save power
    ldo2.disable()

    ulp = ULP()

    if alarm.wake_alarm == None:
        print("No wake alarm, initializing...")

        print("Initializing WiFi...", end=" ")
        init_wifi()
        print("Done!")

        print("Setting time...", end=" ")
        set_time()
        print("Done!")
    
        print("Starting ULP...", end=" ")
        ulp.start()
        print("Done!")
    else:
        print("Wake alarm detected, updating...")
        
        print("shared_mem", ulp.shared_mem)

        print("Updating display...", end=" ")
        Display().update(datetime.now())
        print("Done!")


    print("Entering deep sleep...")
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)

main()
