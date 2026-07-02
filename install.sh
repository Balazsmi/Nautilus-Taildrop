#!/usr/bin/env bash
set -e

echo "Installing Taildrop integration..."

# Check dependencies
if ! command -v tailscale &> /dev/null; then
    echo "Error: Tailscale is not installed. Please install it first: https://tailscale.com/download"
    exit 1
fi

if ! python3 -c "import gi" &> /dev/null; then
    echo "Error: python3-gi (PyGObject) is not installed. The GTK sender UI requires PyGObject."
    echo "  Fedora/RHEL: sudo dnf install python3-gobject"
    echo "  Ubuntu/Debian: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
    exit 1
fi

# The right-click entry needs the nautilus-python loader; warn but don't fail.
if ! python3 -c "import gi; gi.require_version('Nautilus', '4.1'); from gi.repository import Nautilus" &> /dev/null \
   && ! python3 -c "import gi; gi.require_version('Nautilus', '4.0'); from gi.repository import Nautilus" &> /dev/null; then
    echo "Warning: the nautilus-python extension bindings were not found."
    echo "  The right-click 'Send via Taildrop' entry needs them:"
    echo "  Fedora/RHEL: sudo dnf install nautilus-python"
    echo "  Ubuntu/Debian: sudo apt install python3-nautilus"
    echo "  Arch: sudo pacman -S nautilus-python"
fi

# Create required directories
mkdir -p ~/.local/bin
mkdir -p ~/.config/systemd/user
mkdir -p ~/.local/share/nautilus-python/extensions

# Install the sender and auto-receive daemon
cp send-via-taildrop.py ~/.local/bin/send-via-taildrop
chmod +x ~/.local/bin/send-via-taildrop

cp taildrop-auto-receive.sh ~/.local/bin/
chmod +x ~/.local/bin/taildrop-auto-receive.sh

# Install the file-manager context-menu extension (no Scripts submenu needed)
cp nautilus-taildrop.py ~/.local/share/nautilus-python/extensions/nautilus-taildrop.py

cp taildrop-auto-receive.service ~/.config/systemd/user/

# Enable and start the systemd user service
systemctl --user daemon-reload
systemctl --user enable --now taildrop-auto-receive.service

# Restart Nautilus so the extension is loaded
nautilus -q 2>/dev/null || true

echo ""
echo "Installation complete!"
echo "Right-click a file and choose 'Send via Taildrop'."
echo "Files sent to this device will appear in ~/Downloads with a desktop notification."
