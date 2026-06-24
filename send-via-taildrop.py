#!/usr/bin/env python3
import sys
import os
import subprocess
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


class TaildropSenderWindow(Adw.ApplicationWindow):
    def __init__(self, app, files):
        super().__init__(application=app, title="Send via Taildrop")
        self.files = files
        self.set_default_size(360, 420)

        # UI Setup
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)

        header = Adw.HeaderBar()
        box.append(header)

        # Spinner & Refresh Button
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        header.pack_end(self.spinner)

        self.btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.btn_refresh.connect("clicked", self.on_refresh_clicked)
        header.pack_start(self.btn_refresh)

        # Device List Box
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.list_box)
        box.append(scrolled)

        self.load_devices()

    def load_devices(self):
        # Clear existing entries
        while True:
            row = self.list_box.get_first_child()
            if not row:
                break
            self.list_box.remove(row)

        # Query tailscale status
        try:
            res = subprocess.run(
                ["tailscale", "status", "--peers=true"],
                capture_output=True,
                text=True,
            )
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    row = Gtk.ListBoxRow()
                    btn = Gtk.Button(label=name)
                    btn.connect("clicked", self.on_device_selected, name)
                    row.set_child(btn)
                    self.list_box.append(row)
        except Exception:
            pass

    def on_refresh_clicked(self, btn):
        self.load_devices()

    def on_device_selected(self, btn, device_name):
        self.list_box.set_sensitive(False)
        self.spinner.set_visible(True)
        self.spinner.start()
        thread = threading.Thread(target=self.send_operation, args=(device_name,))
        thread.daemon = True
        thread.start()

    def send_operation(self, device):
        success = True
        for f in self.files:
            res = subprocess.run(["tailscale", "file", "cp", f, f"{device}:"])
            if res.returncode != 0:
                success = False
        GLib.idle_add(self.on_finished, success)

    def on_finished(self, success):
        self.spinner.stop()
        self.close()


def main():
    app = Adw.Application(application_id="org.balazs.TaildropSender")
    app.connect(
        "activate", lambda a: TaildropSenderWindow(a, sys.argv[1:]).present()
    )
    app.run(sys.argv)


if __name__ == "__main__":
    main()
