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
from neelakantha import shiva_entry, neelakantha_drinks

import time

TURTLE_PURR = "media/turtle-purr.mp3"
HISSING_POISON = "media/hissing-poison.mp3"
NEELAKANTHA_CALL = "media/srikantha.mp3"
NAMAMEESHAM = "media/namameesham.mp3"
DHANVANTARI = "media/dhanvantari-mantra.mp3"

def make_story():
    """Return the churn story steps: the Media objects are created once,
    up front, and each step starts its media on TUG_START."""
    purr = Media(TURTLE_PURR)
    hiss = Media(HISSING_POISON)
    neelakantha_call = Media(NEELAKANTHA_CALL)
    namameesham = Media(NAMAMEESHAM)
    dhanvantari = Media(DHANVANTARI)

    def step_just_churn(event):
        if event == TUG_START:
            print("[story] first tug")
            purr.play()
            return regular_sea_churn()

    def step_haalahala(event):
        if event == TUG_START:
            print("[story] poison release")
            hiss.play()
            return poison_sea_churn()

    def call_neelakantha(event):
        if event == TUG_START:
            print("[story] calling neelakantha")
            neelakantha_call.play()
            return shiva_entry()

    def step_neelakantha(event):
        if event == TUG_START:
            print("[story] neelakantha")
            namameesham.play()
            return neelakantha_drinks()

    def step_danvantri_rakshasa(event):
        if event == TUG_START:
            print("[story] danvantri")
            dhanvantari.play()
            return dhanvantari_rocks()

    def step_mohini_returns(event):
        if event == TUG_START:
            print("[story] mohini returns")

    return [step_just_churn, step_haalahala, call_neelakantha, step_neelakantha, 
            step_just_churn, step_danvantri_rakshasa, step_mohini_returns]


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
        t = steps[i](TUG_START)
        if t is not None:
            t.join()
        time.sleep(1)
        return
    for i, step in enumerate(steps):
        print(f"[main] step {i}: {step.__name__}")
        t = step(TUG_START)
        if t is not None:
            t.join()
        print("---")


if __name__ == "__main__":
    import sys

    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
