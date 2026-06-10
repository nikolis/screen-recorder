#!/usr/bin/env python3
"""
Screen recorder — saves to MP4.
Usage:
    python3 screen_recorder.py                  # records full screen
    python3 screen_recorder.py --fps 30         # custom frame rate
    python3 screen_recorder.py -o my_video.mp4  # custom output file

Press Ctrl+C to stop recording.
"""

import argparse
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import mss
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Screen recorder → MP4")
    parser.add_argument("-o", "--output", default=None, help="Output file (default: recording_TIMESTAMP.mp4)")
    parser.add_argument("--fps", type=int, default=20, help="Frames per second (default: 20)")
    parser.add_argument("--monitor", type=int, default=1, help="Monitor index (default: 1 = primary)")
    return parser.parse_args()


def main():
    args = parse_args()

    output = args.output or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output = str(Path(output).expanduser().resolve())

    with mss.MSS() as sct:
        monitor = sct.monitors[args.monitor]
        width = monitor["width"]
        height = monitor["height"]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output, fourcc, args.fps, (width, height))

        print(f"Recording {width}x{height} @ {args.fps}fps  →  {output}")
        print("Press Ctrl+C to stop.\n")

        frame_duration = 1.0 / args.fps
        frame_count = 0
        start = time.time()

        def stop(sig, frame):
            elapsed = time.time() - start
            print(f"\nStopped. {frame_count} frames, {elapsed:.1f}s  →  {output}")
            writer.release()
            sys.exit(0)

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        while True:
            t0 = time.time()
            img = np.array(sct.grab(monitor))
            # mss gives BGRA — drop alpha, keep BGR for OpenCV
            frame = img[:, :, :3]
            writer.write(frame)
            frame_count += 1

            elapsed = time.time() - t0
            sleep = frame_duration - elapsed
            if sleep > 0:
                time.sleep(sleep)


if __name__ == "__main__":
    main()
