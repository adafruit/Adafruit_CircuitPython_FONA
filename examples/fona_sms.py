import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA

print("FONA SMS")

# Create a serial connection for the FONA connection
uart = busio.UART(board.TX, board.RX)
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
