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
            background_pulse(rgb_ratio=(1.0, 0.5, 0.17), pulses=2)  # ~ #7F3F16 scaled

    def step_haalahala(event):
        if event == TUG_START:
            print("[story] second purr starts")
            purr.play()
            background_pulse(rgb_ratio=(1.0, 0.0, 1.0), pulses=2)  # purple

    def step_neelakantha(event):
        if event == TUG_START:
            print("[story] neelakantha video starts")
            neelakantha_video.play()

    def step_danvantri_rakshasa(event):
        if event == TUG_START:
            print("[story] danvantri amruta rakshasa video starts")
            danvantri_rakshasa_video.play()

    def step_mohini_returns(event):
        if event == TUG_START:
            print("[story] mohini returns video starts")
            mohini_returns_video.play()

    return [step_just_churn, step_haalahala, step_neelakantha, 
            step_just_churn, step_danvantri_rakshasa,
            step_just_churn, step_mohini_returns]
