# This module is added by the forked version of CircuitPython. It adds a function to
# convert raw ADC values to voltages so we can use the values read by the ULP in Python.
import espadc


class Sensors:
    def __init__(self, shared_memory, calibration):
        self.__shared_memory = shared_memory
        self.__calibration = calibration
        self.update()

    def update(self):
        self.air_temp = self.__ds18b20(self.__shared_memory.air_temp)
        self.water_temp = self.__ds18b20(self.__shared_memory.water_temp)
        self.pH = self.__pH()
        self.DO_percent_saturation = self.__DO_percent_saturation()
        self.DO_mg_L = self.__DO_mg_L(self.water_temp, self.DO_percent_saturation)
        self.modified = self.__modified()

    @property
    def raw(self):
        return {
            "air_temp": self.__shared_memory.air_temp,
            "water_temp": self.__shared_memory.water_temp,
            "pH": self.__shared_memory.pH,
            "DO": self.__shared_memory.DO,
        }

    def print(self):
        print("pH:", self.pH)
        print("DO (mg/L):", self.DO_mg_L)
        print("DO (% sat):", self.DO_percent_saturation)
        print("Air temp:", self.air_temp)
        print("Water temp:", self.water_temp)
        print("Modified:", self.modified)

    # Binary format to send across the wire
    # 0x00: air_temp
    # 0x01: water_temp
    # 0x02: pH (in 0.1 increments)
    # 0x03: DO_percent_saturation
    def to_binary(self):
        return (
            (int(round(self.air_temp)) << 24)
            | (int(round(self.water_temp)) << 16)
            | (int(round(self.pH * 10)) << 8)
            | int(round(self.DO_percent_saturation))
        )

    # https://files.atlas-scientific.com/Gravity-pH-datasheet.pdf
    def __pH(self):
        mV = espadc.raw_to_voltage(self.__shared_memory.pH)
        cal = self.__calibration["pH"]
        if mV > cal["mid"]:  # high voltage = low pH
            return 7 - 3 / (cal["low"] - cal["mid"]) * (mV - cal["mid"])
        else:
            return 7 - 3 / (cal["mid"] - cal["high"]) * (mV - cal["mid"])

    # https://files.atlas-scientific.com/Gravity-DO-datasheet.pdf
    def __DO_percent_saturation(self):
        cal = self.__calibration["DO"]
        mV = espadc.raw_to_voltage(self.__shared_memory.DO)
        return mV / cal * 100

    # Magic
    def __DO_mg_L(self, water_temp, DO_percent_saturation):
        return (DO_percent_saturation / 100) * (
            14.641
            - 0.41022 * water_temp
            + 0.007991 * water_temp**2
            - 0.000077774 * water_temp**3
        )

    # https://www.analog.com/media/en/technical-documentation/data-sheets/DS18B20.pdf
    def __ds18b20(self, raw):
        return raw / 16.0

    def __modified(self):
        return {
            "pH": bool(self.__shared_memory.modified & (1 << 0)),
            "DO": bool(self.__shared_memory.modified & (1 << 1)),
            "air_temp": bool(self.__shared_memory.modified & (1 << 2)),
            "water_temp": bool(self.__shared_memory.modified & (1 << 3)),
        }
