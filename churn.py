"""
The churning story (samudra manthana): one step per tug.

Each step plays its media when the tug begins (TUG_START):

    step 0: play media/turtle-purr.mp3   (the turtle purrs)
    step 1: play media/turtle-purr.mp3   (again)
    step 2: play media/neelakantha.mp4   (the video)

The steps are an array of callables for Pacer(); each is called with
TUG_START when the tug begins and TUG_END when it ends.
"""

from pacer import TUG_START
from play_media import Media
from kurma_pulse import regular_sea_churn, poison_sea_churn

import time

TURTLE_PURR = "media/turtle-purr.mp3"
NEELAKANTHA = "media/neelakantha.mp4"
DANVANTRI_AMRUTA_RAKSHASA = "media/danvantri-amruta-rakshasa.mp4"
MOHINI_RETURNS = "media/mohini-return.mp4"


def make_story():
    """Return the churn story steps: the Media objects are created once,
    up front, and each step starts its media on TUG_START."""
    purr = Media(TURTLE_PURR)
    neelakantha_video = Media(NEELAKANTHA, fullscreen=True)
    danvantri_rakshasa_video = Media(DANVANTRI_AMRUTA_RAKSHASA, fullscreen=True)
    mohini_returns_video = Media(MOHINI_RETURNS, fullscreen=True)

    def step_just_churn(event):
        if event == TUG_START:
            print("[story] first purr starts")
            purr.play()
            regular_sea_churn()

    def step_haalahala(event):
        if event == TUG_START:
            print("[story] second purr starts")
            purr.play()
            poison_sea_churn()

    def step_neelakantha(event):
        if event == TUG_START:
            print("[story] neelakantha")

    def step_danvantri_rakshasa(event):
        if event == TUG_START:
            print("[story] danvantri")

    def step_mohini_returns(event):
        if event == TUG_START:
            print("[story] mohini returns")

    return [step_just_churn, step_haalahala, step_neelakantha, 
            step_just_churn, step_danvantri_rakshasa,
            step_just_churn, step_mohini_returns]


def main(step_index=None):
    """Play every story step, waiting between steps.

    If step_index is given (1-based, from the command line),
    execute only that step and return."""
    steps = make_story()
    if step_index is not None:
        i = step_index - 1
        if not 0 <= i < len(steps):
            raise SystemExit(f"step {step_index} out of range (1..{len(steps)})")
        print(f"[main] step {i}: {steps[i].__name__}")
        steps[i](TUG_START)
        time.sleep(15)
        return
    for i, step in enumerate(steps):
        print(f"[main] step {i}: {step.__name__}")
        step(TUG_START)
        if i < len(steps) - 1:
            time.sleep(15)


if __name__ == "__main__":
    import sys

    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
