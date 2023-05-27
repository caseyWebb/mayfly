def init(ulp):
    import adafruit_ntp
    import ldo2 as ldo2
    import rtc
    from secrets import WIFI_SSID, WIFI_PASS, TZ_OFFSET
    import socketpool
    import wifi

    # We don't use the second LDO, disable it to save power
    ldo2.disable()

    print("Initializing WiFi...", end=" ")
    wifi.radio.connect(WIFI_SSID, WIFI_PASS)
    print("Done!")

    print("Setting time...", end=" ")
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime
    print("Done!")

    print("Starting ULP...", end=" ")
    ulp.start()
    print("Done!")


def update(ulp):
    from display import Display
    from sensors import Sensors
    import socketpool
    import adafruit_minimqtt.adafruit_minimqtt as MQTT
    import wifi

    mqtt_topic = "mayfly/backyard"
    pool = socketpool.SocketPool(wifi.radio)
    sensors = Sensors(ulp.shared_memory)

    def on_connect(client, userdata, flags, rc):
        print("Connected to MQTT broker!")

    def on_disconnect(client, userdata, rc):
        print("Disconnected from MQTT broker!")

    def on_publish(client, userdata, topic, pid):
        print(f"Published to {topic} with PID {pid}!")

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


try:
    from adafruit_datetime import datetime
    import alarm
    from ulp import ULP
    import supervisor

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
except:
    import microcontroller

    print("Exception encountered, resetting microcontroller...")
    microcontroller.reset()
