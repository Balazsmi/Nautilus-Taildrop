#!/usr/bin/env python3
import sys
import os
import subprocess
import threading
import json
import gi
import math

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Adw, GLib, Gio, Pango


DEVICE_ICONS = {
    "windows": "computer-symbolic",
    "linux":   "computer-symbolic",
    "android": "phone-symbolic",
    "ios":     "phone-symbolic",
    "darwin":  "laptop-symbolic",
    "macos":   "laptop-symbolic",
}


class DeviceButton(Gtk.Box):
    def __init__(self, name, os_name, callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_size_request(96, 120)
        self.name = name
        self._anim_id = None
        self._angle = 0.0
        self._loading = False

        # Overlay: ring drawn around the button
        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)
        overlay.set_size_request(84, 84)

        self.btn = Gtk.Button()
        self.btn.add_css_class("circular")
        self.btn.add_css_class("device-btn")
        self.btn.set_size_request(76, 76)
        self.btn.set_halign(Gtk.Align.CENTER)
        self.btn.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name(DEVICE_ICONS.get(os_name, "computer-symbolic"))
        icon.set_pixel_size(32)
        self.btn.set_child(icon)
        self.btn.connect("clicked", lambda _: callback(name))
        overlay.set_child(self.btn)

        # DrawingArea for the spinning arc ring — pointer-transparent
        self.da = Gtk.DrawingArea()
        self.da.set_size_request(84, 84)
        self.da.set_halign(Gtk.Align.CENTER)
        self.da.set_valign(Gtk.Align.CENTER)
        self.da.set_can_target(False)
        self.da.set_draw_func(self.on_draw)
        overlay.add_overlay(self.da)

        self.append(overlay)

        label = Gtk.Label(label=name)
        label.set_max_width_chars(10)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.add_css_class("caption")
        self.append(label)

    def on_draw(self, area, cr, width, height):
        if not self._loading:
            return
        import math
        xc, yc, r = width / 2, height / 2, 40.0
        arc = math.pi * 0.75  # arc length ~270°

        # Get accent color from theme
        style = self.btn.get_style_context()
        found, accent = style.lookup_color("accent_color")
        if not found:
            found, accent = style.lookup_color("theme_selected_bg_color")
        if not found:
            from gi.repository import Gdk
            accent = Gdk.RGBA()
            accent.red, accent.green, accent.blue, accent.alpha = 0.21, 0.52, 0.89, 1.0

        cr.set_line_width(3.0)
        cr.set_line_cap(1)  # ROUND

        # Faint full ring
        cr.set_source_rgba(accent.red, accent.green, accent.blue, 0.18)
        cr.arc(xc, yc, r, 0, 2 * math.pi)
        cr.stroke()

        # Spinning arc
        cr.set_source_rgba(accent.red, accent.green, accent.blue, 1.0)
        start = self._angle
        cr.arc(xc, yc, r, start, start + arc)
        cr.stroke()

    def start_loading(self):
        self._loading = True
        self._angle = 0.0

        def tick():
            if not self._loading:
                return False
            import math
            self._angle = (self._angle + 0.08) % (2 * math.pi)
            self.da.queue_draw()
            return True

        self._anim_id = GLib.timeout_add(16, tick)  # ~60fps

    def stop_loading(self):
        self._loading = False
        if self._anim_id is not None:
            GLib.source_remove(self._anim_id)
            self._anim_id = None
        self.da.queue_draw()


class TaildropSenderWindow(Adw.ApplicationWindow):
    def __init__(self, app, files):
        super().__init__(application=app, title="Taildrop")
        self.files = files
        self.set_resizable(False)

        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .title-label {
                font-size: 15pt;
                font-weight: bold;
                color: @window_fg_color;
            }
            .subtitle-label {
                font-size: 10pt;
            }
            .device-btn {
                min-width: 76px;
                min-height: 76px;
            }
            .device-btn image {
                color: @accent_color;
            }
            .device-btn image {
                color: @accent_color;
            }
            .caption {
                font-weight: 500;
                font-size: 10pt;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        # HeaderBar
        header = Adw.HeaderBar()
        

        # Profile row — avatar + text on same line
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_start(16)
        header_box.set_margin_end(16)
        header_box.set_margin_top(16)
        header_box.set_margin_bottom(16)
        header_box.set_valign(Gtk.Align.CENTER)

        avatar = Adw.Avatar(size=40, text="me", show_initials=False)
        avatar.set_icon_name("computer-symbolic")
        avatar.set_valign(Gtk.Align.CENTER)
        avatar.set_margin_start(0)
        avatar.set_margin_top(0)
        avatar.set_margin_bottom(0)
        header_box.append(avatar)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_box.set_valign(Gtk.Align.CENTER)
        text_box.set_hexpand(True)
        title_label = Gtk.Label(label="Taildrop")
        title_label.add_css_class("title-label")
        title_label.set_xalign(0)
        self.subtitle_label = Gtk.Label(label="As …")
        self.subtitle_label.add_css_class("subtitle-label")
        self.subtitle_label.add_css_class("dim-label")
        self.subtitle_label.set_xalign(0)
        text_box.append(title_label)
        text_box.append(self.subtitle_label)
        header_box.append(text_box)

        root.append(header_box)
        root.append(Gtk.Separator())

        # Device grid
        self.flow = Gtk.FlowBox()
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_halign(Gtk.Align.START)
        self.flow.set_max_children_per_line(4)
        self.flow.set_min_children_per_line(2)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_row_spacing(8)
        self.flow.set_column_spacing(8)
        self.flow.set_margin_top(16)
        self.flow.set_margin_bottom(16)
        self.flow.set_margin_start(16)
        self.flow.set_margin_end(16)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(False)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scrolled.set_propagate_natural_height(True)
        scrolled.set_child(self.flow)
        root.append(scrolled)

        root.append(Gtk.Separator())

        # Bottom bar — use the same outer margins as the main flow so corners align
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_start(16)
        bottom_bar.set_margin_end(16)
        bottom_bar.set_margin_top(16)
        bottom_bar.set_margin_bottom(16)

        self.status_label = Gtk.Label(label="Searching for devices…")
        self.status_label.add_css_class("caption")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_hexpand(True)
        self.status_label.set_xalign(0)
        bottom_bar.append(self.status_label)

        self.btn_cancel = Gtk.Button(label="Cancel")
        self.btn_cancel.connect("clicked", lambda _: self.get_application().quit())
        # Remove any extra outer margin on the button so its corner aligns with the window
        self.btn_cancel.set_margin_top(0)
        self.btn_cancel.set_margin_end(0)
        self.btn_cancel.set_margin_bottom(0)
        self.btn_cancel.set_valign(Gtk.Align.CENTER)
        bottom_bar.append(self.btn_cancel)

        root.append(bottom_bar)

        self.refresh_timeout_id = None
        self._last_peers = []
        self.device_buttons = {}

        self.connect("destroy", self.on_destroy)
        self.load_devices()
        self.start_auto_refresh()

    def on_destroy(self, _):
        self.stop_auto_refresh()

    def start_auto_refresh(self):
        if self.refresh_timeout_id is None:
            self.refresh_timeout_id = GLib.timeout_add_seconds(5, self.auto_refresh)

    def stop_auto_refresh(self):
        if self.refresh_timeout_id is not None:
            GLib.source_remove(self.refresh_timeout_id)
            self.refresh_timeout_id = None

    def auto_refresh(self):
        if self.flow.get_sensitive():
            self.load_devices_silent()
        return True

    def load_devices(self):
        self.status_label.set_label("Searching for devices…")
        self.load_devices_silent()

    def load_devices_silent(self):
        threading.Thread(target=self.query_devices_async, daemon=True).start()

    def query_devices_async(self):
        try:
            res = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=5,
            )
            data = json.loads(res.stdout)
            self_name = data.get("Self", {}).get("HostName", "").lower()
            peers = []
            for peer in data.get("Peer", {}).values():
                if not peer.get("Online", False):
                    continue
                raw = peer.get("HostName", peer.get("DNSName", "Unknown"))
                name = raw.split(".")[0]
                if name.lower() in (self_name, "localhost", "", "127"):
                    continue
                # Also skip if this peer's IPs include the machine's own addresses
                peer_ips = peer.get("TailscaleIPs", [])
                self_ips = set(data.get("Self", {}).get("TailscaleIPs", []))
                if self_ips & set(peer_ips):
                    continue
                os_name = peer.get("OS", "").lower()
                peers.append((name, os_name))
            GLib.idle_add(self.update_ui_with_peers, peers, self_name)
        except Exception:
            pass

    def update_ui_with_peers(self, peers, self_name):
        if self_name:
            self.subtitle_label.set_label(f"As {self_name}")

        if peers == self._last_peers:
            return
        self._last_peers = peers

        while self.flow.get_child_at_index(0):
            self.flow.remove(self.flow.get_child_at_index(0))

        self.device_buttons = {}

        if not peers:
            self.status_label.set_label("No online devices found.")
            return

        for name, os_name in peers:
            btn = DeviceButton(name, os_name, self.on_device_selected)
            self.flow.append(btn)
            self.device_buttons[name] = btn

        n = len(peers)
        self.status_label.set_label(f"{n} device{'s' if n != 1 else ''} available")

        # Do not force a window size here — allow the toolkit to size naturally
        # The previous behavior computed a large `height` and called
        # `set_size_request`/`set_default_size`, which caused the visible
        # bottom padding to increase. Keeping sizing automatic keeps margins stable.

    def on_device_selected(self, device_name):
        self.stop_auto_refresh()
        self.flow.set_sensitive(False)
        self.btn_cancel.set_sensitive(False)

        self.status_label.set_label(f"Sending to {device_name}…")
        if device_name in self.device_buttons:
            self.device_buttons[device_name].start_loading()
        threading.Thread(target=self.send_operation, args=(device_name,), daemon=True).start()

    def send_operation(self, device):
        success = all(
            subprocess.run(["tailscale", "file", "cp", f, f"{device}:"]).returncode == 0
            for f in self.files
        )
        GLib.idle_add(self.on_finished, device, success)

    def on_finished(self, device, success):

        if device in self.device_buttons:
            self.device_buttons[device].stop_loading()
        filenames = [os.path.basename(f) for f in self.files]
        summary = filenames[0] if len(filenames) == 1 else f"{len(filenames)} files"
        if success:
            subprocess.Popen(["notify-send", "-a", "Taildrop",
                              "Sent successfully", f"{summary} → {device}"])
        else:
            subprocess.Popen(["notify-send", "-a", "Taildrop",
                              "Send failed", f"Could not send {summary} to {device}."])
        self.get_application().quit()


def main():
    app = Adw.Application(application_id="org.balazs.TaildropSender")
    app.set_flags(app.get_flags() | Gio.ApplicationFlags.HANDLES_OPEN)

    def on_activate(a):
        TaildropSenderWindow(a, sys.argv[1:]).present()

    def on_open(a, files, n_files, hint):
        paths = [f.get_path() for f in files if f.get_path()]
        TaildropSenderWindow(a, paths).present()

    app.connect("activate", on_activate)
    app.connect("open", on_open)
    app.run([])


if __name__ == "__main__":
    main()