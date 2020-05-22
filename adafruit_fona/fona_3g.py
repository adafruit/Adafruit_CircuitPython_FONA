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
`adafruit_fona`
================================================================================

FONA3G cellular module instance.

* Author(s): ladyada, Brent Rubell

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

from .adafruit_fona import FONA, REPLY_OK

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FONA.git"
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

    def ue_system_info(self):
        """Returns True if UE system is online, otherwise False."""
        if not super()._send_parse_reply(b"AT+CPSI?\r\n", b"+CPSI: ", idx=1):
            return False
        if not self._buf == "Online": # 5.15
            return False
        return True
