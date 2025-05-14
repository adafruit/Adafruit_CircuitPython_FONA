# SPDX-FileCopyrightText: 2020 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_fona_network`
=================================================================================

Interface for connecting to and interacting with GSM and CDMA cellular networks.

* Author(s): Brent Rubell

"""

try:
    from types import TracebackType
    from typing import Optional, Tuple, Type

    from adafruit_fona.adafruit_fona import FONA
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FONA.git"

# Network types
NET_GSM = 0x01
NET_CDMA = 0x02


class CELLULAR:
    """Interface for connecting to and interacting with GSM and CDMA cellular networks.

    :param FONA fona: The Adafruit FONA module we are using.
    :param tuple apn: Tuple containing APN name, (optional) APN username,
                        and APN password.
    """

    def __init__(self, fona: FONA, apn: Tuple[str, Optional[str], Optional[str]]) -> None:
        self._iface = fona
        self._apn = apn
        self._network_connected = False
        self._network_type = NET_GSM
        self._has_gps = False

        # These are numbers defined in adafruit_fona FONA versions
        # For some reason, we can't import them from the adafruit_fona file

        if self._iface.version in {0x4, 0x5}:
            self._network_type = NET_CDMA

        if self._iface.version in {0x2, 0x3, 0x4, 0x5}:
            self._iface.gps = True
            self._has_gps = True

    def __enter__(self) -> "CELLULAR":
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[type]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.disconnect()

    @property
    def imei(self) -> str:
        """Returns the modem's IEMI number, as a string."""
        return self._iface.iemi

    @property
    def iccid(self) -> str:
        """Returns the SIM card's ICCID, as a string."""
        return self._iface.iccid

    @property
    def is_attached(self) -> bool:
        """Returns if the modem is attached to the network."""
        if self._network_type == NET_GSM:
            if self._has_gps and self._iface.gps == 3 and self._iface.network_status == 1:
                return True

            if not self._has_gps and self._iface.network_status == 1:
                return True
        elif self._iface.ue_system_info == 1 and self._iface.network_status == 1:
            return True
        return False

    @property
    def is_connected(self):
        """Returns if attached to network and an IP Addresss was obtained."""
        if not self._network_connected:
            return False
        return True

    def connect(self) -> None:
        """Connect to cellular network."""
        if self._iface.set_gprs(self._apn, True):
            self._network_connected = True
        else:
            # reset context for next connection attempt
            self._iface.set_gprs(self._apn, False)

    def disconnect(self) -> None:
        """Disconnect from cellular network."""
        self._iface.set_gprs(self._apn, False)
        self._network_connected = False
