# Screen Recorder

A lightweight Python screen recorder that captures your display and saves it as an MP4 video. Originally created for recording a demo video to submit as part of the Instagram API access application.

## Requirements

- Python 3.8+
- Linux (tested on Ubuntu 22.04 / 24.04)

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd screen-recorder

# Install dependencies
pip install -r requirements.txt
```

Or install dependencies directly:

```bash
pip install mss opencv-python numpy
```

## Usage

```bash
# Record full screen, auto-named output (recording_YYYYMMDD_HHMMSS.mp4)
python3 screen_recorder.py

# Custom output filename
python3 screen_recorder.py -o my_demo.mp4

# Custom frame rate (default is 20fps)
python3 screen_recorder.py --fps 30 -o demo.mp4

# Record a specific monitor (1 = primary, 2 = secondary, etc.)
python3 screen_recorder.py --monitor 2 -o secondary.mp4
```

Press **Ctrl+C** to stop recording. The output file is written to disk immediately.

## Options

| Flag | Default | Description |
|---|---|---|
| `-o`, `--output` | `recording_TIMESTAMP.mp4` | Output file path |
| `--fps` | `20` | Frames per second |
| `--monitor` | `1` | Monitor index to capture |

## Output

- Format: MP4 (MPEG-4 codec via OpenCV)
- Resolution: matches the selected monitor's native resolution
- Compatible with Instagram, YouTube, and most video platforms

## Instagram API Access

When applying for access to the Instagram Graph API, Meta requires a screen-recorded video demonstrating your app's intended use of the API. Steps:

1. Prepare your app flow in the browser
2. Run the recorder: `python3 screen_recorder.py -o instagram_demo.mp4`
3. Walk through your app demonstrating each permission you're requesting
4. Press Ctrl+C to stop
5. Upload `instagram_demo.mp4` in the Meta app review submission form

## How It Works

- Uses [`mss`](https://python-mss.readthedocs.io/) for fast cross-platform screen capture
- Uses [`opencv-python`](https://opencv.org/) (`cv2.VideoWriter`) to encode frames into MP4
- Captures BGRA frames from `mss`, strips the alpha channel, and writes BGR frames at the target FPS
- A signal handler on `SIGINT`/`SIGTERM` cleanly finalizes and closes the video file on Ctrl+C
