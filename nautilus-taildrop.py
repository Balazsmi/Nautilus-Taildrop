"""Nautilus / Nemo context-menu extension for Nautilus-Taildrop.

Installed system-wide (e.g. ``/usr/share/nautilus-python/extensions/``) via the
``nautilus-python`` loader, this adds a top-level "Send via Taildrop" right-click
entry for selected files — no per-user setup required, unlike a Nautilus script.
It just launches the standalone sender (``send-via-taildrop``), preferring the
packaged ``/usr/bin`` binary and falling back to a per-user install.
"""
import importlib
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GObject", "2.0")

# Resolve whichever file-manager extension API is available. Nautilus bumped its
# introspection version over time (4.1 on current GNOME, 4.0 previously); Nemo is
# the Cinnamon fallback. Try newest first and stop at the first that loads.
FileManager = None
for _namespace, _version in (("Nautilus", "4.1"), ("Nautilus", "4.0"), ("Nemo", "3.0")):
    try:
        gi.require_version(_namespace, _version)
        FileManager = importlib.import_module(f"gi.repository.{_namespace}")
    except (ImportError, ValueError):
        continue
    break

if FileManager is None:
    _msg = "No supported Nautilus or Nemo extension API found"
    raise ImportError(_msg)

from gi.repository import Gio, GObject  # noqa: E402


def _find_sender():
    """Return the path to the send-via-taildrop launcher, or None if unavailable."""
    candidates = [
        Path("/usr/bin/send-via-taildrop"),
        Path.home() / ".local/share/nautilus/scripts/Send via Taildrop",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return shutil.which("send-via-taildrop")


class TaildropMenuProvider(GObject.Object, FileManager.MenuProvider):
    def _send(self, _menu, files):
        sender = _find_sender()
        if not sender:
            return
        paths = [
            Gio.File.new_for_uri(f.get_uri()).get_path()
            for f in files
            if f.get_uri_scheme() == "file"
        ]
        paths = [p for p in paths if p and not Path(p).is_dir()]
        if paths:
            # Fixed argv, no shell, sender resolved to an absolute/known path.
            subprocess.Popen([sender, *paths])  # noqa: S603

    def get_file_items(self, *args):
        # Nautilus 4.0 passes (files,); older Nautilus/Nemo pass (window, files).
        files = args[-1]
        if not files or any(f.is_directory() for f in files):
            return ()
        item = FileManager.MenuItem(
            name="TaildropMenuProvider::SendViaTaildrop",
            label="Send via Taildrop",
            tip="Send the selected file(s) via Tailscale Taildrop",
        )
        item.connect("activate", self._send, files)
        return (item,)
