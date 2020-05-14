import time
import board
import busio
import digitalio
from adafruit_fona.adafruit_fona import FONA

print("FONA SMS Response")

# Create a serial connection for the FONA connection
uart = busio.UART(board.TX, board.RX)
rst = digitalio.DigitalInOut(board.D4)

# Initialize FONA module (this may take a few seconds)
fona = FONA(uart, rst, debug=True)

# Initialize Network
while fona.network_status != 1:
    print("Connecting to network...")
    time.sleep(1)
print("Connected to network!")
print("RSSI: %ddB" % fona.rssi)

# Enable FONA SMS notification
fona.enable_sms_notification = True

# store incoming notification info
notification_buf = bytearray(64)

print("FONA Ready!")
while True:
    if fona.in_waiting:  # data is available from FONA
        notification_buf = fona.read_line()[1]
        # Split out the sms notification slot num.
        notification_buf = notification_buf.decode()
        sms_slot = notification_buf.split(",")[1]

        print("NEW SMS!\n\t Slot: ", sms_slot)

        # Get sms message and address
        sender, message = fona.read_sms(sms_slot)
        print("FROM: ", sender)
        print("MSG: ", message)

        # Reply back!
        print("Sending response...")
        if not fona.send_sms(int(sender), "Hey, I got your text!"):
            print("SMS Send Failed")
        print("SMS Sent!")

        # Delete the original message
        if not fona.delete_sms(sms_slot):
            print("Could not delete SMS in slot", sms_slot)
        print("OK!")
