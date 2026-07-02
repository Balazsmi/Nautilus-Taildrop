"""Skip the GTK test module when PyGObject/typelibs are unavailable."""


def _gi_stack_available() -> bool:
    try:
        import gi  # noqa: PLC0415

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        gi.require_version("Pango", "1.0")
        from gi.repository import Gtk  # noqa: F401, PLC0415
    except (ImportError, ValueError):
        return False
    return True


collect_ignore = []
if not _gi_stack_available():
    collect_ignore.append("test_taildrop.py")
