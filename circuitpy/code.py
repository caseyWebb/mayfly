from adafruit_datetime import datetime
import adafruit_ntp
import alarm
from display import Display
import ldo2 as ldo2
import rtc
from secrets import WIFI_SSID, WIFI_PASS, TZ_OFFSET
import socketpool
import supervisor
from ulp import ULP
import wifi

supervisor.runtime.autoreload = False

def init_wifi():
    wifi.radio.connect(WIFI_SSID, WIFI_PASS)


def set_time():
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime


def main():

    ulp = ULP()

    if alarm.wake_alarm == None:
        print("No wake alarm, initializing...")
        
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
    else:
        print("ULP requested wake up at", datetime.now())
        print("shared_mem", ulp.shared_memory)

        print("Updating display...", end=" ")
        # Display().update(datetime.now())
        print("Done!")


    print("Entering deep sleep at", datetime.now())
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)

main()