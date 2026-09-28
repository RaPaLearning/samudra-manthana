"""
Pacer: advances the story when the audience tugs and releases the snake.

Reads the Arduino (via arduino_ws2812b) once every 250 ms. Lines arrive in
the form '!243', where 243 is how far the audience has tugged the snake.

Each new reading is added to a sliding window. On every addition the window
is checked for two things:

    a run of rising readings                ->  a tug is starting
    rise -> fall -> (stop | reversal)       ->  the tug is ending

i.e. rising readings announce the tug; the reading then comes back down
(the release) and either settles within a small deadband for a few samples
(stop) or starts rising again (reversal - another tug beginning). When the
ending pattern completes, the window is cleared.

The story steps are an array of callables passed to Pacer(); each is called
with a single argument, TUG_START when a tug begins and TUG_END when it
ends. The same step sees both events of one tug - the step index advances
when a tug ends.

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

TUG_START = "start"  # passed to a story step when a tug begins
TUG_END = "end"      # passed to a story step when a tug ends


class Pacer:
    """Detects tugs from a sliding window of readings and calls the story
    steps as each tug starts and ends."""

    WINDOW_SIZE = 32    # readings kept in the sliding window (32 * 250ms = 8s)
    PATTERN_LEN = 6     # minimum samples before a tug can be judged complete
    DELTA = 20          # per-sample change counted as a rise/fall; smaller
                        # changes count as "flat" (the stop deadband)
    STOP_SAMPLES = 2    # consecutive flat samples after a fall = "stopped"
    RISE_RUN = 2        # consecutive rising samples that announce a tug

    def __init__(self, story_steps, strip=None, poll_interval=POLL_INTERVAL_S,
                 window_size=WINDOW_SIZE, delta=DELTA, stop_samples=STOP_SAMPLES,
                 rise_run=RISE_RUN, loop=True):
        """
        story_steps:   array of callables, one per story step; each is
                       called with TUG_START or TUG_END.
        strip:         controller with read_activity(); defaults to
                       get_controller() (stub when STUB_ARDUINO is set).
        poll_interval: seconds between Arduino reads.
        window_size:   sliding window length (readings).
        delta:         threshold (in reading counts) for a rise or fall;
                       also the deadband that counts as "stopped".
        stop_samples:  flat samples after a fall that confirm a stop.
        rise_run:      consecutive rising samples that announce a tug start.
        loop:          if True, the story wraps around after the last step.
        """
        self.steps = list(story_steps)
        self.strip = strip if strip is not None else get_controller()
        self.poll_interval = poll_interval
        self.delta = delta
        self.stop_samples = stop_samples
        self.rise_run = rise_run
        self.loop = loop
        self.window = []           # sliding window of readings, oldest first
        self.window_size = window_size
        self.step_index = 0        # next story step to run
        self.tug_active = False    # True between a tug's start and its end
        self._running = False

    # ------------------------------------------------------------------ #
    # reading / window handling
    # ------------------------------------------------------------------ #

    def _check_rise(self):
        """Return True if the window shows a tug starting: a run of
        consecutive rising samples long enough to be deliberate. Only
        meaningful while no tug is active (the flag is reset when a tug
        ends), so one tug produces a single start event.

        A fall breaks the rise; flat samples do not (the reading may
        pause briefly on its way up)."""
        if self.tug_active:
            return False
        run = 0
        for a, b in zip(self.window, self.window[1:]):
            if b - a >= self.delta:
                run += 1
                if run >= self.rise_run:
                    return True
            elif a - b >= self.delta:
                run = 0
        return False

    def poll_once(self):
        """Read one line from the Arduino and feed any readings into the
        window. Returns True if a story step was called."""
        line = self.strip.read_activity()
        if not line:
            return False
        called = False
        for value in READING_RE.findall(line):
            self._add_reading(int(value))
            # A run of rising readings announces the tug's start.
            if self._check_rise():
                self.tug_active = True
                self._advance(TUG_START)
                called = True
            # A completed rise -> fall -> (stop | reversal) ends the tug.
            if self._check_pattern():
                self.window.clear()
                self.tug_active = False
                self._advance(TUG_END)
                called = True
        return called

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
