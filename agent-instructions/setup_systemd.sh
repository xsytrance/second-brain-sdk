#!/bin/bash
set -e
PORT="${1:-8009}"
HOST="${2:-127.0.0.1}"
SERVICE="second-brain"
echo "Installing systemd user service..."
cp "$(dirname "$0")/../deploy/systemd/second-brain.service" "$HOME/.config/systemd/user/"
sed -i "s/--port [0-9]*/--port $PORT/" "$HOME/.config/systemd/user/$SERVICE.service"
sed -i "s/--host [0-9.]*/--host $HOST/" "$HOME/.config/systemd/user/$SERVICE.service"
if command -v loginctl &>/dev/null; then sudo loginctl enable-linger $USER || true; fi
systemctl --user daemon-reload
systemctl --user enable "$SERVICE"
systemctl --user start "$SERVICE"
systemctl --user status "$SERVICE"
echo "Service installed."
