import sys
import time
import threading

from arduino_ws2812b import disconnect_controller, get_controller
from led_colors import SEA_COLOR_LOW, POISON_COLOR_MAX
from led_indexes import WAVE1_RIGHT, WAVE2_RIGHT, WAVE1_LEFT, WAVE2_LEFT, SHIVA_PATH_START, SHIVA_PATH_END

def neelakantha_drinks_sync():
    try:
        strip = get_controller()  # waits for the Arduino 'ready' banner
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    strip.send_command(16, 140, 170, 0, 170)
    time.sleep(1)
    steps = 25
    wave1_step = (WAVE1_LEFT - WAVE1_RIGHT) / steps
    wave2_step = (WAVE2_RIGHT - WAVE2_LEFT) / steps
    drink_step = (SHIVA_PATH_END - SHIVA_PATH_START) / steps
    strip.send_command(WAVE1_LEFT, WAVE2_LEFT, SEA_COLOR_LOW[0], SEA_COLOR_LOW[1], SEA_COLOR_LOW[2])
    for i in range(steps):
        progress = (i + 1) / steps
        time.sleep(0.1)
        strip.send_command(
            int(WAVE1_LEFT - wave1_step * (i + 1)), int(WAVE2_LEFT + wave2_step * (i + 1)),
            SEA_COLOR_LOW[0], SEA_COLOR_LOW[1], SEA_COLOR_LOW[2]
        )
        time.sleep(0.1)
        strip.send_command(
            SHIVA_PATH_START, int(SHIVA_PATH_START + drink_step * (i + 1)),
            POISON_COLOR_MAX[0], POISON_COLOR_MAX[1], POISON_COLOR_MAX[2]
        )

    strip.send_command(16, 140, 0, 0, 0)
    print('done sending commands')

def neelakantha_drinks():
    return threading.Thread(target=neelakantha_drinks_sync).start()

if __name__ == "__main__":
    try:
        neelakantha_drinks_sync()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        disconnect_controller()
        sys.exit(0)
