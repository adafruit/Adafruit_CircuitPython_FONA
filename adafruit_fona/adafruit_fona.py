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

CircuitPython library for the Adafruit FONA cellular module


* Author(s): ladyada, Brent Rubell

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""
import time
from micropython import const
from simpleio import map_range

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FONA.git"

# pylint: disable=bad-whitespace
FONA_DEFAULT_TIMEOUT_MS = 500  # TODO: Check this against arduino...

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
FONA_3G_A = const(0x4)
FONA_3G_E = const(0x5)

# HTTP Actions
FONA_HTTP_GET = const(0x00)
FONA_HTTP_POST = const(0x01)
FONA_HTTP_HEAD = const(0x02)

FONA_MAX_SOCKETS = const(6)

# pylint: enable=bad-whitespace

# pylint: disable=too-many-instance-attributes, too-many-public-methods
class FONA:
    """CircuitPython FONA module interface.
    :param ~busio.uart UART: FONA UART connection.
    :param ~digialio RST: FONA RST Pin.
    :param bool debug: Enable debugging output.

    """

    # Connection modes
    TCP_MODE = const(0)
    UDP_MODE = const(1)

    # pylint: disable=too-many-arguments
    def __init__(self, uart, rst, debug=False):
        self._buf = b""  # shared buffer
        self._fona_type = 0
        self._debug = debug

        self._uart = uart
        self._rst = rst
        self._rst.switch_to_output()
        if not self._init_fona():
            raise RuntimeError("Unable to find FONA. Please check connections.")

    # pylint: disable=too-many-branches, too-many-statements
    def _init_fona(self):
        """Initializes FONA module."""
        self.reset()

        timeout = 7000
        while timeout > 0:
            while self._uart.in_waiting:
                if self._send_check_reply(CMD_AT, reply=REPLY_OK):
                    break
            if self._send_check_reply(CMD_AT, reply=REPLY_AT):
                break
            time.sleep(0.5)
            timeout -= 500

        if timeout <= 0:
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

        self.uart_write(b"ATI\r\n")
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
            # determine if SIM800H
            self.uart_write(b"AT+GMM\r\n")
            self._read_line(multiline=True)

            if self._buf.find(b"SIM800H") != -1:
                self._fona_type = FONA_800_H
        return True

    def factory_reset(self):
        """Resets modem to factory configuration."""
        self.uart_write(b"ATZ\r\n")

        if not self._expect_reply(REPLY_OK):
            return False
        return True

    def reset(self):
        """Performs a hardware reset on the modem.
        NOTE: This may take a few seconds to complete.

        """
        if self._debug:
            print("* Reset FONA")
        # Reset the module
        self._rst.value = True
        time.sleep(0.01)
        self._rst.value = False
        time.sleep(0.1)
        self._rst.value = True

    @property
    # pylint: disable=too-many-return-statements
    def version(self):
        """Returns FONA Version, as a string."""
        if self._fona_type == FONA_800_L:
            return "FONA 800L"
        if self._fona_type == FONA_800_H:
            return "FONA 800H"
        if self._fona_type == FONA_808_V1:
            return "FONA 808 (v1)"
        if self._fona_type == FONA_808_V2:
            return "FONA 808 (v2)"
        if self._fona_type == FONA_3G_A:
            return "FONA 3G (US)"
        if self._fona_type == FONA_3G_E:
            return "FONA 3G (EU)"
        return -1

    @property
    def iemi(self):
        """Returns FONA module's IEMI number."""
        if self._debug:
            print("FONA IEMI")
        self._buf = b""
        self._uart.reset_input_buffer()

        self.uart_write(b"AT+GSN\r\n")
        self._read_line(multiline=True)
        iemi = self._buf[0:15]
        return iemi.decode("utf-8")

    @property
    def local_ip(self):
        """Returns the local IP Address, False if not set."""
        self.uart_write(b"AT+CIFSR\r\n")
        self._read_line()
        try:
            ip_addr = self.pretty_ip(self._buf)
        except ValueError:
            return False
        return ip_addr

    @property
    def iccid(self):
        """Returns SIM Card's ICCID number as a string."""
        if self._debug:
            print("ICCID")
        self.uart_write(b"AT+CCID\r\n")
        self._read_line(timeout=2000)  # 6.2.23, 2sec max. response time
        iccid = self._buf.decode()
        self._read_line()  # eat 'OK'
        return iccid

    @property
    def gprs(self):
        """Returns module's GPRS state."""
        self._read_line()

        if not self._send_parse_reply(b"AT+CGATT?", b"+CGATT: ", ":"):
            return False
        if not self._buf:
            return False
        return True

    # pylint: disable=too-many-return-statements
    def set_gprs(self, apn=None, enable=True):
        """Configures and brings up GPRS.
        :param bool enable: Enables or disables GPRS.

        """
        if enable:
            apn_name, apn_user, apn_pass = apn

            apn_name = apn_name.encode()
            apn_user = apn_user.encode()
            apn_pass = apn_pass.encode()

            # enable multi connection mode (3,1)
            if not self._send_check_reply(b"AT+CIPMUX=1", reply=REPLY_OK):
                return False
            self._read_line()

            # enable receive data manually (7,2)
            if not self._send_check_reply(b"AT+CIPRXGET=1", reply=REPLY_OK):
                return False

            # disconnect all sockets
            if not self._send_check_reply(
                b"AT+CIPSHUT", reply=b"SHUT OK", timeout=20000
            ):
                return False

            if not self._send_check_reply(b"AT+CGATT=1", reply=REPLY_OK, timeout=10000):
                return False

            # set bearer profile (APN)
            if not self._send_check_reply(
                b'AT+SAPBR=3,1,"CONTYPE","GPRS"', reply=REPLY_OK, timeout=10000
            ):
                return False

            # Send command AT+SAPBR=3,1,"APN","<apn value>"
            # where <apn value> is the configured APN value.
            self._send_check_reply_quoted(
                b'AT+SAPBR=3,1,"APN",', apn_name, REPLY_OK, 10000
            )

            # send AT+CSTT,"apn","user","pass"
            self._uart.reset_input_buffer()

            self.uart_write(b'AT+CSTT="' + apn_name)

            if apn_user is not None:
                self.uart_write(b'","' + apn_user)

            if apn_pass is not None:
                self.uart_write(b'","' + apn_pass)
            self.uart_write(b'"\r\n')

            if not self._get_reply(REPLY_OK):
                return False

            # Set username
            if not self._send_check_reply_quoted(
                b'AT+SAPBR=3,1,"USER",', apn_user, REPLY_OK, 10000
            ):
                return False

            # Set password
            if not self._send_check_reply_quoted(
                b'AT+SAPBR=3,1,"PWD",', apn_pass, REPLY_OK, 100000
            ):
                return False

            # Open GPRS context
            if not self._send_check_reply(
                b"AT+SAPBR=1,1", reply=REPLY_OK, timeout=1850
            ):
                return False

            # Bring up wireless connection
            if not self._send_check_reply(b"AT+CIICR", reply=REPLY_OK, timeout=10000):
                return False

            # Query local IP
            if not self.local_ip:
                return False
        else:
            # reset PDP state
            if not self._send_check_reply(
                b"AT+CIPSHUT", reply=b"SHUT OK", timeout=20000
            ):
                return False

        return True

    @property
    def network_status(self):
        """Returns cellular/network status"""
        if self._debug:
            print("Network status")
        if not self._send_parse_reply(b"AT+CREG?", b"+CREG: ", idx=1):
            return False
        if self._buf == 0:
            # Not Registered
            return self._buf
        if self._buf == 1:
            # Registered (home)
            return self._buf
        if self._buf == 2:
            # Not Registered (searching)
            return self._buf
        if self._buf == 3:
            # Denied
            return self._buf
        if self._buf == 4:
            # Unknown
            return self._buf
        if self._buf == 5:
            # Registered Roaming
            return self._buf
        # "Unknown"
        return self._buf

    @property
    def rssi(self):
        """Returns cellular network's Received Signal Strength Indicator (RSSI)."""
        if self._debug:
            print("RSSI")
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

        if 2 <= reply_num <= 30:
            rssi = map_range(reply_num, 2, 30, -110, -54)

        # read out the 'ok'
        self._read_line()
        return rssi

    @property
    def gps(self):
        """Returns the GPS fix."""
        if self._debug:
            print("GPS Fix")
        if self._fona_type == FONA_808_V2:
            # 808 V2 uses GNS commands and doesn't have an explicit 2D/3D fix status.
            # Instead just look for a fix and if found assume it's a 3D fix.
            self._get_reply(b"AT+CGNSINF")

            if not b"+CGNSINF: " in self._buf:
                return False

            status = int(self._buf[10:11].decode("utf-8"))
            if status == 1:
                status = 3  # assume 3D fix
            self._read_line()
        elif self._fona_type == FONA_3G_A or self._fona_type == FONA_3G_E:
            raise NotImplementedError(
                "FONA 3G not currently supported by this library."
            )
        else:
            raise NotImplementedError(
                "FONA 808 v1 not currently supported by this library."
            )
        return status

    @gps.setter
    def gps(self, gps_on=False):
        """Sets GPS module power, parses returned buffer.
        :param bool gps_on: Enables the GPS module, disabled by default.

        """
        if not (
            self._fona_type == FONA_3G_A
            or self._fona_type == FONA_3G_E
            or self._fona_type == FONA_808_V1
            or self._fona_type == FONA_808_V2
        ):
            raise TypeError("GPS unsupported for this FONA module.")

        # check if already enabled or disabled
        if self._fona_type == FONA_808_V2:
            if not self._send_parse_reply(b"AT+CGPSPWR?", b"+CGPSPWR: ", ":"):
                return False
        self._read_line()
        if not self._send_parse_reply(b"AT+CGNSPWR?", b"+CGNSPWR: ", ":"):
            return False

        state = self._buf

        if gps_on and not state:
            self._read_line()
            if self._fona_type == FONA_808_V2:
                # try GNS
                if not self._send_check_reply(b"AT+CGNSPWR=1", reply=REPLY_OK):
                    return False
            else:
                if not self._send_parse_reply(b"AT+CGPSPWR=1", reply_data=REPLY_OK):
                    return False
        else:
            if self._fona_type == FONA_808_V2:
                # try GNS
                if not self._send_check_reply(b"AT+CGNSPWR=0", reply=REPLY_OK):
                    return False
                if not self._send_check_reply(b"AT+CGPSPWR=0", reply=REPLY_OK):
                    return False

        return True

    def get_host_by_name(self, hostname):
        """Converts a hostname to a packed 4-byte IP address.
        Returns a 4 bytearray.
        :param str hostname: Destination server.

        """
        if self._debug:
            print("*** Get host by name")
        self._read_line()
        if isinstance(hostname, str):
            hostname = bytes(hostname, "utf-8")

        if not self._send_check_reply(
            b'AT+CDNSGIP="' + hostname + b'"\r\n', reply=REPLY_OK
        ):
            return False

        # attempt to parse a response
        self._read_line()
        while not self._parse_reply(b"+CDNSGIP:", idx=2):
            self._read_line()

        return self._buf

    def pretty_ip(self, ip):  # pylint: disable=no-self-use, invalid-name
        """Converts a bytearray IP address to a dotted-quad string for printing"""
        return "%d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3])

    def unpretty_ip(self, ip):  # pylint: disable=no-self-use, invalid-name
        """Converts a dotted-quad string to a bytearray IP address"""
        octets = [int(x) for x in ip.split(".")]
        return bytes(octets)

    ### Socket API (TCP, UDP) ###

    def get_socket(self):
        """Returns an avaliable socket (INITIAL or CLOSED state).

        """
        if self._debug:
            print("*** Get socket")

        self.uart_write(b"AT+CIPSTATUS\r\n")
        self._read_line(100)  # OK
        self._read_line(100)  # table header

        allocated_socket = 0
        for sock in range(0, FONA_MAX_SOCKETS):
            # parse and check for INITIAL client state
            self._read_line(100)
            self._parse_reply(b"C:", idx=5)
            if self._buf.strip('"') == "INITIAL" or self._buf.strip('"') == "CLOSED":
                allocated_socket = sock
                break
        # read out the rest of the responses
        for _ in range(allocated_socket, FONA_MAX_SOCKETS):
            self._read_line(100)
        if self._debug:
            print("Allocated socket #%d" % allocated_socket)
        return allocated_socket

    def remote_ip(self, sock_num):
        """Returns the IP address of the host who sent the current incoming packet.
        :param int sock_num: Desired socket.

        """
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."
        self.uart_write(b"AT+CIPSTATUS=" + str(sock_num).encode() + b"\r\n")
        self._read_line(100)

        self._parse_reply(b"+CIPSTATUS:", idx=3)
        return self._buf

    def socket_status(self, sock_num):
        """Returns if socket is connected.
        :param int sock_num: Desired socket number.

        """
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."
        if not self._send_check_reply(b"AT+CIPSTATUS", reply=REPLY_OK, timeout=100):
            return False

        # eat the 'STATE: ' message
        self._read_line()

        # read "C: <n>" for each active connection
        for state in range(0, sock_num + 1):
            self._read_line()
            if state == sock_num:
                break
        self._parse_reply(b"C:", idx=5)

        state = self._buf

        # eat the rest of the sockets
        for _ in range(sock_num, FONA_MAX_SOCKETS):
            self._read_line()

        if not "CONNECTED" in state:
            return False

        return True

    def socket_available(self, sock_num):
        """Returns the amount of bytes to be read from the socket.
        :param int sock_num: Desired socket to return bytes available from.

        """
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."
        if not self._send_parse_reply(
            b"AT+CIPRXGET=4," + str(sock_num).encode(),
            b"+CIPRXGET: 4," + str(sock_num).encode() + b",",
        ):
            return False
        data = self._buf
        if self._debug:
            print("\t {} bytes available.".format(self._buf))

        self._read_line()
        self._read_line()

        return data

    def socket_connect(self, sock_num, dest, port, conn_mode=TCP_MODE):
        """Connects to a destination IP address or hostname.
        By default, we use conn_mode TCP_MODE but we may also use UDP_MODE.
        :param int sock_num: Desired socket number
        :param str dest: Destination dest address.
        :param int port: Destination dest port.
        :param int conn_mode: Connection mode (TCP/UDP)

        """
        if self._debug:
            print(
                "*** Socket connect, protocol={}, port={}, ip={}".format(
                    conn_mode, port, dest
                )
            )

        self._uart.reset_input_buffer()
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."

        if self._debug:
            print(
                "* FONA socket connect, socket={}, protocol={}, port={}, ip={}".format(
                    sock_num, conn_mode, port, dest
                )
            )

        # Query local IP Address
        self.uart_write(b"AT+CIFSR\r\n")
        self._read_line()

        # Start connection
        self.uart_write(b"AT+CIPSTART=")
        self.uart_write(str(sock_num).encode())
        if conn_mode == 0:
            self.uart_write(b',"TCP","')
        else:
            self.uart_write(b',"UDP","')
        self.uart_write(dest.encode() + b'","')
        self.uart_write(str(port).encode() + b'"')
        self.uart_write(b"\r\n")

        if not self._expect_reply(REPLY_OK):
            return False

        if not self._expect_reply(b"CONNECT OK"):
            return False

        return True

    def socket_close(self, sock_num, quick_close=1):
        """Close TCP or UDP connection
        :param int sock_num: Desired socket number.
        :param int quick_close: Quickly or slowly close the socket. Enabled by default

        """
        if self._debug:
            print("*** Closing socket #%d" % sock_num)
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."
        self._read_line()

        self.uart_write(b"AT+CIPCLOSE=" + str(sock_num).encode() + b",")
        self.uart_write(str(quick_close).encode() + b"\r\n")
        self._read_line()
        if not self._parse_reply(b"CLOSE OK", idx=0):
            return False
        return True

    def socket_read(self, sock_num, length):
        """Read data from the network into a buffer.
        Returns buffer and amount of bytes read.
        :param int sock_num: Desired socket to read from.
        :param int length: Desired length to read.

        """
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."
        self._read_line()
        if self._debug:
            print("* socket read")

        self.uart_write(b"AT+CIPRXGET=2,")
        self.uart_write(str(sock_num).encode())
        self.uart_write(b",")
        self.uart_write(str(length).encode() + b"\r\n")

        self._read_line()

        if not self._parse_reply(b"+CIPRXGET:"):
            return False

        self._buf = self._uart.read(length)

        return self._buf

    def socket_write(self, sock_num, buffer):
        """Writes bytes to the socket.
        :param int sock_num: Desired socket number to write to.
        :param bytes buffer: Bytes to write to socket.

        """
        self._read_line()
        self._read_line()
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."

        self._uart.reset_input_buffer()
        self.uart_write(b"AT+CIPSEND=" + str(sock_num).encode())
        self.uart_write(b"," + str(len(buffer)).encode())
        self.uart_write(b"\r\n")
        self._read_line()

        if self._buf[0] != 62:
            # promoting mark ('>') not found
            return False

        self.uart_write(buffer + b"\r\n")
        self._read_line(3000)

        if "SEND OK" not in self._buf.decode():
            return False

        return True

    ### UART Reply/Response Helpers ###

    def uart_write(self, buffer):
        """UART ``write`` with optional debug that prints
        the buffer before sending.
        :param bytes buffer: Buffer of bytes to send to the bus.

        """
        if self._debug:
            print("\tUARTWRITE ::", buffer.decode())
        self._uart.write(buffer)

    def _send_parse_reply(self, send_data, reply_data, divider=",", idx=0):
        """Sends data to FONA module, parses reply data returned.
        :param bytes send_data: Data to send to the module.
        :param bytes send_data: Data received by the FONA module.
        :param str divider: Separator

        """
        self._get_reply(send_data)

        if not self._parse_reply(reply_data, divider, idx):
            return False
        return True

    def _get_reply(
        self, data=None, prefix=None, suffix=None, timeout=FONA_DEFAULT_TIMEOUT_MS
    ):
        """Send data to FONA, read response into buffer.
        :param bytes data: Data to send to FONA module.
        :param int timeout: Time to wait for UART response.

        """
        self._uart.reset_input_buffer()

        if data is not None:
            self.uart_write(data + b"\r\n")
        else:
            self.uart_write(prefix + suffix + b"\r\n")

        line = self._read_line(timeout)
        return line

    def _parse_reply(self, reply, divider=",", idx=0):
        """Attempts to find reply in UART buffer, reads up to divider.
        :param bytes reply: Expected response from FONA module.
        :param str divider: Divider character.

        """
        # attempt to find reply in buffer
        parsed_reply = self._buf.find(reply)
        if parsed_reply == -1:
            return False
        parsed_reply = self._buf[parsed_reply:]

        parsed_reply = self._buf[len(reply) :]
        parsed_reply = parsed_reply.decode("utf-8")

        parsed_reply = parsed_reply.split(divider)
        parsed_reply = parsed_reply[idx]

        try:
            self._buf = int(parsed_reply)
        except ValueError:
            self._buf = parsed_reply

        return True

    def _read_line(self, timeout=FONA_DEFAULT_TIMEOUT_MS, multiline=False):
        """Reads one or multiple lines into the buffer. Optionally prints the buffer
        after reading.
        :param int timeout: Time to wait for UART serial to reply, in seconds.
        :param bool multiline: Read multiple lines.

        """
        self._buf = b""
        reply_idx = 0
        while timeout:
            if reply_idx >= 254:
                break

            while self._uart.in_waiting:
                char = self._uart.read(1)
                # print(char)
                if char == b"\r":
                    continue
                if char == b"\n":
                    if reply_idx == 0:
                        # ignore first '\n'
                        continue
                    if not multiline:
                        # second '\n' is EOL
                        timeout = 0
                        break
                # print(char, self._buf)
                self._buf += char
                reply_idx += 1

            if timeout == 0:
                # if self._debug:
                # print("* Timed out!")
                break
            timeout -= 1
            time.sleep(0.001)

        if self._debug:
            print("\tUARTREAD ::", self._buf.decode())

        return reply_idx

    def _send_check_reply(
        self,
        send=None,
        prefix=None,
        suffix=None,
        reply=None,
        timeout=FONA_DEFAULT_TIMEOUT_MS,
    ):
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
        if not self._buf == reply:
            return False

        return True

    def _send_check_reply_quoted(
        self, prefix, suffix, reply, timeout=FONA_DEFAULT_TIMEOUT_MS
    ):
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

        self.uart_write(prefix + b'"')
        self.uart_write(suffix + b'"\r\n')

        line = self._read_line(timeout)
        return line

    def _expect_reply(self, reply, timeout=10000):
        """Reads line from FONA module and compares to reply from FONA module.
        :param bytes reply: Expected reply from module.

        """
        self._read_line(timeout)
        if reply not in self._buf:
            return False
        return True
