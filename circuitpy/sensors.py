# This module is added by the forked version of CircuitPython. It adds a function to
# convert raw ADC values to voltages so we can use the values read by the ULP in Python.
import espadc

class Sensors:
    def __init__(self, shared_memory):
        self.__shared_memory = shared_memory

    @property
    def pH(self):
        raw = self.__shared_memory.read_uint16('pH')
        voltage = espadc.raw_to_voltage(raw)
        return voltage
        # Magic numbers from: https://files.atlas-scientific.com/Gravity-pH-datasheet.pdf
        # return (-5.6548 * voltage) + 15.509
    
    @property
    def DO(self):
        raw = self.__shared_memory.read_uint16('DO')
        voltage = espadc.raw_to_voltage(raw)
        return voltage
