#!/data/data/com.termux/files/usr/bin/bash
# Sharoob VPN - Installer v2.3.13

GH_USER="sawsan180"
GH_REPO="sharoob-vpn"
GH_BRANCH="main"
BASE="https://raw.githubusercontent.com/${GH_USER}/${GH_REPO}/${GH_BRANCH}"
BIN_DIR="/data/data/com.termux/files/usr/bin"

echo ""
echo "=== Sharoob VPN - Installer ==="
echo ""

# 1) Check curl
if ! command -v curl &>/dev/null; then
    echo "[*] Installing curl..."
    pkg install curl -y
fi

# 2) Check python3
if ! command -v python3 &>/dev/null; then
    echo "[*] Installing python..."
    pkg install python -y
fi

# 3) Download files
echo "[*] Downloading launcher..."
curl -fsSL "${BASE}/sharoob" -o "${BIN_DIR}/sharoob"

echo "[*] Downloading menu (Python)..."
curl -fsSL "${BASE}/sharoob_menu.py" -o "${BIN_DIR}/sharoob_menu.py"

echo "[*] Downloading core..."
curl -fsSL "${BASE}/sharoob.bin" -o "${BIN_DIR}/sharoob.bin"

echo "[*] Downloading version..."
curl -fsSL "${BASE}/version.txt" -o "${BIN_DIR}/.sharoob_version"

# 4) Permissions
chmod +x "${BIN_DIR}/sharoob" "${BIN_DIR}/sharoob.bin" "${BIN_DIR}/sharoob_menu.py"

echo ""
echo "[+] Installation complete!"
echo ""
echo "Run: sharoob"
echo ""
