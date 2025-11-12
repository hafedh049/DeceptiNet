#!/usr/bin/env bash
set -euo pipefail

sudo apt-get remove -y docker docker.io docker-ce docker-ce-cli containerd containerd.io runc
sudo apt-get autoremove -y
sudo apt-get autoclean
sudo apt install -y docker.io docker-compose python3-pip

pip install setuptools

# -------------------------
# 1) Clone T-Pot repo
# -------------------------
if [ ! -d "tpotce" ]; then
    echo "[*] Cloning T-Pot repository..."
    git clone https://github.com/telekom-security/tpotce.git
else
    echo "[*] T-Pot repo already exists, skipping clone."
fi

cd tpotce

# -------------------------
# 2) Run installer
# -------------------------
echo "[*] Running T-Pot installer..."
chmod +x install.sh
./install.sh

# -------------------------
# 3) Post-install instructions (optional reminders)
# -------------------------
echo "[*] Installer finished. Check messages for:"
echo "    - SSH port (default may be 64295)"
echo "    - Open ports conflicts"
echo "    - Firewall / SELinux adjustments"
echo "[*] Reboot your system to finalize installation:"
echo "    sudo reboot"
