#!/usr/bin/env bash
# Set up the project environment on Linux.
set -e
cd "$(dirname "$0")"

echo "[Setup] Beginning setup"
if [ ! -d ".venv" ]; then
    echo "[Setup] Creating virtual environment"
    python3 -m venv .venv
fi

echo "[Setup] Upgrading pip"
.venv/bin/python -m pip install --upgrade pip -q

echo "[Setup] Installing requirements"
.venv/bin/python -m pip install -r requirements.txt

echo "[Setup] Setup complete"
echo
echo "Run the app with: ./run.sh"
