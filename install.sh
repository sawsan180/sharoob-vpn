#!/data/data/com.termux/files/usr/bin/bash
# Sharoob VPN - Installer

GH_USER="sawsan180"
GH_REPO="sharoob-vpn"
GH_BRANCH="main"
BASE="https://raw.githubusercontent.com/${GH_USER}/${GH_REPO}/${GH_BRANCH}"
BIN_DIR="/data/data/com.termux/files/usr/bin"

echo ""
echo "=== Sharoob VPN - Installer ==="
echo ""

if ! command -v curl &>/dev/null; then
    echo "[*] Installing curl..."
    pkg install curl -y
fi

echo "[*] Downloading launcher..."
curl -fsSL "${BASE}/sharoob" -o "${BIN_DIR}/sharoob"

echo "[*] Downloading core..."
curl -fsSL "${BASE}/sharoob.bin" -o "${BIN_DIR}/sharoob.bin"

echo "[*] Downloading version..."
curl -fsSL "${BASE}/version.txt" -o "${BIN_DIR}/.sharoob_version"

chmod +x "${BIN_DIR}/sharoob" "${BIN_DIR}/sharoob.bin"

echo ""
echo "[+] Installation complete!"
echo ""
echo "Run: sharoob"
echo ""

