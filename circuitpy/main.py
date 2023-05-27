import alarm
from ulp import ULP  # type: ignore

ulp = ULP()


def get_wifi_connection(attempts=0):
    try:
        from secrets import (
            WIFI_SSID,  # type: ignore
            WIFI_PASS,  # type: ignore
        )
        import socketpool
        import wifi

        print(f"Connecting to WiFi network {WIFI_SSID}...", end=" ")
        wifi.radio.connect(WIFI_SSID, WIFI_PASS, timeout=3)
        print("Done!")

        return socketpool.SocketPool(wifi.radio)

    except Exception as e:
        if attempts < 3:
            print("Exception encoutered:", e)
            print(f"Trying again ({++attempts}/3)")
            return get_wifi_connection()
        else:
            print("Giving up!")
            return None


def get_current_time():
    try:
        from adafruit_datetime import datetime

        return datetime.now()

    except:
        return None


def init():
    import adafruit_ntp
    import board
    from digitalio import DigitalInOut, Direction
    import rtc
    from secrets import TZ_OFFSET  # type: ignore

    # Disable the second LDO to save power
    ldo2 = DigitalInOut(board.LDO2)
    ldo2.direction = Direction.OUTPUT
    ldo2.value = False

    pool = get_wifi_connection()
    if pool is None:
        return

    print("Setting time...", end=" ")
    ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime
    print("Done!")

    print("Starting ULP...", end=" ")
    ulp.start()
    print("Done!")


def update():
    from adafruit_datetime import datetime
    from display import Display
    from sensors import Sensors
    from secrets import (
        MQTT_TOPIC,  # type: ignore
        MQTT_BROKER,  # type: ignore
        MQTT_PORT,  # type: ignore
    )
    import adafruit_minimqtt.adafruit_minimqtt as MQTT

    debug = ulp.shared_memory.read_bool("debug")
    display = Display()
    now = get_current_time()
    sensors = Sensors(ulp.shared_memory)

    if debug:
        print("Time:", now)
        print("pH:", sensors.pH)
        print("DO (mg/L):", sensors.DO_mg_L)
        print("DO (% sat):", sensors.DO_percent_saturation)
        print("Air temp:", sensors.air_temp)
        print("Water temp:", sensors.water_temp)
        print("Modified:", sensors.modified)
        ulp.resume()
    else:
        display.update(now, sensors)

    pool = get_wifi_connection()
    if pool is None:
        return

    mqtt = MQTT.MQTT(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        socket_pool=pool,
    )
    payload = sensors.to_binary()

    print(f"Sending data {payload} to MQTT broker {MQTT_BROKER}...", end=" ")
    mqtt.connect()
    mqtt.publish(MQTT_TOPIC, payload)
    mqtt.disconnect()
    print("Done!")


try:
    import supervisor

    # Auto-reload and the ULP is a bad time. Use serial communication or hardware to reset.
    supervisor.runtime.autoreload = False

    if alarm.wake_alarm == None:
        init()
    else:
        update()

except Exception as e:
    print("Exception encountered:", e)

finally:
    print("Entering deep sleep")
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)
