import time
import board
import digitalio
from adafruit_fona.adafruit_fona import FONA
import adafruit_fona.adafruit_fona_socket as socket

# Name address for wifitest.adafruit.com
SERVER_ADDRESS = ("wifitest.adafruit.com", 80)

# Get GPRS details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("GPRS secrets are kept in secrets.py, please add them there!")
    raise

# Initialize FONA module (this may take a few seconds)
rst = digitalio.DigitalInOut(board.D4)
fona = FONA(board.TX, board.RX, rst, debug=True)

print("FONA WebClient Test")

# Enable GPS
fona.gps = True
while fona.gps != 3: 
    print("Waiting for GPS fix, retrying...")
    time.sleep(5)

# Bring up cellular connection
fona.set_gprs((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))
while fona.network_status != 1:
    print("Not registered to a network, waiting...")
    time.sleep(5)
time.sleep(5)

# Bring up GPRS
fona.gprs = True
time.sleep(6)

print("Local IP: ", fona.local_ip)

# Set socket interface
socket.set_interface(fona)

sock = socket.socket()

print("Connecting to: ", SERVER_ADDRESS[0])
sock.connect(SERVER_ADDRESS)

print("Connected to ", sock.getpeername())