import time
import board
import busio
import digitalio
import adafruit_fona

# rst pin
rst = digitalio.DigitalInOut(board.D4)

# Initialize adafruit fona
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
print("Turning on GPS...")
fona.GPS
fona.GPS = True

time.sleep(2) # wait for a fix
fona.GPS


## GPRS ##
fona.set_GRPS((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))

print("GRPS ON? ", fona.GPRS)

# ensure we're connected to a cellular network
while fona.network_status != 1:
    print("Not registered to a network, waiting...")
    time.sleep(5)

time.sleep(5)

fona.GPRS = True

print("GRPS ON? ", fona.GPRS)

time.sleep(10)

## Website - HTTP ##
url = "wifitest.adafruit.com/testwifi/index.html"
fona.http_get(url)


