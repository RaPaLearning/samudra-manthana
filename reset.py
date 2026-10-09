import sys
import time

from arduino_ws2812b import get_controller
from led_indexes import PATH_END, SEA_START


def reset():
    try:
        strip = get_controller()  # waits for the Arduino 'ready' banner
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    for _ in range(3):
        strip.send_command(SEA_START, PATH_END, 0, 0, 0)
    time.sleep(0.3)

if __name__ == "__main__":
    reset()
