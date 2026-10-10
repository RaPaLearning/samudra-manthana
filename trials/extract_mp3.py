#!/usr/bin/env python3
"""
Extract MP3 audio from an MP4 video file.

Requirements:
    - ffmpeg must be installed and available on your PATH.
      (Windows: https://ffmpeg.org/download.html
       macOS:   brew install ffmpeg
       Linux:   sudo apt install ffmpeg)

Usage:
    python extract_mp3.py input.mp4
    python extract_mp3.py input.mp4 -o output.mp3
    python extract_mp3.py input.mp4 -b 320k     # custom bitrate
"""

import argparse
import os
import shutil
import subprocess
import sys


def check_ffmpeg() -> None:
    """Ensure ffmpeg is available on the system."""
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "Error: ffmpeg not found on PATH.\n"
            "Install it first (e.g. 'winget install Gyan.FFmpeg', "
            "'brew install ffmpeg', or 'sudo apt install ffmpeg')."
        )


def extract_mp3(video_path: str, output_path: str, bitrate: str) -> None:
    """Extract the audio track from a video file and save it as MP3."""
    if not os.path.isfile(video_path):
        sys.exit(f"Error: file not found: {video_path}")

    # Default output: same name as video, with .mp3 extension
    if output_path is None:
        output_path = os.path.splitext(video_path)[0] + ".mp3"

    # Overwrite output without asking (-y), convert audio to mp3
    cmd = [
        "ffmpeg",
        "-y",                # overwrite output if it exists
        "-i", video_path,    # input file
        "-vn",               # disable video
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,     # audio bitrate
        output_path,
    ]

    print(f"Extracting audio from: {video_path}")
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except KeyboardInterrupt:
        sys.exit("\nCancelled by user.")

    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{result.stderr[-2000:]}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done: {output_path} ({size_mb:.2f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract MP3 audio from an MP4 video file."
    )
    parser.add_argument("video", help="path to the input video file (e.g. clip.mp4)")
    parser.add_argument("-o", "--output", help="output MP3 file path (optional)")
    parser.add_argument(
        "-b", "--bitrate", default="192k",
        help="audio bitrate (default: 192k, e.g. 128k, 256k, 320k)",
    )
    args = parser.parse_args()

    check_ffmpeg()
    extract_mp3(args.video, args.output, args.bitrate)


if __name__ == "__main__":
    main()
