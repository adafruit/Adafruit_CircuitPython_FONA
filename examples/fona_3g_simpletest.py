import time
import board
import busio
import digitalio
import adafruit_fona.fona_3g as FONA
from adafruit_fona.adafruit_fona_cdma import CDMA
import adafruit_fona.adafruit_fona_socket as cellular_socket
import adafruit_requests as requests

print("FONA 3G Webclient")

SERVER_ADDRESS = ("104.236.193.178", 80)

# Get GPRS details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("GPRS secrets are kept in secrets.py, please add them there!")
    raise

# Create a serial connection for the FONA connection
uart = busio.UART(board.TX, board.RX, baudrate=4800)
rst = digitalio.DigitalInOut(board.D9)

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
print("Network Connected!")

print("Local IP: ", fona.local_ip)

# Set socket interface
cellular_socket.set_interface(fona)

sock = cellular_socket.socket()

print("Connecting to: ", SERVER_ADDRESS[0])
sock.connect(SERVER_ADDRESS)

print("Connected to:", sock.getpeername())

# Make a HTTP Request
sock.send(b"GET /testwifi/index.html HTTP/1.1\n")
sock.send(b"Host: 104.236.193.178")
sock.send(b"Connection: close\n\n")

bytes_avail = 0
while not bytes_avail:
    bytes_avail = sock.available()
    print(bytes_avail)
    if bytes_avail > 0:
        print("bytes_avail: ", bytes_avail)
    time.sleep(1)
