"""
Serial interface for the Arduino Nano running ws2812b_serial_control.ino.

Protocol (from the .ino):
    >startLed endLed R G B<

Exports:
    ArduinoStrip  - real serial connection to the Nano (auto-detects port)
    StubStrip     - stub that just prints what it would send
    get_controller() - returns a StubStrip if STUB_ARDUINO is set in the
                       environment, otherwise ArduinoStrip

Requires:
    pip install pyserial
"""

import os
from collections import deque

from serial.tools import list_ports

try:
    import serial
except ImportError:  # allow importing the stub without pyserial installed
    serial = None

BAUD_RATE = 9600

__all__ = ["ArduinoStrip", "StubStrip", "get_controller", "find_arduino", "BAUD_RATE"]


def find_arduino(vid_pids=(("1A86", "7523"),   # CH340 clone (most Nanos)
                          ("2341", "0043"),    # genuine ATmega328P
                          ("0403", "6001"),    # FTDI
                          ("2341", "0001"))):
    """Return an open Serial port for the first plausible Arduino found."""
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No serial ports found.")

    candidates = []
    # First pass: ports whose VID/PID matches known Arduino/USB-serial chips
    for p in ports:
        vid = f"{p.vid:04X}" if p.vid else ""
        pid = f"{p.pid:04X}" if p.pid else ""
        if (vid, pid) in vid_pids:
            candidates.append(p)
    # Second pass: anything with 'arduino' or 'ch340' in the description
    for p in ports:
        if p not in candidates and any(
            k in (p.description or "").lower()
            for k in ("arduino", "ch340", "usb serial")
        ):
            candidates.append(p)

    if len(candidates) == 1:
        return serial.Serial(candidates[0].device, BAUD_RATE, timeout=1)
    elif len(candidates) > 1:
        raise RuntimeError("Multiple plausible Arduino candidates found, unable to figure.")

    raise RuntimeError("No plausible Arduino candidates found.")


class StubStrip:
    """Drop-in stand-in for ArduinoStrip: prints commands instead of sending."""

    def __init__(self, port=None, quiet=False):
        self.port = port or "STUB"
        self.quiet = quiet
        self._pending = deque()  # lines queued via simulate_activity()
        if not self.quiet:
            print(f"[STUB] STUB_ARDUINO is set - using stub on '{self.port}'")

    def send_command(self, start, end, r, g, b):
        cmd = f">{start} {end} {r} {g} {b}<"
        if not self.quiet:
            print(f"[STUB] {cmd}")

    def simulate_activity(self, text):
        """Queue a line that the next read_activity() call will return."""
        self._pending.append(str(text))

    def read_activity(self):
        """Return the next simulated Arduino line, or None if the queue is empty."""
        if not self._pending:
            return None
        line = self._pending.popleft()
        if not self.quiet:
            print(f"[STUB] <- {line}")
        return line

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class ArduinoStrip:
    """Encapsulates the serial connection to the WS2812B controller."""

    def __init__(self, port=None):
        """
        port: serial device path (e.g. 'COM3', '/dev/ttyUSB0').
              If None, auto-detect the Arduino.
        """
        if serial is None:
            raise RuntimeError("pyserial is not installed (pip install pyserial)")
        if port is None:
            self.ser = find_arduino()
        else:
            self.ser = serial.Serial(port, BAUD_RATE, timeout=1)
        self.port = self.ser.port

    def send_command(self, start, end, r, g, b):
        """Send '>start end R G B<' and drain any acknowledgment lines."""
        cmd = f">{start} {end} {r} {g} {b}<"
        self.ser.write(cmd.encode("ascii"))
        self.ser.flush()
        while (line := self.read_activity()) is not None:
            print(f"  <- {line}")

    def read_activity(self):
        """Return the next line from the Arduino, or None if nothing is waiting."""
        if self.ser.in_waiting <= 0:
            return None
        try:
            line = self.ser.readline().decode(errors="ignore").strip()
        except Exception:
            return None
        return line or None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def get_controller(port=None):
    """Return a controller: StubStrip if STUB_ARDUINO is set, else ArduinoStrip.

    With STUB_ARDUINO set, no serial port is opened at all, so the script can
    be run/tested without the device attached.
    """
    if os.environ.get("STUB_ARDUINO"):
        return StubStrip(port=port)
    return ArduinoStrip(port=port)
