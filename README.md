# nautilus-taildrop

A lightweight Tailscale Taildrop integration for GNOME's Nautilus file manager. Send files to any device on your Tailnet directly from the right-click context menu, and automatically receive incoming files with a desktop notification.

## Features

- **Right-click → Share → Send via Taildrop** in Nautilus (and Nemo)
- Native GTK4/libadwaita device picker UI
- Background auto-receive daemon that saves files to `~/Downloads`
- Desktop notification with an "Open" action when a file arrives
- Runs as a systemd user service — starts automatically on login

## Preview

Right-clicking a file shows a **Share** submenu with **Send via Taildrop**. Clicking it opens a small window listing all online Tailnet peers. Select a device and the file is sent immediately.

## Requirements

- Fedora / GNOME (also works on other distros with Nautilus or Nemo)
- [Tailscale](https://tailscale.com/download) installed and logged in
- `python3-gobject` (PyGObject) for the GTK4 UI and Nautilus extension
- `nautilus-python` for the extension loader

### Install dependencies on Fedora

```bash
sudo dnf install python3-gobject nautilus-python
```

### Install dependencies on Ubuntu/Debian

```bash
sudo apt install python3-gi gir1.2-nautilus-4.0
```

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/nautilus-taildrop.git
cd nautilus-taildrop
bash install.sh
```

The installer will:
1. Copy the scripts to `~/.local/bin` and `~/.local/share/nautilus/`
2. Install the Nautilus extension to `~/.local/share/nautilus-python/extensions/`
3. Enable and start the `taildrop-auto-receive` systemd user service
4. Restart Nautilus to load the extension

## Uninstallation

```bash
bash uninstall.sh
```

## File Overview

| File | Purpose |
|---|---|
| `install.sh` | One-command installer |
| `uninstall.sh` | Removes all installed files and disables the service |
| `taildrop-auto-receive.sh` | Daemon script — waits for incoming Taildrop files and sends a notification |
| `taildrop-auto-receive.service` | systemd user unit that runs the daemon on login |
| `nautilus-taildrop.py` | Nautilus/Nemo extension — adds the right-click menu entry |
| `send-via-taildrop.py` | GTK4 UI — lists Tailnet peers and sends the selected files |

## How It Works

**Sending:** The Nautilus extension registers a context menu item. When triggered, it launches `send-via-taildrop.py` with the selected file paths as arguments. The GTK4 window queries `tailscale status --peers` to list online devices. Selecting a device runs `tailscale file cp <file> <device>:` in a background thread.

**Receiving:** The systemd service runs `taildrop-auto-receive.sh` as a persistent daemon. It calls `tailscale file get --wait` in a loop, which blocks until a file arrives. On success it sends a desktop notification via `notify-send`. Clicking "Open" on the notification opens the file with the default application.

## Troubleshooting

**The context menu doesn't appear**

Make sure `nautilus-python` is installed and Nautilus was restarted after installation:
```bash
nautilus -q
```

**The service is not running**

```bash
systemctl --user status taildrop-auto-receive.service
journalctl --user -u taildrop-auto-receive.service -f
```

**Tailscale permission error when receiving files**

Make sure Taildrop is enabled for your device in the [Tailscale admin console](https://login.tailscale.com/admin/machines).

## License

MIT
