import sys
import time
import threading

from arduino_ws2812b import disconnect_controller, get_controller
from led_colors import SEA_COLOR_LOW, POISON_COLOR_MAX
from led_indexes import SEA_START, SEA_END, SHIVA_ENTRY_END, SHIVA_ENTRY_START, SHIVA_PATH_START, SHIVA_PATH_END, SHIVA_THROAT_START, SHIVA_THROAT_END
from kurma_pulse import pulse, SEA_COLOR_RATIO

def shiva_entry_sync():
    pulse(start=SHIVA_ENTRY_START, end=SHIVA_ENTRY_END, rgb_ratio=(1.0, 0.4, 0), period=2, pulses=6)

def shiva_entry():
    t = threading.Thread(target=shiva_entry_sync)
    t.start()
    return t

def neelakantha_drinks_sync():
    try:
        strip = get_controller()  # waits for the Arduino 'ready' banner
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    strip.send_command(SEA_START, SEA_END, 170, 0, 170)
    time.sleep(1)
    steps = 100
    sea_step = (SEA_END - SEA_START) / steps
    drink_step = (SHIVA_PATH_END - SHIVA_PATH_START) / steps
    for i in range(steps):
        progress = (i + 1) / steps
        time.sleep(0.1)
        strip.send_command(
            SEA_START, int(SEA_START + sea_step * (i + 1)),
            SEA_COLOR_LOW[0], SEA_COLOR_LOW[1], SEA_COLOR_LOW[2]
        )
        time.sleep(0.1)
        strip.send_command(
            SHIVA_PATH_START, int(SHIVA_PATH_START + drink_step * (i + 1)),
            POISON_COLOR_MAX[0], POISON_COLOR_MAX[1], POISON_COLOR_MAX[2]
        )

    strip.send_command(SEA_START, SEA_END, 0, 0, 0)
    strip.send_command(SHIVA_PATH_START, SHIVA_PATH_END, 0, 0, 0)
    strip.send_command(SHIVA_THROAT_START, SHIVA_THROAT_END, 170, 0, 170)
    time.sleep(1)
    pulse(start=SEA_START, end=SEA_END, rgb_ratio=SEA_COLOR_RATIO, period=2, pulses=6)

def neelakantha_drinks():
    t = threading.Thread(target=neelakantha_drinks_sync)
    t.start()
    return t

if __name__ == "__main__":
    try:
        neelakantha_drinks_sync()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        disconnect_controller()
        sys.exit(0)
