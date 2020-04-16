# The MIT License (MIT)
#
# Copyright (c) 2019 ladyada for Adafruit Industries
# Modified by Brent Rubell for Adafruit Industries, 2020
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
`adafruit_fona_socket`
================================================================================

A socket compatible interface with the Adafruit FONA cellular module.

* Author(s): ladyada, Brent Rubell

"""
import gc
import time
from micropython import const
from adafruit_fona import adafruit_fona

_the_interface = None  # pylint: disable=invalid-name

def set_interface(iface):
    """Helper to set the global internet interface."""
    global _the_interface  # pylint: disable=global-statement, invalid-name
    _the_interface = iface


def htonl(x):
    """Convert 32-bit positive integers from host to network byte order."""
    return (
        ((x) << 24 & 0xFF000000)
        | ((x) << 8 & 0x00FF0000)
        | ((x) >> 8 & 0x0000FF00)
        | ((x) >> 24 & 0x000000FF)
    )


def htons(x):
    """Convert 16-bit positive integers from host to network byte order."""
    return (((x) << 8) & 0xFF00) | (((x) >> 8) & 0xFF)


# pylint: disable=bad-whitespace
SOCK_STREAM = const(0x00)  # TCP
TCP_MODE = 80
SOCK_DGRAM = const(0x01)  # UDP
AF_INET = const(3)
NO_SOCKET_AVAIL = const(255)
# pylint: enable=bad-whitespace

# keep track of sockets we allocate
SOCKETS = []

# pylint: disable=too-many-arguments, unused-argument
def getaddrinfo(host, port, family=0, socktype=0, proto=0, flags=0):
    """Translate the host/port argument into a sequence of 5-tuples that
    contain all the necessary arguments for creating a socket connected to that service.

    """
    # TODO!
    pass


def gethostbyname(hostname):
    """Translate a host name to IPv4 address format. The IPv4 address
    is returned as a string.
    :param str hostname: Desired hostname.
    """
    # TODO!
    pass


class socket:
    """A simplified implementation of the Python 'socket' class
    for connecting to a FONA cellular module.
    :param int family: Socket address (and protocol) family.
    :param int type: Socket type.

    """

    def __init__(
        self, family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None, socknum=None
    ):
        if family != AF_INET:
            raise RuntimeError("Only AF_INET family supported by cellular sockets.")
        self._sock_type = type
        self._buffer = b""
        self._timeout = 0

        self._socknum = _the_interface.get_socket(SOCKETS)
        SOCKETS.append(self._socknum)
        self.settimeout(self._timeout)


    @property
    def socknum(self):
        """Returns the socket object's socket number."""
        return self._socknum
        pass

    @property
    def connected(self):
        """Returns whether or not we are connected to the socket."""
        # TODO!
        pass

    def getpeername(self):
        """Return the remote address to which the socket is connected."""
        return _the_interface.remote_ip(self.socknum)
        pass

    def inet_aton(self, ip_string):
        """Convert an IPv4 address from dotted-quad string format.
        :param str ip_string: IP Address, as a dotted-quad string.

        """
        # TODO!
        pass

    def connect(self, address, conntype=None):
        """Connect to a remote socket at address. (The format of address depends
        on the address family — see above.)
        :param tuple address: Remote socket as a (host, port) tuple.
        :param int conntype: Connection type (HTTP or HTTPS).

        """
        assert (
            conntype != 0x03
        ), "Error: SSL/TLS is not currently supported by CircuitPython."
        host, port = address

        print(host, port)
        
        """
        if hasattr(host, "split"):
            host = tuple(map(int, host.split(".")))
        """

        if not _the_interface.socket_connect(
            self.socknum, host, port, conn_mode=self._sock_type
        ):
            raise RuntimeError("Failed to connect to host", host)
        self._buffer = b""

    def send(self, data):
        """Send data to the socket. The socket must be connected to
        a remote socket.
        :param bytearray data: Desired data to send to the socket.

        """
        # TODO!
        pass

    def recv(self, bufsize=0):  # pylint: disable=too-many-branches
        """Reads some bytes from the connected remote address.
        :param int bufsize: Maximum number of bytes to receive.
        """
        # TODO!
        pass

    def readline(self):
        """Attempt to return as many bytes as we can up to \
        but not including '\r\n'.

        """
        # TODO!
        pass

    def available(self):
        """Returns how many bytes of data are available to be read from the socket.

        """
        # TODO!
        pass

    def settimeout(self, value):
        """Sets socket read timeout.
        :param int value: Socket read timeout, in seconds.

        """
        if value < 0:
            raise Exception("Timeout period should be non-negative.")
        self._timeout = value

    def gettimeout(self):
        """Return the timeout in seconds (float) associated
        with socket operations, or None if no timeout is set.

        """
        # TODO!
        pass

    def disconnect(self):
        """Disconnects an active socket."""
        # TODO!
        pass

    def close(self):
        """Closes the socket."""
        # TODO!
        pass