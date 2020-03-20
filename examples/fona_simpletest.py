import time
import board
import busio
import digitalio
import adafruit_fona

### Cellular ###

# Get GPRS details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("GPRS secrets are kept in secrets.py, please add them there!")
    raise

# rst pin
rst = digitalio.DigitalInOut(board.D4)

# initialize adafruit fona
print("Initializing FONA... (this may take 3 seconds)")
fona = adafruit_fona.FONA(board.TX, board.RX, rst, debug=True)

print("FONA OK\nFound: ", fona.version)

#print("Module IEMI: ", fona.IEMI)

# Configure GRPS
print("configuring GRPS....")
fona.config_GPRS((secrets["apn"], secrets["apn_username"], secrets["apn_password"]))
print("configured!")

#print("RSSI: {}dBm".format(fona.RSSI))

#fona.network_status

print("checking status:")
status = fona.GPS

print("turning on...")
fona.GPS = True

print("enabling GPRS")
fona.GPRS = True