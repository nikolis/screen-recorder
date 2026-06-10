# Screen Recorder

A lightweight Python screen recorder that captures your display and saves it as an MP4 video. Uses `ffmpeg` with `x11grab` under the hood — works on both X11 and Wayland (via XWayland).

Originally created for recording a demo video to submit as part of the Instagram API access application.

## Requirements

- Python 3.8+
- Linux (tested on Ubuntu 22.04 / 24.04)
- `ffmpeg` and `xdpyinfo` installed:

```bash
sudo apt install ffmpeg x11-utils
```

## Usage

```bash
# Record full screen, auto-named output (recording_YYYYMMDD_HHMMSS.mp4)
python3 screen_recorder.py

# Custom output filename
python3 screen_recorder.py -o my_demo.mp4

# Custom frame rate (default is 30fps)
python3 screen_recorder.py --fps 60 -o demo.mp4

# Record a specific region: x,y,width,height
python3 screen_recorder.py --region 0,0,1280,720 -o cropped.mp4

# Specify a display (useful with multiple monitors)
python3 screen_recorder.py --display :0
```

Press **Ctrl+C** to stop recording. The file is finalized and saved cleanly on exit.

## Options

| Flag | Default | Description |
|---|---|---|
| `-o`, `--output` | `recording_TIMESTAMP.mp4` | Output file path |
| `--fps` | `30` | Frames per second |
| `--display` | `$DISPLAY` or `:0` | X display to capture |
| `--region` | full screen | Region as `x,y,width,height` |

## Output

- Format: MP4 (H.264 via libx264)
- Resolution: matches your screen's native resolution (or the specified region)
- Compatible with Instagram, YouTube, and most video platforms

## Instagram API Access

When applying for access to the Instagram Graph API, Meta requires a screen-recorded video demonstrating your app's intended use of the API. Steps:

1. Prepare your app flow in the browser
2. Start recording: `python3 screen_recorder.py -o instagram_demo.mp4`
3. Walk through your app demonstrating each permission you're requesting
4. Press Ctrl+C to stop
5. Upload `instagram_demo.mp4` in the Meta app review submission form

## How It Works

- Uses `ffmpeg` with the `x11grab` input device to capture the X display directly
- Encodes with `libx264` at `ultrafast` preset for low CPU overhead during recording
- Sends `q` to ffmpeg stdin on Ctrl+C for a clean, finalized MP4 (no corrupt file on exit)
- `xdpyinfo` is used to auto-detect screen resolution when no region is specified

## Troubleshooting

**Black screen / blank video** — this happens if you try to use `mss` or `pyautogui` on Wayland. This recorder uses `ffmpeg x11grab` which works via XWayland on Wayland desktops.

**`xdpyinfo` not found** — install with `sudo apt install x11-utils`. The recorder still works without it but won't auto-detect resolution.

**Wrong monitor captured** — use `--region` to specify exact pixel coordinates, or `--display :0.1` for a second screen.
