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

# HTTP Actions
FONA_HTTP_GET = const(0x00)
FONA_HTTP_POST = const(0x01)
FONA_HTTP_HEAD = const(0x02)

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
        self._user_agent = b"FONA"
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
        self._buf = b""
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t---> ", "AT+GSN")
        self._uart.write(b"AT+GSN\r\n")
        self.read_line(multiline=True)
        iemi = self._buf[0:15]
        return iemi.decode("utf-8")

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
            if self.send_check_reply(CMD_AT, reply=REPLY_OK):
                break
            if self.send_check_reply(CMD_AT, reply=REPLY_AT):
                break
            time.sleep(0.5)
            timeout -= 500

        if timeout <= 0:
            if self._debug:
                print(" * Timeout: No response to AT. Last ditch attempt.")
            self.send_check_reply(CMD_AT, reply=REPLY_OK)
            time.sleep(0.1)
            self.send_check_reply(CMD_AT, reply=REPLY_OK)
            time.sleep(0.1)
            self.send_check_reply(CMD_AT, reply=REPLY_OK)
            time.sleep(0.1)

        # turn off echo
        self.send_check_reply(b"ATE0", reply=REPLY_OK)
        time.sleep(0.1)

        if not self.send_check_reply(b"ATE0", reply=REPLY_OK):
            return False
        time.sleep(0.1)

        # turn on hangupitude
        self.send_check_reply(b"AT+CVHU=0", reply=REPLY_OK)
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

    @property
    def GPRS(self):
        """Returns module's GPRS state."""
        if self._debug:
            print("* Check GPRS State")
        if not self.send_parse_reply(b"AT+CGATT?", b"+CGATT: ", ":"):
            return False
        return self._buf

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
    def GPRS(self, gprs_on=True):
        """Enables or disables GPRS configuration.
        :param bool gprs_on: Turns on GPRS, enabled by default.

        """
        if gprs_on:
            if self._debug:
                print("* Enabling GPRS..")

            # disconnect all sockets
            self.send_check_reply(b"AT+CIPSHUT",
                                  reply=b"SHUT OK", timeout=20000)

            if not self.send_check_reply(b"AT+CGATT=1",
                                         reply=REPLY_OK, timeout=10000):
                return False

            # set bearer profile - access point name
            if not self.send_check_reply(b"AT+SAPBR=3,1,\"CONTYPE\",\"GPRS\"", reply=REPLY_OK, timeout=10000):
                return False

            if self._apn is not None:
                # Send command AT+SAPBR=3,1,"APN","<apn value>"
                # where <apn value> is the configured APN value.

                self.send_check_reply_quoted(b"AT+SAPBR=3,1,\"APN\",", self._apn, REPLY_OK, 10000)

                # send AT+CSTT,"apn","user","pass"
                self._uart.reset_input_buffer()

                # TODO: This needs to be modified to send over uart and check reply
                self._uart.write(b"AT+CSTT=\"")
                self._uart.write(self._apn)

                if self._apn_username is not None:
                    self._uart.write(b"\",\"")
                    self._uart.write(self._apn_username)

                if self._apn_password is not None:
                    self._uart.write(b"\",\"")
                    self._uart.write(self._apn_password)
                self._uart.write(b"\"")
                self._uart.write(b"\r\n")

                if not self.get_reply(REPLY_OK):
                    return False

                # Set username
                if not self.send_check_reply_quoted(b"AT+SAPBR=3,1,\"USER\",", self._apn_username, REPLY_OK, 10000):
                    return False

                # Set password
                if not self.send_check_reply_quoted(b"AT+SAPBR=3,1,\"PWD\",", self._apn_password, REPLY_OK, 100000):
                    return False

                # Open GPRS context
                self.send_check_reply(b"AT+SAPBR=1,1", reply=b'', timeout=100000)

                # Bring up wireless connection
                if not self.send_check_reply(b"AT+CIICR", reply=REPLY_OK, timeout=10000):
                    return False

            else:
                # Disconnect all sockets
                if not self.send_check_reply(b"AT+CIPSHUT", reply=b"SHUT OK", timeout=20000):
                    return False
                
                # Close GPRS context
                if not self.send_check_reply(b"AT+SAPBR=0,1", reply=REPLY_OK, timeout=10000):
                    return False
                if not self.send_check_reply(b"AT+CGATT=0", reply=REPLY_OK, timeout=10000):
                    return False

        return True

    @property
    def network_status(self):
        """Returns cellular/network status"""
        if not self.send_parse_reply(b"AT+CREG?", b"+CREG: ", idx=1):
        
            return False
        if self._buf == 0:
            # Not Registered
            return self._buf
        elif self._buf == 1:
            # Registered (home)
            return self._buf
        elif self._buf == 2:
            # Not Registered (searching)
            return self._buf
        elif self._buf == 3:
            # Denied
            return self._buf
        elif self._buf == 4:
            # Unknown
            return self._buf
        elif self._buf == 5:
            # Registered Roaming
            return self._buf
        else:
            # "Unknown"
            return self._buf

    @property
    def RSSI(self):
        """Returns cellular network'sReceived Signal Strength Indicator (RSSI)."""
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
        self.read_line()
        return rssi

    @property
    def GPS(self):
        """Returns the GPS status, as a string."""
        if self._debug:
            print("GPS STATUS")
        if self._fona_type == FONA_808_V2:
            # 808 V2 uses GNS commands and doesn't have an explicit 2D/3D fix status.
            # Instead just look for a fix and if found assume it's a 3D fix.
            self.get_reply(b"AT+CGNSINF")

            if not b"+CGNSINF: " in self._buf:
                return False

            status = int(self._buf[10:11].decode("utf-8"))
            if status == 1:
                status = 3 # assume 3D fix
            self.read_line()
        elif self._fona_type == FONA_3G_A or self._fona_type == FONA_3G_E:
            raise NotImplementedError("FONA 3G not currently supported by this library.")
        else:
            raise NotImplementedError("FONA 808 v1 not currently supported by this library.")

        if status < 0:
            return "Failed to query module"
        elif status == 0:
            return "GPS off"
        elif status == 1:
            return "No fix"
        elif status == 2:
            return "2D fix"
        elif status == 3:
            return "3D fix"
        else:
            return "Failed to query GPS module, is it connected?"

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
                if not self.send_check_reply(b"AT+CGNSPWR=1", reply=REPLY_OK):
                    return False
            else:
                if not self.send_parse_reply(b"AT+CGPSPWR=1", reply=REPLY_OK):
                    return False
        else:
            if self._fona_type == FONA_808_V2:
                # try GNS
                if not self.send_check_reply(b"AT+CGNSPWR=0", reply=REPLY_OK):
                    return False
                else:
                    if not self.send_check_reply(b"AT+CGPSPWR=0", reply=REPLY_OK):
                        return False

        return True

    ### HTTP (High Level Methods) ###

    def http_get(self, url):
        """Performs a HTTP GET request.
        :param str url: Destination URL.

        """
        # initialize HTTP/HTTPS config.
        if not self._http_setup(url):
            return False

        # perform HTTP GET action
        if not self._http_action(FONA_HTTP_GET, 30000):
            return False

        print("L1587")
        # L1587
        pass


    ### HTTP Helpers ###

    def _http_action(self, method, status, timeout=10000):
        """Perform a HTTP method action. 
        :param int method: FONA_HTTP_ method to perform.
        :param int status: TODO
        :param int timeout: Time to wait for response, in milliseconds.

        """
        # send request
        if not self.send_check_reply(prefix=b"AT+HTTPACTION=", suffix=str(method).encode(), reply=REPLY_OK):
            return False

        # parse response status and size
        self.read_line(timeout)
        if not self.parse_reply(b"+HTTPACTION:", divider=",", idx=1):
            return False
        status = self._buf
        if not self.parse_reply(b"+HTTPACTION:", divider=",", idx=2):
            return False
        return True

    def _http_setup(self, url):
        """Initializes HTTP and HTTPS configuration
        :param str url: Desired HTTP/HTTPS address.

        """
        # terminate any http sessions
        self._http_terminate()

        # initialize HTTP service
        if not self._http_init():
            return False
        
        print("* Setting CID...")
        # set client id
        if not self._http_para(b"CID", 1):
            return False
        
        print("setting UA...")
        # set user agent
        if not self._http_para(b"UA", self._user_agent):
            return False
        # set URL
        if not self._http_para(b"URL", url.encode()):
            return False
        
        # set https redirect
        if self._https_redirect:
            if not self._http_para(b"REDIR", 1):
                return False
            # set HTTP SSL
            if not self.http_ssl(True):
                return False

        return True

    def _http_ssl(self, enable):
        """Sets if SSL is used for HTTP.
        :param bool enable: Enable or disable SSL for HTTP

        """
        if enable:
            if not self.send_check_reply(b"AT+HTTPSSL=1", reply=REPLY_OK):
                return False
        else:
            if not self.send_check_reply(b"AT+HTTPSSL=0", reply=REPLY_OK):
                return True

    def _http_para(self, param, value):
        """Command sets up HTTP parameters for the HTTP call.
        Parameters which can be set are: CID, URL,
            redirect, and useragent.
        """
        is_quoted = True
        if hasattr(value, 'to_bytes'):
            is_quoted = False
            value = str(value).encode()

        self._http_para_start(param, is_quoted)
        self._uart.write(value)
        return self._http_para_end(is_quoted)


    def _http_para_start(self, param, quoted=False):
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t---> AT+HTTPPARA={}".format(param))

        self._uart.write(b"AT+HTTPPARA=\"")

        self._uart.write(param)
        if quoted:
            self._uart.write(b"\",\"")
        else:
            self._uart.write(b"\",")


    def _http_para_end(self, quoted=False):
        if quoted:
            self._uart.write(b'"')
        self._uart.write(b"\r\n")
        return self.expect_reply(REPLY_OK)


    def _http_terminate(self):
        """Terminates the HTTP session"""
        self.send_check_reply(b"AT+HTTPTERM", reply=REPLY_OK)

    def _http_init(self):
        """ Initializes the HTTP service."""
        return self.send_check_reply(b"AT+HTTPINIT", reply=REPLY_OK)


    ### UART Reply/Response Helpers ###

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


    def get_reply(self, data=None, prefix=None, suffix=None, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Send data to FONA, read response into buffer.
        :param bytes data: Data to send to FONA module.
        :param int timeout: Time to wait for UART response.

        """
        self._uart.reset_input_buffer()

        if data is not None:
            if self._debug:
                print("\t---> ", data)
            self._uart.write(data+"\r\n")
        else:
            if self._debug:
                print("\t---> {}{}".format(prefix, suffix))
            self._uart.write(prefix+suffix+b"\r\n")

        self._buf = b""
        line = self.read_line(timeout)

        if self._debug:
            print("\t<--- ", self._buf)
        return line


    def parse_reply(self, reply, divider=",", idx=0):
        """Attempts to find reply in UART buffer, reads up to divider.
        :param bytes reply: Expected response from FONA module.
        :param str divider: Divider character.

        """
        # TODO: The issue here is buff gets overwritten at the end, subsequent calls
        # which attempt to use the buffer fail because its not the original value
        # TOFIX: Attempt to ret. the parsed value, do NOT modify the buffer.

        # attempt to find reply in buffer
        p = self._buf.find(reply)
        if p == -1:
            return False
        p = self._buf[p:]

        p = self._buf[len(reply):]
        p = p.decode("utf-8")

        print("buf: ", self._buf)

        p = p.split(divider)
        
        print("div: ", divider)
        print("buf: ", p)
        print("index: ", idx)
        p = p[idx]

        self._buf = int(p)

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


    def send_check_reply(self, send=None, prefix=None, suffix=None, reply=None, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Sends data to FONA, validates response.
        :param bytes send: Command.
        :param bytes reply: Expected response from module.

        """
        if send is None:
            if not self.get_reply(prefix=prefix, suffix=suffix, timeout=timeout):
                return False
        else:
            if not self.get_reply(send, timeout=timeout):
                return False
        # validate response
        if not reply in self._buf:
            return False

        return True


    def send_check_reply_quoted(self, prefix, suffix, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Send prefix, ", suffix, ", and a newline. Verify response against reply.
        :param bytes prefix: Command prefix.
        :param bytes prefix: Command ", suffix, ".
        :param bytes reply: Expected response from module.
        :param int timeout: Time to expect reply back from FONA, in milliseconds.

        """
        self._buf = b""

        self._get_reply_quoted(prefix, suffix, timeout)

        # validate response
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
        self._uart.write(b"\"")
        self._uart.write(suffix)
        self._uart.write(b"\"")
        self._uart.write(b"\r\n")


        line = self.read_line(timeout)

        if self._debug:
            print("\t<--- ", self._buf)

        return line

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

