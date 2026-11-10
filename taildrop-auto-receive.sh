#!/usr/bin/env bash
# Native blocking Taildrop auto-receive daemon using tailscale's --wait flag
set -uo pipefail

TAILSCALE_BIN=$(command -v tailscale || true)
if [ -z "$TAILSCALE_BIN" ]; then
    echo "Tailscale is not installed." >&2
    exit 1
fi

XDG_USER_DIR_BIN=$(command -v xdg-user-dir || true)
if [ -z "$XDG_USER_DIR_BIN" ]; then
    echo "xdg-user-dir is not installed. Please install the xdg-user-dirs package." >&2
    exit 1
fi

DOWNLOAD_DIR=$(xdg-user-dir DOWNLOAD)
if [ -z "$DOWNLOAD_DIR" ]; then
    echo "Could not determine the XDG download directory." >&2
    exit 1
fi
mkdir -p "$DOWNLOAD_DIR"

# Most recently modified file in a directory (find/sort handles spaces).
newest_file() {
    find "$1" -maxdepth 1 -type f -printf '%T@\t%p\n' 2>/dev/null \
        | sort -rn | head -n 1 | cut -f2-
}

while true; do
    if "$TAILSCALE_BIN" file get --wait --conflict=rename "$DOWNLOAD_DIR/" 2>&1; then
        sleep 0.5  # let the write settle before locating the file

        filepath=$(newest_file "$DOWNLOAD_DIR")

        if [ -z "$filepath" ] || [ ! -e "$filepath" ]; then
            filepath="$DOWNLOAD_DIR"
            msg="Saved to Downloads folder."
        else
            msg="Received: $(basename "$filepath")"
        fi

        ACTION=$(notify-send --app-name="" --icon=none \
            --action="default=Open" "Taildrop Received" "$msg")

        if [ "$ACTION" = "default" ]; then
            xdg-open "$filepath" &
        fi
    else
        sleep 5
    fi
done
