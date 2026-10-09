import sys
import time
from churn import run_in_sequence
from arduino_ws2812b import disconnect_controller, get_controller

valid_inputs = ['!L', '!R', None]

def wait_for_user_action(arduino):
    while True:
        line = arduino.read_activity()
        if line in valid_inputs:
            return line


def main():
    arduino = get_controller()
    line = wait_for_user_action(arduino)
    print(f"Initial line: {line}")
    try:
        while True:
            new_line = wait_for_user_action(arduino)
            if new_line:
                print(f"New line: {new_line}")
                run_in_sequence()
                time.sleep(5) # to prevent immediate starting/looping
                line = new_line
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        disconnect_controller()
        sys.exit(0)

if __name__ == "__main__":
    main()
