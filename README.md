# Nautilus Taildrop

A lightweight Tailscale Taildrop integration for GNOME's Nautilus file manager


![Taildrop sender UI](screenshots/light.png)
![Taildrop sender UI](screenshots/dark.png)


## 📋 Features

- **Nautilus Integration:** Right-click a file $\rightarrow$ `Scripts` $\rightarrow$ `Send via Taildrop`.
- **Modern UI:** Borderless GTK4/Libadwaita device picker matching GNOME's design language and dynamic accent color.
- **Auto-Receive Daemon:** Background systemd user service that automatically saves incoming files to `~/Downloads`.
- **Desktop Notifications:** Native alerts with an immediate "Open" action upon receiving a file.

## 💻 Requirements

- Fedora / Ubuntu / Debian with Nautilus or Nemo
- Active [Tailscale](https://tailscale.com) installation and logged in on this device
- `tailscale` CLI available in `PATH`
- Python 3 with GObject introspection bindings

### Install Dependencies

**Fedora:**
```bash
sudo dnf install python3-gobject
```

**Ubuntu / Debian:**

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

> The `tailscale` CLI must also be installed and authenticated separately. See https://tailscale.com/download for platform-specific instructions.

## 🔨 Installation & Setup

```bash
git clone https://github.com/Balazsmi/Nautilus-Taildrop.git
cd Nautilus-Taildrop
bash install.sh
```

## 🧑‍💻 Development

The project uses [uv](https://docs.astral.sh/uv/) to manage dev tooling (ruff and
pytest). Runtime dependencies (PyGObject, GTK4, libadwaita, the `tailscale` CLI)
are **system** packages — they provide GObject-introspection typelibs and native
binaries and are not pip/uv-installable, so `pyproject.toml` intentionally leaves
`dependencies` empty. Install them via your distro (see above).

```bash
uv sync              # create the dev venv (ruff + pytest)
uv run ruff check .  # lint
uv run pytest        # run tests
```

> The tests import the GTK sender and therefore need system PyGObject **and** an
> active display. In uv's isolated venv (or headless) they are skipped
> automatically via `conftest.py`; run them against the system Python
> (`python3 -m pytest`) in a graphical session to exercise them.

## 📂 Project Structure

* `send-via-taildrop.py` — The standalone frameless GTK4 device selection window.
* `taildrop-auto-receive.sh` — The background loop utilizing `tailscale file get --wait`.
* `taildrop-auto-receive.service` — Systemd user service managing the auto-receive lifecycle.
* `pyproject.toml` — Project metadata, uv dev dependency group, and ruff lint config.
