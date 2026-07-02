"""Nautilus/Nemo context-menu extension: adds a "Send via Taildrop" entry that
launches the standalone sender for the selected files."""
import importlib
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GObject", "2.0")

# Nautilus bumped its introspection version over time; try newest first, then Nemo.
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
    candidates = [
        Path("/usr/bin/send-via-taildrop"),
        Path.home() / ".local/bin/send-via-taildrop",
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
            subprocess.Popen([sender, *paths])  # noqa: S603

    def get_file_items(self, *args):
        # Nautilus 4.x passes (files,); older Nautilus/Nemo pass (window, files).
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
