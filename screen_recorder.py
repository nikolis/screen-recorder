#!/usr/bin/env python3
"""
Screen recorder — saves to MP4 using ffmpeg x11grab.
Works on both X11 and Wayland (via XWayland).

Usage:
    python3 screen_recorder.py                  # records full screen
    python3 screen_recorder.py --fps 30         # custom frame rate
    python3 screen_recorder.py -o my_video.mp4  # custom output file
    python3 screen_recorder.py --region 0,0,1280,720  # record a region (x,y,w,h)

Press Ctrl+C to stop recording.
"""

import argparse
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Screen recorder → MP4")
    parser.add_argument("-o", "--output", default=None, help="Output file (default: recording_TIMESTAMP.mp4)")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    parser.add_argument("--display", default=None, help="X display to capture (default: $DISPLAY or :0)")
    parser.add_argument("--region", default=None, help="Region to capture as x,y,width,height (default: full screen)")
    return parser.parse_args()


def get_screen_size(display):
    try:
        out = subprocess.check_output(
            ["xdpyinfo", "-display", display], stderr=subprocess.DEVNULL
        ).decode()
        for line in out.splitlines():
            if "dimensions:" in line:
                dims = line.split()[1]
                w, h = dims.split("x")
                return int(w), int(h)
    except Exception:
        pass
    return None, None


def main():
    args = parse_args()

    output = args.output or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output = str(Path(output).expanduser().resolve())

    display = args.display or os.environ.get("DISPLAY", ":0")

    if args.region:
        x, y, w, h = [int(v) for v in args.region.split(",")]
        grab_input = f"{display}+{x},{y}"
        size_arg = ["-video_size", f"{w}x{h}"]
        region_desc = f"{w}x{h} at ({x},{y})"
    else:
        w, h = get_screen_size(display)
        if w and h:
            size_arg = ["-video_size", f"{w}x{h}"]
            region_desc = f"{w}x{h} (full screen)"
        else:
            size_arg = []
            region_desc = "full screen"
        grab_input = display

    cmd = [
        "ffmpeg",
        "-f", "x11grab",
        "-framerate", str(args.fps),
        *size_arg,
        "-i", grab_input,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-y",
        output,
    ]

    print(f"Recording {region_desc} @ {args.fps}fps  →  {output}")
    print("Press Ctrl+C to stop.\n")

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def stop(sig, frame):
        print("\nStopping...")
        proc.communicate(input=b"q")
        print(f"Saved  →  {output}")
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    proc.wait()


if __name__ == "__main__":
    main()
