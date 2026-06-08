#!/usr/bin/env python3
"""
Drone Detection Engine

WiFi monitor mode packet capture and analysis for detecting nearby drones.
Focuses on DJI drones but can identify other manufacturers.

Key Functions:
- WiFi beacon frame parsing
- MAC address-based drone identification
- RSSI signal strength analysis
- Distance and direction estimation
- Real-time drone tracking
"""

import logging
import threading
import time
import subprocess
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

try:
    from scapy.all import (
        sniff, Dot11, Dot11Beacon, Dot11Elt, Dot11ProbeResp,
        get_if_raw_hwaddr, get_windows_if_list
    )
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available - WiFi scanning disabled")

from dji_signatures import get_signature_database, DroneType


logger = logging.getLogger(__name__)


@dataclass
class DroneDetection:
    """A detected drone instance"""
    mac_address: str
    ssid: Optional[str] = None
    drone_type: Optional[DroneType] = None
    last_seen: datetime = field(default_factory=datetime.utcnow)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    rssi_samples: List[float] = field(default_factory=list)
    confidence: float = 0.0
    
    # Geolocation
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    estimated_distance_m: Optional[float] = None
    estimated_distance_miles: Optional[float] = None
    
    # Tracking
    packet_count: int = 0
    last_channel: Optional[int] = None
    
    def get_avg_rssi(self) -> float:
        """Get average RSSI from samples"""
        if not self.rssi_samples:
            return 0.0
        return sum(self.rssi_samples) / len(self.rssi_samples)
    
    def get_last_rssi(self) -> float:
        """Get most recent RSSI sample"""
        if self.rssi_samples:
            return self.rssi_samples[-1]
        return 0.0
    
    def is_active(self, timeout_seconds: int = 30) -> bool:
        """Check if drone is still actively transmitting"""
        elapsed = (datetime.utcnow() - self.last_seen).total_seconds()
        return elapsed < timeout_seconds
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'mac_address': self.mac_address,
            'ssid': self.ssid,
            'drone_type': self.drone_type.value if self.drone_type else None,
            'last_seen': self.last_seen.isoformat(),
            'first_seen': self.first_seen.isoformat(),
            'avg_rssi_dbm': self.get_avg_rssi(),
            'last_rssi_dbm': self.get_last_rssi(),
            'confidence': self.confidence,
            'estimated_distance_m': self.estimated_distance_m,
            'estimated_distance_miles': self.estimated_distance_miles,
            'packet_count': self.packet_count,
            'is_active': self.is_active(),
        }


class DroneDetector:
    """WiFi monitor mode drone detection engine"""

    def __init__(self, interface: str = "wlan0", channels: List[int] = None,
                 dwell_time_ms: int = 100, rssi_threshold: float = -85):
        """
        Initialize drone detector
        
        Args:
            interface: WiFi interface in monitor mode
            channels: List of WiFi channels to scan
            dwell_time_ms: Milliseconds to spend on each channel
            rssi_threshold: Minimum signal strength to detect
        """
        self.interface = interface
        self.channels = channels or [1, 6, 11, 36, 40, 44, 48, 149, 153, 157, 161, 165]
        self.dwell_time_ms = dwell_time_ms
        self.rssi_threshold = rssi_threshold
        
        self.detected_drones: Dict[str, DroneDetection] = {}
        self.running = False
        self.scan_thread = None
        self.packet_count = 0
        self.last_channel = None
        
        self.dji_db = get_signature_database()
        
        # Locks for thread safety
        self.lock = threading.Lock()
        
        logger.info(f"DroneDetector initialized on interface {interface}")

    def start(self) -> bool:
        """
        Start WiFi scanning in background thread
        
        Returns:
            True if successfully started
        """
        if not SCAPY_AVAILABLE:
            logger.error("Scapy not available - cannot start detector")
            return False
        
        if self.running:
            logger.warning("Detector already running")
            return False
        
        # Verify interface is in monitor mode
        if not self._verify_monitor_mode():
            logger.error(f"Interface {self.interface} not in monitor mode")
            return False
        
        self.running = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("Drone detector started")
        return True

    def stop(self) -> bool:
        """
        Stop WiFi scanning
        
        Returns:
            True if successfully stopped
        """
        if not self.running:
            return True
        
        self.running = False
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
        
        logger.info("Drone detector stopped")
        return True

    def _verify_monitor_mode(self) -> bool:
        """Check if interface is in monitor mode"""
        try:
            result = subprocess.run(
                ["iwconfig", self.interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "Monitor" in result.stdout
        except Exception as e:
            logger.error(f"Failed to verify monitor mode: {e}")
            return False

    def _set_channel(self, channel: int) -> bool:
        """Set WiFi interface to specific channel"""
        try:
            subprocess.run(
                ["iwconfig", self.interface, "channel", str(channel)],
                capture_output=True,
                timeout=2
            )
            self.last_channel = channel
            return True
        except Exception as e:
            logger.warning(f"Failed to set channel {channel}: {e}")
            return False

    def _scan_loop(self):
        """Main scanning loop - runs in background thread"""
        logger.info("Starting WiFi scan loop")
        
        while self.running:
            for channel in self.channels:
                if not self.running:
                    break
                
                # Set channel
                if not self._set_channel(channel):
                    continue
                
                # Capture packets on this channel
                try:
                    sniff(
                        iface=self.interface,
                        prn=self._packet_handler,
                        timeout=self.dwell_time_ms / 1000.0,
                        store=False
                    )
                except Exception as e:
                    logger.debug(f"Sniff error on channel {channel}: {e}")
                    continue

    def _packet_handler(self, packet):
        """Process captured WiFi packet"""
        try:
            if not packet.haslayer(Dot11):
                return
            
            self.packet_count += 1
            
            # Extract MAC address
            mac_addr = packet[Dot11].addr2
            if not mac_addr or mac_addr == "ff:ff:ff:ff:ff:ff":
                return
            
            # Get RSSI
            try:
                rssi = -(256 - ord(packet.notdecoded[-2:-1]))
            except:
                rssi = 0
            
            if rssi < self.rssi_threshold:
                return
            
            # Look for beacon or probe response
            ssid = None
            if packet.haslayer(Dot11Beacon):
                beacon = packet[Dot11Beacon]
                ssid = self._extract_ssid(beacon)
            elif packet.haslayer(Dot11ProbeResp):
                probe = packet[Dot11ProbeResp]
                ssid = self._extract_ssid(probe)
            
            # Update or create drone detection
            self._update_detection(mac_addr, ssid, rssi)
        
        except Exception as e:
            logger.debug(f"Error processing packet: {e}")

    def _extract_ssid(self, layer) -> Optional[str]:
        """Extract SSID from beacon/probe response"""
        try:
            for elt in layer.elt:
                if elt.ID == 0:  # SSID element
                    return elt.info.decode('utf-8', errors='ignore')
        except:
            pass
        return None

    def _update_detection(self, mac_addr: str, ssid: Optional[str], rssi: float):
        """Update or create drone detection"""
        with self.lock:
            mac_upper = mac_addr.upper()
            
            if mac_upper not in self.detected_drones:
                # New detection
                drone = DroneDetection(mac_address=mac_upper, ssid=ssid)
                self.detected_drones[mac_upper] = drone
            else:
                drone = self.detected_drones[mac_upper]
            
            # Update detection
            drone.last_seen = datetime.utcnow()
            drone.packet_count += 1
            drone.last_channel = self.last_channel
            
            # Keep last 10 RSSI samples for averaging
            drone.rssi_samples.append(rssi)
            if len(drone.rssi_samples) > 10:
                drone.rssi_samples.pop(0)
            
            if ssid and not drone.ssid:
                drone.ssid = ssid
            
            # Try to identify drone
            if not drone.drone_type:
                # Try MAC-based identification
                drone.drone_type = self.dji_db.identify_by_mac(mac_addr)
                
                # Try SSID-based identification
                if not drone.drone_type and ssid:
                    drone.drone_type = self.dji_db.identify_by_ssid(ssid)
                
                # Calculate confidence
                if self.dji_db.is_known_dji_mac(mac_addr):
                    drone.confidence = 0.95
                elif drone.drone_type:
                    drone.confidence = 0.75
                else:
                    drone.confidence = 0.5 if drone.packet_count > 3 else 0.0
            
            # Estimate distance
            drone.estimated_distance_m = self.dji_db.estimate_distance_meters(rssi)
            drone.estimated_distance_miles = drone.estimated_distance_m * 0.000621371

    def get_active_drones(self, timeout_seconds: int = 30) -> List[DroneDetection]:
        """Get list of currently active drones"""
        with self.lock:
            return [
                d for d in self.detected_drones.values()
                if d.is_active(timeout_seconds)
            ]

    def get_all_detections(self) -> List[DroneDetection]:
        """Get all detected drones (including inactive)"""
        with self.lock:
            return list(self.detected_drones.values())

    def get_drones_by_type(self, drone_type: DroneType) -> List[DroneDetection]:
        """Get drones of specific type"""
        with self.lock:
            return [
                d for d in self.detected_drones.values()
                if d.drone_type == drone_type
            ]

    def get_closest_drones(self, count: int = 5) -> List[DroneDetection]:
        """Get N closest detected drones"""
        active = self.get_active_drones()
        if not active:
            return []
        
        # Sort by estimated distance
        sorted_drones = sorted(
            active,
            key=lambda d: d.estimated_distance_m or float('inf')
        )
        return sorted_drones[:count]

    def get_statistics(self) -> Dict:
        """Get detector statistics"""
        active = self.get_active_drones()
        all_drones = self.get_all_detections()
        
        dji_count = sum(1 for d in all_drones if d.drone_type and d.drone_type != DroneType.NOT_DJI)
        
        return {
            'total_packets': self.packet_count,
            'active_drones': len(active),
            'total_unique_drones': len(all_drones),
            'dji_drones': dji_count,
            'running': self.running,
            'interface': self.interface,
            'last_channel': self.last_channel,
        }

    def export_detections_json(self) -> str:
        """Export all detections as JSON"""
        with self.lock:
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'statistics': self.get_statistics(),
                'drones': [d.to_dict() for d in self.detected_drones.values()],
            }
        return json.dumps(data, indent=2)

    def clear_history(self):
        """Clear all detections"""
        with self.lock:
            self.detected_drones.clear()
        logger.info("Detection history cleared")
