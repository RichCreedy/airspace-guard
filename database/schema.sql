-- Airspace Guard SQLite Database Schema
-- Initialize with: sqlite3 airspace.db < schema.sql

-- Aircraft detections (from ADS-B)
CREATE TABLE IF NOT EXISTS aircraft (
    id INTEGER PRIMARY KEY,
    icao TEXT UNIQUE,
    callsign TEXT,
    altitude_ft INTEGER,
    speed_knots INTEGER,
    heading_deg REAL,
    latitude REAL,
    longitude REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_update DATETIME DEFAULT CURRENT_TIMESTAMP,
    range_miles REAL,
    vertical_rate_ft_min INTEGER,
    squawk TEXT,
    track_start DATETIME,
    track_end DATETIME
);

CREATE INDEX idx_aircraft_callsign ON aircraft(callsign);
CREATE INDEX idx_aircraft_timestamp ON aircraft(timestamp);
CREATE INDEX idx_aircraft_range ON aircraft(range_miles);

-- Drone detections (WiFi monitor mode)
CREATE TABLE IF NOT EXISTS drones (
    id INTEGER PRIMARY KEY,
    mac_address TEXT UNIQUE,
    ssid TEXT,
    drone_type TEXT,  -- 'DJI_MINI_4', 'DJI_AVATA_360', 'DJI_NEO', etc.
    manufacturer TEXT,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_rssi_dbm REAL,
    avg_rssi_dbm REAL,
    estimated_distance_m REAL,
    estimated_distance_miles REAL,
    signal_samples INTEGER,
    last_latitude REAL,
    last_longitude REAL,
    confidence_score REAL,  -- 0.0-1.0
    active BOOLEAN DEFAULT 1
);

CREATE INDEX idx_drones_mac ON drones(mac_address);
CREATE INDEX idx_drones_type ON drones(drone_type);
CREATE INDEX idx_drones_timestamp ON drones(last_seen);

-- Signal observations for triangulation
CREATE TABLE IF NOT EXISTS signal_samples (
    id INTEGER PRIMARY KEY,
    drone_id INTEGER,
    mac_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    rssi_dbm REAL,
    frequency_hz INTEGER,
    channel INTEGER,
    latitude REAL,
    longitude REAL,
    gps_accuracy_m REAL,
    FOREIGN KEY(drone_id) REFERENCES drones(id)
);

CREATE INDEX idx_samples_drone ON signal_samples(drone_id);
CREATE INDEX idx_samples_timestamp ON signal_samples(timestamp);
CREATE INDEX idx_samples_mac ON signal_samples(mac_address);

-- Alerts and events
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    alert_type TEXT,  -- 'DRONE_DETECTED', 'AIRCRAFT_PROXIMITY', 'DRONE_PROXIMITY'
    severity TEXT,    -- 'INFO', 'WARNING', 'CRITICAL'
    target_id TEXT,   -- MAC address for drones, ICAO for aircraft
    target_type TEXT, -- 'DRONE' or 'AIRCRAFT'
    description TEXT,
    latitude REAL,
    longitude REAL,
    distance_miles REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_at DATETIME
);

CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_target ON alerts(target_id);

-- GPS location history
CREATE TABLE IF NOT EXISTS gps_history (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    altitude_m REAL,
    accuracy_m REAL,
    hdop REAL,
    vdop REAL,
    satellite_count INTEGER,
    fix_type TEXT  -- '2D', '3D', 'NO_FIX'
);

CREATE INDEX idx_gps_timestamp ON gps_history(timestamp);

-- Geolocation calculations
CREATE TABLE IF NOT EXISTS geolocation_results (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    mac_address TEXT,
    drone_type TEXT,
    estimated_latitude REAL,
    estimated_longitude REAL,
    confidence REAL,  -- 0.0-1.0
    method TEXT,      -- 'RSSI_ONLY', 'TRIANGULATION', 'DIRECTION_FINDING'
    sample_count INTEGER,
    accuracy_m REAL
);

CREATE INDEX idx_geoloc_mac ON geolocation_results(mac_address);
CREATE INDEX idx_geoloc_timestamp ON geolocation_results(timestamp);

-- System events and diagnostics
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT,  -- 'SERVICE_START', 'SERVICE_STOP', 'GPS_FIX', 'WIFI_ERROR', etc.
    level TEXT,       -- 'INFO', 'WARNING', 'ERROR'
    message TEXT,
    details TEXT
);

CREATE INDEX idx_events_timestamp ON system_events(timestamp);
CREATE INDEX idx_events_type ON system_events(event_type);

-- Statistics and summary
CREATE TABLE IF NOT EXISTS daily_statistics (
    id INTEGER PRIMARY KEY,
    date DATE UNIQUE,
    aircraft_count INTEGER,
    drones_detected INTEGER,
    alerts_triggered INTEGER,
    total_scan_time_minutes INTEGER,
    uptime_minutes INTEGER,
    avg_cpu_percent REAL,
    avg_memory_mb REAL
);

CREATE INDEX idx_stats_date ON daily_statistics(date);

-- Views for convenience
CREATE VIEW active_aircraft AS
SELECT * FROM aircraft
WHERE track_end IS NULL
ORDER BY timestamp DESC;

CREATE VIEW active_drones AS
SELECT * FROM drones
WHERE active = 1 AND last_seen > datetime('now', '-5 minutes')
ORDER BY last_seen DESC;

CREATE VIEW recent_alerts AS
SELECT * FROM alerts
WHERE timestamp > datetime('now', '-24 hours')
ORDER BY timestamp DESC;

CREATE VIEW latest_gps_position AS
SELECT * FROM gps_history
ORDER BY timestamp DESC
LIMIT 1;
