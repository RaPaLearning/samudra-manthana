"""
Pacer: advances the story when the audience pulls and releases the snake.

Reads the Arduino (via arduino_ws2812b) once every 250 ms. The Arduino's
E18-D80NK proximity sensor reports its edges as single-character events
(see ws2812b_serial_control.ino):

    !L   - pull:    sensor changed from clear (non-proximal) to detecting
    !R   - release: sensor changed back to clear

Debouncing happens on the Arduino, so each event line received here is
used as-is: a pull (TUG_START) marks the current story step as begun and
the matching release (TUG_END) advances to the next step.

Unmatched events are ignored: a release with no pull before it, or a
second pull while a tug is still active (e.g. after an Arduino reset
mid-pull).

The story steps are an array of callables passed to Pacer(); each is
called with a single argument, TUG_START when a tug begins and TUG_END
when it ends. The same step sees both events of one tug - the step index
advances when a tug ends.

Usage:
    python pacer.py                 # real Arduino
    python simulate.py              # no device: stub with simulated tugs

Requires:
    pip install pyserial
"""

import time

from arduino_ws2812b import get_controller

POLL_INTERVAL_S = 0.25  # read the Arduino every 250 ms

TUG_START = "start"  # passed to a story step when a tug begins
TUG_END = "end"      # passed to a story step when a tug ends


class Pacer:
    """Maps '!L'/'!R' event lines from the Arduino to TUG_START/TUG_END
    and calls the story steps as each tug starts and ends."""

    def __init__(self, story_steps, strip=None, poll_interval=POLL_INTERVAL_S,
                 loop=True):
        """
        story_steps:   array of callables, one per story step; each is
                       called with TUG_START or TUG_END.
        strip:         controller with read_activity(); defaults to
                       get_controller() (granular stub via the STUB_*
                       environment variables, see arduino_ws2812b).
        poll_interval: seconds between Arduino reads.
        loop:          if True, the story wraps around after the last step.
        """
        self.steps = list(story_steps)
        self.strip = strip if strip is not None else get_controller()
        self.poll_interval = poll_interval
        self.loop = loop
        self.step_index = 0        # next story step to run
        self.tug_active = False    # True between a tug's start and its end
        self._running = False

    # ------------------------------------------------------------------ #
    # event handling
    # ------------------------------------------------------------------ #

    def poll_once(self):
        """Read one line from the Arduino and act on any tug events in it.
        Returns True if a story step was called."""
        line = self.strip.read_activity()
        if not line:
            return False
        called = False
        if "!L" in line and not self.tug_active:
            # The sensor saw the audience reach in: the tug begins.
            self.tug_active = True
            self._advance(TUG_START)
            called = True
        if "!R" in line and self.tug_active:
            # The audience let go: complete the tug, advance the story.
            self.tug_active = False
            self._advance(TUG_END)
            called = True
        return called

    # ------------------------------------------------------------------ #
    # story advancing
    # ------------------------------------------------------------------ #

    def _advance(self, event):
        """Call the current story step with the tug event (TUG_START or
        TUG_END). The same step sees both events of one tug: the step
        index advances when a tug ends."""
        if not self.steps:
            return
        if not self.loop and self.step_index >= len(self.steps):
            return
        idx = self.step_index % len(self.steps)
        step = self.steps[idx]
        if event == TUG_END:
            self.step_index += 1
        print(f"--- tug {event} -> story step {idx}: "
              f"{getattr(step, '__name__', step)}")
        step(event)

    # ------------------------------------------------------------------ #
    # main loop
    # ------------------------------------------------------------------ #

    def run(self, once=False):
        """Poll the Arduino every poll_interval seconds, calling the story
        steps as tugs start (TUG_START) and end (TUG_END). Runs forever
        (or until the story is exhausted when loop=False); with once=True
        it performs a single poll."""
        self._running = True
        try:
            while self._running:
                if self.loop or self.step_index < len(self.steps):
                    self.poll_once()
                if once:
                    return
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            self._running = False
            self.strip.close()

    def stop(self):
        self._running = False
