# This module is added by the forked version of CircuitPython. It adds a function to
# convert raw ADC values to voltages so we can use the values read by the ULP in Python.
import espadc


class Sensors:
    def __init__(self, shared_memory):
        self.__shared_memory = shared_memory

    # https://files.atlas-scientific.com/Gravity-pH-datasheet.pdf
    @property
    def pH(self):
        raw = self.__shared_memory.read_uint16("pH")
        mV = espadc.raw_to_voltage(raw)
        return (-5.6548 * mV / 1000) + 15.509

    # https://files.atlas-scientific.com/Gravity-DO-datasheet.pdf
    @property
    def DO_mg_L(self):
        T = self.water_temp
        P = self.DO_percent_saturation / 100
        return P * (14.641 - 0.41022 * T + 0.007991 * T**2 - 0.000077774 * T**3)

    @property
    def DO_percent_saturation(self):
        cal = 278
        raw = self.__shared_memory.read_uint16("DO")
        mV = espadc.raw_to_voltage(raw)
        return mV / cal * 100

    # https://www.analog.com/media/en/technical-documentation/data-sheets/DS18B20.pdf
    @property
    def air_temp(self):
        return self.__shared_memory.read_uint16("air_temp") / 16.0

    # Same as above
    @property
    def water_temp(self):
        return self.__shared_memory.read_uint16("water_temp") / 16.0

    @property
    def modified(self):
        return self.__shared_memory.read_bool("modified")
