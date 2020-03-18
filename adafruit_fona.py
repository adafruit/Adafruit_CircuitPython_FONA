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
from simpleio import map_range

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FONA.git"

FONA_BAUD = const(4800)
FONA_DEFAULT_TIMEOUT_MS = 500

# COMMANDS
CMD_AT = b"AT"

# REPLIES
REPLY_OK = b"OK"
REPLY_AT = b"AT"

# FONA Versions
FONA_800_L = const(0x01)
FONA_800_H = const(0x6)

FONA_808_V1 = const(0x2)
FONA_808_V2 = const(0x3)

FONA_3G_A   = const(0x4)
FONA_3G_E   = const(0x5)


class FONA:
    """CircuitPython FONA module interface.
    :param ~digialio TX: FONA TX Pin
    :param ~digialio RX: FONA RX Pin
    :param ~digialio RST: FONA RST Pin
    :param bool set_https_redir: Optionally configure HTTP gets to follow
                                    redirects over SSL.
    :param bool debug: Enable debugging output.

    """
    def __init__(self, tx, rx, rst, set_https_redir=False, debug=False):
        self._buf = b""
        self._fona_type = 0
        self._debug = debug
        # Set up UART interface
        self._uart = busio.UART(tx, rx, baudrate=FONA_BAUD)
        self._rst = rst
        if not self._init_fona():
            raise RuntimeError("Unable to find FONA. Please check connections.")
        self._init_fona()

        self._apn = "FONAnet"
        self._apn_username = 0
        self._apn_password = 0
        self._https_redirect = set_https_redir
        self._user_agent = "FONA"
        self._ok_reply = "OK"

    @property
    def version(self):
        """Returns FONA Version,as a string."""
        if self._fona_type == FONA_800_L:
            return "FONA 800L"
        elif self._fona_type == FONA_800_H:
            return "FONA 800H"
        elif self._fona_type == FONA_808_V1:
            return "FONA 808 (v1)"
        elif self._fona_type == FONA_808_V2:
            return "FONA 808 (v2)"
        elif self._fona_type == FONA_3G_A:
            return "FONA 3G (US)"
        elif self._fona_type == FONA_3G_E:
            return "FONA 3G (EU)"
        else:
            return -1

    @property
    def IEMI(self):
        """Returns FONA module's IEMI number."""
        #self.send_check_reply(b"AT+GSN\r\n", REPLY_OK)
        self._buf = b""
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t---> ", "AT+GSN")
        self._uart.write(b"AT+GSN\r\n")
        self.read_line(multiline=True)
        iemi = self._buf[0:15]
        return iemi.decode("utf-8")

    @property
    def GPRS(self):
        """Returns module's GPRS configuration, as a tuple."""
        return (self._apn, self._apn_username, self._apn_password)
    
    @GPRS.setter
    def GPRS(self, config):
        """Sets GPRS configuration to provided tuple in format:
        (apn_network, apn_username, apn_password)
        """
        apn, username, password = config
        self._apn = apn
        self._apn_username = username
        self._apn_password = password

    @property
    def RSSI(self):
        """Returns cellular network's Received Signal Strength Indicator."""
        self.get_reply(b"AT+CSQ")
        reply_num = self.parse_reply(self._buf)

        rssi = 0
        if reply_num == 0:
            rssi = -115
        elif reply_num == 1:
            rssi = -111
        elif reply_num == 31:
            rssi = -52
        
        if reply_num >= 2 and reply_num <= 30:
            rssi = map_range(reply_num, 2, 30, -110, -54)
        return rssi

    def parse_reply(self, reply, divider=","):
        if hasattr(reply, "decode"):
            reply = reply.decode("utf-8")
        idx = reply.find(divider)
        return int(reply[idx-3:idx])

    def get_reply(self, data, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Send data to FONA, read response into buffer.
        :param bytes data: Data to send to FONA module.
        :param int timeout: Time to wait for UART response.

        """
        self._uart.reset_input_buffer()
        if self._debug:
            print("\t---> ", data)

        self._uart.timeout = FONA_DEFAULT_TIMEOUT_MS/1000
        result = self._uart.write(data+"\r\n")

        self._buf = b""
        line = self.read_line(multiline=True)

        if self._debug:
            print("\t<--- ", self._buf)
        return line


    def _init_fona(self):
        """Initializes FONA module."""
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
            if self.send_check_reply(CMD_AT, REPLY_OK):
                break
            if self.send_check_reply(CMD_AT, REPLY_AT):
                break
            time.sleep(0.5)
            timeout -= 500

        if timeout <= 0:
            if self._debug:
                print(" * Timeout: No response to AT. Last ditch attempt.")
            self.send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.01)
            self.send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.01)
            self.send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.01)

        # turn off echo
        self.send_check_reply(b"ATE0", REPLY_OK)
        time.sleep(0.01)

        if not self.send_check_reply(b"ATE0", REPLY_OK):
            return False

        # turn on hangupitude
        self.send_check_reply(b"AT+CVHU=0", REPLY_OK)

        time.sleep(0.01)
        self._buf = b""
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t---> ", "ATI")
        self._uart.write(b"ATI\r\n")
        self.read_line(multiline=True)

        if self._buf.find(b"SIM808 R14") != -1:
            self._fona_type = FONA_808_V2
        elif self._buf.find(b"SIM808 R13") != -1:
            self._fona_type = FONA_808_V1
        elif self._buf.find(b"SIMCOM_SIM5320A") != -1:
            self._fona_type = FONA_3G_A
        elif self._buf.find(b"SIMCOM_SIM5320E") != -1:
            self._fona_type = FONA_3G_E

        if self._fona_type == FONA_800_L:
            # determine if _H
            if self._debug:
                print("\t ---> AT+GMM")
            self._uart.write(b"AT+GMM\r\n")
            self.read_line(multiline=True)
            if self._debug:
                print("\t <---", self._buf)
            
            if self._buf.find(b"SIM800H") != -1:
                self._fona_type = FONA_800_H

        return True


    def read_line(self, timeout=FONA_DEFAULT_TIMEOUT_MS, multiline=False):
        """Reads one or multiple lines into the buffer.
        :param int timeout: Time to wait for UART serial to reply, in seconds.
        :param bool multiline: Read multiple lines.

        """
        reply_idx = 0

        while timeout:
            if reply_idx >= 254:
                break

            while self._uart.in_waiting:
                c = self._uart.read(1)
                #print(c)
                if c == b'\r':
                    continue
                if c == b'\n':
                    if reply_idx == 0:
                        # ignore first '\n'
                        continue
                    if not multiline:
                        # second '\n' is EOL
                        timeout = 0
                        break
                self._buf += c
                reply_idx += 1
            timeout -= 1
            time.sleep(0.001)

        # append null
        self._buf += b"0x00"
        return reply_idx


    def send_check_reply(self, send, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
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
