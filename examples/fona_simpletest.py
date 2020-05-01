import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
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

# Enable GPS
fona.gps = True

# Bring up cellular connection
fona.configure_gprs((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))

# Bring up GPRS
fona.gprs = True

# Initialize a requests object with a socket and cellular interface
requests.set_socket(cellular_socket, fona)

print("My IP address is:", fona.local_ip)
print("IP lookup adafruit.com: %s" % fona.get_host_by_name("adafruit.com"))

# fona._debug = True
print("Fetching text from", TEXT_URL)
r = requests.get(TEXT_URL)
print("-" * 40)
print(r.text)
print("-" * 40)
r.close()

print()
print("Fetching json from", JSON_URL)
r = requests.get(JSON_URL)
print("-" * 40)
print(r.json())
print("-" * 40)
r.close()

print("Done!")
