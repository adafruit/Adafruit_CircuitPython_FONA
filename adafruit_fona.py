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

* `Adafruit FONA 808 Breakout <https://www.adafruit.com/product/2542>`_
* `Adafruit FONA 808 Shield <https://www.adafruit.com/product/2636>`_

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

        self._apn = None
        self._apn_username = None
        self._apn_password = None
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
        """Returns module's GPRS state."""
        if not self.send_parse_reply(b"AT+CGATT?", b"+CGATT: ", ":"):
            return False
        if self._buf == 0: # +CGATT: 0
            return False
        return True

    def set_GRPS(self, config):
        """If config provided, sets GPRS configuration to provided tuple in format:
        (apn_network, apn_username, apn_password)
        """
        if self._debug:
            print("* Setting GPRS Config to: ", config)
        apn, username, password = config
        self._apn = apn.encode()
        self._apn_username = username.encode()
        self._apn_password = password.encode()
        return self._apn, self._apn_username, self._apn_password

    @GPRS.setter
    def GPRS(self, gprs_on):
        """Enables or disables GPRS configuration.

        :param bool gprs_on: Turns on GPRS.
        """
        if gprs_on:
            # disconnect all sockets
            self.send_check_reply(b"AT+CIPSHUT", b"SHUT OK", 20000)

            if not self.send_check_reply(b"AT+CGATT=1", REPLY_OK, 10000):
                return False
            
            # set bearer profile - connection type GPRS
            if not self.send_check_reply(b"AT+SAPBR=3,1,\"CONTYPE\",\"GPRS\"", REPLY_OK, 10000):
                return False
            
            # set bearer profile - access point name
            if self._apn is not None:
                # Send command AT+SAPBR=3,1,"APN","<apn value>"
                #where <apn value> is the configured APN value.
                if not self.send_check_reply_quoted(b"AT+SAPBR=3,1,\"APN\",", self._apn, REPLY_OK, 10000):
                    return False

                # send ATT+CSTT, "apn", "user", "pass"
                self._uart.reset_input_buffer()

                # TODO: This needs to be neatened up!
                self._uart.write(b"AT+CSTT=\"")
                self._uart.write(self._apn)
                self._uart.write(b"\",\"")
                self._uart.write(self._apn_username)
                self._uart.write(b"\",\"")
                self._uart.write(self._apn_password)
                self._uart.write(b"\"")
                """
                # TODO: Re-impl, reference for adding username/pw
                self._uart.write(b"AT+CSTT=")
                self._uart.write(self._apn)
                if self._apn_username is not None:
                    self._uart.write(b","+self._apn_username)
                if self._apn_password is not None:
                    self._uart.write(b","+self._apn_password)
                """

                if self._debug:
                    print("\t---> AT+CSTT='{}'".format(self._apn), end="")
                    if self._apn_username is not None:
                        print(", '{}'".format(self._apn_username), end="")
                    if self._apn_password is not None:
                        print(", '{}'".format(self._apn_password), end="")
                    print("") # endl

                if not self.expect_reply(REPLY_OK):
                    return False

                # set username
                print("username")
                if self._apn_username:
                    # TODO: This does not send as expected!
                    #if not self.send_check_reply_quoted(b"AT+SAPBR=3,1,\"USER\",", self._apn_username, REPLY_OK, 10000):
                    self._uart.write(b"AT+SAPBR=3,1,\"USER\",\"your username\"")
                    if not self.expect_reply(REPLY_OK):
                        return False
                self._buf = b""

                # set password
                print("pw")
                if self._apn_password:
                    # TODO: This does not send as expected!
                    #self._uart.write(b"AT+SAPBR=3,1,\"PWD\",\"your password\"")
                    #if not self.expect_reply(REPLY_OK):
                    #    print("return!")
                    if not self.send_check_reply_quoted(b"AT+SAPBR=3,1,\"PWD\",", self._apn_password, REPLY_OK, 10000):
                        return False
                self._buf = b""

                # open GPRS context
                print("open context")
                if not self.send_check_reply(b"AT+SAPBR=1,1", REPLY_OK, 30000):
                    return False

                # bring up wireless connection
                print("bring up")
                if not self.send_check_reply(b"AT+CIICR", REPLY_OK, 10000):
                    return False
            else:
                # disconnect all sockets
                if not self.send_check_reply(b"AT+CIPSHUT", b"SHUT OK", 20000):
                    return False
                
                # close GPRS context
                if not self.send_check_reply(b"AT+SAPBR=0,1", REPLY_OK, 10000):
                    return False
                if not self.send_check_reply(b"AT+CGATT=0", REPLY_OK, 10000):
                    return False

        return True

    @property
    def network_status(self):
        """Returns cellular/network status"""
        if not self.send_parse_reply(b"AT+CREG?", b"+CREG: ", idx=1):
            return False
        if self._buf == 0:
            print("Not Registered!")
        elif self._buf == 1:
            print("Registered (home)")
        elif self._buf == 2:
            print("Not Registered (searching)")
        elif self._buf == 3:
            print("Denied")
        elif self._buf == 4:
            print("Unknown")
        elif self._buf == 5:
            print("Registered Roaming")
        return self._buf

    @property
    def RSSI(self):
        """Returns cellular network's Received Signal Strength Indicator (RSSI)."""
        if not self.send_parse_reply(b"AT+CSQ", b"+CSQ: "):
            return False

        reply_num = self._buf
        rssi = 0
        if reply_num == 0:
            rssi = -115
        elif reply_num == 1:
            rssi = -111
        elif reply_num == 31:
            rssi = -52
        
        if reply_num >= 2 and reply_num <= 30:
            rssi = map_range(reply_num, 2, 30, -110, -54)

        # read out the 'ok'
        self._buf = b""
        self.read_line()
        return rssi

    @property
    def GPS(self):
        """Returns if the GPS is disabled or enabled."""
        if self._debug:
            print("GPS STATUS")
        if self._fona_type == FONA_808_V2:
            # 808 V2 uses GNS commands and doesn't have an explicit 2D/3D fix status.
            # Instead just look for a fix and if found assume it's a 3D fix.
            self.get_reply(b"AT+CGNSINF")

            if not b"+CGNSINF: " in self._buf:
                return False

            status = int(self._buf[10:11].decode("utf-8"))
            print("Status: ", status)
            if status == 1:
                status = 3 # assume 3D fix
            self.read_line()
        else:
            # TODO: implement other fona versions: 3g, 808v1
            raise NotImplementedError("FONA 3G and FONA 808 v1 not currently supported by this library.")

        if status < 0:
            print("Failed to query module")
        elif status == 0:
            print("GPS off")
        elif status == 1:
            print("No fix")
        elif status == 2:
            print("2D fix")
        elif status == 3:
            print("3D fix")
        else:
            print("Failed to query GPS module, is it connected?")
        return status

    @GPS.setter
    def GPS(self, gps_on=False):
        """Enables or disables the GPS module.
        NOTE: This is only for FONA 3G or FONA808 modules.
        :param bool gps_on: Enables the GPS module, disabled by default.

        """
        if self._debug:
            print("* Setting GPS")
        if not (self._fona_type == FONA_3G_A or self._fona_type == FONA_3G_E or
                    self._fona_type == FONA_808_V1 or self._fona_type == FONA_808_V2):
                        raise TypeError("GPS unsupported for this FONA module.")

        # check if already enabled or disabled
        if self._fona_type == FONA_808_V2:
            if not self.send_parse_reply(b"AT+CGPSPWR?", b"+CGPSPWR: ", ":"):
                return False
            else:
                self.read_line()
                if not self.send_parse_reply(b"AT+CGNSPWR?", b"+CGNSPWR: ", ":"):
                    return False

        state = self._buf

        if gps_on and not state:
            self.read_line()
            if self._fona_type == FONA_808_V2:
                # try GNS
                print("trying GNS...")
                if not self.send_check_reply(b"AT+CGNSPWR=1", REPLY_OK):
                    return False
            else:
                if not self.send_parse_reply(b"AT+CGPSPWR=1", REPLY_OK):
                    return False
        else:
            if self._fona_type == FONA_808_V2:
                # try GNS
                if not self.send_check_reply(b"AT+CGNSPWR=0", REPLY_OK):
                    return False
                else:
                    if not self.send_check_reply(b"AT+CGPSPWR=0", REPLY_OK):
                        return False

        return True

    def send_parse_reply(self, send_data, reply_data, divider=',', idx=0):
        """Sends data to FONA module, parses reply data returned.
        :param bytes send_data: Data to send to the module.
        :param bytes send_data: Data received by the FONA module.
        :param str divider: Separator

        """
        self.get_reply(send_data)

        if not self.parse_reply(reply_data, divider, idx):
            return False

        return True

    def parse_reply(self, reply, divider=",", idx=0):
        """Attempts to find reply in UART buffer, reads up to divider.
        :param bytes reply: Expected response from FONA module.
        :param str divider: Divider character.

        """
        # attempt to find reply in buffer
        p = self._buf.find(reply)
        if p == -1:
            return False
        p = self._buf[p:]

        p = self._buf[len(reply):]
        p = p.decode("utf-8")

        p = p.split(divider)
        p = p[idx]

        self._buf = int(p)

        return True

    def _init_fona(self):
        """Initializes FONA module."""
        # RST module
        self._rst.switch_to_output()
        self._rst.value = True
        time.sleep(0.01)
        self._rst.value = False
        time.sleep(0.1)
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
            time.sleep(0.1)
            self.send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.1)
            self.send_check_reply(CMD_AT, REPLY_OK)
            time.sleep(0.1)

        # turn off echo
        self.send_check_reply(b"ATE0", REPLY_OK)
        time.sleep(0.1)

        if not self.send_check_reply(b"ATE0", REPLY_OK):
            return False
        time.sleep(0.1)

        # turn on hangupitude
        self.send_check_reply(b"AT+CVHU=0", REPLY_OK)
        time.sleep(0.1)

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
        self._buf = b""
        reply_idx = 0
        while timeout:
            if reply_idx >= 254:
                break

            while self._uart.in_waiting:
                c = self._uart.read(1)
                # print(c)
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
                # print(c, self._buf)
                self._buf += c
                reply_idx += 1

            if timeout == 0:
                # if self._debug:
                    # print("* Timed out!")
                break
            timeout -= 1
            time.sleep(0.001)

        return reply_idx


    def send_check_reply(self, send, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
        if not self.get_reply(send, timeout):
            return False

        if not reply in self._buf:
            return False
        return True

    def get_reply(self, data, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Send data to FONA, read response into buffer.
        :param bytes data: Data to send to FONA module.
        :param int timeout: Time to wait for UART response.

        """
        self._uart.reset_input_buffer()
        if self._debug:
            print("\t---> ", data)

        result = self._uart.write(data+"\r\n")

        self._buf = b""
        line = self.read_line()

        if self._debug:
            print("\t<--- ", self._buf)
        return line

    def send_check_reply_quoted(self, prefix, suffix, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Send prefix, ", suffix, ", and a newline. Verify response against reply.
        :param bytes prefix: Command prefix.
        :param bytes prefix: Command ", suffix, ".
        :param int timeout: Time to expect reply back from FONA, in milliseconds.

        """
        self._buf = b""

        self._get_reply_quoted(prefix, suffix, timeout)

        if reply not in self._buf:
            print("not reply!")
            return False
        return True

    def expect_reply(self, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Reads line from FONA module and compares to reply from FONA module.
        :param bytes reply: Expected reply from module.

        """
        self.read_line(timeout)
        if self._debug:
            print("\t<--- ", self._buf)
        if reply not in self._buf:
            return False
        return True

    def _get_reply_quoted(self, prefix, suffix, timeout):
        """Send prefix, ", suffix, ", and newline.
        Returns: Response (and also fills buffer with response).
        :param bytes prefix: Command prefix.
        :param bytes prefix: Command ", suffix, ".
        :param int timeout: Time to expect reply back from FONA, in milliseconds.

        """
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t---> ", end="")
            print(prefix, end="")
            print('""', end="")
            print(suffix, end="")
            print('""')

        self._uart.write(prefix)
        self._uart.write(b'""')
        self._uart.write(suffix)
        self._uart.write(b'""')

        line = self.read_line(timeout)

        if self._debug:
            print("\t<--- ", self._buf)

        return line
