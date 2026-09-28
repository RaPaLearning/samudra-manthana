"""
Media playback with programmatic play / pause / resume / stop.

Uses VLC's libvlc (portable copy at C:\\Users\\sudee\\tools\\vlc-3.0.23),
so audio and video are controlled from Python directly - no media player
app, no initialization screen. Video renders in its own borderless-capable
window (fullscreen optional); audio is invisible.

Story usage (with pacer.py):

    from play_media import Media

    video = Media("media/neelakantha.mp4", fullscreen=True)

    def step_show_video():      # a tug starts the video
        video.play()

    def step_freeze():          # next tug freezes it
        video.pause()

    def step_resume():          # next tug continues from the same point
        video.resume()

    def step_end():             # final tug stops it
        video.stop()

A paused player remembers its position, so resume() continues exactly
where it stopped; play() restarts from the beginning.

Usage:
    python play_media.py <sound|video> <filename>
"""

import ctypes
import os
import sys
import time

# --------------------------------------------------------------------- #
# locate the portable libvlc
# --------------------------------------------------------------------- #

VLC_DIR = r"C:\Users\sudee\tools\vlc-3.0.23"   # portable VLC (no install)


def _init_vlc():
    """Make libvlc.dll importable before `import vlc`."""
    candidates = [VLC_DIR, os.environ.get("VLC_HOME"),
                  r"C:\Program Files\VideoLAN\VLC"]
    for d in candidates:
        if not d:
            continue
        dll = os.path.join(d, "libvlc.dll")
        if os.path.isfile(dll):
            # python-vlc picks these up in find_lib()
            os.environ["PYTHON_VLC_LIB_PATH"] = dll
            os.environ["PYTHON_VLC_MODULE_PATH"] = os.path.join(d, "plugins")
            return d
    raise RuntimeError("libvlc.dll not found; set VLC_DIR or install VLC")


_init_vlc()
import vlc  # noqa: E402


class Media:
    """One media file, controlled from Python.

    Methods:
        play([from_s])   start playback (optionally at from_s seconds)
        pause()          freeze playback (position is remembered)
        resume()         continue from the paused position
        stop()           stop and reset to the beginning
        play_from(s)     jump to s seconds and play from there
    Properties:
        is_playing       True while actually playing (False when paused)
        is_paused        True while paused mid-file
        position         current position in seconds
        length           total length in seconds
    """

    def __init__(self, filename, *, fullscreen=False, volume=100, loop=False):
        self.filename = os.path.abspath(filename)
        if not os.path.isfile(self.filename):
            raise FileNotFoundError(self.filename)

        self._player = vlc.MediaPlayer(self.filename)
        self._player.audio_set_volume(volume)
        self.loop = loop
        if fullscreen:
            self._player.set_fullscreen(True)

        # Loop: restart automatically when the media ends.
        if loop:
            em = self._player.event_manager()
            em.event_attach(vlc.EventType.MediaPlayerEndReached,
                            self._on_end)

    # -------------------- callbacks -------------------- #

    def _on_end(self, _event):
        # Called from VLC's thread; a fresh play() restarts the file.
        self._player.play()

    # -------------------- control -------------------- #

    def _wait_state(self, states, timeout=2.0):
        """Wait (max timeout seconds) until the player reaches one of the
        given vlc.State values. VLC state changes are asynchronous, so
        control calls are followed by a short settle wait."""
        end = time.time() + timeout
        while time.time() < end:
            if self._player.get_state() in states:
                return True
            time.sleep(0.02)
        return False

    def play(self, from_s=0):
        """Play from the given offset (seconds). Restarts if already playing."""
        # After the media ends, the player sits in State.Ended and a
        # bare play() is a no-op. stop() resets it so playback can start.
        if self._player.get_state() == vlc.State.Ended:
            self._player.stop()
        self._player.play()
        if from_s:
            # set_time only takes effect once playback has started
            self._wait_state({vlc.State.Playing, vlc.State.Paused})
            self._player.set_time(int(from_s * 1000))

    def pause(self):
        """Freeze playback. Position is kept for resume()."""
        self._player.set_pause(1)          # explicit (pause() toggles)
        self._wait_state({vlc.State.Paused})

    def resume(self):
        """Continue from where pause() left off (no-op if not paused)."""
        if self._player.get_state() == vlc.State.Paused:
            self._player.set_pause(0)
            self._wait_state({vlc.State.Playing})

    def stop(self):
        """Stop playback and reset to the beginning."""
        self._player.stop()

    def play_from(self, seconds):
        """Jump to `seconds` and play from there."""
        self.play(from_s=seconds)

    # -------------------- status -------------------- #

    @property
    def is_playing(self):
        return self._player.is_playing() == 1

    @property
    def is_paused(self):
        return self._player.get_state() == vlc.State.Paused

    @property
    def position(self):
        return self._player.get_time() / 1000.0

    @property
    def length(self):
        return self._player.get_length() / 1000.0

    def wait_until_done(self, timeout=None):
        """Block until playback ends (or timeout seconds)."""
        start = time.time()
        while self._player.get_state() not in (vlc.State.Ended,
                                               vlc.State.Stopped):
            if timeout and time.time() - start > timeout:
                return False
            time.sleep(0.1)
        return True

    def close(self):
        self._player.stop()
        self._player.release()

    def __repr__(self):
        state = "playing" if self.is_playing else \
                "paused" if self.is_paused else "stopped"
        return f"<Media {os.path.basename(self.filename)} {state}>"


# --------------------------------------------------------------------- #
# one-shot convenience helpers (used like the old startfile version)
# --------------------------------------------------------------------- #

def play_sound(filename):
    """Play an audio file invisibly and return the Media handle."""
    m = Media(filename)
    m.play()
    return m


def play_video(filename, *, fullscreen=False):
    """Play a video file in a video window and return the Media handle."""
    m = Media(filename, fullscreen=fullscreen)
    m.play()
    return m


# --------------------------------------------------------------------- #
# self-test / CLI
# --------------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python play_media.py <sound|video> <filename>")
        sys.exit(1)

    mode, path = sys.argv[1], sys.argv[2]
    m = Media(path, fullscreen=True) if mode == "video" \
        else Media(path)
    
    for i in range(2):
        print(f"Iteration {i+1}: playing {path}")
        m.play()
        time.sleep(3)

    m.stop()
    m.close()