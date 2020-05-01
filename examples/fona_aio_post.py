import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
import adafruit_fona.adafruit_fona_socket as cellular_socket
import adafruit_requests as requests

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

counter = 0

while True:
    print("Posting data...", end="")
    data = counter
    feed = "test"
    payload = {"value": data}
    response = requests.post(
        "http://io.adafruit.com/api/v2/"
        + secrets["aio_username"]
        + "/feeds/"
        + feed
        + "/data",
        json=payload,
        headers={"X-AIO-KEY": secrets["aio_key"]},
    )
    print(response.json())
    response.close()
    counter = counter + 1
    print("OK")
    response = None
    time.sleep(15)
