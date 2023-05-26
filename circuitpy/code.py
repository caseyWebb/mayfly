from adafruit_datetime import datetime
import alarm
from secrets import WIFI_SSID, WIFI_PASS, TZ_OFFSET
import supervisor
from ulp import ULP

try:
    import wifi
except MemoryError:
    import microcontroller

    print("MemoryError importing wifi module, resetting microcontroller...")
    microcontroller.reset()


def init(ulp):
    def init_wifi():
        wifi.radio.connect(WIFI_SSID, WIFI_PASS)

    def set_time():
        import adafruit_ntp
        import rtc
        import socketpool

        pool = socketpool.SocketPool(wifi.radio)
        ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
        rtc.RTC().datetime = ntp.datetime

    import ldo2 as ldo2

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


def update(ulp):
    from display import Display
    from sensors import Sensors

    sensors = Sensors(ulp.shared_memory)

    if ulp.shared_memory.read_bool("debug"):
        print("pH:", sensors.pH)
        print("DO (mg/L):", sensors.DO_mg_L)
        print("DO (% sat):", sensors.DO_percent_saturation)
        print("Air temp:", sensors.air_temp)
        print("Water temp:", sensors.water_temp)
        print("Modified:", sensors.modified)
        ulp.resume()
    else:
        Display().update(datetime.now(), sensors)


def main():
    # Auto-reload and the ULP is a bad time. Use serial communication or hardware to reset.
    supervisor.runtime.autoreload = False

    ulp = ULP()

    if alarm.wake_alarm == None:
        print("No wake alarm, initializing...")
        init(ulp)
    else:
        print("ULP requested wake up at", datetime.now())
        update(ulp)

    print("Entering deep sleep at", datetime.now())
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)


main()
