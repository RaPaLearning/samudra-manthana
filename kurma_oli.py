import argparse
import math
import sys
import threading
import time

from arduino_ws2812b import disconnect_controller, get_controller
from led_indexes import SEA_START, SEA_END
from led_colors import SEA_COLOR_RATIO, POISON_COLOR_RATIO, MAX_ALLOWED_BRIGHT, BRIGHTNESS_MAX

STEP_DELAY_S = 0.05  # 20 Hz refresh
CHURN_PULSE_S = 1.0  # default seconds for one half-pulse


def _sea_halves():
    """Split the sea range into two halves.

    Returns (first_half, second_half) as (start, end) tuples,
    with the extra LED (odd count) going to the second half.
    """
    n = SEA_END - SEA_START + 1
    first = (SEA_START, SEA_START + n // 2 - 1 + 10)
    second = (SEA_START + n // 2 - 10, SEA_END)
    return first, second


def _sea_color(brightness, rgb_ratio):
    r = min(MAX_ALLOWED_BRIGHT, int(round(rgb_ratio[0] * brightness)))
    g = min(MAX_ALLOWED_BRIGHT, int(round(rgb_ratio[1] * brightness)))
    b = min(MAX_ALLOWED_BRIGHT, int(round(rgb_ratio[2] * brightness)))
    return r, g, b


def churn_halves(pulse_duration=CHURN_PULSE_S, pulses=1,
                 rgb_ratio=SEA_COLOR_RATIO, bmax=BRIGHTNESS_MAX):
    """Churn the sea: pulse the two halves of SEA_START..SEA_END alternately.

    pulse_duration: seconds for one pulse (one half brightens and dims).
    pulses: total number of half-pulses to run; each pulse lights one half.

    While one half pulses, the other half is dark, so the churn visibly
    swaps sides: left, right, left, right, ...

    Owns nothing: does not catch KeyboardInterrupt and does not close
    the strip. The caller handles interrupts and disconnect_controller().
    """
    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    first, second = _sea_halves()

    print(f"Churning sea halves {first} / {second}: "
          f"{pulse_duration}s per pulse, {pulses} pulse(s). Ctrl+C to stop.")

    for p in range(pulses):
        lit, dark = (first, second) if p % 2 == 0 else (second, first)
        # Keep the resting half dark while the active half pulses.
        strip.send_command(dark[0], dark[1], 0, 0, 0)

        t0 = time.monotonic()
        while True:
            t = time.monotonic() - t0
            if t >= pulse_duration:
                break
            # Cosine pulse: 0 at t=0, bmax at t=pulse_duration/2, 0 at end
            phase = t / pulse_duration * 2 * math.pi
            brightness = bmax / 2 * (1 - math.cos(phase))
            r, g, b = _sea_color(int(round(brightness)), rgb_ratio)
            strip.send_command(lit[0], lit[1], r, g, b)
            time.sleep(STEP_DELAY_S)

        # Hand off cleanly: darken the half we just pulsed.
        strip.send_command(lit[0], lit[1], 0, 0, 0)


def spread_from_middle(total_time, steps, rgb_ratio=SEA_COLOR_RATIO,
                       bmax=BRIGHTNESS_MAX):
    """Start at the middle of the sea and spread outwards to both ends.

    total_time: seconds for the whole spread.
    steps: number of discrete frames; radius grows a step each frame.
    Leaves the sea fully lit in rgb_ratio at bmax when done (caller
    can turn it off, e.g. main()'s cleanup).

    Owns nothing: does not catch KeyboardInterrupt and does not close
    the strip. The caller handles interrupts and disconnect_controller().
    """
    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    mid = (SEA_START + SEA_END) // 2
    max_radius = max(mid - SEA_START, SEA_END - mid)

    print(f"Spreading sea from LED {mid} outwards: "
          f"{total_time}s over {steps} steps. Ctrl+C to stop.")

    r, g, b = _sea_color(bmax, rgb_ratio)
    delay = total_time / steps
    for step in range(1, steps + 1):
        radius = round(step / steps * max_radius)
        start = max(SEA_START, mid - radius)
        end = min(SEA_END, mid + radius)
        strip.send_command(start, end, r, g, b)
        time.sleep(delay)

def churn_with_oli_sync():
    spread_from_middle(total_time=1, steps=20)
    time.sleep(0.1)
    spread_from_middle(total_time=1, steps=20, rgb_ratio=(0, 0, 0))
    time.sleep(0.1)
    spread_from_middle(total_time=1, steps=20)
    time.sleep(0.1)
    churn_halves(pulse_duration=1, pulses=8)
    time.sleep(0.1)
    spread_from_middle(total_time=1, steps=20)
    time.sleep(0.1)
    spread_from_middle(total_time=1, steps=20, rgb_ratio=(0, 0, 0))
    time.sleep(0.1)

def churn_with_oli():
    t = threading.Thread(target=churn_with_oli_sync, daemon=True)
    t.start()
    return t

def main():
    try:
        churn_with_oli_sync()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Turn the LEDs off and close the connection before exiting.
        try:
            print("Turning off LEDs.")
            strip = get_controller()
            for _ in range(3):
                strip.send_command(SEA_START, SEA_END, 0, 0, 0)
            time.sleep(0.1)  # let the off commands drain before closing
            disconnect_controller()
        except Exception as e:
            print(f"Cleanup failed: {e}")


if __name__ == "__main__":
    main()
