# Metro M4 FONA808 Testing Initialization :)
import time
import board
import busio
import digitalio
import adafruit_fona

# rst pin
rst = digitalio.DigitalInOut(board.D4)

# initialize adafruit fona
fona = adafruit_fona.FONA(board.TX, board.RX, rst)

print("OK!")