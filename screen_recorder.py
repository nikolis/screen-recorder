#!/usr/bin/env python3
"""
Screen recorder for GNOME Wayland — uses xdg-desktop-portal + PipeWire + GStreamer.

Usage:
    python3 screen_recorder.py                  # records screen, auto-named output
    python3 screen_recorder.py -o my_video.mp4  # custom output file
    python3 screen_recorder.py --fps 30         # custom frame rate

A GNOME "Share your screen" dialog will appear — click Share to start recording.
Press Ctrl+C to stop.
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)


def parse_args():
    parser = argparse.ArgumentParser(description="Screen recorder → MP4 (GNOME Wayland)")
    parser.add_argument("-o", "--output", default=None, help="Output file (default: recording_TIMESTAMP.mp4)")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    return parser.parse_args()


class ScreenCastPortal:
    PORTAL_BUS = "org.freedesktop.portal.Desktop"
    PORTAL_PATH = "/org/freedesktop/portal/desktop"
    SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
    REQUEST_IFACE = "org.freedesktop.portal.Request"

    def __init__(self):
        self.bus = dbus.SessionBus()
        self.portal = self.bus.get_object(self.PORTAL_BUS, self.PORTAL_PATH)
        self.screencast = dbus.Interface(self.portal, self.SCREENCAST_IFACE)
        self.session_path = None
        self.node_id = None
        self.fd = None
        self._loop = GLib.MainLoop()
        self._sender = self.bus.get_unique_name().lstrip(":").replace(".", "_")

    def _make_handle(self, token):
        return f"/org/freedesktop/portal/desktop/request/{self._sender}/{token}"

    def _subscribe(self, handle, callback):
        return self.bus.add_signal_receiver(
            callback,
            signal_name="Response",
            dbus_interface=self.REQUEST_IFACE,
            path=handle,
        )

    def open(self):
        token = f"recorder_{int(time.time())}"
        handle = self._make_handle(token)

        result = {}

        def on_create_session(response, results):
            if response != 0:
                print(f"CreateSession failed (response={response})")
                self._loop.quit()
                return
            self.session_path = str(results["session_handle"])
            self._select_sources()

        sub = self._subscribe(handle, on_create_session)
        self.screencast.CreateSession(
            {"session_handle_token": token, "handle_token": token},
            dbus_interface=self.SCREENCAST_IFACE,
        )
        self._loop.run()
        sub.remove()

    def _select_sources(self):
        token = f"src_{int(time.time())}"
        handle = self._make_handle(token)

        def on_select(response, results):
            if response != 0:
                print("SelectSources cancelled.")
                self._loop.quit()
                sys.exit(1)
            self._start()

        sub = self._subscribe(handle, on_select)
        session = self.bus.get_object(self.PORTAL_BUS, self.session_path)
        self.screencast.SelectSources(
            self.session_path,
            {
                "handle_token": token,
                # 1=monitor, 2=window, 3=both
                "types": dbus.UInt32(1),
                "multiple": False,
                "cursor_mode": dbus.UInt32(2),  # embedded cursor
            },
            dbus_interface=self.SCREENCAST_IFACE,
        )
        self._loop.run()
        sub.remove()

    def _start(self):
        token = f"start_{int(time.time())}"
        handle = self._make_handle(token)

        def on_start(response, results):
            if response != 0:
                print("Start cancelled.")
                self._loop.quit()
                sys.exit(1)
            streams = results.get("streams", [])
            if not streams:
                print("No streams returned.")
                self._loop.quit()
                sys.exit(1)
            self.node_id = int(streams[0][0])
            self.fd = int(self.screencast.OpenPipeWireRemote(
                self.session_path, {},
                dbus_interface=self.SCREENCAST_IFACE,
            ).take())
            self._loop.quit()

        sub = self._subscribe(handle, on_start)
        self.screencast.Start(
            self.session_path,
            "",
            {"handle_token": token},
            dbus_interface=self.SCREENCAST_IFACE,
        )
        self._loop.run()
        sub.remove()


def build_pipeline(fd, node_id, fps, output):
    pipeline_str = (
        f"pipewiresrc fd={fd} path={node_id} do-timestamp=true "
        f"! video/x-raw,max-framerate={fps}/1 "
        f"! videoconvert "
        f"! x264enc tune=zerolatency speed-preset=ultrafast "
        f"! mp4mux "
        f"! filesink location={output}"
    )
    return Gst.parse_launch(pipeline_str)


def main():
    args = parse_args()

    output = args.output or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output = str(Path(output).expanduser().resolve())

    print("Opening screen share dialog — click 'Share' in the GNOME popup...")
    portal = ScreenCastPortal()
    portal.open()

    print(f"Recording @ {args.fps}fps  →  {output}")
    print("Press Ctrl+C to stop.\n")

    pipeline = build_pipeline(portal.fd, portal.node_id, args.fps, output)
    pipeline.set_state(Gst.State.PLAYING)

    def stop(sig, frame):
        print("\nStopping...")
        pipeline.send_event(Gst.Event.new_eos())
        time.sleep(1)
        pipeline.set_state(Gst.State.NULL)
        print(f"Saved  →  {output}")
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()

    def on_message(bus, msg):
        if msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            print(f"Pipeline error: {err} — {debug}")
            loop.quit()
        elif msg.type == Gst.MessageType.EOS:
            loop.quit()

    bus.connect("message", on_message)
    loop.run()

    pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
