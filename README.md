# Airspace Guard - Local Drone & Aircraft Tracking

A comprehensive airspace monitoring system for **ClockworkPi uConsole + HackerGadgets CM5 + AIoV2 Expansion** designed to protect your drone flights by detecting both commercial aircraft and unauthorized drones in your operating airspace.

## Hardware Requirements

✅ **Your Exact Setup:**
- ClockworkPi uConsole
- HackerGadgets CM5 Upgrade Kit (16GB eMMC, 8GB RAM)
- **AIoV2 Expansion Board:**
  - RTL-SDR (RTL2832U + R860) - ADS-B reception + spectrum analysis
  - GPS (Multi-mode: GPS/BDS/GNSS) - Geolocation & timestamping
  - LoRa (SX1262, 860-960 MHz) - Mesh monitoring
  - RTC (PCF85063A) - Accurate timekeeping
  - USB 3.0 Hub + Gigabit Ethernet
- **Dual Wireless:**
  - HackerGadgets MediaTek AC1200 - Monitor mode (drone detection)
  - CM5 onboard wireless - Network connectivity

## What You Can Track

### ✈️ Aircraft (via ADS-B)
- Commercial aircraft within ~50-150 mile range
- Altitude, speed, heading, callsign
- Real-time visualization on interactive map

### 🛸 Drones (via WiFi Monitor Mode)
- **DJI Mini 4** - OcuSync + WiFi beacon detection
- **DJI Avata 360** - FPV control signals + HD transmission
- **DJI Neo / Neo 2** - Compact drone WiFi patterns
- Distance estimation via signal strength (RSSI)
- Direction finding using SDR + GPS
- Drone identification & classification

### 🔗 Integration
- Combined airspace dashboard
- Alerts when aircraft/drones approach your location
- Historical logging with GPS coordinates
- LoRa mesh network monitoring

## Quick Start

```bash
# Clone repository
git clone https://github.com/RichCreedy/airspace-guard.git
cd airspace-guard

# Run installation (requires sudo)
sudo bash install.sh

# Start monitoring
sudo systemctl start airspace-guard
sudo systemctl status airspace-guard

# Access dashboard
# Open browser: http://localhost:8000
```

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│     Airspace Guard Dashboard (Flask)         │
│  http://localhost:8000                       │
├──────────────────────────────────────────────────────┤
│                                              │
├──── Aircraft Data Provider ────┐               │
│   readsb (ADS-B)              │               │
│   Port: 30003 (raw JSON)      │               │
│                               │               │
├──── Drone Detection Engine ─────┤               │
│   WiFi Monitor Scanner        │   Combined   │
│   DJI Signature Database      │   Data       │
│   RSSI Triangulation         │   Fusion ─────→ Dashboard
│                               │               │
├──── Geolocation Engine ────────┤               │
│   GPS (AIoV2)                │               │
│   Direction Finding (SDR)    │               │
│   Signal Strength Analysis   │               │
│                              │               │
├──── Logging & Alerts ──────────┤               │
│   SQLite Database            │               │
│   Real-time Notifications    │               │
└──────────────────────────────────────────────────────┘

┌──────────────────────────┐  ┌──────────────────────────┐
│   Hardware Layer     │  │  Services        │
├──────────────────────────┤  ├──────────────────────────┤
│ RTL-SDR: ADS-B + DF  │  │ airspace-guard   │
│ AC1200: WiFi Monitor │  │ (systemd)        │
│ GPS: Geolocation     │  │                  │
│ LoRa: Mesh Network   │  │ readsb           │
└──────────────────────────┘  │ tar1090 (legacy) │
                          └──────────────────────────┘
```

## Directory Structure

```
airspace-guard/
├── README.md                          # This file
├── install.sh                         # Installation script
├── requirements.txt                   # Python dependencies
├── config.yaml                        # Configuration file
│
├── src/
│   ├── airspace_guard.py             # Main application
│   ├── drone_detector.py             # WiFi drone detection engine
│   ├── ads_b_provider.py             # ADS-B data integration
│   ├── geolocation_engine.py         # GPS + direction finding
│   ├── dji_signatures.py             # DJI drone identification database
│   └── alert_handler.py              # Notification system
│
├── web/
│   ├── app.py                        # Flask application
│   ├── templates/
│   │   ├── index.html               # Main dashboard
│   │   ├── settings.html            # Configuration UI
│   │   └── logs.html                # Historical data viewer
│   └── static/
│       ├── css/
│       │   └── style.css
│       ├── js/
│       │   ├── map.js               # Leaflet map integration
│       │   ├── realtime.js          # WebSocket updates
│       │   └── alerts.js            # Alert system
│       └── icons/
│           ├── aircraft.png
│           ├── drone.png
│           └── alert.png
│
├── services/
│   ├── airspace-guard.service       # Systemd service file
│   └── airspace-guard.timer         # Optional scheduled startup
│
├── database/
│   └── schema.sql                   # SQLite schema
│
└── docs/
    ├── INSTALLATION.md              # Detailed setup guide
    ├── TROUBLESHOOTING.md           # Common issues
    ├── DJI_SIGNATURES.md            # DJI detection methodology
    └── HARDWARE_NOTES.md            # AIoV2 / CM5 specific info
```

## Key Features

### 🎯 Detection
- **Passive WiFi Scanning** - No active probing, stealth operation
- **DJI Signature Recognition** - MAC prefixes, SSID patterns, beacon analysis
- **Signal Strength Triangulation** - Estimate distance from RSSI
- **Direction Finding** - Use SDR for angle-of-arrival estimation
- **ADS-B Aircraft Tracking** - Commercial aviation awareness

### 🔗 Integration
- **Multi-source Data Fusion** - Combine aircraft + drone + GPS data
- **Real-time Geolocation** - Your position from GPS, signals relative to you
- **Mesh Network Support** - LoRa integration for remote sensors
- **Historical Database** - SQLite logging with timestamps

### 🚨 Alerting
- **Web Dashboard Alerts** - Real-time visual notifications
- **Sound/Visual Warnings** - Configurable alert thresholds
- **Log File Export** - CSV/JSON historical data
- **Flight Risk Assessment** - Automatic airspace safety scoring

## Configuration

Edit `config.yaml` to customize:

```yaml
# WiFi Monitoring
wifi:
  interface: "wlan0"        # AC1200 monitor mode interface
  channels: [1, 6, 11, 36, 40, 44, 48]  # WiFi channels to scan
  dwell_time: 100           # ms per channel
  rssi_threshold: -85       # dBm minimum to detect

# ADS-B (readsb)
ads_b:
  enabled: true
  host: "127.0.0.1"
  port: 30003
  max_range: 150            # miles

# Geolocation
gps:
  enabled: true
  device: "/dev/ttyUSB0"    # AIoV2 GPS serial port
  update_rate: 1            # Hz

# Drone Detection
drone_detection:
  dwell_time: 1000          # ms total scan time per cycle
  min_rssi: -85             # Minimum signal strength
  alert_distance: 2.0       # miles - alert if drone closer than this
  alert_altitude: 500       # feet - alert if aircraft below this

# Web Dashboard
web:
  host: "0.0.0.0"
  port: 8000
  update_interval: 2        # seconds
  map_center_lat: 0.0       # Use GPS location
  map_center_lon: 0.0
```

## Installation Details

### Prerequisites
```bash
# Debian/ARM packages needed
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-scapy \
  iw \
  aircrack-ng \
  gpsd \
  sqlite3 \
  build-essential
```

### Install Steps
```bash
# 1. Clone repo
git clone https://github.com/RichCreedy/airspace-guard.git
cd airspace-guard

# 2. Install Python dependencies
sudo pip3 install -r requirements.txt

# 3. Setup database
sudo sqlite3 database/airspace.db < database/schema.sql

# 4. Configure system
sudo cp config.yaml /etc/airspace-guard/config.yaml
sudo nano /etc/airspace-guard/config.yaml  # Edit as needed

# 5. Install systemd service
sudo cp services/airspace-guard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable airspace-guard

# 6. Start service
sudo systemctl start airspace-guard
```

## Usage

### Web Dashboard
```
http://localhost:8000
```

**Features:**
- Interactive map (Leaflet)
- Real-time aircraft positions
- Detected drones with distance/direction
- Alert history log
- GPS location overlay
- System status indicators

### Command Line Monitoring
```bash
# Check service status
sudo systemctl status airspace-guard

# View live logs
sudo journalctl -u airspace-guard -f

# Query database
sqlite3 database/airspace.db
> SELECT * FROM detections WHERE type='DRONE' ORDER BY timestamp DESC LIMIT 10;

# Export data
sqlite3 database/airspace.db ".mode csv" "SELECT * FROM detections;" > airspace_log.csv
```

## Technical Details

### DJI Detection Method

**MAC Address Prefixes:**
- `60:60:1F` - DJI standard
- `94:2F:C6` - DJI OcuSync
- `28:6C:07` - DJI Mini/Air series
- `3C:15:C2` - DJI Mavic series
- `90:3A:E6` - DJI Neo series

**SSID Patterns:**
- `DJI-` prefix (most consumer models)
- `Phantom`, `Mavic`, `Air`, `Mini`, `Avata`, `Neo` in SSID
- OcuSync protocol identification

**Signal Analysis:**
- Beacon frame parsing
- RSSI-based distance estimation (calibrated for 2.4GHz)
- Traffic pattern analysis (periodic control packets)

### ADS-B Integration

- Connects to existing `readsb` service (port 30003)
- Receives raw JSON aircraft data
- Parses latitude, longitude, altitude, speed, callsign
- Maintains historical track database

### Geolocation

**GPS Component:**
- Reads from AIoV2 GPS module
- Provides your exact location
- Timestamps all events

**Direction Finding (SDR):**
- Uses RTL-SDR to measure signal strength at different frequencies
- Estimates angle-of-arrival to drone transmitter
- Triangulates position with second observation point

## Performance

**Expected Results on CM5:**
- WiFi Scan: ~5-10 drones detected per minute in active airspace
- ADS-B: ~50-100 aircraft in view (depends on altitude/range)
- Dashboard Update: 2-second refresh rate
- Database: SQLite handles 1000s of records efficiently
- Memory: ~150-200 MB typical usage
- CPU: <40% single core during peak activity

## Safety & Legal

⚠️ **Important:**
- Passive monitoring is legal in most jurisdictions
- Active drone interference is illegal - this system is **detection only**
- Ensure you have permission to operate WiFi monitoring in your location
- System is designed for **self-defense awareness** during your own flights
- Always follow local drone regulations and airspace rules

## Troubleshooting

### No drones detected
- Check AC1200 is in monitor mode: `iwconfig`
- Verify WiFi channels configured: Edit `config.yaml`
- Check RSSI threshold not too high
- See `TROUBLESHOOTING.md`

### No aircraft detected
- Verify `readsb` running: `ps aux | grep readsb`
- Check RTL-SDR is connected: `lsusb`
- Confirm antenna placement (RTL-SDR needs external antenna)
- Port 30003 accessible: `netstat -tlnp | grep 30003`

### High CPU/Memory usage
- Reduce WiFi scan channels
- Increase dwell time to reduce scan frequency
- Check for database bloat: `sqlite3 airspace.db VACUUM;`

## Contributing

Contributions welcome! Areas of interest:
- Additional drone signatures
- Signal processing improvements
- UI enhancements
- Documentation

## References

- [DJI Forensics](https://github.com/fduflyer/dji-forensics)
- [DroneAware-Node](https://github.com/fduflyer/DroneAware-Node-Releases)
- [Sparrow WiFi](https://github.com/ghostop14/sparrow-wifi)
- [RTL-SDR Guide](https://www.rtl-sdr.com/)
- [readsb Documentation](https://github.com/wiedehopf/readsb)

## License

MIT License - See LICENSE file

## Support

For issues specific to your hardware:
- AIoV2 Configuration: See `docs/HARDWARE_NOTES.md`
- AK-Rex Debian Fork: Compatibility tested on latest version
- uConsole Display: Headless or SSH recommended
