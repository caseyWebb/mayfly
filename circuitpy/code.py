
import board
import analogio
import time

# Create analog input on pin IO1
pin = analogio.AnalogIn(board.IO1)

print("Starting")

while True:
    # Read and print the voltage of the analog pin
    print("IO1 Voltage: ", pin.value)
    time.sleep(0.1)