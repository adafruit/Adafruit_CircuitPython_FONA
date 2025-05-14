# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
from os import getenv

import adafruit_connection_manager
import adafruit_requests
import board
import busio
import digitalio

import adafruit_fona.adafruit_fona_network as network
import adafruit_fona.adafruit_fona_socket as pool
from adafruit_fona.adafruit_fona import FONA
from adafruit_fona.fona_3g import FONA3G

# Get FONA details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
apn = getenv("apn")
apn_username = getenv("apn_username")
apn_password = getenv("apn_password")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

# Create a serial connection for the FONA
uart = busio.UART(board.TX, board.RX)
rst = digitalio.DigitalInOut(board.D4)

# Use this for FONA800 and FONA808
fona = FONA(uart, rst)

# Use this for FONA3G
# fona = FONA3G(uart, rst)

# Initialize cellular data network
network = network.CELLULAR(fona, (apn, apn_username, apn_password))

while not network.is_attached:
    print("Attaching to network...")
    time.sleep(0.5)
print("Attached!")

while not network.is_connected:
    print("Connecting to network...")
    network.connect()
    time.sleep(0.5)
print("Network Connected!")

# create requests session
ssl_context = adafruit_connection_manager.create_fake_ssl_context(pool, fona)
requests = adafruit_requests.Session(pool, ssl_context)

counter = 0

while True:
    print("Posting data...", end="")
    data = counter
    feed = "test"
    payload = {"value": data}
    response = requests.post(
        "http://io.adafruit.com/api/v2/" + aio_username + "/feeds/" + feed + "/data",
        json=payload,
        headers={"X-AIO-KEY": aio_key},
    )
    print(response.json())
    response.close()
    counter = counter + 1
    print("OK")
    response = None
    time.sleep(15)
