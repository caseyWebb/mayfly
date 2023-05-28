from adafruit_datetime import datetime
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_ntp
import alarm
from config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC,
    TZ_OFFSET,
    WIFI_PASS,
    WIFI_SSID,
)
from display import Display
from digitalio import Direction, Pull
import espadc
from espulp import ULPAlarm
import json
from pins import ldo2, buzzer, BUTTON_A_PIN, button_b, button_c
import rtc
from sensors import Sensors
import socketpool
import supervisor
from time import sleep
from ulp import ULP, ULPRunMode

ulp = ULP()


def get_calibration():
    try:
        with open("/calibration/calibration.json") as f:
            return json.load(f)

    except Exception as e:
        print("Exception reading calibration:", e)
        return {
            "ph": {
                "low": 4,
                "mid": 7,
                "high": 10,
            },
            "DO": 400,
        }


def set_calibration(calibration):
    try:
        with open("/calibration/calibration.json", "w") as f:
            json.dump(calibration, f)

    except Exception as e:
        print("Exception writing calibration:", e)


def get_current_time():
    try:
        return datetime.now()

    except:
        return None


def get_wifi_connection(attempts=0):
    try:
        # Sometimes importing the wifi module throws a MemoryError
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


def init():
    # Disable the second LDO to save power
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
    display = Display()
    now = get_current_time()
    calibration = get_calibration()
    sensors = Sensors(ulp.shared_memory, calibration)

    if ulp.shared_memory.debug:
        sensors.print()
        ulp.set_run_mode(ULPRunMode.NORMAL)
    else:
        display.show_sensors(now, sensors)

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


def calibrate():
    ulp.set_run_mode(ULPRunMode.CALIBRATION)

    calibration = get_calibration()
    display = Display()
    sensors = Sensors(ulp.shared_memory, calibration)

    display.show_message("Calibrating...")
    beep()
    print("Waiting for confirmation...")
    confirmed = wait_for_confirmation(button_b, button_c)
    if confirmed:
        beep()
        print("Confirmed, calibrating DO...")
        readings = list((0,) * 10)
        i = 0
        threshold = 80
        while True:
            raw = sensors.raw["DO"]
            readings[i] = raw
            spread = max(readings) - min(readings)
            i = (i + 1) % 10
            print(raw, f"∆{spread}")
            if len(readings) == 10 and spread < threshold:
                break
            sleep(0.1)
        calibration["DO"] = espadc.raw_to_voltage(round(sum(readings) / len(readings)))
        beep()

    print("Saving calibration...", end=" ")
    set_calibration(calibration)
    print("Done!")


def beep():
    buzzer.direction = Direction.OUTPUT
    buzzer.value = True
    sleep(0.25)
    buzzer.value = False


def wait_for_confirmation(confirm_button, cancel_button):
    confirm_button.direction = Direction.INPUT
    cancel_button.direction = Direction.INPUT
    confirm_button.pull = Pull.UP
    cancel_button.pull = Pull.UP
    while True:
        if not confirm_button.value:
            return True
        elif not cancel_button.value:
            return False


def main():
    try:
        # Auto-reload and the ULP is a bad time. Use serial communication or hardware to reset.
        supervisor.runtime.autoreload = False

        if alarm.wake_alarm == None:
            print("No wake alarm detected, initializing...")
            init()
        elif isinstance(alarm.wake_alarm, ULPAlarm):
            print("ULP requested wake-up, updating...")
            update()
        elif isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
            print("Calibration button pressed, starting calibration...")
            calibrate()
            ulp.set_run_mode(ULPRunMode.NORMAL)

    except Exception as e:
        print("Exception encountered:", e)

    finally:
        calibration_button_alarm = alarm.pin.PinAlarm(
            pin=BUTTON_A_PIN, value=False, pull=True
        )
        print("Entering deep sleep")
        alarm.exit_and_deep_sleep_until_alarms(ulp.alarm, calibration_button_alarm)


main()
