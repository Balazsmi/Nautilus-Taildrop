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

## 📂 Project Structure

* `send-via-taildrop.py` — The standalone frameless GTK4 device selection window.
* `taildrop-auto-receive.sh` — The background loop utilizing `tailscale file get --wait`.
* `taildrop-auto-receive.service` — Systemd user service managing the auto-receive lifecycle.

## 📄 License

Licensed under the [MIT License](LICENSE).
