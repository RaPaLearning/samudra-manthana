"""
Simulation harness for pacer.py: runs the Pacer without an Arduino.

Uses the StubStrip from arduino_ws2812b (STUB_ARDUINO is forced) and feeds
simulated tug readings into it via simulate_activity(), so the whole
detect-and-advance pipeline can be exercised with no device attached.

Tug control:
    Hold the TAB key  -> the pull reading rises toward 300 (the tug).
    Release TAB       -> the pull reading falls back toward 10 (the release).

The key state is *peeked* every 250 ms (never blocking/waiting for input),
and a reading is only queued when the value actually changes - so once the
pull reaches the 300 or 10 limit, nothing more is sent until it moves again.

Usage:
    python simulate.py
"""

import os
import sys
import threading
import time

# Force the stub before creating any controller.
os.environ["STUB_ARDUINO"] = "1"

from arduino_ws2812b import get_controller
from pacer import Pacer
from churn import make_story

POLL_INTERVAL_S = 0.25  # peek the TAB key every 250 ms

PULL_MIN = 10
PULL_MAX = 300
PULL_STEP = 40          # pull change per 250 ms tick while rising/falling


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
    """Background thread that watches TAB and queues readings shaped like
    the Arduino would send: '!<pull>' lines.

    While TAB is held the pull climbs to PULL_MAX; on release it decays to
    PULL_MIN. Values are only queued when they change."""
    is_tab_held = make_tab_peek()

    def feed():
        pull = PULL_MIN
        last_queued = None
        was_held = False
        announced_max = announced_min = False

        while True:
            held = is_tab_held()
            if held != was_held:
                print(f"[sim] TAB {'pressed - tugging' if held else 'released'}")
                was_held = held

            if held:
                announced_min = False
                if pull < PULL_MAX:
                    pull = min(pull + PULL_STEP, PULL_MAX)
                    if pull == PULL_MAX and not announced_max:
                        print(f"[sim] pull at max ({PULL_MAX}) - holding")
                        announced_max = True
            else:
                announced_max = False
                if pull > PULL_MIN:
                    pull = max(pull - PULL_STEP, PULL_MIN)
                    if pull == PULL_MIN and not announced_min:
                        print(f"[sim] pull at rest ({PULL_MIN})")
                        announced_min = True

            if pull != last_queued:
                strip.simulate_activity(f"!{pull}")
                last_queued = pull

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
