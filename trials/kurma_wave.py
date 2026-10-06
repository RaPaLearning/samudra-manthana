"""
kurma_wave.py - sweep a moving block of uniformly lit LEDs along the strip.

A block of `length` LEDs (all at the same color/brightness) travels from
`start` to `end`. Each frame costs just two commands:
    1. one command switching off the LEDs the block has left behind
       (previous trailing edge up to the current one), then
    2. one command painting the whole block (">start end R G B<").
The whole sweep range is cleared once at the start and once at the end,
so the block never flickers while it moves.

Serial reliability: the .ino runs strip.show() inside every command with
interrupts disabled (~7.5 ms for a 250-LED strip). The ATmega328 UART has
only a 2-byte hardware RX buffer, so any bytes arriving during show() are
silently dropped - back-to-back commands corrupt each other and stale
clears get lost, leaving trail LEDs lit. To prevent that, every command
is sent and then we WAIT for the .ino's 'OK:' acknowledgment (sent after
show() completes) before sending the next one, with one retry on timeout.

CLI:
    python kurma_wave.py 8 70 9 ff6600 6000
    python kurma_wave.py --start 8 --end 70 --length 9 --color orange --ms 6000
"""

import argparse
import math
import sys
import time

from arduino_ws2812b import ArduinoStrip, get_controller

LED_START = 8
LED_END = 70  # NUM_LEDS - 1 in the .ino

BAUD_RATE = 9600
MIN_FRAME_S = 0.02  # never hammer the serial link faster than 50 Hz
BYTES_PER_CMD = 18  # rough ASCII length of ">start end R G B<"
ACK_TIMEOUT_S = 0.5  # per-command wait for the Arduino's 'OK:' reply
ACK_ROUNDTRIP_S = 0.05  # ~show() + 'OK:' line TX at 9600 baud

NAMED_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "orange": (255, 102, 0),
    "yellow": (255, 200, 0),
    "gold": (255, 180, 0),
    "white": (255, 255, 255),
    "cyan": (0, 220, 255),
    "magenta": (255, 0, 200),
    "purple": (160, 0, 255),
    "pink": (255, 80, 150),
    "saffron": (255, 153, 51),
}


def parse_color(text):
    """Accept 'r,g,b', '0xRRGGBB'/'#RRGGBB', or a name from NAMED_COLORS."""
    text = text.strip().lower()
    if text in NAMED_COLORS:
        return NAMED_COLORS[text]
    if text.startswith("#"):
        text = text[1:]
    if text.startswith("0x"):
        text = text[2:]
    if len(text) == 6 and all(c in "0123456789abcdef" for c in text):
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    parts = text.replace(" ", "").split(",")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        rgb = tuple(int(p) for p in parts)
        if all(0 <= c <= 255 for c in rgb):
            return rgb
    raise ValueError(f"unknown color: {text!r} (use rrggbb hex, 'r,g,b' or a "
                     f"named color: {', '.join(sorted(NAMED_COLORS))})")


def frame_time_s():
    """Rough serial cost of one frame: two acked commands (stale clear
    + block paint)."""
    return max(2 * ACK_ROUNDTRIP_S, MIN_FRAME_S)


class AckStrip:
    """Wraps a real ArduinoStrip so each command is acknowledged.

    Writes '>start end R G B<', then reads lines until the .ino's
    'OK:'/'Error:' reply arrives (it is printed after strip.show()
    returns). Unsolicited lines (!L / !R tug events) are printed and
    skipped. If no ack arrives within ACK_TIMEOUT_S the command is
    retried once - this is what keeps stale-clears from being dropped
    by RX overruns during show().

    Only real ArduinoStrip instances get the ack treatment; stubs just
    delegate (they never send 'OK:').
    """

    def __new__(cls, strip):
        # No-op wrapper for stubs: return them unchanged.
        if isinstance(strip, ArduinoStrip):
            return super().__new__(cls)
        return strip

    def __init__(self, strip):
        self.strip = strip

    def send_command(self, start, end, r, g, b):
        cmd = f">{start} {end} {r} {g} {b}<"
        for attempt in (1, 2):
            self.strip.ser.write(cmd.encode("ascii"))
            self.strip.ser.flush()
            deadline = time.monotonic() + ACK_TIMEOUT_S
            while time.monotonic() < deadline:
                line = self.strip.read_activity()
                if line is None:
                    time.sleep(0.001)
                    continue
                print(f"  <- {line}", end='\r')
                if line.startswith(("OK:", "Error:")):
                    return
            print(f"  ! no ack (attempt {attempt}), retrying", end='\r')
        print("  !! command unacknowledged, giving up", end='\r')

    def __getattr__(self, name):
        # Delegate everything else (ser, read_activity, close, ...) to the
        # wrapped strip. Only called for attributes not set on self.
        return getattr(self.strip, name)


def kurma_wave(strip, start, end, length, color, duration_ms):
    """Sweep a uniformly lit block of `length` LEDs from `start` to `end`.

    strip:       controller from arduino_ws2812b.get_controller()
    start, end:  LED index the block's center starts / ends at
    length:      number of LEDs in the moving block (>= 1)
    color:       (r, g, b) tuple
    duration_ms: how long the whole start->end sweep should take
    """
    if length < 1:
        raise ValueError("length must be >= 1")
    r, g, b = color
    lo, hi = min(start, end), max(start, end)
    span = hi - lo
    duration = max(duration_ms, 1) / 1000.0

    strip = AckStrip(strip)  # real hardware: ack per command, no lost clears
    print(f"Sweeping {length}-LED block {lo} -> {hi} "
          f"over {duration_ms} ms (serial floor ~"
          f"{(span + 1) * frame_time_s() * 1000:.0f} ms). Ctrl+C to stop.")

    strip.send_command(lo, hi, 0, 0, 0)  # clean slate: clear the sweep range
    t0 = time.monotonic()
    prev = None  # (first, last) indices painted in the previous frame
    try:
        while True:
            elapsed = time.monotonic() - t0
            frac = min(elapsed / duration, 1.0)
            pos = lo + span * frac

            first = int(round(pos - (length - 1) / 2))
            last = first + length - 1
            first, last = max(first, lo), min(last, hi)  # clip to sweep range

            # Switch off just what the block left behind (stale trailing
            # LEDs when moving forward, receding leading edge when moving
            # backward); a single contiguous command, no flicker.
            if prev is not None:
                p_lo, p_hi = prev
                stale_lo, stale_hi = (p_lo, first - 1) if first > p_lo \
                    else (last + 1, p_hi)
                if stale_lo <= stale_hi:
                    strip.send_command(stale_lo, stale_hi, 0, 0, 0)

            strip.send_command(first, last, r, g, b)  # paint the block
            prev = (first, last)

            if frac >= 1.0:
                break

            # Pace frames so the whole sweep lands on `duration`, but never
            # faster than the serial link / MIN_FRAME_S allows.
            step = max(duration / max(span, 1), frame_time_s())
            target = t0 + (math.floor(elapsed / step) + 1) * step
            time.sleep(max(0.0, target - time.monotonic()))
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        try:
            strip.send_command(lo, hi, 0, 0, 0)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(
        description="Sweep a moving block of uniformly lit LEDs along the strip")
    ap.add_argument("start", type=int, nargs="?", default=LED_START,
                    help=f"LED the block's center starts at (default {LED_START})")
    ap.add_argument("end", type=int, nargs="?", default=LED_END,
                    help=f"LED the block's center ends at (default {LED_END})")
    ap.add_argument("length", type=int, nargs="?", default=9,
                    help="LEDs in the moving block (default 9)")
    ap.add_argument("color", type=str, nargs="?", default="orange",
                    help="name, 'r,g,b' or RRGGBB hex (default orange)")
    ap.add_argument("ms", type=int, nargs="?", default=6000,
                    help="milliseconds for the whole sweep (default 6000)")
    args = ap.parse_args()

    try:
        color = parse_color(args.color)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    try:
        strip = get_controller()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    kurma_wave(strip, args.start, args.end, args.length, color, args.ms)
    strip.close()


if __name__ == "__main__":
    main()