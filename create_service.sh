#!/bin/bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run with sudo"
    exit 1
fi

DIRNAME="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="dashboard"
RUN_SCRIPT="$DIRNAME/run.sh"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
REMOVE_SCRIPT="$DIRNAME/remove_service.sh"

if [ ! -f "$RUN_SCRIPT" ]; then
    echo "The file $RUN_SCRIPT does not exist."
    exit 1
fi

if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
    echo "The service $SERVICE_NAME already exists."
    exit 1
fi

chmod +x "$RUN_SCRIPT"
if [ -f "$REMOVE_SCRIPT" ]; then
    chmod +x "$REMOVE_SCRIPT"
fi

# Prepare the environment before systemd starts the service. Native Raspberry Pi
# modules are installed from Debian packages and the venv is created with
# --system-site-packages so those modules are visible inside it.
echo "Preparing dashboard environment..."
"$RUN_SCRIPT" --prepare-only

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Run LCD Dashboard
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$DIRNAME
ExecStart=$RUN_SCRIPT
Restart=on-failure
RestartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "The service $SERVICE_NAME has been created and started."
echo "Environment preparation completed before service startup."
