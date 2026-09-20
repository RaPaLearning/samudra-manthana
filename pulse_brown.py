#!/usr/bin/env python3
"""
Pulse the brightness of a WS2812B strip (driven by the Arduino Nano running
ws2812b_serial_control.ino) between 30 and 120, in a warm brown color.

Protocol (from the .ino):
    >startLed endLed R G B<

Requires:
    pip install pyserial
"""

import argparse
import math
import sys
import time

import serial
from serial.tools import list_ports

BAUD_RATE = 9600

# Brown hue as normalized ratios (R > G > B, warm/chocolate tone).
# The final RGB = ratio * brightness, so brightness 120 -> max channel 120.
# BROWN_RATIO = (1.0, 0.5, 0.17)  # ~ #7F3F16 scaled
BROWN_RATIO = (0.0, 0.0, 1.0)  # ~ #7F3F16 scaled
MAX_BRIGHT = 200

LED_START = 0
LED_END = 40

BRIGHTNESS_MIN = 5
BRIGHTNESS_MAX = 120
PULSE_PERIOD_S = 4.0  # seconds for a full down->up->down cycle
STEP_DELAY_S = 0.02 # <<try 0.02  # 50 Hz refresh

def find_arduino(vid_pids=(("1A86", "7523"),   # CH340 clone (most Nanos)
                          ("2341", "0043"),    # genuine ATmega328P
                          ("0403", "6001"),    # FTDI
                          ("2341", "0001"))):
    """Return an open Serial port for the first plausible Arduino found."""
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError("No serial ports found.")

    candidates = []
    # First pass: ports whose VID/PID matches known Arduino/USB-serial chips
    for p in ports:
        vid = f"{p.vid:04X}" if p.vid else ""
        pid = f"{p.pid:04X}" if p.pid else ""
        if (vid, pid) in vid_pids:
            candidates.append(p)
    # Second pass: anything with 'arduino' or 'ch340' in the description
    for p in ports:
        if p not in candidates and any(
            k in (p.description or "").lower()
            for k in ("arduino", "ch340", "usb serial")
        ):
            candidates.append(p)

    if len(candidates) == 1:
        return serial.Serial(candidates[0].device, BAUD_RATE, timeout=1)
    elif len(candidates) > 1:
        raise RuntimeError("Multiple plausible Arduino candidates found, unable to figure.")

    raise RuntimeError("No plausible Arduino candidates found.")


def send_command(ser, start, end, r, g, b):
    cmd = f">{start} {end} {r} {g} {b}<"
    # print(f"  -> {cmd}")
    ser.write(cmd.encode("ascii"))
    ser.flush()
    # Read any acknowledgment ("OK: ...") so the buffer doesn't back up
    if ser.in_waiting:
        try:
            reply = ser.readline().decode(errors="ignore").strip()
            if reply:
                print(f"  <- {reply}")
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Pulse WS2812B strip brown 30-120")
    ap.add_argument("--start", type=int, default=LED_START)
    ap.add_argument("--end", type=int, default=LED_END)
    ap.add_argument("--period", type=float, default=PULSE_PERIOD_S)
    ap.add_argument("--min", dest="bmin", type=int, default=BRIGHTNESS_MIN)
    ap.add_argument("--max", dest="bmax", type=int, default=BRIGHTNESS_MAX)
    args = ap.parse_args()

    try:
        ser = find_arduino()
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

            send_command(ser, args.start, args.end, r, g, b)
            time.sleep(STEP_DELAY_S)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Turn the LEDs off before exiting
        try:
            send_command(ser, args.start, args.end, 0, 0, 0)
        except Exception:
            pass
        ser.close()


if __name__ == "__main__":
    main()
