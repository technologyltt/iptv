#!/usr/bin/env bash
# Install on Raspberry Pi OS Lite (64-bit) Bookworm.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip bluetooth bluez-tools

echo "==> Virtualenv"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> User permissions"
sudo usermod -aG dialout,gpio "$USER"

echo "==> systemd unit"
sudo cp systemd/edc17-vtg.service /etc/systemd/system/edc17-vtg.service
sudo sed -i "s|__REPO__|$REPO_DIR|g" /etc/systemd/system/edc17-vtg.service
sudo sed -i "s|__USER__|$USER|g" /etc/systemd/system/edc17-vtg.service
sudo systemctl daemon-reload
sudo systemctl enable edc17-vtg

echo
echo "Listo. Conecta el ELM327 y arranca con:"
echo "   sudo systemctl start edc17-vtg"
echo "Logs:"
echo "   journalctl -u edc17-vtg -f"
echo
echo "Si usas BT pairing, primero hazlo con bluetoothctl y luego:"
echo "   sudo rfcomm bind 0 <MAC-DEL-ELM> 1"
echo "y ajusta port: /dev/rfcomm0 en app/config.yaml"
