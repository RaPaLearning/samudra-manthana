
import argparse
import math
import sys
import threading
import time

from arduino_ws2812b import get_controller

# The final RGB = ratio * brightness, so brightness 120 -> max channel 120.
SEA_COLOR_RATIO = (1.0, 0.7, 0.0)     # can also try ~brown #7F3F16 scaled (1.0, 0.5, 0.17)
POISON_COLOR_RATIO = (1.0, 0.0, 1.0)  # purple

MAX_BRIGHT = 200

LED_START = 8
LED_END = 240  # NUM_LEDS - 1 in the .ino

WAVE1_RIGHT = 16
WAVE1_LEFT = 70
WAVE2_LEFT = 71
WAVE2_RIGHT = 140
SHIVA_PATH_START = 141
SHIVA_PATH_END = 170
VISHNU_PATH_START = 298
VISHNU_PATH_END = 240

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 170
PULSE_PERIOD_S = 1.0  # seconds for a full down->up->down cycle
STEP_DELAY_S = 0.05 # 20 Hz refresh

DRAIN_DURATION_S = 6.0 # total duration of the drain sweep in seconds
FILL_DELAY_S = 1.5     # pause after the initial purple fill
DRAIN_HOLD_S = 1.5     # how long to hold the final state before clearing the path
OFF = (0.0, 0.0, 0.0)


def poison_sea_drain(duration_s=DRAIN_DURATION_S,
                     brightness=BRIGHTNESS_MAX, hold_s=DRAIN_HOLD_S):
    """Fill the waves purple, then drain it up the SHIVA_PATH.

    The waves (WAVE1 + WAVE2) start fully purple. Progress p goes 0->1
    over duration_s seconds (judged with time.monotonic()):

      - The sea color spreads from WAVE2_LEFT (the left edge shared by
        both waves) out to both sides: along WAVE2 towards WAVE2_RIGHT
        and along WAVE1 towards WAVE1_RIGHT. LEDs not yet reached keep
        their purple until the front arrives.
      - The purple climbs SHIVA_PATH from SHIVA_PATH_START (bottom) to
        SHIVA_PATH_END (top) at the same progress; LEDs above the head
        stay dark.

    Strip layout note (continuous winding strip):
      - WAVE1 runs right->left: WAVE1_RIGHT (16) is the right edge,
        WAVE1_LEFT (70) is the left edge.
      - WAVE2 runs left->right: WAVE2_LEFT (71) is the left edge,
        WAVE2_RIGHT (140) is the right edge.
      - SHIVA_PATH runs bottom->top: 141 -> 170.

    Leaves the waves at SEA_COLOR_RATIO when done; the Shiva path is
    cleared after hold_s seconds.
    """
    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    def send(start, end, rgb_ratio, bright):
        strip.send_command(
            start, end,
            min(MAX_BRIGHT, int(round(rgb_ratio[0] * bright))),
            min(MAX_BRIGHT, int(round(rgb_ratio[1] * bright))),
            min(MAX_BRIGHT, int(round(rgb_ratio[2] * bright))),
        )

    print(f"Poison sea drain: waves {WAVE1_RIGHT}-{WAVE2_RIGHT} purple, "
          f"sea spreading from {WAVE2_LEFT} over {duration_s:.1f}s while "
          f"purple climbs SHIVA_PATH {SHIVA_PATH_START}->{SHIVA_PATH_END}. "
          "Ctrl+C to stop.")

    try:
        # 1. Fill both waves purple.
        send(WAVE1_RIGHT, WAVE2_RIGHT, POISON_COLOR_RATIO, brightness)
        print('purple fill done')
        time.sleep(5)

        # # 2. Sea spreads from WAVE2_LEFT outward while purple climbs.
        # t0 = time.monotonic()
        # while (p := (time.monotonic() - t0) / duration_s) < 1.0:
        #     # Wave2 side: sea from the left edge towards the right edge.
        #     e2 = round(WAVE2_LEFT + p * (WAVE2_RIGHT - WAVE2_LEFT))
        #     # Wave1 side: sea from the left edge towards the right edge.
        #     e1 = round(WAVE1_LEFT - p * (WAVE1_LEFT - WAVE1_RIGHT))
        #     send(e1, e2, SEA_COLOR_RATIO, brightness)
        #     time.sleep(STEP_DELAY_S)
        #     # Shiva path: purple up to the head, dark above it.
        #     head = round(SHIVA_PATH_START + p * (SHIVA_PATH_END - SHIVA_PATH_START))
        #     send(SHIVA_PATH_START, head, POISON_COLOR_RATIO, brightness)
        #     if head + 1 <= SHIVA_PATH_END:
        #         send(head + 1, SHIVA_PATH_END, OFF, 0)
        #     time.sleep(STEP_DELAY_S)

        # # 3. Final state: sea everywhere, path fully lit.
        # send(WAVE1_RIGHT, WAVE2_RIGHT, SEA_COLOR_RATIO, brightness)
        # send(SHIVA_PATH_START, SHIVA_PATH_END, POISON_COLOR_RATIO, brightness)
        # time.sleep(hold_s)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Clear the Shiva path; leave the waves at sea color.
        try:
            for _ in range(3):
                send(SHIVA_PATH_START, SHIVA_PATH_END, OFF, 0)
        except Exception:
            pass
        strip.close()


def pulse(start=LED_START, end=LED_END, period=PULSE_PERIOD_S,
          bmin=BRIGHTNESS_MIN, bmax=BRIGHTNESS_MAX, rgb_ratio=SEA_COLOR_RATIO,
          pulses=None):
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

            r = min(MAX_BRIGHT, int(round(rgb_ratio[0] * brightness)))
            g = min(MAX_BRIGHT, int(round(rgb_ratio[1] * brightness)))
            b = min(MAX_BRIGHT, int(round(rgb_ratio[2] * brightness)))

            strip.send_command(start, end, r, g, b)
            time.sleep(STEP_DELAY_S)
            if (time.monotonic() - t0) >= (n + 1) * period:
                n += 1
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Turn the LEDs off before exiting
        try:
            print("Turning off LEDs.")
            for _ in range(3): strip.send_command(start, end, 0, 0, 0)
        except Exception:
            pass
        strip.close()


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
    return background_pulse(start=WAVE1_RIGHT, end=WAVE2_RIGHT, rgb_ratio=SEA_COLOR_RATIO, pulses=6)

def poison_sea_churn():
    return background_pulse(start=WAVE1_RIGHT, end=WAVE2_RIGHT, rgb_ratio=POISON_COLOR_RATIO, pulses=6)

def background_poison_sea_drain():
    return threading.Thread(target=poison_sea_drain, daemon=True).start()

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
    # pulse(args.start, args.end, args.period, args.bmin, args.bmax, SEA_COLOR_RATIO, args.pulses)
    poison_sea_drain()


if __name__ == "__main__":
    main()
