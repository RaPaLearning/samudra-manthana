"""
Start the real samudra manthana story - no stubs, no simulation.

Everything talks to the actual Arduino Nano (see
ws2812b_serial_control.ino for the wiring and protocol):

    - strip commands  -> the WS2812B strip on D6
    - '!L' / '!R'     -> the E18-D80NK sensor on D2 (pull / release)

Each audience pull (sensor goes proximal, '!L') starts the current story
step; the release ('!R') completes the tug and advances to the next step
(churn.make_story() defines the steps).

Note: any STUB_* variables in the environment are removed on startup -
this is the real run, and a leftover STUB_TUG=1 from tugstub.bat would
otherwise silently switch the tugs back to simulation.

Usage:
    python start.py
"""

import os

# Drop any stub switches before anything that might read them.
for _var in ("STUB_ARDUINO", "STUB_STRIP", "STUB_TUG"):
    os.environ.pop(_var, None)

from arduino_ws2812b import ArduinoStrip
from churn import make_story
from pacer import Pacer


def main():
    pacer = Pacer(make_story())
    print(f"Story running on '{pacer.strip.port}'. "
          "Pull (!L) starts a step, release (!R) advances it. "
          "Ctrl+C to stop.")
    try:
        pacer.run()
    finally:
        # Pacer.run() calls strip.close(), which is a no-op on the shared
        # static connection - this actually releases the COM port.
        ArduinoStrip.disconnect()


if __name__ == "__main__":
    main()