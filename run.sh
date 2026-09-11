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

# Some Python dependencies (lgpio, spidev, netifaces) contain native C
# extensions. On a fresh Raspberry Pi OS installation pip therefore needs the
# matching Python development headers and a compiler toolchain.
#
# We deliberately check the packages first so apt is only used during initial
# setup (or after one of these packages was removed), not on every dashboard
# restart.
SYSTEM_PACKAGES=(
    python3-venv
    python3-dev
    build-essential
    swig
)

install_system_dependencies() {
    local missing_packages=()
    local package

    if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-query >/dev/null 2>&1; then
        echo "ERROR: This installer currently expects a Debian/Raspberry Pi OS system with apt/dpkg."
        exit 1
    fi

    for package in "${SYSTEM_PACKAGES[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then
            missing_packages+=("$package")
        fi
    done

    if (( ${#missing_packages[@]} > 0 )); then
        echo "Installing required system packages: ${missing_packages[*]}"
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing_packages[@]}"
    else
        echo "Required system build packages already installed."
    fi
}

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

install_system_dependencies

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS"

echo "Starting dashboard..."
exec "$VENV_DIR/bin/python" "$APPLICATION"
