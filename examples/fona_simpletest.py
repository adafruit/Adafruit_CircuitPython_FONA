import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
from adafruit_fona.adafruit_fona_gsm import GSM
import adafruit_fona.adafruit_fona_socket as cellular_socket
import adafruit_requests as requests

print("FONA WebClient Test")

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_URL = "http://api.coindesk.com/v1/bpi/currentprice/USD.json"

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
fona = FONA(uart, rst)

# Initialize Network
while fona.network_status != 1:
    print("Connecting to network...")
    time.sleep(1)
print("Connected to network!")
print("RSSI: %ddB" % fona.rssi)

# Text a number
print("Sending SMS...")
if not fona.send_sms(140404, "HELP"):
    raise RuntimeError("FONA did not successfully send SMS")
print("SMS Sent!")

# Ask the FONA how many SMS message it has
num_sms = fona.num_sms
print("%d SMS's on SIM Card" % num_sms)

# Read out all the SMS messages on the FONA's SIM
for slot in range(1, num_sms):
    print(fona.read_sms(slot))
