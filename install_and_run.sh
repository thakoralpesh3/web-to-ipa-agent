#!/usr/bin/env bash
# Web-to-IPA AI Agent — One-Command Fast Cloud & Local Installer
set -e

REPO_URL="https://github.com/thakoralpesh3/web-to-ipa-agent.git"
INSTALL_DIR="${HOME}/web-to-ipa-agent"

echo "============================================================"
echo "  🚀 Web-to-IPA AI Agent — Fast Cloud & Local Installer    "
echo "============================================================"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Cloning repository from GitHub..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✓ Installation complete!"
echo "Starting Web-to-IPA AI Studio Dashboard on http://localhost:8992 ..."
./launch_agent.sh --gui
