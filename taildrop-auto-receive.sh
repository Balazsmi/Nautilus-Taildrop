#!/usr/bin/env bash
# Native blocking Taildrop auto-receive daemon using tailscale's --wait flag

if ! command -v tailscale &> /dev/null; then
    echo "Tailscale ist nicht installiert." >&2
    exit 1
fi

DOWNLOADS_DIR="$HOME/Downloads"

while true; do
    output=$(/usr/bin/tailscale file get --wait --conflict=rename "$DOWNLOADS_DIR/" 2>&1)
    status=$?

    if [ $status -eq 0 ]; then
        sleep 0.5
        filename=$(ls -t "$DOWNLOADS_DIR" | head -n 1)
        filepath="$DOWNLOADS_DIR/$filename"

        if [ -z "$filename" ] || [ ! -e "$filepath" ]; then
            filepath="$DOWNLOADS_DIR"
            msg="Saved to Downloads folder."
        else
            msg="Empfangen: $filename"
        fi

        ACTION=$(notify-send -a "Tailscale" -i "networkworkgroup-symbolic" \
            --action="default=Öffnen" "Taildrop Received" "$msg")

        if [ "$ACTION" = "default" ]; then
            xdg-open "$filepath" &
        fi
    else
        sleep 5
    fi
done
