#!/usr/bin/env python3
"""
Pulse the brightness of a WS2812B strip (driven by the Arduino Nano running
ws2812b_serial_control.ino) between 30 and 120, in a warm brown color.

Set one of the STUB_* environment variables to run without (or partially
without) the device attached - see get_controller() in arduino_ws2812b
(STUB_ARDUINO = full stub, STUB_STRIP = print commands instead of sending).

Requires:
    pip install pyserial
"""

import argparse
import math
import sys
import time

from arduino_ws2812b import get_controller

# Brown hue as normalized ratios (R > G > B, warm/chocolate tone).
# The final RGB = ratio * brightness, so brightness 120 -> max channel 120.
BROWN_RATIO = (1.0, 0.0, 1.0) #(1.0, 0.5, 0.17)  # ~ #7F3F16 scaled
MAX_BRIGHT = 200

LED_START = 8
LED_END = 70  # NUM_LEDS - 1 in the .ino

BRIGHTNESS_MIN = 5
BRIGHTNESS_MAX = 120
PULSE_PERIOD_S = 4.0  # seconds for a full down->up->down cycle
STEP_DELAY_S = 0.05 # 20 Hz refresh


def main():
    ap = argparse.ArgumentParser(description="Pulse WS2812B strip brown 30-120")
    ap.add_argument("--start", type=int, default=LED_START)
    ap.add_argument("--end", type=int, default=LED_END)
    ap.add_argument("--period", type=float, default=PULSE_PERIOD_S)
    ap.add_argument("--min", dest="bmin", type=int, default=BRIGHTNESS_MIN)
    ap.add_argument("--max", dest="bmax", type=int, default=BRIGHTNESS_MAX)
    args = ap.parse_args()

    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    print(f"Pulsing LEDs {args.start}-{args.end} brown, "
          f"brightness {args.bmin}->{args.bmax}. Ctrl+C to stop.")

    try:
        t0 = time.monotonic()
        while True:
            # Cosine pulse: 0 at min, pi at min -> smooth up and back down
            phase = (time.monotonic() - t0) % args.period / args.period * 2 * math.pi
            brightness = (args.bmin + args.bmax) / 2 + \
                (args.bmax - args.bmin) / 2 * (-math.cos(phase))
            brightness = int(round(brightness))

            r = min(MAX_BRIGHT, int(round(BROWN_RATIO[0] * brightness)))
            g = min(MAX_BRIGHT, int(round(BROWN_RATIO[1] * brightness)))
            b = min(MAX_BRIGHT, int(round(BROWN_RATIO[2] * brightness)))

            strip.send_command(args.start, args.end, r, g, b)
            time.sleep(STEP_DELAY_S)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Turn the LEDs off before exiting
        try:
            strip.send_command(args.start, args.end, 0, 0, 0)
        except Exception:
            pass
        strip.close()


if __name__ == "__main__":
    main()
