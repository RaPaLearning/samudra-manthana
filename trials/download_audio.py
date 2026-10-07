#!/usr/bin/env python3
"""Download audio from a YouTube video (no ffmpeg required).

Usage:
    python download_audio.py https://www.youtube.com/watch?v=SgMbPe9v2E4
    python download_audio.py https://www.youtube.com/watch?v=SgMbPe9v2E4 -o ./music
    python download_audio.py <url> --mp3   # only if ffmpeg is installed

Requires: pip install yt-dlp
"""

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("yt-dlp is not installed. Run: pip install yt-dlp")


def download_audio(url: str, output_dir: str = "downloads", to_mp3: bool = False) -> str:
    """Download the audio track of a YouTube video.

    Without ffmpeg, saves YouTube's native audio stream (m4a/webm/opus).
    With ffmpeg and to_mp3=True, converts to MP3.

    Returns the path to the downloaded file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        # Best available audio-only stream, prefer m4a (widely playable)
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(out_path / "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": True,
    }

    if to_mp3:
        if not shutil.which("ffmpeg"):
            sys.exit("--mp3 requires ffmpeg on PATH. Re-run without --mp3 "
                     "to save the native audio format instead.")
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp may give a playlist-like dict; handle both cases
        entries = info.get("entries") if "entries" in info else [info]
        entry = entries[0]
        requested = entry.get("requested_downloads") or entry.get("filepath")
        if requested and isinstance(requested, list):
            return requested[0]["filepath"]
        return ydl.prepare_filename(entry)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download audio from a YouTube video")
    parser.add_argument("url", help="YouTube video URL, e.g. https://www.youtube.com/watch?v=SgMbPe9v2E4")
    parser.add_argument("-o", "--output", default="downloads", help="Output directory (default: ./downloads)")
    parser.add_argument("--mp3", action="store_true", help="Convert to MP3 (requires ffmpeg)")
    args = parser.parse_args()

    path = download_audio(args.url, args.output, to_mp3=args.mp3)
    print(f"\n✅ Saved to: {path}")


if __name__ == "__main__":
    main()