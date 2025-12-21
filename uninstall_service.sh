#!/bin/bash

# Uninstall Kikai-kun systemd service

SERVICE_NAME="kikai-kun.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "Uninstalling Kikai-kun service..."

# Stop the service if running
echo "Stopping service..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null

# Disable the service
echo "Disabling service..."
sudo systemctl disable $SERVICE_NAME 2>/dev/null

# Remove service file
echo "Removing service file..."
sudo rm -f "$SYSTEMD_DIR/$SERVICE_NAME"

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo ""
echo "Uninstallation complete!"
