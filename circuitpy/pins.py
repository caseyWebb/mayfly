import board
from digitalio import DigitalInOut

###
# Long side of the board
###
# RESET
# 3V3
ANALOG_SENSORS_ENABLE_PIN = board.IO0
# GND
# board.IO17
# board.IO18
# board.IO14
# board.IO12
PH_ADC_PIN = board.IO6
DO_ADC_PIN = board.IO5
SCK = board.SCK
# board.MISO
MOSI = board.MOSI
# board.IO44
# board.IO43
ldo2 = DigitalInOut(board.LDO2)

###
# Short side of the board
###
# VBAT
# EN
# 5V
BUTTON_C_PIN = board.IO11  # this is used by a wake alarm directly
button_b = DigitalInOut(board.IO10)
button_a = DigitalInOut(board.IO7)
EPD_DC = board.IO3
EPD_CS = board.IO1
buzzer = DigitalInOut(board.IO38)
# board.IO33
# board.IO9
ONEWIRE_BUS_PIN = board.IO8

###
# These pins are used by the ULP and can not be accessed by the main CPU
###
ULP_GPIO_PINS = [ANALOG_SENSORS_ENABLE_PIN, ONEWIRE_BUS_PIN]
ULP_ADC_PINS = [PH_ADC_PIN, DO_ADC_PIN]
