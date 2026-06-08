#!/usr/bin/env python3
"""
Main Airspace Guard Application

Orchestrates all components:
- WiFi drone detection (AC1200)
- ADS-B aircraft tracking (RTL-SDR)
- GPS geolocation (AIoV2 GPS)
- Web dashboard (Flask)
- Alert system
- Database logging
"""

import logging
import logging.handlers
import os
import sys
import signal
import yaml
import sqlite3
import threading
from typing import Dict, Optional
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from drone_detector import DroneDetector
from ads_b_provider import ADS_BProvider

# Configure logging
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            '/var/log/airspace-guard.log',
            maxBytes=10485760,
            backupCount=5
        )
    ]
)

logger = logging.getLogger(__name__)


class AirspaceGuard:
    """Main application orchestrator"""

    def __init__(self, config_path: str = '/etc/airspace-guard/config.yaml'):
        """Initialize Airspace Guard"""
        self.config = self._load_config(config_path)
        self.running = False
        
        # Initialize components
        self.drone_detector = None
        self.ads_b_provider = None
        self.db_path = self.config['system']['database']
        
        # Setup database
        self._init_database()
        
        logger.info("Airspace Guard initialized")

    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration"""
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            return self._get_default_config()
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'system': {'log_level': 'INFO', 'database': '/var/lib/airspace-guard/airspace.db'},
            'wifi': {'enabled': True, 'interface': 'wlan0', 'channels': [1, 6, 11], 'rssi_threshold': -85},
            'ads_b': {'enabled': True, 'host': '127.0.0.1', 'port': 30003, 'max_range': 150},
            'gps': {'enabled': True, 'device': '/dev/ttyUSB0'},
            'web': {'enabled': True, 'host': '0.0.0.0', 'port': 8000},
        }

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            conn.close()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def start(self) -> bool:
        """Start Airspace Guard"""
        if self.running:
            logger.warning("Airspace Guard already running")
            return False
        
        try:
            logger.info("Starting Airspace Guard...")
            
            if self.config['wifi']['enabled']:
                try:
                    self.drone_detector = DroneDetector(
                        interface=self.config['wifi']['interface'],
                        channels=self.config['wifi'].get('channels', [1, 6, 11]),
                        rssi_threshold=self.config['wifi'].get('rssi_threshold', -85)
                    )
                    if self.drone_detector.start():
                        logger.info("WiFi drone detector started")
                except Exception as e:
                    logger.error(f"Error starting drone detector: {e}")
            
            if self.config['ads_b']['enabled']:
                try:
                    self.ads_b_provider = ADS_BProvider(
                        host=self.config['ads_b']['host'],
                        port=self.config['ads_b']['port'],
                        max_range_miles=self.config['ads_b'].get('max_range', 150)
                    )
                    if self.ads_b_provider.start():
                        logger.info("ADS-B provider started")
                except Exception as e:
                    logger.error(f"Error starting ADS-B provider: {e}")
            
            self.running = True
            logger.info("Airspace Guard started successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start Airspace Guard: {e}")
            return False

    def stop(self) -> bool:
        """Stop Airspace Guard"""
        if not self.running:
            return True
        
        try:
            logger.info("Stopping Airspace Guard...")
            if self.drone_detector:
                self.drone_detector.stop()
            if self.ads_b_provider:
                self.ads_b_provider.stop()
            self.running = False
            logger.info("Airspace Guard stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping Airspace Guard: {e}")
            return False

    def get_detections(self) -> Dict:
        """Get current detections (drones + aircraft)"""
        detections = {'timestamp': datetime.utcnow().isoformat(), 'drones': [], 'aircraft': []}
        
        if self.drone_detector:
            active_drones = self.drone_detector.get_active_drones()
            detections['drones'] = [d.to_dict() for d in active_drones]
        
        if self.ads_b_provider:
            active_aircraft = self.ads_b_provider.get_active_aircraft()
            detections['aircraft'] = [ac.to_dict() for ac in active_aircraft]
        
        return detections


def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("Airspace Guard - Local Airspace Monitoring System")
    logger.info("="*60)
    
    app = AirspaceGuard()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        app.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    if not app.start():
        logger.error("Failed to start application")
        sys.exit(1)
    
    try:
        while app.running:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        app.stop()
    
    logger.info("Airspace Guard exited")


if __name__ == '__main__':
    main()
