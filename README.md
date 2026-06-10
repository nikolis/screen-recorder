# Screen Recorder

A Python screen recorder for **GNOME Wayland** that saves to MP4. Uses `xdg-desktop-portal` + PipeWire + GStreamer via a GTK4 control window.

Originally created for recording a demo video to submit as part of the Instagram API access application.

## Requirements

- Python 3.8+
- GNOME on Wayland (Ubuntu 22.04 / 24.04)
- System packages:

```bash
sudo apt install python3-dbus python3-gi \
    gstreamer1.0-pipewire \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-plugins-bad \
    gir1.2-gtk-4.0
```

## Usage

```bash
# Record screen, auto-named output (recording_YYYYMMDD_HHMMSS.mp4)
python3 screen_recorder.py

# Custom output filename
python3 screen_recorder.py -o instagram_demo.mp4

# Custom frame rate (default is 30fps)
python3 screen_recorder.py --fps 60 -o demo.mp4
```

A small **control window** will appear with a **Start Recording** button.

1. Click **Start Recording** — a GNOME "Share your screen" dialog appears
2. Click **Share** in that dialog — recording begins immediately
3. Click **Stop Recording** when done — the file is saved and the app exits

## Options

| Flag | Default | Description |
|---|---|---|
| `-o`, `--output` | `recording_TIMESTAMP.mp4` | Output file path |
| `--fps` | `30` | Max frames per second |

## Output

- Format: MP4 (H.264 via x264enc)
- Resolution: native monitor resolution (set by PipeWire)
- Compatible with Instagram, YouTube, and most video platforms

## Instagram API Access

When applying for access to the Instagram Graph API, Meta requires a screen-recorded video demonstrating your app's intended use. Steps:

1. Prepare your app flow in the browser
2. Run: `python3 screen_recorder.py -o instagram_demo.mp4`
3. Click **Start Recording** in the control window
4. Click **Share** in the GNOME dialog
5. Walk through your app demonstrating each permission you're requesting
6. Click **Stop Recording** — file is saved automatically
7. Upload `instagram_demo.mp4` in the Meta app review submission form

## How It Works

- Launches a GTK4 window which provides a valid Wayland surface handle (required by the portal)
- Opens `org.freedesktop.portal.ScreenCast` D-Bus portal, which shows GNOME's native screen share consent dialog
- After the user clicks Share, retrieves a PipeWire node ID and file descriptor for the stream
- Captures frames via `pipewiresrc` in a GStreamer pipeline
- Encodes with `x264enc` and muxes to MP4 via `mp4mux`
- On Stop, sends an EOS event to flush and finalize the file cleanly

## Why a GTK4 window?

The `xdg-desktop-portal-gnome` requires a parent window handle when called from a Wayland session. Calling the portal without one causes it to crash (SEGV). The GTK4 window exports its Wayland surface handle and passes it to the portal, satisfying this requirement.

## Why not x11grab / mss?

Both `ffmpeg -f x11grab` and Python `mss` capture the XWayland virtual display (`:0`), which is isolated from the real Wayland compositor — resulting in a black screen on GNOME Wayland. The PipeWire portal is the correct capture path.
