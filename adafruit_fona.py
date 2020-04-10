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

FONA_TCP_MODE = const(0)
FONA_UDP_MODE = const(1)

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

        # GPRS
        self._apn = None
        self._apn_username = None
        self._apn_password = None
        # HTTP
        self._https_redirect = set_https_redir
        self._user_agent = b"FONA"
        self._ok_reply = "OK"
        self._http_data_len = 0
        self._http_status = 0

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
        self._read_line(multiline=True)
        iemi = self._buf[0:15]
        return iemi.decode("utf-8")

    def pretty_ip(self, ip):
        """Converts a bytearray IP address to a dotted-quad string for printing"""
        return "%d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3])

    @property
    def local_ip(self):
        """Returns the local IP Address."""
        if self._debug:
            print("\t---> AT+CIFSR")

        self._uart.write(b"AT+CIFSR\r\n")
        self._read_line()
        return self.pretty_ip(self._buf)

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
            if self._send_check_reply(CMD_AT, reply=REPLY_OK):
                break
            if self._send_check_reply(CMD_AT, reply=REPLY_AT):
                break
            time.sleep(0.5)
            timeout -= 500

        if timeout <= 0:
            if self._debug:
                print(" * Timeout: No response to AT. Last ditch attempt.")
            self._send_check_reply(CMD_AT, reply=REPLY_OK)
            time.sleep(0.1)
            self._send_check_reply(CMD_AT, reply=REPLY_OK)
            time.sleep(0.1)
            self._send_check_reply(CMD_AT, reply=REPLY_OK)
            time.sleep(0.1)

        # turn off echo
        self._send_check_reply(b"ATE0", reply=REPLY_OK)
        time.sleep(0.1)

        if not self._send_check_reply(b"ATE0", reply=REPLY_OK):
            return False
        time.sleep(0.1)

        # turn on hangupitude
        self._send_check_reply(b"AT+CVHU=0", reply=REPLY_OK)
        time.sleep(0.1)

        self._buf = b""
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t---> ", "ATI")
        self._uart.write(b"ATI\r\n")
        self._read_line(multiline=True)

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
            self._read_line(multiline=True)
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
        if not self._send_parse_reply(b"AT+CGATT?", b"+CGATT: ", ":"):
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
            self._send_check_reply(b"AT+CIPSHUT",
                                  reply=b"SHUT OK", timeout=20000)

            if not self._send_check_reply(b"AT+CGATT=1",
                                         reply=REPLY_OK, timeout=10000):
                return False

            # set bearer profile - access point name
            if not self._send_check_reply(b"AT+SAPBR=3,1,\"CONTYPE\",\"GPRS\"", reply=REPLY_OK, timeout=10000):
                return False

            if self._apn is not None:
                # Send command AT+SAPBR=3,1,"APN","<apn value>"
                # where <apn value> is the configured APN value.
                self._send_check_reply_quoted(b"AT+SAPBR=3,1,\"APN\",", self._apn, REPLY_OK, 10000)

                # send AT+CSTT,"apn","user","pass"
                if self._debug:
                    print("setting APN...")
                self._uart.reset_input_buffer()

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

                if not self._get_reply(REPLY_OK):
                    return False

                # Set username
                if not self._send_check_reply_quoted(b"AT+SAPBR=3,1,\"USER\",", self._apn_username, REPLY_OK, 10000):
                    return False

                # Set password
                if not self._send_check_reply_quoted(b"AT+SAPBR=3,1,\"PWD\",", self._apn_password, REPLY_OK, 100000):
                    return False

                # Open GPRS context
                self._send_check_reply(b"AT+SAPBR=1,1", reply=b'', timeout=100000)

                # Bring up wireless connection
                if not self._send_check_reply(b"AT+CIICR", reply=REPLY_OK, timeout=10000):
                    return False

            else:
                # Disconnect all sockets
                if not self._send_check_reply(b"AT+CIPSHUT", reply=b"SHUT OK", timeout=20000):
                    return False
                
                # Close GPRS context
                if not self._send_check_reply(b"AT+SAPBR=0,1", reply=REPLY_OK, timeout=10000):
                    return False
                if not self._send_check_reply(b"AT+CGATT=0", reply=REPLY_OK, timeout=10000):
                    return False

        return True

    @property
    def network_status(self):
        """Returns cellular/network status"""
        if not self._send_parse_reply(b"AT+CREG?", b"+CREG: ", idx=1):
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
        """Returns cellular network's Received Signal Strength Indicator (RSSI)."""
        if not self._send_parse_reply(b"AT+CSQ", b"+CSQ: "):
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
        self._read_line()
        return rssi

    @property
    def GPS(self):
        """Returns the GPS status, as a string."""
        if self._debug:
            print("GPS STATUS")
        if self._fona_type == FONA_808_V2:
            # 808 V2 uses GNS commands and doesn't have an explicit 2D/3D fix status.
            # Instead just look for a fix and if found assume it's a 3D fix.
            self._get_reply(b"AT+CGNSINF")

            if not b"+CGNSINF: " in self._buf:
                return False

            status = int(self._buf[10:11].decode("utf-8"))
            if status == 1:
                status = 3 # assume 3D fix
            self._read_line()
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
            if not self._send_parse_reply(b"AT+CGPSPWR?", b"+CGPSPWR: ", ":"):
                return False
            else:
                self._read_line()
                if not self._send_parse_reply(b"AT+CGNSPWR?", b"+CGNSPWR: ", ":"):
                    return False

        state = self._buf

        if gps_on and not state:
            self._read_line()
            if self._fona_type == FONA_808_V2:
                # try GNS
                print("trying GNS...")
                if not self._send_check_reply(b"AT+CGNSPWR=1", reply=REPLY_OK):
                    return False
            else:
                if not self._send_parse_reply(b"AT+CGPSPWR=1", reply=REPLY_OK):
                    return False
        else:
            if self._fona_type == FONA_808_V2:
                # try GNS
                if not self._send_check_reply(b"AT+CGNSPWR=0", reply=REPLY_OK):
                    return False
                else:
                    if not self._send_check_reply(b"AT+CGPSPWR=0", reply=REPLY_OK):
                        return False

        return True

    def get_host_by_name(self, hostname):
        """DNS Function - converts a hostname to a packed 4-byte IP address.
        Returns a 4 bytearray.
        :param str hostname: Destination server.

        """
        if self._debug:
            print("*** get_host_by_name")
        if isinstance(hostname, str):
            hostname = bytes(hostname, "utf-8")

        self._uart.write(b"AT+CDNSGIP=\"")
        self._uart.write(hostname)
        self._uart.write(b"\"\r\n")
        if not self._expect_reply(REPLY_OK):
            return False

        # eat the second line
        self._read_line()
        # parse the third 
        self._read_line()

        self._parse_reply(b"+CDNSGIP:", idx=1)
        return self._buf

    ### Socket API (TCP, UDP) ###

    @property
    def socket_status(self):
        """Returns if socket is connected."""
        if not self._send_check_reply(b"AT+CIPSTATUS", reply=REPLY_OK, timeout=100):
            return False
        self._read_line(100)
        
        if self._debug:
            print("\t<--- ", self._buf)
        
        if not "STATE: CONNECT OK" in self._buf.decode():
            return False
        return True

    @property
    def socket_available(self):
        """Returns the amount of bytes to be read from the socket."""
        if not self._send_parse_reply(b"AT+CIPRXGET=4", b"+CIPRXGET: 4,"):
            return False
        if self._debug:
            print("\t {} bytes available.".format(self._buf))

        return self._buf

    def socket_connect(self, dest, port, conn_mode=FONA_TCP_MODE):
        """Connects to a destination IP address or hostname.
        By default, we use `conn_mode` FONA_TCP_MODE but we may also
        use FONA_UDP_MODE.
        :param str dest: Destination dest address.
        :param int port: Destination dest port.

        """
        self._uart.reset_input_buffer()
        if not self._send_check_reply(b"AT+CIPSHUT", reply=b"SHUT OK", timeout=20000):
            return False 
        
        # single connection mode
        if not self._send_check_reply(b"AT+CIPMUX=0", reply=REPLY_OK):
            return False
        
        # enable receive data manually (7,2)
        if not self._send_check_reply(b"AT+CIPRXGET=1", reply=REPLY_OK):
            return False
        
        # Start connection
        if conn_mode == FONA_TCP_MODE:
            if self._debug:
                print("\t--->AT+CIPSTART\"TCP\",\"{}\",{}".format(dest, port))
            self._uart.write(b"AT+CIPSTART=\"TCP\",\"")
        else:
            if self._debug:
                print("\t--->AT+CIPSTART\"UDP\",\"{}\",{}".format(dest, port))
            self._uart.write(b"AT+CIPSTART=\"UDP\",\"")

        self._uart.write(dest.encode());
        self._uart.write(b"\",\"")
        self._uart.write(str(port).encode())
        self._uart.write(b"\"")
        self._uart.write(b"\r\n")

        if not self._expect_reply(REPLY_OK):
            return False
        if not self._expect_reply(b"CONNECT OK"):
            return False

        return True

    def socket_close(self):
        """Closes UDP or TCP connection."""
        if not self._send_check_reply(b"AT+CIPCLOSE", reply=REPLY_OK):
            return False
        return True

    def tcp_read(self, buf, length):
        """Read data from the network into a buffer.
        Returns buffer and amount of bytes read.
        :param bytes buf: Buffer to read into.
        :param int length: Desired length to read.

        """
        self._read_line()
        if self._debug:
            print("\t ---> AT+CIPRXGET=2,{}".format(length))
        self._uart.write(b"AT+CIPRXGET=2,")
        self._uart.write(str(length).encode())
        self._uart.write(b"\r\n")

        self._read_line()
        if not self._parse_reply(b"+CIPRXGET: 2,"):
            return False
        avail = self._buf

        # read into buffer
        self._read_line()

        if self._debug:
            print("\t {} bytes read".format(avail))

        buf = self._buf
        return buf, avail

    def tcp_send(self, data):
        """Send data to remote server.
        :param str data: Data to POST to the URL.
        :param int data: Data to POST to the URL.
        :param float data: Data to POST to the URL.

        """
        self._uart.reset_input_buffer()

        # convert data -> bytes for uart
        if hasattr(data, "encode"):
            data = data.encode()
        elif hasattr(data, "from_bytes") or isinstance(data, float):
            data = str(data).encode()


        if self._debug:
            print("\t--->AT+CIPSEND=", len(data))
            print("\t--->", data)

        self._uart.write(b"AT+CIPSEND=")
        self._uart.write(str(len(data)).encode())
        self._uart.write(b"\r\n")
        self._read_line()

        if self._debug:
            print("\t<--- ", self._buf)

        if self._buf[0] != 62:
            # promoting mark ('>') not found
            return False

        self._uart.write(data)
        self._uart.write(b"\r\n")
        self._read_line(3000)

        if self._debug:
            print("\t<--- ", self._buf)
        
        if not "SEND OK" in self._buf.decode():
            return False
        return True

    ### HTTP (High Level Methods) ###

    def http_get(self, url, buf):
        """Performs a HTTP GET request.
        :param str url: Destination URL.
        :param bytearray buf: Provided buffer to store HTTP GET request data.

        """
        # initialize HTTP/HTTPS config.
        if not self._http_setup(url):
            return False

        # perform HTTP GET action
        if not self._http_action(FONA_HTTP_GET, 30000):
            return False
        if self._debug:
            print("HTTP Status: ", self._http_status)
            print("HTTP Data Length: ", self._http_data_len)

        # Read HTTP response data
        if not self._http_read_all():
            return False

        # resize buffer to data_len
        buf = bytearray(self._http_data_len)
        # and read data into the buffer
        self._uart.readinto(buf)

        # terminate the session
        self._http_terminate()
        return buf

    def http_post(self, url, data, buf):
        """Performs a HTTP POST request.
        :param str url: Destination URL.
        :param str data: Data to POST to the URL.
        :param int data: Data to POST to the URL.
        :param float data: Data to POST to the URL.
        :parm bytearray: Buffer to store data returned from server.

        """

        # initialize HTTP/HTTPS config.
        if not self._http_setup(url):
            return False

        # set CONTENT param.
        if not self._http_para(b"CONTENT", b"text/plain"):
            return False

        # Configure POST
        if hasattr(data, "from_bytes") or isinstance(data, float):
            data = str(data)
        if not self._http_data(len(data)):
            return False

        # Write data to UART
        self._uart.write(data.encode())
        if not self._expect_reply(REPLY_OK):
            return False
        
        # Perform HTTP POST
        if not self._http_action(FONA_HTTP_POST):
            return False

        if self._debug:
            print("Status: ", self._http_status)
            print("Length: ", self._http_data_len)
        
        # Check bytes in buffer
        if not self._http_read_all():
            return False


        # resize buffer to data_len
        buf = bytearray(self._http_data_len)
        # and read data into the buffer
        self._uart.readinto(buf)

        # terminate the session
        self._http_terminate()

        return buf

    ### HTTP Low-Level Helpers ###

    def _http_data(self, size, max_time=10000):
        """POST the data with size and max_time latency.
        :param int size: Data size, in bytes.
        :param int max_time: Latency, recommended as long enough to
                             allow downloading all the data.

        """
        self._uart.reset_input_buffer()

        if self._debug:
            print("\t--->AT+HTTPDATA={},{}".format(size, max_time))

        self._uart.write(b"AT+HTTPDATA=")
        self._uart.write(str(size).encode())
        self._uart.write(b",")
        self._uart.write(str(max_time).encode())
        self._uart.write(b"\r\n")

        return self._expect_reply(b"DOWNLOAD")

    def _http_read_all(self):
        """Sends a HTTPRead command to FONA module."""
        self._get_reply(b"AT+HTTPREAD")
        if not self._parse_reply(b"+HTTPREAD:"):
            return False
        return True

    def _http_action(self, method, timeout=10000):
        """Perform a HTTP method action. 
        :param int method: FONA_HTTP_ method to perform.
        :param int timeout: Time to wait for response, in milliseconds.

        """
        # send request
        if not self._send_check_reply(prefix=b"AT+HTTPACTION=", suffix=str(method).encode(), reply=REPLY_OK):
            return False

        # parse response status and size
        self._read_line(timeout)
        resp = self._buf
        if not self._parse_reply(b"+HTTPACTION:", divider=",", idx=1):
            return False
        self._http_status = self._buf

        self._buf = resp
        if not self._parse_reply(b"+HTTPACTION:", divider=",", idx=2):
            return False
        self._http_data_len = self._buf

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
        
        # set client id
        if not self._http_para(b"CID", 1):
            return False
        
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
            if not self._send_check_reply(b"AT+HTTPSSL=1", reply=REPLY_OK):
                return False
        else:
            if not self._send_check_reply(b"AT+HTTPSSL=0", reply=REPLY_OK):
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
        return self._expect_reply(REPLY_OK)


    def _http_terminate(self):
        """Terminates the HTTP session"""
        self._send_check_reply(b"AT+HTTPTERM", reply=REPLY_OK)

    def _http_init(self):
        """ Initializes the HTTP service."""
        return self._send_check_reply(b"AT+HTTPINIT", reply=REPLY_OK)


    ### UART Reply/Response Helpers ###

    def _send_parse_reply(self, send_data, reply_data, divider=',', idx=0):
        """Sends data to FONA module, parses reply data returned.
        :param bytes send_data: Data to send to the module.
        :param bytes send_data: Data received by the FONA module.
        :param str divider: Separator

        """
        self._get_reply(send_data)

        if not self._parse_reply(reply_data, divider, idx):
            return False
        return True


    def _get_reply(self, data=None, prefix=None, suffix=None, timeout=FONA_DEFAULT_TIMEOUT_MS):
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
        line = self._read_line(timeout)

        if self._debug:
            print("\t<--- ", self._buf)
        return line


    def _parse_reply(self, reply, divider=",", idx=0):
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


        try:
            self._buf = int(p)
        except:
            self._buf = p

        return True

    def _read_line(self, timeout=FONA_DEFAULT_TIMEOUT_MS, multiline=False):
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


    def _send_check_reply(self, send=None, prefix=None, suffix=None, reply=None, timeout=FONA_DEFAULT_TIMEOUT_MS):
        """Sends data to FONA, validates response.
        :param bytes send: Command.
        :param bytes reply: Expected response from module.

        """
        if send is None:
            if not self._get_reply(prefix=prefix, suffix=suffix, timeout=timeout):
                return False
        else:
            if not self._get_reply(send, timeout=timeout):
                return False
        # validate response
        if not reply in self._buf:
            return False

        return True


    def _send_check_reply_quoted(self, prefix, suffix, reply, timeout=FONA_DEFAULT_TIMEOUT_MS):
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

        line = self._read_line(timeout)

        if self._debug:
            print("\t<--- ", self._buf)

        return line

    def _expect_reply(self, reply, timeout=10000):
        """Reads line from FONA module and compares to reply from FONA module.
        :param bytes reply: Expected reply from module.

        """
        self._read_line(timeout)
        if self._debug:
            print("\t<--- ", self._buf)
        if reply not in self._buf:
            return False
        return True

