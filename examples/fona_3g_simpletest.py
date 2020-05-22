import time
import board
import busio
import digitalio
import adafruit_fona.fona_3g as FONA
from adafruit_fona.adafruit_fona_cdma import CDMA
import adafruit_fona.adafruit_fona_socket as cellular_socket
import adafruit_requests as requests

print("FONA 3G Webclient")

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_URL = "http://api.coindesk.com/v1/bpi/currentprice/USD.json"

# Get GPRS details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("GPRS secrets are kept in secrets.py, please add them there!")
    raise

# Create a serial connection for the FONA connection
uart = busio.UART(board.TX, board.RX, baudrate=4800)
rst = digitalio.DigitalInOut(board.D7)

# Initialize FONA module (this may take a few seconds)
fona = FONA.FONA3G(uart, rst, debug=True)

# Initialize CDMA
cdma = CDMA(fona, (secrets["apn"], secrets["apn_username"], secrets["apn_password"]))

while not cdma.is_attached:
    print("Attaching to network...")
    time.sleep(0.5)

print("Attached!")

while not cdma.is_connected:
    print("Connecting to network...")
    cdma.connect()
    time.sleep(0.5)

print("OK!")

print("My IP address is:", fona.local_ip)