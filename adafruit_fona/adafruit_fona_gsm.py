# The MIT License (MIT)
#
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
`adafruit_fona_gsm`
=================================================================================

Interface for 2G GSM cellular modems such as the Adafruit FONA808.

* Author(s): Brent Rubell

"""
import time

class GSM:
    def __init__(self, fona, apn, debug=True):
        """Initializes interface with 2G GSM modem.
        :param adafruit_fona fona: Adafruit FONA module. 
        :param tuple apn: Tuple containing APN name, (optional) APN username,
                            and APN password.
        :param bool debug: Enable verbose debug output.

        """
        self._iface = fona
        self._debug = debug

        # Attempt to enable GPS module and obtain GPS fix
        attempts = 10
        self._iface.gps = True
        while not self._iface.gps == 3:
            if attempts < 0:
                raise RuntimeError("Unable to establish GPS fix.")
            attempts -= 1
            time.sleep(0.5)

        # Check if FONA is registered to GSM network
        attempts = 30
        while self._iface.network_status != 1:
            if attempts == 0:
                raise TimeoutError("Not registered with GSM network.")
            if self._debug:
                print("* Not registered with network, retrying, ", attempts)
            attempts -= 1
            time.sleep(1)

        # Set GPRS
        attempts = 5
        while not self._iface.set_gprs(apn, True):
            if attempts == 0:
                raise RuntimeError("Unable to establish PDP context.")
            if self._debug:
                print("* Unable to bringup network, retrying, ", attempts)
            self._iface.set_gprs(apn, False)
            attempts -= 1
            time.sleep(5)

        # Query local IP
        if not self._iface.local_ip:
            raise RuntimeError("Unable to obtain module IP address.")

    def network_attached(self):
        """Returns if modem is attached to cellular network."""
        # TODO!
        pass

