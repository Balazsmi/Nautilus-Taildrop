#!/usr/bin/env bash
set -e

echo "Installing Nautilus Taildrop Integration..."

# Check dependencies
if ! command -v tailscale &> /dev/null; then
    echo "Error: Tailscale is not installed. Please install it first: https://tailscale.com/download"
    exit 1
fi

if ! python3 -c "import gi" &> /dev/null; then
    echo "Error: python3-gi (PyGObject) is not installed."
    echo "  Fedora/RHEL: sudo dnf install python3-gobject"
    echo "  Ubuntu/Debian: sudo apt install python3-gi"
    exit 1
fi

# Create required directories
mkdir -p ~/.local/bin
mkdir -p ~/.config/systemd/user
mkdir -p ~/.local/share/nautilus/scripts
mkdir -p ~/.local/share/nautilus-python/extensions

# Copy and set permissions
cp taildrop-auto-receive.sh ~/.local/bin/
chmod +x ~/.local/bin/taildrop-auto-receive.sh

cp taildrop-auto-receive.service ~/.config/systemd/user/

cp send-via-taildrop.py ~/.local/share/nautilus/scripts/"Send via Taildrop"
chmod +x ~/.local/share/nautilus/scripts/"Send via Taildrop"

cp nautilus-taildrop.py ~/.local/share/nautilus-python/extensions/

# Enable and start the systemd user service
systemctl --user daemon-reload
systemctl --user enable --now taildrop-auto-receive.service

# Restart Nautilus to load the new extension
nautilus -q 2>/dev/null || true

echo ""
echo "Installation complete!"
echo "The 'Share > Send via Taildrop' context menu entry is now active."
echo "Files sent to this device will appear in ~/Downloads with a desktop notification."
