# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
from os import getenv

import adafruit_connection_manager
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_requests
import board
import busio
import digitalio
import neopixel

import adafruit_fona.adafruit_fona_network as network
import adafruit_fona.adafruit_fona_socket as pool
from adafruit_fona.adafruit_fona import FONA
from adafruit_fona.fona_3g import FONA3G

# Get FONA details, ensure these are setup in settings.toml
apn = getenv("apn")
apn_username = getenv("apn_username")
apn_password = getenv("apn_password")

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

DATA_SOURCE = "http://api.thingspeak.com/channels/1417/feeds.json?results=1"
DATA_LOCATION = ["feeds", 0, "field2"]

# neopixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
pixels.fill(0)

attempts = 3  # Number of attempts to retry each request
failure_count = 0
response = None

# we'll save the value in question
last_value = value = None

while True:
    print("Fetching json from", DATA_SOURCE)
    response = requests.get(DATA_SOURCE)
    print(response.json())
    value = response.json()
    for key in DATA_LOCATION:
        value = value[key]
        print(value)
    response.close()

    if not value:
        continue
    if last_value != value:
        color = int(value[1:], 16)
        red = color >> 16 & 0xFF
        green = color >> 8 & 0xFF
        blue = color & 0xFF
        gamma_corrected = fancy.gamma_adjust(fancy.CRGB(red, green, blue)).pack()

        pixels.fill(gamma_corrected)
        last_value = value
    response = None
    time.sleep(60)
