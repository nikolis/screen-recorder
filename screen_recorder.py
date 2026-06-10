#!/usr/bin/env python3
"""
Screen recorder for GNOME Wayland.
Uses xdg-desktop-portal + PipeWire + GStreamer with a real GTK4 window
as parent (required to avoid portal SEGV on Wayland).

Usage:
    python3 screen_recorder.py                  # auto-named output
    python3 screen_recorder.py -o my_video.mp4  # custom output file
    python3 screen_recorder.py --fps 30

A small control window appears. Click "Start Recording", then click
"Stop Recording" when done. The portal "Share your screen" dialog will
appear after clicking Start.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import dbus
import dbus.mainloop.glib
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GdkWayland", "4.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gdk, GdkWayland, GLib, Gst, Gtk

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)


def parse_args():
    parser = argparse.ArgumentParser(description="Screen recorder → MP4 (GNOME Wayland)")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--fps", type=int, default=30)
    return parser.parse_args()


class Recorder:
    PORTAL_BUS = "org.freedesktop.portal.Desktop"
    PORTAL_PATH = "/org/freedesktop/portal/desktop"
    SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
    REQUEST_IFACE = "org.freedesktop.portal.Request"

    def __init__(self, output, fps):
        self.output = output
        self.fps = fps
        self.pipeline = None
        self.session_path = None
        self.bus = dbus.SessionBus()
        self.portal = self.bus.get_object(self.PORTAL_BUS, self.PORTAL_PATH)
        self.sc = dbus.Interface(self.portal, self.SCREENCAST_IFACE)
        self._sender = self.bus.get_unique_name().lstrip(":").replace(".", "_")

    def _make_handle(self, token):
        return f"/org/freedesktop/portal/desktop/request/{self._sender}/{token}"

    def _subscribe(self, token, cb):
        handle = self._make_handle(token)
        return self.bus.add_signal_receiver(
            cb, signal_name="Response",
            dbus_interface=self.REQUEST_IFACE, path=handle,
        )

    def start(self, parent_handle, on_recording, on_error):
        self._on_recording = on_recording
        self._on_error = on_error
        t = f"t{int(time.time())}"

        def on_create(response, results):
            if response != 0:
                on_error("CreateSession failed")
                return
            self.session_path = str(results["session_handle"])
            t2 = f"t{int(time.time())}b"
            def on_select(response, results):
                if response != 0:
                    on_error("Source selection cancelled")
                    return
                t3 = f"t{int(time.time())}c"
                def on_start(response, results):
                    if response != 0:
                        on_error("Start cancelled")
                        return
                    streams = results.get("streams", [])
                    if not streams:
                        on_error("No streams")
                        return
                    node_id = int(streams[0][0])
                    fd = int(self.sc.OpenPipeWireRemote(
                        self.session_path, {},
                        dbus_interface=self.SCREENCAST_IFACE,
                    ).take())
                    self._start_pipeline(fd, node_id)
                self._subscribe(t3, on_start)
                self.sc.Start(self.session_path, parent_handle, {"handle_token": t3})
            self._subscribe(t2, on_select)
            self.sc.SelectSources(self.session_path, {
                "handle_token": t2,
                "types": dbus.UInt32(1),
                "multiple": False,
                "cursor_mode": dbus.UInt32(2),
            })

        self._subscribe(t, on_create)
        self.sc.CreateSession({"handle_token": t, "session_handle_token": t})

    def _start_pipeline(self, fd, node_id):
        pipeline_str = (
            f"pipewiresrc fd={fd} path={node_id} do-timestamp=true "
            f"! video/x-raw,max-framerate={self.fps}/1 "
            f"! videoconvert "
            f"! x264enc tune=zerolatency speed-preset=ultrafast "
            f"! mp4mux "
            f"! filesink location={self.output}"
        )
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.pipeline.set_state(Gst.State.PLAYING)
        self._on_recording()

    def stop(self):
        if self.pipeline:
            self.pipeline.send_event(Gst.Event.new_eos())
            GLib.timeout_add(800, self._teardown)

    def _teardown(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
        return False


class App(Gtk.Application):
    def __init__(self, output, fps):
        super().__init__(application_id="io.nikolis.ScreenRecorder")
        self.output = output
        self.fps = fps
        self.recorder = None
        self.window = None

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(application=self, title="Screen Recorder")
        self.window.set_default_size(300, 120)
        self.window.set_resizable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        self.label = Gtk.Label(label=f"Output: {Path(self.output).name}")
        box.append(self.label)

        self.btn = Gtk.Button(label="Start Recording")
        self.btn.connect("clicked", self._on_btn_clicked)
        box.append(self.btn)

        self.window.set_child(box)
        self.window.present()

    def _get_parent_handle(self):
        surface = self.window.get_surface()
        if isinstance(surface, GdkWayland.WaylandSurface):
            handle_holder = []
            done = []

            def got_handle(surface, handle, user_data):
                handle_holder.append(handle or "")
                done.append(True)

            GdkWayland.WaylandToplevel.export_handle(surface, got_handle, None)
            deadline = time.time() + 2.0
            while not done and time.time() < deadline:
                GLib.main_context_default().iteration(False)
            return f"wayland:{handle_holder[0]}" if handle_holder else ""
        return ""

    def _on_btn_clicked(self, btn):
        if self.recorder is None:
            self.btn.set_sensitive(False)
            self.label.set_text("Waiting for screen share dialog...")
            self.recorder = Recorder(self.output, self.fps)
            parent_handle = self._get_parent_handle()
            self.recorder.start(
                parent_handle,
                on_recording=self._on_recording_started,
                on_error=self._on_error,
            )
        else:
            self.btn.set_sensitive(False)
            self.label.set_text("Saving...")
            self.recorder.stop()
            GLib.timeout_add(1000, self._finish)

    def _on_recording_started(self):
        self.label.set_text("Recording...")
        self.btn.set_label("Stop Recording")
        self.btn.set_sensitive(True)

    def _on_error(self, msg):
        self.label.set_text(f"Error: {msg}")
        self.btn.set_label("Start Recording")
        self.btn.set_sensitive(True)
        self.recorder = None

    def _finish(self):
        print(f"Saved → {self.output}")
        self.quit()
        return False


def main():
    args = parse_args()
    output = args.output or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output = str(Path(output).expanduser().resolve())

    app = App(output, args.fps)
    app.run(sys.argv[:1])


if __name__ == "__main__":
    main()
