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
time.sleep(2) # wait for a fix

## GPRS ##
fona.set_GRPS((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))

# ensure we're connected to a cellular network
while fona.network_status != 1:
    print("Not registered to a network, waiting...")
    time.sleep(5)
time.sleep(5)

fona.GPRS = True
time.sleep(10)

## HTTP ##

# POST to URL
print("GET'ing...")
# GET URL
data_buf = b""
url = "wifitest.adafruit.com/testwifi/index.html"
data_buf = fona.http_get(url, data_buf)
print(data_buf)

time.sleep(6)

print("POSTING...")
data_buf = b""
post_url = "httpbin.org/post"
data_buf = fona.http_post(post_url, "hello", data_buf)
if not len(data_buf):
    print("Unable to POST data")
print(data_buf)




