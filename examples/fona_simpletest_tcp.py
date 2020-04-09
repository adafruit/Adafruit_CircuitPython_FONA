import time
import board
import busio
import digitalio
import adafruit_fona

# rst pin
rst = digitalio.DigitalInOut(board.D4)

# Initialize FONA
print("Initializing FONA... (this may take 3 seconds)")
fona = adafruit_fona.FONA(board.TX, board.RX, rst, debug=True)

### Cellular ###
# Get GPRS details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("GPRS secrets are kept in secrets.py, please add them there!")
    raise

## GPS ##
fona.GPS = True
time.sleep(5) # wait for a fix

## GPRS ##
fona.set_GRPS((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))

# ensure we're connected to a cellular network
while fona.network_status != 1:
    print("Not registered to a network, waiting...")
    time.sleep(5)
time.sleep(5)

fona.GPRS = True
time.sleep(6)

print('IP: ', fona.local_ip)

host_ip = fona.get_host_by_name("www.sim.com")
print("Host IP: ", host_ip)


## TCP ### 
server = "IP_ADDR"
port = 80

print("Connecting...")
if not fona.tcp_connect(server, port):
    raise RuntimeError("Unable to connect to TCP Server")
print("Connected to {}:{}".format(server, port))

time.sleep(3)

print("Status: ", fona.tcp_status)

time.sleep(3)

print("sending bytes...")
fona.tcp_send(12345678912)

