# The MIT License (MIT)
#
# Copyright Limor Fried/Ladyada for Adafruit Industries
# Copyright (c) 2020 Brent Rubell for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_fona`
================================================================================

CircuitPython library for the Adafruit FONA


* Author(s): ladyada, Brent Rubell

Implementation Notes
--------------------

**Hardware:**

.. todo:: Add links to any specific hardware product page(s), or category page(s). Use unordered list & hyperlink rST
   inline format: "* `Link Text <url>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""
import time
from micropython import const
import busio

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FONA.git"

FONA_BAUD = const(4800)
FONA_DEFAULT_TIMEOUT_MS = const(500)

# COMMANDS
CMD_AT = b"AT"

# REPLIES
REPLY_OK = b"OK"
REPLY_AT = b"AT"

class FONA:
    """CircuitPython FONA module interface.
    :param ~digialio TX: FONA TX Pin
    :param ~digialio RX: FONA RX Pin
    :param ~digialio RST: FONA RST Pin
    :param bool debug: Enable debugging output.

    """
    def __init__(self, tx, rx, rst, debug=True):
        self._buf = b""
        self._debug = debug
        # Set up UART interface
        self._uart = busio.UART(tx, rx, baudrate=FONA_BAUD)
        self._rst = rst
        if not self._init_fona():
            raise RuntimeError("Unable to find FONA. Please check your connections.")
        self._init_fona()

        self._apn = "FONAnet"
        self._apn_username = 0
        self._apn_password = 0
        self._https_redirect = False
        self._user_agent = "FONA"
        self._ok_reply = "OK"

    def _init_fona(self):
        """Initialize FONA module.
        """
        # RST module
        self._rst.switch_to_output()
        self._rst.value = True
        time.sleep(0.01)
        self._rst.value = False
        time.sleep(0.01)
        self._rst.value = True

        if self._debug:
            print("Attempting to open comm with ATs")
        timeout = 7
        while timeout > 0:
            if self._send_check_reply(CMD_AT, REPLY_OK):
                break
            if self._send_check_reply(CMD_AT, REPLY_AT):
                break
            time.sleep(0.5)
            timeout -= 500

        if timeout <= 0:
            if self._debug:
                print(" * Timeout: No response to AT. Last ditch attempt.")
            self._send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.01)
            self._send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.01)
            self._send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.01)

        # turn off echo
        self._send_check_reply(b"ATE0", REPLY_OK)
        time.sleep(0.01)

        if not self._send_check_reply(b"ATE0", REPLY_OK):
            return False

        # turn on hangupitude
        self._send_check_reply(b"AT+CVHU=0", REPLY_OK)

        time.sleep(0.01)
        self._buf = b""

        if self._debug:
            print("\t---> ", "ATI")
        self._uart.write(b"ATI\r\n")
        time.sleep()

        # TODO: this call below needs to be converted into a multi-readline, see L1764 for implementation
        self._uart.read(255)
        if self._debug:
            print("\t<--- ", self._buf)

        return True


    def _send_check_reply(self, send, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Send command to the FONA and check its reply.
        :param bytes send: Data to send to the FONA.
        :param str reply: Expected reply from the FONA.
        :param int timeout: Time to expect data back from FONA, in seconds.
        """
        # flush the buffer
        self._buf = b""
        timestamp = time.monotonic()
        while True:
            if self._debug:
                print("\t---> ", send)
            result = self._uart.write(send+"\r\n")

            self._buf = self._uart.read(255)
            if time.monotonic() - timestamp > timeout:
                return False
            if self._debug:
                print("\t<--- ", self._buf)
            if self._buf != None:
                if reply in self._buf:
                    break
            time.sleep(0.5)
        return True
