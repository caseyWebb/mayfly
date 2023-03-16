from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_il0373
import board
import busio
import displayio

DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128
BACKGROUND_COLOR = 0xFFFFFF
FOREGROUND_COLOR = 0x000000
FONT = bitmap_font.load_font("/font/UpheavalTT-BRK--28.bdf")
SMALL_FONT = bitmap_font.load_font("/font/UpheavalTT-BRK--16.bdf")

EPD_CS = board.D5
EPD_DC = board.D6

class Display:
    def __init__(self):
        displayio.release_displays()
        spi = busio.SPI(board.SCK, board.MOSI)
        display_bus = displayio.FourWire(
            spi, command=EPD_DC, chip_select=EPD_CS, baudrate=1000000
        )
        self.__display = adafruit_il0373.IL0373(
            display_bus,
            width=DISPLAY_WIDTH,
            height=DISPLAY_HEIGHT,
            rotation=270,
            black_bits_inverted=False,
            color_bits_inverted=False,
            grayscale=True,
            refresh_time=1,
        )

    def update(self, updated_at):
        g = displayio.Group()
        palette = displayio.Palette(1)
        palette[0] = BACKGROUND_COLOR

        background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
        t = displayio.TileGrid(background_bitmap, pixel_shader=palette)
        g.append(t)

        Display.__add_text_to_group(g, "pH: 7.0", 20, 15)
        Display.__add_text_to_group(g, "DO: 50%", 20, 45)
        Display.__add_text_to_group(g, "Temp (Air): 25C", 20, 75)
        Display.__add_text_to_group(g, "Temp (Water): 25C", 20, 105)
        Display.__add_text_to_group(g, "Last updated:", 160, 15, SMALL_FONT)
        Display.__add_text_to_group(g, f'{updated_at.month}/{updated_at.day} {updated_at.hour}:{updated_at.minute:02}', 160, 30, SMALL_FONT)

        self.__display.show(g)
        self.__display.refresh()

    @staticmethod
    def __add_text_to_group(group, text, x, y, font=FONT):
        text_group = displayio.Group(scale=1, x=x, y=y)
        text_area = label.Label(text=text, font=font, color=FOREGROUND_COLOR)
        text_group.append(text_area)
        group.append(text_group)


