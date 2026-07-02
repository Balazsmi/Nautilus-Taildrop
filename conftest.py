"""Pytest configuration.

``test_taildrop.py`` imports the GTK4 sender module, which requires PyGObject with
GObject-introspection typelibs (a *system* dependency) and, for widget
construction, an active display. When either is unavailable — e.g. `uv run pytest`
in a headless venv without system site packages — skip collecting that module
rather than failing, so the dev workflow degrades gracefully.
"""
import os


def _gi_stack_available() -> bool:
    try:
        import gi  # noqa: PLC0415  (lazy: conftest must load even without PyGObject)

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        gi.require_version("Pango", "1.0")
        from gi.repository import Gtk  # noqa: F401, PLC0415
    except (ImportError, ValueError):
        return False
    return True


def _has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


collect_ignore = []
if not (_gi_stack_available() and _has_display()):
    collect_ignore.append("test_taildrop.py")
