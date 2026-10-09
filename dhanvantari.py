import threading
import sys
import time

from arduino_ws2812b import disconnect_controller, get_controller
from led_indexes import DHANVANTARI_PATH_END, SEA_END, SEA_START, DHANVANTARI_PATH_START

def dhanvantari_aarati_sync():
    try:
        strip = get_controller()  # waits for the Arduino 'ready' banner
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    strip.send_command(SEA_START, SEA_END, 100, 78, 0)
    aarati_pos = DHANVANTARI_PATH_END
    prev_aarati_pos = DHANVANTARI_PATH_END
    for _ in range(3 * (DHANVANTARI_PATH_END - DHANVANTARI_PATH_START)):
        strip.send_command(prev_aarati_pos, prev_aarati_pos + 1, 0, 0, 0)
        time.sleep(0.1)
        strip.send_command(aarati_pos, aarati_pos + 1, 200, 156, 0)
        time.sleep(0.2)
        prev_aarati_pos = aarati_pos
        aarati_pos = DHANVANTARI_PATH_END if aarati_pos == DHANVANTARI_PATH_START else aarati_pos - 1
    strip.send_command(DHANVANTARI_PATH_START, DHANVANTARI_PATH_END + 1, 0, 0, 0)

def dhanvantari_aarati():
    t = threading.Thread(target=dhanvantari_aarati_sync)
    t.start()
    return t

if __name__ == "__main__":
    try:
        dhanvantari_aarati_sync()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        disconnect_controller()
        sys.exit(0)
