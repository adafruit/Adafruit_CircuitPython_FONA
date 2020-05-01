import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
import adafruit_fona.adafruit_fona_socket as cellular_socket
import adafruit_requests as requests

import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy

# Get GPRS details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("GPRS secrets are kept in secrets.py, please add them there!")
    raise

# Create a serial connection for the FONA connection using 4800 baud.
# These are the defaults you should use for the FONA Shield.
# For other boards set RX = GPS module TX, and TX = GPS module RX pins.
uart = busio.UART(board.TX, board.RX, baudrate=4800)
rst = digitalio.DigitalInOut(board.D4)

# Initialize FONA module (this may take a few seconds)
print("Initializing FONA")
fona = FONA(uart, rst)

# Enable GPS
fona.gps = True

# Bring up cellular connection
fona.configure_gprs((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))

# Bring up GPRS
fona.gprs = True
print("FONA initialized")

# Initialize a requests object with a socket and cellular interface
requests.set_socket(cellular_socket, fona)

DATA_SOURCE = "http://api.thingspeak.com/channels/1417/feeds.json?results=1"
DATA_LOCATION = ["feeds", 0, "field2"]

# neopixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
pixels.fill(0)

attempts = 3  # Number of attempts to retry each request
failure_count = 0
response = None

# we'll save the value in question
last_value = value = None

while True:
    print("Fetching json from", DATA_SOURCE)
    response = requests.get(DATA_SOURCE)
    print(response.json())
    value = response.json()
    for key in DATA_LOCATION:
        value = value[key]
        print(value)
    response.close()

    if not value:
        continue
    if last_value != value:
        color = int(value[1:], 16)
        red = color >> 16 & 0xFF
        green = color >> 8 & 0xFF
        blue = color & 0xFF
        gamma_corrected = fancy.gamma_adjust(fancy.CRGB(red, green, blue)).pack()

        pixels.fill(gamma_corrected)
        last_value = value
    response = None
    time.sleep(60)
