#!/bin/bash

# Install Kikai-kun as a systemd service

SERVICE_NAME="kikai-kun.service"
SERVICE_FILE="$(pwd)/${SERVICE_NAME}"
SYSTEMD_DIR="/etc/systemd/system"

echo "Installing Kikai-kun service..."

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Copy service file to systemd directory
echo "Copying service file to $SYSTEMD_DIR..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
sudo systemctl enable $SERVICE_NAME

echo ""
echo "Installation complete!"
echo ""
echo "Service commands:"
echo "  Start service:   sudo systemctl start $SERVICE_NAME"
echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  View status:     sudo systemctl status $SERVICE_NAME"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "To start the service now, run:"
echo "  sudo systemctl start $SERVICE_NAME"
