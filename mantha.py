"""
Story steps for the samudra-manthana snake-tug experience.

Each step is a callable taking one argument: the tug event (TUG_START or
TUG_END, from pacer.py). A step starts its media when a tug begins
(TUG_START) and deliberately leaves it running after the step returns -
the media keeps playing while the audience holds and releases the snake.
play_media stops the running media before the next step's playback starts,
so a new step always begins clean.

All playback is handled by play_media.py (libvlc, win32); this module only
says what to play and when. Requires python-vlc to be installed.

The steps, in order (STORY_STEPS):
    1. step_turtle_purr    plays media/turtle-purr.mp3
    2. step_purr_again     plays media/turtle-purr.mp3 again
    3. step_neelakantha    plays media/neelakantha.mp4 full-screen
"""

import os

import play_media
from pacer import TUG_START, TUG_END

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")


def _media(filename):
    return os.path.join(MEDIA_DIR, filename)


# ---------------------------------------------------------------------- #
# story steps
# ---------------------------------------------------------------------- #

def step_turtle_purr(event):
    """Step 1: the turtle purrs."""
    if event != TUG_START:
        return
    print("[story] step 1: the turtle purrs")
    play_media.play_sound(_media("turtle-purr.mp3"))


def step_purr_again(event):
    """Step 2: the turtle purrs again."""
    if event != TUG_START:
        return
    print("[story] step 2: the turtle purrs again")
    play_media.play_sound(_media("turtle-purr.mp3"))


def step_neelakantha(event):
    """Step 3: Neelakantha swallows the poison - full-screen video."""
    if event != TUG_START:
        return
    print("[story] step 3: Neelakantha swallows the poison")
    play_media.play_video(_media("neelakantha.mp4"))


STORY_STEPS = [step_turtle_purr, step_purr_again, step_neelakantha]
