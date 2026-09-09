#!/bin/bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

DIRNAME="$(cd "$(dirname "$0")" && pwd)"
APPLICATION="$DIRNAME/dashboard.py"
VENV_DIR="$DIRNAME/venv"
REQUIREMENTS="$DIRNAME/requirements.txt"

cd "$DIRNAME"

echo "Dashboard service runner"
echo "Working directory: $DIRNAME"
echo "Application: $APPLICATION"

if [ ! -f "$APPLICATION" ]; then
    echo "ERROR: Application not found: $APPLICATION"
    exit 1
fi

if [ ! -f "$REQUIREMENTS" ]; then
    echo "ERROR: requirements.txt not found: $REQUIREMENTS"
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS"

echo "Starting dashboard..."
exec "$VENV_DIR/bin/python" "$APPLICATION"
