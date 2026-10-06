"""
Simulation stubs for arduino_ws2812b.

The stubbing is granular and composable; which pieces are stubbed is
chosen by the STUB_* environment variables (see get_controller() in
arduino_ws2812b):

    STUB_STRIP    - stub only the strip functionality: send_command()
                    prints what it would send, no serial port is opened.
                    read_activity() always returns None (no tug events).
    STUB_TUG      - stub only the tugging: strip commands are sent to the
                    real Arduino, but tug events are injected via
                    simulate_activity() instead of being read from the
                    serial port.
    STUB_ARDUINO  - stub the whole thing: no serial port is opened at all
                    (equivalent to STUB_STRIP + STUB_TUG).

Classes:
    StripStub  - stubs only send_command (colour & brightness)
    StubStrip  - stubs everything (the original full stub)
    TugStub    - wraps a real ArduinoStrip; only the tug-reading side is
                 stubbed, send_command() goes to the actual device

Requires:
    pip install pyserial (only for TugStub)
"""

from collections import deque

__all__ = ["StripStub", "StubStrip", "TugStub"]


class _TugQueue:
    """Mixin: simulate_activity()/read_activity() backed by an in-memory
    queue, shaped like the lines the Arduino would send."""

    def _init_tug_queue(self, quiet=False):
        self._pending = deque()
        self._quiet = quiet

    def simulate_activity(self, text):
        """Queue a line that the next read_activity() call will return."""
        self._pending.append(str(text))

    def read_activity(self):
        """Return the next simulated line, or None if the queue is empty."""
        if not self._pending:
            return None
        line = self._pending.popleft()
        if not self._quiet:
            print(f" [STUB] <- {line}")
        return line


class StripStub:
    """Stubs only the strip side (STUB_STRIP): send_command prints what it
    would send instead of talking to a serial port. read_activity() always
    returns None - there is no tug simulation here."""

    def __init__(self, port=None, quiet=False):
        self.port = port or "STUB"
        self.quiet = quiet
        if not self.quiet:
            print(f" [STUB] STUB_STRIP is set - strip commands are printed, not sent")

    def send_command(self, start, end, r, g, b):
        cmd = f">{start} {end} {r} {g} {b}<"
        if not self.quiet:
            print(f" [STUB] {cmd}", end='\r')

    def read_activity(self):
        return None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class StubStrip(_TugQueue, StripStub):
    """Full stub (STUB_ARDUINO): prints strip commands and queues simulated
    tug events fed in via simulate_activity(). No serial port involved."""

    def __init__(self, port=None, quiet=False):
        StripStub.__init__(self, port=port, quiet=quiet)
        self._init_tug_queue(quiet=quiet)
        if not self.quiet:
            print(f" [STUB] tugs are simulated - feed lines via simulate_activity()")

    # read_activity() comes from _TugQueue (earlier in the MRO than
    # StripStub's always-None version).


class TugStub(_TugQueue):
    """Stubs only the tug side (STUB_TUG): wraps a real ArduinoStrip so
    send_command() reaches the actual device, while tug events are
    injected via simulate_activity(). When the queue is empty,
    read_activity() falls through to the serial port (draining any ack
    lines the Arduino sent)."""

    def __init__(self, port=None, quiet=False):
        # Imported lazily to avoid a circular import with arduino_ws2812b.
        from arduino_ws2812b import ArduinoStrip

        self._strip = ArduinoStrip(port=port)
        self.port = self._strip.port
        self.quiet = quiet
        self._init_tug_queue(quiet=quiet)
        if not self.quiet:
            print(f" [STUB] STUB_TUG is set - strip commands go to '{self.port}', "
                  f"tugs are simulated via simulate_activity()")

    def send_command(self, start, end, r, g, b):
        self._strip.send_command(start, end, r, g, b)

    def read_activity(self):
        line = _TugQueue.read_activity(self)
        if line is not None:
            return line
        return self._strip.read_activity()

    def close(self):
        self._strip.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()