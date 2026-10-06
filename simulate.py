"""
Simulation harness for pacer.py: runs the Pacer and feeds simulated tug
events (on TAB) into the strip via simulate_activity().

The stubbing is chosen by the STUB_* environment variables (see
get_controller() in arduino_ws2812b):

    STUB_TUG=1 python simulate.py   # strip commands go to the REAL Arduino,
                                    # tugs are simulated
    STUB_STRIP=1 python simulate.py # strip commands are printed, and the
                                    # simulated tugs are queued but never
                                    # consumed (read_activity is a no-op)
    python simulate.py              # full stub, no device needed
                                    # (STUB_ARDUINO is forced if no STUB_*
                                    # variable was set)

So STUB_STRIP + STUB_TUG together behave like STUB_ARDUINO.

Tug control (mimics the E18-D80NK on the Arduino):
    Hold the TAB key  -> the sensor goes proximal: a '!L' line (the pull).
    Release TAB       -> the sensor goes clear:    a '!R' line (the release).

The key state is *peeked* every 250 ms (never blocking/waiting for input);
only the edges are queued, so nothing is sent while TAB stays held or up.

Usage:
    python simulate.py
"""

import os
import sys
import threading
import time

# Default to the full stub, but let the user pick a granular one.
if not any(os.environ.get(v) for v in ("STUB_ARDUINO", "STUB_STRIP", "STUB_TUG")):
    os.environ["STUB_ARDUINO"] = "1"

from arduino_ws2812b import get_controller
from pacer import Pacer
from churn import make_story

POLL_INTERVAL_S = 0.25  # peek the TAB key every 250 ms


# ---------------------------------------------------------------------- #
# non-blocking key peeking
# ---------------------------------------------------------------------- #

def make_tab_peek():
    """Return a zero-arg function that reports whether TAB is currently
    held down. Never blocks. Windows uses the async key state (true held
    state, no events consumed); other platforms fall back to msvcrt
    key-event approximation."""
    if sys.platform == "win32":
        import ctypes
        VK_TAB = 0x09
        GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState

        def peek():
            return bool(GetAsyncKeyState(VK_TAB) & 0x8000)

        return peek

    # Non-Windows fallback: msvcrt only reports key events (with auto-repeat
    # while held), so treat "no events for a couple of polls" as released.
    try:
        import msvcrt
    except ImportError:
        return lambda: False

    def peek():
        pressed = False
        while msvcrt.kbhit():
            if msvcrt.getch() == b"\t":
                pressed = True
        return pressed

    return peek


# ---------------------------------------------------------------------- #
# tug simulation
# ---------------------------------------------------------------------- #

def feed_tugs(strip):
    """Background thread that watches TAB and queues event lines shaped
    like the Arduino would send: '!L' while TAB is held (the sensor sees
    the audience), '!R' when it is released (the sensor goes clear).
    Only the edges are queued - holding TAB does not repeat."""
    is_tab_held = make_tab_peek()

    def feed():
        was_held = False

        while True:
            held = is_tab_held()
            if held != was_held:
                print(f"[sim] TAB {'pressed - tugging' if held else 'released'}")
                strip.simulate_activity("!L" if held else "!R")
                was_held = held

            time.sleep(POLL_INTERVAL_S)

    threading.Thread(target=feed, daemon=True).start()


def clear_keyboard_buffer():
    """Discard any pending keyboard input (held keys, auto-repeat, the
    Ctrl+C keystroke itself) so nothing leaks into the shell after exit."""
    if sys.platform == "win32":
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        except ImportError:
            pass
    else:
        try:
            import termios
        except ImportError:
            return
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except termios.error:
            pass


def main():
    strip = get_controller()
    pacer = Pacer(make_story(), strip=strip)

    feed_tugs(strip)

    print("Simulator running. Hold TAB to tug, release to let go. Ctrl+C to stop.")
    try:
        pacer.run()
    finally:
        # pacer.run() swallows Ctrl+C itself, so clean up here on the way
        # out either way: drop any keys still buffered at exit.
        clear_keyboard_buffer()


if __name__ == "__main__":
    main()
