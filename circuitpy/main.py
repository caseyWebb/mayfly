from adafruit_datetime import datetime
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_ntp
import alarm
from button import wait_for_confirmation, wait_for_selection
from buzzer import beep_confirm, beep_done, beep_error, beep_success, beep_morse
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
from pins import ldo2, buzzer, button_a, button_b, BUTTON_C_PIN
import rtc
from sensors import Sensors
import socketpool
import supervisor
import time
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
                "low": 2030,
                "mid": 1500,
                "high": 975,
            },
            "DO": 440,
        }


def set_calibration(calibration):
    with open("/calibration/calibration.json", "w") as f:
        json.dump(calibration, f)


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

    sensors.print()

    if ulp.shared_memory.debug:
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
    try:
        ulp.set_run_mode(ULPRunMode.CALIBRATION)
        beep_confirm()

        selected = wait_for_selection(button_a, button_b, timeout=30)

        if selected == button_a:
            print("Dissolved oxygen selected")
            beep_morse("-..")  # d
            calibrate_DO()
        elif selected == button_b:
            print("pH selected")
            beep_morse(".--.")  # p
            calibrate_pH()
    finally:
        ulp.set_run_mode(ULPRunMode.NORMAL)


def calibrate_DO():
    print("Waiting for confirmation...")
    wait_for_confirmation(button_a, timeout=20)
    beep_confirm()

    while not ulp.shared_memory.calibration_ready:
        print("Waiting for ULP to wake up...")
        time.sleep(5)

    print("Ready. Taking DO readings...")

    calibration = get_calibration()
    sensors = Sensors(ulp.shared_memory, calibration)
    stable_threshold = 80
    stable_timeout = 30
    readings = list((0,) * 10)
    i = 0
    start = time.monotonic()
    while True:
        if time.monotonic() - start > stable_timeout:
            raise TimeoutError("Timed out waiting for stable reading!")
        raw = sensors.raw["DO"]
        readings[i] = raw
        spread = max(readings) - min(readings)
        i = (i + 1) % 10
        print(raw, f"∆{spread}")
        if len(readings) == 10 and spread < stable_threshold:
            break
        time.sleep(0.1)

    saturation_mV = espadc.raw_to_voltage(round(sum(readings) / len(readings)))

    if saturation_mV < 1:
        raise ValueError("Invalid saturation voltage!")

    print("Saving calibration...", end=" ")
    calibration["DO"] = saturation_mV
    set_calibration(calibration)
    print("Done!")
    time.sleep(0.5)
    beep_done()


def calibrate_pH():
    calibration = get_calibration()
    sensors = Sensors(ulp.shared_memory, calibration)
    stable_threshold = 80
    stable_timeout = 30

    low_cal_mV = -1
    mid_cal_mV = -1
    high_cal_mV = -1

    for i in range(3):
        print("Waiting for confirmation...")
        # longer timeout to allow rinsing probe and moving to next buffer
        wait_for_confirmation(button_a, timeout=120)
        beep_confirm()

        print("Ready. Taking pH readings...")
        start = time.monotonic()
        readings = list((0,) * 10)
        i = 0
        while True:
            if time.monotonic() - start > stable_timeout:
                raise TimeoutError("Timed out waiting for stable reading!")
            raw = sensors.raw["pH"]
            readings[i] = raw
            spread = max(readings) - min(readings)
            i = (i + 1) % 10
            print(raw, f"∆{spread}")
            if len(readings) == 10 and spread < stable_threshold:
                break
            time.sleep(0.1)

        cal_mV = espadc.raw_to_voltage(round(sum(readings) / len(readings)))

        # auto-detect calibration point
        sensors.update()
        if sensors.pH > 9:
            high_cal_mV = cal_mV
        elif sensors.pH < 5:
            low_cal_mV = cal_mV
        else:
            mid_cal_mV = cal_mV

        # beep to indicate calibration point taken, but only for first two
        if i < 2:
            beep_success()

    if low_cal_mV == -1 or mid_cal_mV == -1 or high_cal_mV == -1:
        raise Exception("Missing calibration point!")

    print("Saving calibration...", end=" ")
    calibration["pH"] = {
        "low": low_cal_mV,
        "mid": mid_cal_mV,
        "high": high_cal_mV,
    }
    set_calibration(calibration)
    print("Done!")

    beep_done()


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

    except Exception as e:
        beep_error()
        print("Exception encountered:", e)

    finally:
        calibration_button_alarm = alarm.pin.PinAlarm(
            pin=BUTTON_C_PIN, value=False, pull=True
        )
        print("Entering deep sleep")
        alarm.exit_and_deep_sleep_until_alarms(ulp.alarm, calibration_button_alarm)


main()
