
import argparse
import math
import sys
import threading
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


def pulse(start=LED_START, end=LED_END, period=PULSE_PERIOD_S,
          bmin=BRIGHTNESS_MIN, bmax=BRIGHTNESS_MAX, pulses=None):
    """Pulse the strip brown between bmin and bmax brightness.

    pulses: number of full down->up->down cycles to run.
    None (default) pulses endlessly until Ctrl+C.
    """
    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    print(f"Pulsing LEDs {start}-{end} brown, "
          f"brightness {bmin}->{bmax}"
          + (f", {pulses} pulse(s)" if pulses is not None else " endlessly.")
          + " Ctrl+C to stop.")

    try:
        t0 = time.monotonic()
        n = 0
        while pulses is None or n < pulses:
            # Cosine pulse: 0 at min, pi at min -> smooth up and back down
            phase = (time.monotonic() - t0) % period / period * 2 * math.pi
            brightness = (bmin + bmax) / 2 + \
                (bmax - bmin) / 2 * (-math.cos(phase))
            brightness = int(round(brightness))

            r = min(MAX_BRIGHT, int(round(BROWN_RATIO[0] * brightness)))
            g = min(MAX_BRIGHT, int(round(BROWN_RATIO[1] * brightness)))
            b = min(MAX_BRIGHT, int(round(BROWN_RATIO[2] * brightness)))

            strip.send_command(start, end, r, g, b)
            time.sleep(STEP_DELAY_S)
            if (time.monotonic() - t0) >= (n + 1) * period:
                n += 1
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Turn the LEDs off before exiting
        try:
            strip.send_command(start, end, 0, 0, 0)
        except Exception:
            pass
        strip.close()


def background_pulse(start=LED_START, end=LED_END, period=PULSE_PERIOD_S,
                     bmin=BRIGHTNESS_MIN, bmax=BRIGHTNESS_MAX, pulses=None):
    """Run pulse() in a daemon thread and return the thread handle.

    Daemon thread means it won't block the interpreter from exiting;
    call thread.join() if you want to wait for a finite number of pulses.
    """
    t = threading.Thread(target=pulse,
                         args=(start, end, period, bmin, bmax, pulses),
                         daemon=True)
    t.start()
    return t


def main():
    ap = argparse.ArgumentParser(description="Pulse WS2812B strip brown 30-120")
    ap.add_argument("--start", type=int, default=LED_START)
    ap.add_argument("--end", type=int, default=LED_END)
    ap.add_argument("--period", type=float, default=PULSE_PERIOD_S)
    ap.add_argument("--min", dest="bmin", type=int, default=BRIGHTNESS_MIN)
    ap.add_argument("--max", dest="bmax", type=int, default=BRIGHTNESS_MAX)
    ap.add_argument("--pulses", type=int, default=None,
                    help="Number of pulse cycles (default: endless)")
    args = ap.parse_args()
    pulse(args.start, args.end, args.period, args.bmin, args.bmax, args.pulses)


if __name__ == "__main__":
    main()
