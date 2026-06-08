#!/bin/bash
# Installation script for Airspace Guard on Debian ARM (uConsole + AIoV2)
# Run with: sudo bash install.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Airspace Guard Installation Script    ║${NC}"
echo -e "${GREEN}║  ClockworkPi uConsole + AIoV2 Edition   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run with sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/10] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    iw \
    aircrack-ng \
    gpsd \
    gpsd-clients \
    sqlite3 \
    build-essential \
    git \
    curl \
    wireless-tools \
    rfkill

echo -e "${YELLOW}[2/10] Installing Python 3 dependencies...${NC}"
sudo pip3 install --upgrade pip setuptools wheel
sudo pip3 install -r requirements.txt

echo -e "${YELLOW}[3/10] Creating system user...${NC}"
if ! id -u airspace &> /dev/null; then
    sudo useradd -r -s /bin/false -d /var/lib/airspace-guard airspace
    echo -e "${GREEN}✓ Created 'airspace' user${NC}"
else
    echo -e "${GREEN}✓ User 'airspace' already exists${NC}"
fi

echo -e "${YELLOW}[4/10] Creating directories...${NC}"
sudo mkdir -p /etc/airspace-guard
sudo mkdir -p /var/lib/airspace-guard/logs
sudo mkdir -p /var/lib/airspace-guard/database
sudo mkdir -p /run/airspace-guard
sudo chown -R airspace:airspace /var/lib/airspace-guard
sudo chown -R airspace:airspace /run/airspace-guard
sudo chmod 755 /etc/airspace-guard

echo -e "${YELLOW}[5/10] Installing configuration files...${NC}"
sudo cp config.yaml /etc/airspace-guard/config.yaml
sudo chmod 644 /etc/airspace-guard/config.yaml
echo -e "${GREEN}✓ Configuration copied to /etc/airspace-guard/config.yaml${NC}"

echo -e "${YELLOW}[6/10] Setting up database...${NC}"
sudo sqlite3 /var/lib/airspace-guard/airspace.db < database/schema.sql
sudo chown airspace:airspace /var/lib/airspace-guard/airspace.db
sudo chmod 600 /var/lib/airspace-guard/airspace.db
echo -e "${GREEN}✓ Database initialized${NC}"

echo -e "${YELLOW}[7/10] Installing systemd service...${NC}"
sudo cp services/airspace-guard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable airspace-guard
echo -e "${GREEN}✓ Service installed and enabled${NC}"

echo -e "${YELLOW}[8/10] Setting up WiFi monitor mode...${NC}"
echo "" 
echo "Your AC1200 interface will need to be set to monitor mode."
echo "Detected WiFi interfaces:"
iw dev | grep "Interface"
echo ""
read -p "Enter AC1200 interface name (e.g., wlan0): " wifi_interface

if [ ! -z "$wifi_interface" ]; then
    echo "Monitor mode will be automatically set when service starts."
    echo "Updating config with interface: $wifi_interface"
    sudo sed -i "s/interface: \"wlan0\"/interface: \"$wifi_interface\"/" /etc/airspace-guard/config.yaml
    echo -e "${GREEN}✓ WiFi interface configured${NC}"
else
    echo -e "${YELLOW}⚠ Skipping WiFi configuration (set manually in /etc/airspace-guard/config.yaml)${NC}"
fi

echo -e "${YELLOW}[9/10] Configuring GPS...${NC}"
echo "GPS device path (typically /dev/ttyUSB0 for AIoV2): "
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices found"
echo ""
read -p "GPS device path [/dev/ttyUSB0]: " gps_device
gps_device=${gps_device:-/dev/ttyUSB0}

if [ ! -z "$gps_device" ]; then
    sudo sed -i "s|device: \"/dev/ttyUSB0\"|device: \"$gps_device\"|" /etc/airspace-guard/config.yaml
    echo -e "${GREEN}✓ GPS configured${NC}"
fi

echo -e "${YELLOW}[10/10] Final setup...${NC}"

# Create log rotation
sudo bash -c 'cat > /etc/logrotate.d/airspace-guard << EOF
/var/log/airspace-guard.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 airspace airspace
    sharedscripts
    postrotate
        systemctl reload airspace-guard > /dev/null 2>&1 || true
    endscript
}
EOF'

# Create sudoers rule for WiFi monitoring
sudo bash -c 'cat > /etc/sudoers.d/airspace-guard << EOF
airspace ALL=(ALL) NOPASSWD: /sbin/iw, /sbin/ip, /bin/iwconfig, /usr/sbin/rfkill
EOF'
sudo chmod 440 /etc/sudoers.d/airspace-guard

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation Complete!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Verify configuration:"
echo -e "   ${GREEN}sudo nano /etc/airspace-guard/config.yaml${NC}"
echo ""
echo "2. Start the service:"
echo -e "   ${GREEN}sudo systemctl start airspace-guard${NC}"
echo ""
echo "3. Check status:"
echo -e "   ${GREEN}sudo systemctl status airspace-guard${NC}"
echo ""
echo "4. View logs:"
echo -e "   ${GREEN}sudo journalctl -u airspace-guard -f${NC}"
echo ""
echo "5. Access dashboard:"
echo -e "   ${GREEN}http://localhost:8000${NC}"
echo ""
echo "6. Test detection (WiFi monitoring):"
echo -e "   ${GREEN}Turn on a DJI drone nearby and check the dashboard${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  - Ensure readsb is running for ADS-B (aircraft) detection"
echo "  - GPS may take a minute to get first fix"
echo "  - AC1200 needs to be in monitor mode (done automatically)"
echo ""
