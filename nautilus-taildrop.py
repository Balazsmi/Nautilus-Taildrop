import os
import subprocess
import gi

gi.require_version("Gio", "2.0")
gi.require_version("GObject", "2.0")

try:
    gi.require_version("Nautilus", "4.0")
    from gi.repository import Nautilus as FileManager
except Exception:
    gi.require_version("Nemo", "3.0")
    from gi.repository import Nemo as FileManager

from gi.repository import Gio, GObject


class TaildropShareExtension(GObject.Object, FileManager.MenuProvider):
    def __init__(self):
        super().__init__()

    def send_via_taildrop(self, menu, files):
        paths = [
            Gio.File.new_for_uri(f.get_uri()).get_path()
            for f in files
            if f.get_uri_scheme() == "file"
        ]
        paths = [p for p in paths if p and not os.path.isdir(p)]

        if paths:
            script_path = os.path.expanduser(
                "~/.local/share/nautilus/scripts/Send via Taildrop"
            )
            if os.path.exists(script_path):
                subprocess.Popen([script_path] + paths)

    def get_file_items(self, *args):
        files = args[-1]
        if not files or any(f.is_directory() for f in files):
            return ()

        main_item = FileManager.MenuItem(
            name="TaildropShareExtension::ShareMenu",
            label="Share",
            tip="Share files via Taildrop",
        )
        submenu = FileManager.Menu()
        main_item.set_submenu(submenu)

        taildrop_item = FileManager.MenuItem(
            name="TaildropShareExtension::SendViaTaildrop",
            label="Send via Taildrop",
            tip="Send via Tailscale Taildrop",
        )
        taildrop_item.connect("activate", self.send_via_taildrop, files)
        submenu.append_item(taildrop_item)

        return (main_item,)
