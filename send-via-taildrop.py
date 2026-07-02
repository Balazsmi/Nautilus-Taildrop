#!/usr/bin/env python3
import contextlib
import json
import math
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import (  # noqa: E402  (gi requires require_version first)
    Adw,
    Gdk,
    Gio,
    GLib,
    Gtk,
    Pango,
)

DEVICE_ICONS = {
    "windows": "computer-symbolic",
    "linux":   "computer-symbolic",
    "android": "phone-symbolic",
    "ios":     "phone-symbolic",
    "darwin":  "laptop-symbolic",
    "macos":   "laptop-symbolic",
}

# Fallback accent color (GNOME blue) used when the theme exposes no accent.
_FALLBACK_ACCENT = (0.21, 0.52, 0.89, 1.0)

# A fully-specified peer entry is (display_name, os_name, online).
_PEER_ENTRY_FIELDS = 3

# Resolve required/optional executables to absolute paths once, up front. Using an
# absolute path (rather than relying on a mutable PATH at call time) avoids
# accidentally invoking a different binary and lets us fail fast with a clear error.
TAILSCALE_BIN = shutil.which("tailscale")
NOTIFY_SEND_BIN = shutil.which("notify-send")


def _notify(title, body):
    """Best-effort desktop notification; silently no-ops if notify-send is absent."""
    if not NOTIFY_SEND_BIN:
        return
    with contextlib.suppress(Exception):
        subprocess.Popen(  # noqa: S603  (fixed argv, no shell, resolved absolute path)
            [NOTIFY_SEND_BIN, "-a", "Taildrop", title, body],
        )


class DeviceButton(Gtk.Box):
    def __init__(self, name, os_name, callback, online=True):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_size_request(96, 120)
        self.name = name
        self._anim_id = None
        self._angle = 0.0
        self._loading = False
        self.online = online

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
        # always connect the click handler; the button is disabled when offline
        self.btn.connect("clicked", lambda _: callback(name))
        self.set_online(online)
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

    def on_draw(self, _area, cr, width, height):
        if not self._loading:
            return
        xc, yc, r = width / 2, height / 2, 40.0
        arc = math.pi * 0.75  # arc length ~270°

        # Get accent color from theme
        style = self.btn.get_style_context()
        found, accent = style.lookup_color("accent_color")
        if not found:
            found, accent = style.lookup_color("theme_selected_bg_color")
        if not found:
            accent = Gdk.RGBA()
            (accent.red, accent.green,
             accent.blue, accent.alpha) = _FALLBACK_ACCENT

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

    def set_online(self, online: bool):
        """Update visual/interactive state for online/offline devices without
        recreating the widget."""
        self.online = bool(online)
        with contextlib.suppress(Exception):
            if self.online:
                self.btn.set_sensitive(True)
                # ensure offline class removed
                with contextlib.suppress(Exception):
                    self.btn.remove_css_class("offline")
            else:
                self.btn.set_sensitive(False)
                with contextlib.suppress(Exception):
                    self.btn.add_css_class("offline")


class TaildropSenderWindow(Adw.ApplicationWindow):
    def __init__(self, app, files):
        super().__init__(application=app, title="Taildrop")
        self.files = files
        # Resizable with a sensible default so the device area scrolls when a
        # tailnet has many peers, rather than growing the window unbounded.
        self.set_default_size(380, 520)

        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .device-btn {
                min-width: 76px;
                min-height: 76px;
            }
            .device-btn image {
                color: @accent_color;
                opacity: 0.92;
            }
            .device-btn.offline {
                opacity: 0.6;
            }
            .device-btn.offline image {
                color: @theme_fg_color;
                opacity: 0.48;
            }
            .caption {
                font-weight: 500;
                font-size: 10pt;
            }
            flowboxchild {
                background: none;
                border-radius: 0;
                padding: 0;
            }
            flowboxchild:hover,
            flowboxchild:focus,
            flowboxchild:selected {
                background: none;
                box-shadow: none;
                outline: none;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Modern Adwaita layout: ToolbarView with a proper HeaderBar (which gives
        # the window its close button + drag area) on top and a status bar below.
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()
        self.window_title = Adw.WindowTitle(title="Taildrop", subtitle="")
        header.set_title_widget(self.window_title)
        toolbar_view.add_top_bar(header)

        # Device grid
        self.flow = Gtk.FlowBox()
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_halign(Gtk.Align.CENTER)
        # Show at most 3 devices per row so additional devices wrap to the next line
        self.flow.set_max_children_per_line(3)
        self.flow.set_min_children_per_line(3)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_row_spacing(8)
        self.flow.set_column_spacing(8)
        self.flow.set_margin_top(16)
        self.flow.set_margin_bottom(16)
        self.flow.set_margin_start(16)
        self.flow.set_margin_end(16)

        # Clamp keeps the grid a comfortable width on wide windows; the scrolled
        # window (vexpand) makes the grid the scrollable region when it overflows.
        clamp = Adw.Clamp(maximum_size=360, tightening_threshold=280)
        clamp.set_child(self.flow)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)

        # Bottom status bar
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.add_css_class("toolbar")
        bottom_bar.set_margin_start(12)
        bottom_bar.set_margin_end(12)
        bottom_bar.set_margin_top(6)
        bottom_bar.set_margin_bottom(6)

        self.status_label = Gtk.Label(label="Searching for devices…")
        self.status_label.add_css_class("caption")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_hexpand(True)
        self.status_label.set_xalign(0)
        bottom_bar.append(self.status_label)
        toolbar_view.add_bottom_bar(bottom_bar)

        self.refresh_timeout_id = None
        self._last_peers = []
        self.device_buttons = {}

        # Escape closes the window (in addition to the header-bar close button).
        esc = Gtk.EventControllerKey()
        esc.connect("key-pressed", self._on_key_pressed)
        self.add_controller(esc)

        self.connect("destroy", self.on_destroy)
        self.load_devices()
        self.start_auto_refresh()

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def on_destroy(self, _):
        self.stop_auto_refresh()

    def start_auto_refresh(self):
        if self.refresh_timeout_id is None:
            self.refresh_timeout_id = GLib.timeout_add_seconds(1, self.auto_refresh)

    def stop_auto_refresh(self):
        if self.refresh_timeout_id is not None:
            GLib.source_remove(self.refresh_timeout_id)
            self.refresh_timeout_id = None

    def auto_refresh(self):
        # Always poll for devices while the window is open (stops when stop_auto_refresh is called)
        self.load_devices_silent()
        return True

    def load_devices(self):
        self.status_label.set_label("Searching for devices…")
        self.load_devices_silent()

    def load_devices_silent(self):
        threading.Thread(target=self.query_devices_async, daemon=True).start()

    def query_devices_async(self):
        try:
            res = subprocess.run(  # noqa: S603  (fixed argv, no shell, resolved absolute path)
                [TAILSCALE_BIN, "status", "--json"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            data = json.loads(res.stdout)
            # Use device display names where available and include offline peers.
            self_name = data.get("Self", {}).get("HostName", "").lower()
            peers = []
            self_ips = set(data.get("Self", {}).get("TailscaleIPs", []))
            for peer in data.get("Peer", {}).values():
                # Prefer explicit display/name fields from Tailscale JSON
                # Prefer explicit Tailscale name/display if present. Many peers
                # only expose HostName and DNSName; prefer the DNS short label
                # (e.g. "ipad-pro" from "ipad-pro.tail4ed4a8.ts.net.") when available
                name_field = peer.get("Name") or peer.get("DisplayName")
                user = peer.get("User") or {}
                user_field = user.get("DisplayName") or user.get("LoginName")
                dns = peer.get("DNSName") or ""
                dns_label = dns.rstrip('.').split('.')[0] if dns else None
                host = peer.get("HostName")
                display = name_field or user_field or dns_label or host or "Unknown"
                # Do not split on dots — show the user-facing device name
                # Skip adding the local device by comparing Tailscale IPs
                peer_ips = peer.get("TailscaleIPs", [])
                if self_ips & set(peer_ips):
                    continue
                os_name = peer.get("OS", "").lower()
                # Use explicit online status only. Some offline peers can still
                # have Tailscale IPs listed, so fallback on IP presence is unsafe.
                online_val = peer.get("Online")
                online = online_val is True or str(online_val).lower() == "true"
                peers.append((display, os_name, online))
            GLib.idle_add(self.update_ui_with_peers, peers, self_name)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            # Don't crash the poll loop, but surface the cause so a broken/missing
            # tailscale CLI is diagnosable instead of silently showing no devices.
            print(f"taildrop: failed to query devices: {exc}", file=sys.stderr)

    def update_ui_with_peers(self, peers, self_name):
        if self_name:
            self.window_title.set_subtitle(self_name)
        # Build mapping of new peers and sort so online devices are preferred in
        # the resulting list. We'll reuse existing DeviceButton widgets where
        # possible to avoid recreating widgets (which causes hover flicker).
        new_map = {}
        for entry in peers:
            if len(entry) == _PEER_ENTRY_FIELDS:
                name, os_name, online = entry
            else:
                name, os_name = entry
                online = True
            new_map[name] = (os_name, bool(online))
        # If there are no peers at all, remove any existing widgets and
        # show a clearer message.
        if not new_map:
            for name in list(self.device_buttons.keys()):
                w = self.device_buttons.pop(name, None)
                if w:
                    with contextlib.suppress(Exception):
                        self.flow.remove(w)
            self.status_label.set_label("No devices found.")
            return

        # Sort names: online first, then alphabetically
        try:
            sorted_names = sorted(
                new_map.items(),
                key=lambda kv: (0 if kv[1][1] else 1, kv[0].lower()),
            )
            sorted_names = [n for n, _ in sorted_names]
        except Exception:
            sorted_names = list(new_map.keys())

        # Add or update widgets for peers in sorted order; do not remove or
        # recreate widgets unnecessarily so hover states remain.
        existing = set(self.device_buttons.keys())
        for name in sorted_names:
            os_name, online = new_map[name]
            if name in self.device_buttons:
                btn = self.device_buttons[name]
                # update online state without recreating
                btn.set_online(online)
            else:
                btn = DeviceButton(name, os_name, self.on_device_selected, online)
                self.flow.append(btn)
                self.device_buttons[name] = btn

        # Remove widgets for peers that no longer exist
        for name in list(existing - set(new_map.keys())):
            w = self.device_buttons.pop(name, None)
            if w:
                with contextlib.suppress(Exception):
                    self.flow.remove(w)

        # Show only the number of online devices in the status label
        online_count = sum(1 for v in new_map.values() if v[1])
        if online_count == 0:
            self.status_label.set_label("No online devices found.")
        else:
            plural = "s" if online_count != 1 else ""
            self.status_label.set_label(f"{online_count} device{plural} online")

    def on_device_selected(self, device_name):
        self.stop_auto_refresh()
        self.flow.set_sensitive(False)

        self.status_label.set_label(f"Sending to {device_name}…")
        if device_name in self.device_buttons:
            self.device_buttons[device_name].start_loading()
        threading.Thread(target=self.send_operation, args=(device_name,), daemon=True).start()

    def send_operation(self, device):
        # No timeout here: transfers are unbounded in size. check=False is explicit
        # because we branch on returncode ourselves rather than raising.
        success = all(
            subprocess.run(  # noqa: S603  (fixed argv, no shell, resolved absolute path)
                [TAILSCALE_BIN, "file", "cp", f, f"{device}:"], check=False,
            ).returncode == 0
            for f in self.files
        )
        GLib.idle_add(self.on_finished, device, success)

    def on_finished(self, device, success):

        if device in self.device_buttons:
            self.device_buttons[device].stop_loading()
        filenames = [Path(f).name for f in self.files]
        summary = filenames[0] if len(filenames) == 1 else f"{len(filenames)} files"
        if success:
            _notify("Sent successfully", f"{summary} → {device}")
        else:
            _notify("Send failed", f"Could not send {summary} to {device}.")
        self.get_application().quit()


def main():
    if not TAILSCALE_BIN:
        print(
            "taildrop: 'tailscale' CLI not found in PATH. Install Tailscale first: "
            "https://tailscale.com/download",
            file=sys.stderr,
        )
        sys.exit(1)

    app = Adw.Application(application_id="org.balazs.TaildropSender")
    app.set_flags(app.get_flags() | Gio.ApplicationFlags.HANDLES_OPEN)

    def on_activate(a):
        TaildropSenderWindow(a, sys.argv[1:]).present()

    def on_open(a, files, _n_files, _hint):
        paths = [f.get_path() for f in files if f.get_path()]
        TaildropSenderWindow(a, paths).present()

    app.connect("activate", on_activate)
    app.connect("open", on_open)
    app.run([])


if __name__ == "__main__":
    main()
