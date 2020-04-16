import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA
import adafruit_fona.adafruit_fona_socket as socket

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_URL = "http://api.coindesk.com/v1/bpi/currentprice/USD.json"

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
# wait for a fix
# TODO: Change this to wait for a fix instead!
time.sleep(7)

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

"""
socket.set_interface(eth)

# Create a new socket
sock = socket.socket()

print("Connecting to: ", SERVER_ADDRESS[0])
sock.connect(SERVER_ADDRESS)

print("Connected to ", sock.getpeername())

# Make a HTTP Request
sock.send(b"GET /testwifi/index.html HTTP/1.1\n")
sock.send(b"Host: 104.236.193.178\n")
sock.send(b"Connection: close\n\n")

# Start transmission timer
start = time.monotonic()

bytes_avail = 0
while not bytes_avail:
    bytes_avail = sock.available()
    if bytes_avail > 0:
        data = sock.recv(bytes_avail)
        print(data[0])
        break
    time.sleep(0.05)

end = time.monotonic()
print("Received: %d bytes"%bytes_avail)
end = end - start / 1000000.0
rate = bytes_avail / end / 1000.0
print("Rate = %0.5f kbytes/second"%rate)
"""