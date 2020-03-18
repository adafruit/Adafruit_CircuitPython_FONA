import time
import board
import busio
import digitalio
import adafruit_fona

# rst pin
rst = digitalio.DigitalInOut(board.D4)

# initialize adafruit fona
print("Initializing FONA... (this may take 3 seconds)")
fona = adafruit_fona.FONA(board.TX, board.RX, rst)

print("FONA OK\nFound: ", fona.version)

print("IEMI: ", fona.IEMI)