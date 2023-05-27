# This module is added by the forked version of CircuitPython. It adds a function to
# convert raw ADC values to voltages so we can use the values read by the ULP in Python.
import espadc


# https://files.atlas-scientific.com/Gravity-pH-datasheet.pdf
def __pH(raw):
    mV = espadc.raw_to_voltage(raw)
    return (-5.6548 * mV / 1000) + 15.509


# https://files.atlas-scientific.com/Gravity-DO-datasheet.pdf
def __DO_percent_saturation(raw):
    cal = 278
    mV = espadc.raw_to_voltage(raw)
    return mV / cal * 100


# Magic
def __DO_mg_L(water_temp, DO_percent_saturation):
    return (DO_percent_saturation / 100) * (
        14.641
        - 0.41022 * water_temp
        + 0.007991 * water_temp**2
        - 0.000077774 * water_temp**3
    )


# https://www.analog.com/media/en/technical-documentation/data-sheets/DS18B20.pdf
def __ds18b20(raw):
    return raw / 16.0


def __modified(bit_mask):
    return {
        "pH": bool(bit_mask & (1 << 0)),
        "DO": bool(bit_mask & (1 << 1)),
        "air_temp": bool(bit_mask & (1 << 2)),
        "water_temp": bool(bit_mask & (1 << 3)),
    }


class Sensors:
    def __init__(self, shared_memory):
        self.air_temp = __ds18b20(shared_memory.air_temp)
        self.water_temp = __ds18b20(shared_memory.water_temp)
        self.pH = __pH(shared_memory.pH)
        self.DO_percent_saturation = __DO_percent_saturation(shared_memory.DO)
        self.DO_mg_L = __DO_mg_L(self.water_temp, self.DO_percent_saturation)
        self.modified = __modified(shared_memory.modified)

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
