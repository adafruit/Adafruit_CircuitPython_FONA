import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
import adafruit_fona.adafruit_fona_socket as socket

SERVER_ADDRESS = ("wifitest.adafruit.com", 80)

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
fona = FONA(uart, rst, debug=True)

print("Adafruit FONA WebClient Test")

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

print("Connected to:", sock.getpeername())
time.sleep(7)

# Make a HTTP Request
sock.send(b"GET /testwifi/index.html HTTP/1.1\n")
sock.send(b"Host: 104.236.193.178")
sock.send(b"Connection: close\n\n")

bytes_avail = 0
while not bytes_avail:
    bytes_avail = sock.available()
    if bytes_avail > 0:
        print("bytes_avail: ", bytes_avail)
        data = sock.recv(bytes_avail)
        print(data)
        break
    time.sleep(0.05)

sock.close()
print("Socket connected: ", sock.connected)
