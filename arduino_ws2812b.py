"""
Serial interface for the Arduino Nano running ws2812b_serial_control.ino.

Protocol (from the .ino):
    >startLed endLed R G B<

Exports:
    ArduinoStrip  - real serial connection to the Nano (auto-detects port)
    get_controller() - returns a controller based on the STUB_* environment
                       variables (see the docstring there; the stub classes
                       themselves live in arduino_stub.py)

Requires:
    pip install pyserial
"""

import os
import time

from serial.tools import list_ports

try:
    import serial
except ImportError:  # allow importing the stub without pyserial installed
    serial = None

BAUD_RATE = 9600

# Singleton cache for get_controller(): one controller per process.
_controller = None
_controller_key = None

__all__ = ["ArduinoStrip", "get_controller", "disconnect_controller", "find_arduino", "BAUD_RATE"]


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


class ArduinoStrip:
    """Encapsulates the serial connection to the WS2812B controller.

    The underlying serial connection is a class-level (static) resource:
    it is opened once on the first ArduinoStrip and shared by every
    instance afterwards, so the COM port is never opened a second time
    (which the OS would reject while it is already open).
    """

    _ser = None  # shared, opened once for the whole process

    def __init__(self, port=None):
        """
        port: serial device path (e.g. 'COM3', '/dev/ttyUSB0').
              If None, auto-detect the Arduino. Only used the first
              time the connection is opened; later instances reuse it.
        """
        cls = ArduinoStrip
        if cls._ser is not None and cls._ser.is_open:
            self.ser = cls._ser  # reuse the already-open static connection
        else:
            if serial is None:
                raise RuntimeError("pyserial is not installed (pip install pyserial)")
            if port is None:
                cls._ser = find_arduino()
            else:
                cls._ser = serial.Serial(port, BAUD_RATE, timeout=1)
            self.ser = cls._ser
            # Opening the port toggles DTR, which resets the Nano; the
            # bootloader needs ~1.5-2 s before the sketch listens. Any
            # command sent before that is silently lost, so wait for the
            # sketch's 'ready' banner before returning.
            self._wait_for_ready()
        self.port = self.ser.port

    def _wait_for_ready(self, timeout=5.0):
        """Block until the sketch's 'ready' banner arrives (or timeout)."""
        print("Waiting for Arduino to be ready...")
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            line = self.read_activity()
            if line is not None and "ready" in line:
                print("Arduino is ready.")
                return
            time.sleep(0.05)
        print("Warning: no 'ready' banner from Arduino; continuing anyway.")

    def send_command(self, start, end, r, g, b):
        """Send '>start end R G B<' and drain any acknowledgment lines."""
        cmd = f">{start} {end} {r} {g} {b}<"
        self.ser.write(cmd.encode("ascii"))
        self.ser.flush()
        # This will swallow any activity like pulls and releases
        while (line := self.read_activity()) is not None:
            print(f"  <- {line}", end='\r')

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
        """No-op on instances: the connection is shared (static) and stays
        open for other instances. Use disconnect() to actually close it."""
        pass

    @classmethod
    def disconnect(cls):
        """Close the shared static serial connection (e.g. on program exit)."""
        if cls._ser is not None and cls._ser.is_open:
            cls._ser.close()
        cls._ser = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()  # keeps the static connection open; see disconnect()


def get_controller(port=None):
    """Return a (process-wide singleton) controller based on the STUB_*
    environment variables.

    STUB_ARDUINO  - full stub (StubStrip): prints strip commands, tug
                    events are simulated; no serial port is opened at
                    all, so the script can run without the device.
    STUB_STRIP    - only the strip is stubbed (StripStub): send_command()
                    prints instead of sending; no serial port; no tugs.
    STUB_TUG      - only the tugging is stubbed (TugStub): strip commands
                    go to the real Arduino; tug events are injected via
                    simulate_activity() instead of being read from serial.
    (none set)    - real ArduinoStrip.

    The same instance is returned for repeated calls (keyed on which
    stub mode is active), so every part of a program shares one
    connection and one wait-for-ready. Use disconnect_controller() to
    close it.
    """
    # Imported lazily: arduino_stub imports ArduinoStrip from this module.
    from arduino_stub import StripStub, StubStrip, TugStub

    global _controller, _controller_key
    if os.environ.get("STUB_ARDUINO"):
        key, cls = "arduino", StubStrip
    elif os.environ.get("STUB_STRIP"):
        key, cls = "strip", StripStub
    elif os.environ.get("STUB_TUG"):
        key, cls = "tug", TugStub
    else:
        key, cls = "real", ArduinoStrip

    if _controller is None or _controller_key != key:
        _controller = cls(port=port)
        _controller_key = key
    return _controller


def disconnect_controller():
    """Close the shared controller from get_controller(). Safe for stubs
    (their close() is a no-op) and for the real ArduinoStrip (closes the
    shared serial connection)."""
    global _controller
    if _controller is None:
        return
    try:
        if isinstance(_controller, ArduinoStrip):
            _controller.disconnect()
        else:
            _controller.close()
    finally:
        _controller = None
