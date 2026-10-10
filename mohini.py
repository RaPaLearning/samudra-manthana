import threading
import sys
import time

from arduino_ws2812b import disconnect_controller
from kurma_pulse import pulse

from led_indexes import MOHINI_PATH_START, MOHINI_PATH_END

def mohini_rocks_sync():
    pulse(start=MOHINI_PATH_START, end=MOHINI_PATH_END, rgb_ratio=(1.0, 1.0, 1.0), period=2, pulses=9)

def mohini_rocks():
    t = threading.Thread(target=mohini_rocks_sync)
    t.start()
    return t

if __name__ == "__main__":
    try:
        mohini_rocks_sync()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        disconnect_controller()
        sys.exit(0)
