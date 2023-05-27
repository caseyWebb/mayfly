def init(ulp):
    try:
        import adafruit_ntp
        import ldo2 as ldo2
        import rtc
        from secrets import TZ_OFFSET  # type: ignore
        import socketpool
        import wifi

        ldo2.disable()

        print("Setting time...", end=" ")
        pool = socketpool.SocketPool(wifi.radio)
        ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
        rtc.RTC().datetime = ntp.datetime
        print("Done!")

        print("Starting ULP...", end=" ")
        ulp.start()
        print("Done!")

    except Exception as e:
        print("Exception encoutered:", e)
        print("Trying again...")
        init(ulp)


def update(ulp):
    from display import Display
    from sensors import Sensors
    from secrets import (
        MQTT_TOPIC,  # type: ignore
        MQTT_BROKER,  # type: ignore
        MQTT_PORT,  # type: ignore
    )
    import socketpool
    import adafruit_minimqtt.adafruit_minimqtt as MQTT
    import wifi

    debug = ulp.shared_memory.read_bool("debug")
    pool = socketpool.SocketPool(wifi.radio)
    sensors = Sensors(ulp.shared_memory)
    mqtt_client = MQTT.MQTT(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        socket_pool=pool,
    )

    if debug:
        print("pH:", sensors.pH)
        print("DO (mg/L):", sensors.DO_mg_L)
        print("DO (% sat):", sensors.DO_percent_saturation)
        print("Air temp:", sensors.air_temp)
        print("Water temp:", sensors.water_temp)
        print("Modified:", sensors.modified)
        ulp.resume()
    else:
        Display().update(datetime.now(), sensors)

    print(f"Sending data to MQTT broker {MQTT_BROKER}...", end=" ")
    mqtt_client.connect()
    mqtt_client.publish(MQTT_TOPIC, sensors.to_binary())
    mqtt_client.disconnect()
    print("Done!")


import alarm
from ulp import ULP  # type: ignore

ulp = ULP()

try:
    from adafruit_datetime import datetime
    from secrets import (
        WIFI_SSID,  # type: ignore
        WIFI_PASS,  # type: ignore
    )
    import supervisor
    import wifi

    # Auto-reload and the ULP is a bad time. Use serial communication or hardware to reset.
    supervisor.runtime.autoreload = False

    print(f"Connecting to WiFi network {WIFI_SSID}...", end=" ")
    wifi.radio.connect(WIFI_SSID, WIFI_PASS)
    print("Done!")

    if alarm.wake_alarm == None:
        print("No wake alarm, initializing...")
        init(ulp)
    else:
        print("ULP requested wake up at", datetime.now())
        update(ulp)

except Exception as e:
    print("Exception encountered:", e)

finally:
    print("Entering deep sleep at", datetime.now())
    alarm.exit_and_deep_sleep_until_alarms(ulp.alarm)
