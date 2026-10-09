
import argparse
import math
import sys
import threading
import time

from arduino_ws2812b import disconnect_controller, get_controller
from led_indexes import LED_START, LED_END, SEA_START, SEA_END
from led_colors import SEA_COLOR_RATIO, POISON_COLOR_RATIO, MAX_ALLOWED_BRIGHT, BRIGHTNESS_MIN, BRIGHTNESS_MAX

PULSE_PERIOD_S = 1.0  # seconds for a full down->up->down cycle
STEP_DELAY_S = 0.05 # 20 Hz refresh


def pulse(start=LED_START, end=LED_END, period=PULSE_PERIOD_S,
          bmin=BRIGHTNESS_MIN, bmax=BRIGHTNESS_MAX, rgb_ratio=SEA_COLOR_RATIO,
          pulses=None):
    """Pulse the strip brown between bmin and bmax brightness.

    pulses: number of full down->up->down cycles to run.
    None (default) pulses endlessly until Ctrl+C.

    Owns nothing: does not catch KeyboardInterrupt and does not close
    the strip. The caller (e.g. main(), or the churn story) handles
    interrupts and disconnect_controller().
    """
    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    print(f"Pulsing LEDs {start}-{end}, "
          f"brightness {bmin}->{bmax}"
          + (f", {pulses} pulse(s)" if pulses is not None else " endlessly.")
          + " Ctrl+C to stop.")

    t0 = time.monotonic()
    n = 0
    while pulses is None or n < pulses:
        # Cosine pulse: 0 at min, pi at min -> smooth up and back down
        phase = (time.monotonic() - t0) % period / period * 2 * math.pi
        brightness = (bmin + bmax) / 2 + \
            (bmax - bmin) / 2 * (-math.cos(phase))
        brightness = int(round(brightness))

        r = min(MAX_ALLOWED_BRIGHT, int(round(rgb_ratio[0] * brightness)))
        g = min(MAX_ALLOWED_BRIGHT, int(round(rgb_ratio[1] * brightness)))
        b = min(MAX_ALLOWED_BRIGHT, int(round(rgb_ratio[2] * brightness)))

        strip.send_command(start, end, r, g, b)
        time.sleep(STEP_DELAY_S)
        if (time.monotonic() - t0) >= (n + 1) * period:
            n += 1


def background_pulse(start=LED_START, end=LED_END, period=PULSE_PERIOD_S,
                     bmin=BRIGHTNESS_MIN, bmax=BRIGHTNESS_MAX, rgb_ratio=SEA_COLOR_RATIO,
                     pulses=None):
    """Run pulse() in a daemon thread and return the thread handle.

    Daemon thread means it won't block the interpreter from exiting;
    call thread.join() if you want to wait for a finite number of pulses.
    """
    t = threading.Thread(target=pulse,
                         args=(start, end, period, bmin, bmax, rgb_ratio, pulses),
                         daemon=True)
    t.start()
    return t

def regular_sea_churn():
    return background_pulse(start=SEA_START, end=SEA_END, rgb_ratio=SEA_COLOR_RATIO, pulses=6)

def poison_sea_churn():
    return background_pulse(start=SEA_START, end=SEA_END, rgb_ratio=POISON_COLOR_RATIO, pulses=6)

def main():
    ap = argparse.ArgumentParser(description="Pulse WS2812B strip")
    ap.add_argument("--start", type=int, default=LED_START)
    ap.add_argument("--end", type=int, default=LED_END)
    ap.add_argument("--period", type=float, default=PULSE_PERIOD_S)
    ap.add_argument("--min", dest="bmin", type=int, default=BRIGHTNESS_MIN)
    ap.add_argument("--max", dest="bmax", type=int, default=BRIGHTNESS_MAX)
    ap.add_argument("--pulses", type=int, default=None,
                    help="Number of pulse cycles (default: endless)")
    args = ap.parse_args()
    try:
        pulse(args.start, args.end, args.period, args.bmin, args.bmax,
              SEA_COLOR_RATIO, args.pulses)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Turn the LEDs off and close the connection before exiting.
        try:
            print("Turning off LEDs.")
            strip = get_controller()
            for _ in range(3):
                strip.send_command(args.start, args.end, 0, 0, 0)
            time.sleep(0.1)  # let the off commands drain before closing
            disconnect_controller()
        except Exception as e:
            print(f"Cleanup failed: {e}")


if __name__ == "__main__":
    main()
