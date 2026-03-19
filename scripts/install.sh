#!/bin/bash
set -e

echo "=== Menvayal Agent Installer ==="

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash install.sh"
    exit 1
fi

# Install system dependencies
echo "[1/5] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv

# Create install directory
echo "[2/5] Creating install directory..."
mkdir -p /opt/menvayal-agent
mkdir -p /etc/menvayal

# Create virtual environment
echo "[3/5] Setting up Python virtual environment..."
python3 -m venv /opt/menvayal-agent/venv

# Install the agent
echo "[4/5] Installing menvayal-agent..."
/opt/menvayal-agent/venv/bin/pip install --quiet \
    paho-mqtt PyYAML RPi.GPIO gpiozero smbus2 \
    spidev pyserial w1thermsensor 2>/dev/null || true

# Copy agent source
cp -r menvayal_agent /opt/menvayal-agent/
cp setup.py /opt/menvayal-agent/
cd /opt/menvayal-agent
/opt/menvayal-agent/venv/bin/pip install --quiet -e .

# Install systemd service
echo "[5/5] Installing systemd service..."
cp /opt/menvayal-agent/systemd/menvayal-agent.service /etc/systemd/system/ 2>/dev/null || \
    cp systemd/menvayal-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable menvayal-agent

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy your config.yaml to /etc/menvayal/config.yaml"
echo "  2. Start the agent: sudo systemctl start menvayal-agent"
echo "  3. Check status: sudo systemctl status menvayal-agent"
echo "  4. View logs: sudo journalctl -u menvayal-agent -f"
