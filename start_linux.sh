#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

echo "=== Hand Gesture Control System - Linux Launcher ==="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Try to set up Virtual Environment
USE_VENV=false
# If venv exists but is broken (no activate script), remove it
if [ -d "venv" ] && [ ! -f "venv/bin/activate" ]; then
    echo "[INFO] Incomplete/broken virtual environment detected. Cleaning up..."
    rm -rf venv
fi

if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment (venv)..."
    if python3 -m venv venv 2>/dev/null && [ -f "venv/bin/activate" ]; then
        USE_VENV=true
    else
        echo "[WARNING] Could not create virtual environment (python3-venv might be missing)."
        echo "[INFO] Falling back to user-level installation (--user)."
    fi
else
    USE_VENV=true
fi

# Install/Verify Dependencies
if [ "$USE_VENV" = true ]; then
    echo "[INFO] Activating virtual environment..."
    source venv/bin/activate
    echo "[INFO] Installing requirements in virtual environment..."
    # Filter pywin32 out of requirements.txt
    grep -v "pywin32" requirements.txt > temp_reqs.txt
    pip install -r temp_reqs.txt
    pip install pywebview
    rm temp_reqs.txt
else
    echo "[INFO] Installing requirements for user (--user --break-system-packages)..."
    grep -v "pywin32" requirements.txt > temp_reqs.txt
    pip3 install --user --break-system-packages -r temp_reqs.txt
    pip3 install --user --break-system-packages pywebview
    rm temp_reqs.txt
fi

# Apply Xauthority patch for modern Linux / Wayland / Mutter Xwayland environments
echo "[INFO] Patching Xauthority display cookies..."
python3 fix_xauth.py
export XAUTHORITY=/tmp/xauth_fixed

echo "[INFO] Starting application..."
python3 desktop_app.py
