#!/bin/sh
# install.sh - symlink the launcher and install the systemd user service
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
chmod +x "$here/bin/herdr-stb"
ln -sf "$here/bin/herdr-stb" "$HOME/.local/bin/herdr-stb"
cp "$here/systemd/herdr-stb.service" "$HOME/.config/systemd/user/herdr-stb.service"
systemctl --user daemon-reload
systemctl --user enable --now herdr-stb.service
echo "installed. Notifications are OFF until you run: herdr-stb on"
