import threading
import sys
import time

from arduino_ws2812b import disconnect_controller, get_controller
from kurma_pulse import pulse
from led_indexes import SEA_END, SEA_START

def dhanvantari_rocks_sync():
    pulse(start=SEA_START, end=SEA_END, rgb_ratio=(1.0, 1.0, 1.0), period=4, pulses=6)

def dhanvantari_rocks():
    t = threading.Thread(target=dhanvantari_rocks_sync)
    t.start()
    return t

if __name__ == "__main__":
    try:
        dhanvantari_rocks_sync()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        disconnect_controller()
        sys.exit(0)
