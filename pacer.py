"""
Pacer: advances the story when the audience tugs and releases the snake.

Reads the Arduino (via arduino_ws2812b) once every 250 ms. Lines arrive in
the form '!243', where 243 is how far the audience has tugged the snake.

Each new reading is added to a sliding window. On every addition the window
is checked for a completed tug pattern:

    rise  ->  fall  ->  (stop | reversal)

i.e. the reading goes up (the tug), comes back down (the release), and then
either settles within a small deadband for a few samples (stop) or starts
rising again (reversal - another tug beginning). When the pattern completes,
the window is cleared and the next step of the story is invoked.

The story steps are an array of zero-argument callables passed to Pacer().

Usage:
    python pacer.py                 # real Arduino
    python simulate.py              # no device: stub with simulated tugs

Requires:
    pip install pyserial
"""

import re
import time

from arduino_ws2812b import get_controller

POLL_INTERVAL_S = 0.25  # read the Arduino every 250 ms

READING_RE = re.compile(r"!(\d+)")  # a reading line, e.g. '!243'


class Pacer:
    """Detects tugs from a sliding window of readings and advances the story."""

    WINDOW_SIZE = 32    # readings kept in the sliding window (32 * 250ms = 8s)
    PATTERN_LEN = 6     # minimum samples before a tug can be judged complete
    DELTA = 20          # per-sample change counted as a rise/fall; smaller
                        # changes count as "flat" (the stop deadband)
    STOP_SAMPLES = 2    # consecutive flat samples after a fall = "stopped"

    def __init__(self, story_steps, strip=None, poll_interval=POLL_INTERVAL_S,
                 window_size=WINDOW_SIZE, delta=DELTA, stop_samples=STOP_SAMPLES,
                 loop=True):
        """
        story_steps:   array of zero-argument callables, one per story step.
        strip:         controller with read_activity(); defaults to
                       get_controller() (stub when STUB_ARDUINO is set).
        poll_interval: seconds between Arduino reads.
        window_size:   sliding window length (readings).
        delta:         threshold (in reading counts) for a rise or fall;
                       also the deadband that counts as "stopped".
        stop_samples:  flat samples after a fall that confirm a stop.
        loop:          if True, the story wraps around after the last step.
        """
        self.steps = list(story_steps)
        self.strip = strip if strip is not None else get_controller()
        self.poll_interval = poll_interval
        self.delta = delta
        self.stop_samples = stop_samples
        self.loop = loop
        self.window = []           # sliding window of readings, oldest first
        self.window_size = window_size
        self.step_index = 0        # next story step to run
        self._running = False

    # ------------------------------------------------------------------ #
    # reading / window handling
    # ------------------------------------------------------------------ #

    def poll_once(self):
        """Read one line from the Arduino and feed any readings into the
        window. Returns True if a story step was advanced."""
        line = self.strip.read_activity()
        if not line:
            return False
        advanced = False
        for value in READING_RE.findall(line):
            self._add_reading(int(value))
            if self._check_pattern():
                self.window.clear()
                self._advance()
                advanced = True
        return advanced

    def _add_reading(self, value):
        self.window.append(value)
        if len(self.window) > self.window_size:
            self.window.pop(0)

    def _check_pattern(self):
        """Return True if the window contains a completed tug:
        a rise followed by a fall, then a stop or a reversal."""
        w = self.window
        if len(w) < self.PATTERN_LEN:
            return False

        # Classify each step as up (+1), down (-1) or flat (0). Changes
        # smaller than `delta` count as flat, which absorbs sensor jitter
        # and defines the "stopped" deadband.
        moves = []
        for a, b in zip(w, w[1:]):
            if b - a >= self.delta:
                moves.append(1)
            elif a - b >= self.delta:
                moves.append(-1)
            else:
                moves.append(0)

        # Collapse into runs of identical movement, remembering the index
        # of each run's first move (an index into `moves`, where move j is
        # the change from w[j] to w[j + 1]).
        runs = []
        for idx, m in enumerate(moves):
            if not runs or runs[-1][0] != m:
                runs.append([m, 1, idx])
            else:
                runs[-1][1] += 1

        # Drop leading flats: the window may start in the middle of motion.
        start = 0
        while start < len(runs) and runs[start][0] == 0:
            start += 1
        runs = runs[start:]

        # Look for an up run followed (possibly after flat hold/jitter
        # runs, e.g. holding at the top of the tug) by a down run.
        for i in range(len(runs)):
            if runs[i][0] != 1:
                continue
            # First non-flat run after the rise must be the fall.
            j = i + 1
            while j < len(runs) and runs[j][0] == 0:
                j += 1
            if j >= len(runs) or runs[j][0] != -1:
                continue
            baseline = w[runs[i][2]]  # reading just before the rise began
            tail = runs[j + 1:]
            flat_after = sum(c for m, c, _ in tail if m == 0)
            reversed_up = any(m == 1 for m, _, _ in tail)
            # If the fall brought the reading back down to the baseline,
            # the tug is complete even if no further (flat) readings
            # arrive - some devices only report when the value changes.
            returned_to_rest = w[runs[i][2]] - w[-1] >= -self.delta
            # Stopped: enough flat samples after the fall, the reading is
            # back at rest, or the audience is tugging again (reversal):
            # either way the previous tug is complete.
            if (flat_after >= self.stop_samples
                    or reversed_up or returned_to_rest):
                return True
        return False

    # ------------------------------------------------------------------ #
    # story advancing
    # ------------------------------------------------------------------ #

    def _advance(self):
        if not self.steps:
            return
        if not self.loop and self.step_index >= len(self.steps):
            return
        step = self.steps[self.step_index % len(self.steps)]
        self.step_index += 1
        print(f"--- tug detected -> story step {self.step_index - 1}: "
              f"{getattr(step, '__name__', step)}")
        step()

    # ------------------------------------------------------------------ #
    # main loop
    # ------------------------------------------------------------------ #

    def run(self, once=False):
        """Poll the Arduino every poll_interval seconds, advancing the story
        on each completed tug. Runs forever (or until the story is exhausted
        when loop=False); with once=True it performs a single poll."""
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
