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
:py:class:`~adafruit_fona.fona_3g.FONA3G`
`adafruit_fona_3g`
================================================================================

FONA3G cellular module instance.

* Author(s): ladyada, Brent Rubell

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""
from micropython import const
from .adafruit_fona import FONA, REPLY_OK


__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FONA.git"

FONA_MAX_SOCKETS = const(10)


class FONA3G(FONA):
    """FONA 3G module interface.
    :param ~busio.uart UART: FONA UART connection.
    :param ~digialio RST: FONA RST pin.
    :param ~digialio RI: Optional FONA Ring Interrupt (RI) pin.
    :param bool debug: Enable debugging output.

    """

    def __init__(self, uart, rst, ri=None, debug=False):
        super(FONA3G, self).__init__(uart, rst, ri, debug)

    def set_baudrate(self, baudrate):
        """Sets the FONA's UART baudrate."""
        if not super()._send_check_reply(
            b"AT+IPREX=" + str(baudrate).encode(), reply=REPLY_OK
        ):
            return False
        return True

    @property
    def gps(self):
        """Returns True if the GPS session is active, False if it's stopped.."""
        if not super()._send_check_reply(b"AT+CGPS?", reply=b"+CGPS: 1,1"):
            return False
        return True

    @gps.setter
    def gps(self, gps_on=False):
        """Sets GPS module power, parses returned buffer.
        :param bool gps_on: Enables the GPS module, disabled by default.

        """
        # check if GPS is already enabled
        if not super()._send_parse_reply(b"AT+CGPS?", b"+CGPS: "):
            return False

        state = self._buf

        if gps_on and not state:
            super()._read_line()
            if not super()._send_check_reply(b"AT+CGPS=1", reply=REPLY_OK):
                return False
        else:
            if not super()._send_check_reply(b"AT+CGPS=0", reply=REPLY_OK):
                return False
            super()._read_line(2000)  # eat '+CGPS: 0'
        return True

    @property
    def ue_system_info(self):
        """Returns True if UE system is online, otherwise False."""
        super()._send_parse_reply(b"AT+CPSI?\r\n", b"+CPSI: ")
        if not self._buf == "GSM" or self._buf == "WCDMA":  # 5.15
            return False
        return True

    @property
    def local_ip(self):
        """Returns the IP address of the current active socket."""
        if not super()._send_parse_reply(b"AT+IPADDR", b"+IPADDR:"):
            return False
        return self._buf

    # pylint: disable=too-many-return-statements
    def set_gprs(self, apn=None, enable=True):
        """Configures and brings up GPRS.
        :param bool enable: Enables or disables GPRS.

        """
        if enable:
            if not super()._send_check_reply(
                b"AT+CGATT=1", reply=REPLY_OK, timeout=10000
            ):
                return False

            if apn is not None:  # Configure APN
                apn_name, apn_user, apn_pass = apn
                if not super()._send_check_reply_quoted(
                    b'AT+CGSOCKCONT=1,"IP",', apn_name.encode(), REPLY_OK, 10000
                ):
                    return False
                # TODO: Only implement if user/pass are provided
                super()._uart_write(b"AT+CGAUTH=1,1,")
                super()._uart_write(b'"' + apn_pass.encode() + b'"')
                super()._uart_write(b',"' + apn_user.encode() + b'"\r\n')

            if not super()._get_reply(REPLY_OK, timeout=10000):
                return False

            # Enable PDP Context
            if not self._send_check_reply(
                b"AT+CIPMODE=1", reply=REPLY_OK, timeout=10000
            ):  # Transparent mode
                return False

            # TODO: Not sure if this is multi-client, check this out
            if not self._send_check_reply(
                b"AT+NETOPEN=,,1", reply=b"Network opened", timeout=10000
            ):
                return False
            self._read_line()

            if not self.local_ip:
                return True
        else:
            # reset PDP state
            if not self._send_check_reply(
                b"AT+NETCLOSE", reply=b"Network closed", timeout=20000
            ):
                return False
        return True

    ### Socket API (TCP, UDP) ###

    @property
    def sock_timeout(self):
        """Returns the timeout value for sending data."""
        self._read_line()
        if not self._send_parse_reply(b"AT+CIPTIMEOUT?", b"+CIPTIMEOUT: ", idx=2):
            return False
        return self._buf

    def get_host_by_name(self, hostname):
        """Converts a hostname to a 4-byte IP address.
        :param str hostname: Domain name.
        """
        if self._debug:
            print("*** Get host by name")
        if isinstance(hostname, str):
            hostname = bytes(hostname, "utf-8")

        super()._uart_write(b'AT+CDNSGIP="' + hostname + b'"\r\n')
        self._read_line()
        self._read_line(10000)  # Read the +CDNSGIP, takes a while

        if not self._parse_reply(b"+CDNSGIP: ", idx=2):
            return False
        return self._buf

    def get_socket(self):
        """Returns an unused socket."""
        if self._debug:
            print("*** Get socket")

        self._read_line()
        self._uart_write(b"AT+CIPOPEN?\r\n")  # Query which sockets are busy

        for socket in range(0, FONA_MAX_SOCKETS):
            self._read_line()
            try:  # SIMCOM5320 lacks a socket connection status, this is a workaround
                self._parse_reply(b"+CIPOPEN: ", idx=1)
            except IndexError:
                break

        for _ in range(socket, FONA_MAX_SOCKETS):
            self._read_line()  # eat the rest of '+CIPOPEN' responses

        if self._debug:
            print("Allocated socket #%d" % socket)
        return socket

    def socket_connect(self, sock_num, dest, port, conn_mode=0):
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

        self._uart_write(b"AT+CIPHEAD=0\r\n") # Display incoming data 
        self._read_line()
        self._uart_write(b"AT+CIPSRIP=0\r\n") # enable IP recv headers
        self._read_line()

        self._uart_write(b"AT+CIPOPEN=" + str(sock_num).encode())
        if conn_mode == 0:
            self._uart_write(b',"TCP","')
        else:
            self._uart_write(b',"UDP","')
        self._uart_write(dest.encode() + b'",' + str(port).encode() + b"\r\n")

        if not self._expect_reply(b"Connect ok"):
            return False
        return True
    
    def remote_ip(self, sock_num):
        """Returns the IP address of sender."""
        self._read_line()
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."

        self._uart_write(b"AT+CIPOPEN?\r\n")
        for _ in range(0, sock_num+1):
            self._read_line()
            self._parse_reply(b"+CIPOPEN:", idx=2)
        ip_addr = self._buf

        for _ in range(sock_num, FONA_MAX_SOCKETS):
            self._read_line()  # eat the rest of '+CIPOPEN' responses
        return ip_addr

    def socket_write(self, sock_num, buffer):
        """Writes bytes to the socket.
        :param int sock_num: Desired socket number to write to.
        :param bytes buffer: Bytes to write to socket.

        """
        assert (
            sock_num < FONA_MAX_SOCKETS
        ), "Provided socket exceeds the maximum number of \
                                             sockets for the FONA module."

        self._uart.reset_input_buffer()
        self._uart_write(b"AT+CIPSEND=" + str(sock_num).encode() + b"," + str(len(buffer)).encode() + b"\r\n")
        self._read_line()

        if self._buf[0] != 62:
            # promoting mark ('>') not found
            return False

        self._uart_write(buffer + b"\r\n")
        self._read_line() # eat 'OK'

        self._read_line() # expect +CIPSEND
        if not self._parse_reply(b"+CIPSEND:", idx=1):
            return False
        
        if not self._buf == len(buffer):
            return False

        self._read_line(10000) # TODO: Implement cipsend_timeout instead
        if "Send ok" not in self._buf.decode():
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
        print("Reading...")
        self._read_line() # RCV  FROM?
        if not self._expect_reply(b"RECV FROM:"):
            return False
        if not self._parse_reply(b"+IPD"):
            return False
        return 0