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

# Native Raspberry Pi / Linux Python extensions are installed from Debian
# packages instead of being compiled by pip. This avoids requiring Python.h,
# build-essential and SWIG on a fresh Raspberry Pi OS installation.
SYSTEM_PACKAGES=(
    python3-venv
    python3-lgpio
    python3-spidev
    python3-netifaces
)

install_system_dependencies() {
    local missing_packages=()
    local package

    if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-query >/dev/null 2>&1; then
        echo "ERROR: This installer expects a Debian/Raspberry Pi OS system with apt/dpkg."
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
        echo "Required system packages already installed."
    fi
}

ensure_virtual_environment() {
    local recreate=false

    if [ -x "$VENV_DIR/bin/python" ]; then
        if [ ! -f "$VENV_DIR/pyvenv.cfg" ] || \
           ! grep -Eq '^include-system-site-packages[[:space:]]*=[[:space:]]*true$' "$VENV_DIR/pyvenv.cfg"; then
            echo "Existing virtual environment does not expose Debian system packages."
            echo "Recreating virtual environment with --system-site-packages..."
            recreate=true
        fi
    fi

    if [ "$recreate" = true ]; then
        rm -rf "$VENV_DIR"
    fi

    if [ ! -x "$VENV_DIR/bin/python" ]; then
        echo "Creating virtual environment: $VENV_DIR"
        python3 -m venv --system-site-packages "$VENV_DIR"
    fi
}

install_python_dependencies() {
    echo "Installing/updating Python dependencies from requirements.txt..."
    "$VENV_DIR/bin/python" -m pip install --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS"
}

verify_native_dependencies() {
    echo "Verifying Debian-provided Python modules..."
    "$VENV_DIR/bin/python" - <<'PY'
import importlib

modules = ("lgpio", "spidev", "netifaces")
failed = []

for module_name in modules:
    try:
        module = importlib.import_module(module_name)
        path = getattr(module, "__file__", "built-in")
        print(f"  OK {module_name}: {path}")
    except Exception as error:
        failed.append((module_name, error))

if failed:
    for module_name, error in failed:
        print(f"  ERROR {module_name}: {error}")
    raise SystemExit(1)
PY
}

prepare_environment() {
    install_system_dependencies
    ensure_virtual_environment
    install_python_dependencies
    verify_native_dependencies
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

case "${1:-}" in
    "")
        ;;
    --prepare-only)
        prepare_environment
        echo "Dashboard environment prepared successfully."
        exit 0
        ;;
    *)
        echo "Usage: $0 [--prepare-only]"
        exit 2
        ;;
esac

prepare_environment

echo "Starting dashboard..."
exec "$VENV_DIR/bin/python" "$APPLICATION"
