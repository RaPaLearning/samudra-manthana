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
from kurma_pulse import background_pulse

TURTLE_PURR = "media/turtle-purr.mp3"
NEELAKANTHA = "media/neelakantha.mp4"


def make_story():
    """Return the churn story steps: the Media objects are created once,
    up front, and each step starts its media on TUG_START."""
    purr = Media(TURTLE_PURR)
    video = Media(NEELAKANTHA, fullscreen=True)

    def step_first_purr(event):
        if event == TUG_START:
            print("[story] first purr starts")
            purr.play()
            background_pulse(pulses=2)

    def step_second_purr(event):
        if event == TUG_START:
            print("[story] second purr starts")
            purr.play()

    def step_neelakantha(event):
        if event == TUG_START:
            print("[story] neelakantha video starts")
            video.play()

    return [step_first_purr, step_second_purr, step_neelakantha]
