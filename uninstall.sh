#!/usr/bin/env bash
set -e

echo "Uninstalling Nautilus Taildrop Integration..."

# Stop and disable the systemd service
systemctl --user stop taildrop-auto-receive.service 2>/dev/null || true
systemctl --user disable taildrop-auto-receive.service 2>/dev/null || true

# Remove installed files
rm -f ~/.local/bin/taildrop-auto-receive.sh
rm -f ~/.config/systemd/user/taildrop-auto-receive.service
rm -f ~/.local/share/nautilus/scripts/"Send via Taildrop"
rm -f ~/.local/share/nautilus-python/extensions/nautilus-taildrop.py

systemctl --user daemon-reload

# Restart Nautilus
nautilus -q 2>/dev/null || true

echo "Uninstall complete."
