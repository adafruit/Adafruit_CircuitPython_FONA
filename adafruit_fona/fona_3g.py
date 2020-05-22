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
    def __init__(self, uart, rst, ri=None, debug=False):
        super(FONA3G, self).__init__(uart, rst, ri, debug)
    
    def set_baudrate(self, baudrate):
        """Sets the FONA's UART baudrate."""
        if not super()._send_check_reply(b"AT+IPREX=" + str(baudrate).encode(), reply=REPLY_OK):
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
            super()._read_line(2000) # eat '+CGPS: 0'
        return True

    @property
    def ue_system_info(self):
        """Returns True if UE system is online, otherwise False."""
        if not super()._send_parse_reply(b"AT+CPSI?\r\n", b"+CPSI: "):
            return False
        if not self._buf == "GSM" or self._buf == 'WCDMA': # 5.15
            return False
        return True

    @property
    def local_ip(self):
        """Returns the IP address of the current active socket."""
        if not super()._send_parse_reply(b"AT+IPADDR", b"+IPADDR:"):
            return False
        return self._buf

    def set_gprs(self, apn=None, enable=True):
        """Configures and brings up GPRS.
        :param bool enable: Enables or disables GPRS.

        """
        if enable:
            if not super()._send_check_reply(b"AT+CGATT=1", reply=REPLY_OK, timeout=10000):
                return False

            if apn is not None: # Configure APN
                apn_name, apn_user, apn_pass = apn
                if not super()._send_check_reply_quoted(b"AT+CGSOCKCONT=1,\"IP\",", apn_name.encode(), REPLY_OK, 10000):
                    return False
                # TODO: Only implement if user/pass are provided
                super()._uart_write(b"AT+CGAUTH=1,1,")
                super()._uart_write(b"\"" + apn_pass.encode() + b"\"")
                super()._uart_write(b",\"" + apn_user.encode() + b"\"\r\n")

            if not super()._get_reply(REPLY_OK, timeout=10000):
                return False

            # Enable PDP Context
            if not self._send_check_reply(b"AT+CIPMODE=1", reply=REPLY_OK, timeout=10000): # Transparent mode
                return False
            
            # TODO: Not sure if this is multi-client, check this out
            if not self._send_check_reply(b"AT+NETOPEN=,,1", reply=b"Network opened", timeout=10000):
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

    def get_host_by_name(self, hostname):
        """Converts a hostname to a 4-byte IP address.
        :param str hostname: Domain name.
        """
        if self._debug:
            print("*** Get host by name")
        if isinstance(hostname, str):
            hostname = bytes(hostname, "utf-8")

        super()._uart_write(b"AT+CDNSGIP=\"" + hostname + b"\"\r\n")
        self._read_line()
        self._read_line(10000) # Read the +CDNSGIP, takes a while

        if not self._parse_reply(b"+CDNSGIP: ", idx=2):
            return False
        return self._buf

    def get_socket(self):
        """Returns if a socket is not in use.
        """
        if self._debug:
            print("*** Get socket")
        
        self._read_line()
        self._uart_write(b"AT+CIPOPEN?\r\n") # Query which sockets are busy

        for socket in range (0, FONA_MAX_SOCKETS):
            self._read_line()
            try: # SIMCOM5320 lacks a socket connection status, this is a workaround
                self._parse_reply(b"+CIPOPEN: ", idx=1)
            except:
                break

        for _ in range(socket, FONA_MAX_SOCKETS):
            self._read_line() # eat the rest of '+CIPOPEN' responses

        if self._debug:
            print("Allocated socket #%d" % socket)
        return socket
