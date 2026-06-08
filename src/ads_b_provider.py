#!/usr/bin/env python3
"""
ADS-B Aircraft Data Provider

Real-time aircraft tracking via ADS-B transponder signals.
Connects to readsb (or dump1090) to receive aircraft data.
"""

import logging
import json
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class AircraftPosition:
    """Aircraft position and telemetry data"""
    icao: str                      # Aircraft ICAO hex code
    callsign: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_ft: Optional[int] = None
    speed_knots: Optional[int] = None
    heading_deg: Optional[float] = None
    vertical_rate_ft_min: Optional[int] = None
    squawk: Optional[str] = None
    
    # Derived/computed fields
    last_update: datetime = field(default_factory=datetime.utcnow)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    seen_count: int = 0
    
    # Distance/bearing from observer
    range_miles: Optional[float] = None
    bearing_deg: Optional[float] = None
    altitude_diff_ft: Optional[int] = None
    
    def is_recent(self, seconds: int = 60) -> bool:
        """Check if data is recent"""
        elapsed = (datetime.utcnow() - self.last_update).total_seconds()
        return elapsed < seconds
    
    def has_position(self) -> bool:
        """Check if we have valid position data"""
        return (self.latitude is not None and 
                self.longitude is not None and 
                self.altitude_ft is not None)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON"""
        return {
            'icao': self.icao,
            'callsign': self.callsign,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude_ft': self.altitude_ft,
            'speed_knots': self.speed_knots,
            'heading_deg': self.heading_deg,
            'vertical_rate_ft_min': self.vertical_rate_ft_min,
            'squawk': self.squawk,
            'last_update': self.last_update.isoformat(),
            'range_miles': self.range_miles,
            'bearing_deg': self.bearing_deg,
        }


class ADS_BProvider:
    """Real-time aircraft data provider via ADS-B"""

    def __init__(self, host: str = "127.0.0.1", port: int = 30003,
                 timeout: int = 5, max_range_miles: float = 150):
        """
        Initialize ADS-B provider
        
        Args:
            host: readsb host (default localhost)
            port: readsb raw JSON port (default 30003)
            timeout: Connection timeout in seconds
            max_range_miles: Maximum range to track aircraft
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_range_miles = max_range_miles
        
        self.aircraft: Dict[str, AircraftPosition] = {}
        self.running = False
        self.listen_thread = None
        self.socket = None
        
        self.lock = threading.Lock()
        self.observer_lat = None
        self.observer_lon = None
        self.observer_alt_ft = None
        
        logger.info(f"ADS-B Provider initialized: {host}:{port}")

    def set_observer_location(self, latitude: float, longitude: float,
                             altitude_ft: float = 0):
        """Set observer location for distance calculations"""
        self.observer_lat = latitude
        self.observer_lon = longitude
        self.observer_alt_ft = altitude_ft
        logger.info(f"Observer location set: {latitude}, {longitude}, {altitude_ft}ft")

    def start(self) -> bool:
        """Start listening for ADS-B data"""
        if self.running:
            logger.warning("ADS-B provider already running")
            return False
        
        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info("ADS-B provider started")
        return True

    def stop(self) -> bool:
        """Stop listening for ADS-B data"""
        if not self.running:
            return True
        
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        if self.listen_thread:
            self.listen_thread.join(timeout=5)
        
        logger.info("ADS-B provider stopped")
        return True

    def _listen_loop(self):
        """Main listening loop"""
        logger.info(f"Starting ADS-B listener on {self.host}:{self.port}")
        
        reconnect_delay = 1
        max_reconnect_delay = 30
        
        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self.socket.connect((self.host, self.port))
                logger.info(f"Connected to ADS-B provider at {self.host}:{self.port}")
                reconnect_delay = 1
                
                # Read data
                while self.running:
                    try:
                        data = self.socket.recv(4096).decode('utf-8')
                        if not data:
                            break
                        
                        # readsb sends JSON objects separated by newlines
                        for line in data.strip().split('\n'):
                            if line:
                                try:
                                    msg = json.loads(line)
                                    self._process_message(msg)
                                except json.JSONDecodeError:
                                    pass
                    
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.debug(f"Error reading from socket: {e}")
                        break
            
            except ConnectionRefusedError:
                logger.warning(f"Connection refused - readsb may not be running")
            except socket.timeout:
                logger.debug("Connection timeout")
            except Exception as e:
                logger.error(f"Connection error: {e}")
            
            finally:
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
            
            # Reconnect with exponential backoff
            if self.running:
                logger.info(f"Reconnecting in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    def _process_message(self, msg: Dict):
        """Process ADS-B message from readsb"""
        try:
            # readsb message format
            icao = msg.get('hex')
            if not icao:
                return
            
            icao = icao.upper()
            
            with self.lock:
                if icao not in self.aircraft:
                    self.aircraft[icao] = AircraftPosition(icao=icao)
                
                ac = self.aircraft[icao]
                ac.last_update = datetime.utcnow()
                ac.seen_count += 1
                
                # Update fields
                if 'flight' in msg and msg['flight']:
                    ac.callsign = msg['flight'].strip()
                if 'lat' in msg:
                    ac.latitude = msg['lat']
                if 'lon' in msg:
                    ac.longitude = msg['lon']
                if 'alt_baro' in msg:
                    ac.altitude_ft = int(msg['alt_baro'])
                elif 'alt_geom' in msg:
                    ac.altitude_ft = int(msg['alt_geom'])
                if 'gs' in msg:
                    ac.speed_knots = int(msg['gs'])
                if 'track' in msg:
                    ac.heading_deg = msg['track']
                if 'baro_rate' in msg:
                    ac.vertical_rate_ft_min = int(msg['baro_rate'])
                elif 'geom_rate' in msg:
                    ac.vertical_rate_ft_min = int(msg['geom_rate'])
                if 'squawk' in msg:
                    ac.squawk = msg['squawk']
                
                # Calculate distance if we have position
                if (ac.has_position() and self.observer_lat and self.observer_lon):
                    dist = self._calculate_distance(
                        self.observer_lat, self.observer_lon,
                        ac.latitude, ac.longitude
                    )
                    ac.range_miles = dist
                    
                    # Filter by range
                    if dist > self.max_range_miles:
                        if ac.seen_count > 5:  # Keep brief glimpses
                            with self.lock:
                                if icao in self.aircraft:
                                    del self.aircraft[icao]
                    
                    # Calculate bearing
                    ac.bearing_deg = self._calculate_bearing(
                        self.observer_lat, self.observer_lon,
                        ac.latitude, ac.longitude
                    )
                    
                    # Altitude difference
                    if self.observer_alt_ft is not None:
                        ac.altitude_diff_ft = ac.altitude_ft - self.observer_alt_ft
        
        except Exception as e:
            logger.debug(f"Error processing ADS-B message: {e}")

    def _calculate_distance(self, lat1: float, lon1: float,
                           lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        R = 3959  # Earth radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    def _calculate_bearing(self, lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2"""
        import math
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        x = (math.sin(delta_lon) * math.cos(lat2_rad))
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
        
        bearing_rad = math.atan2(x, y)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360

    def get_active_aircraft(self, max_age_seconds: int = 60) -> List[AircraftPosition]:
        """Get list of currently active aircraft"""
        with self.lock:
            return [
                ac for ac in self.aircraft.values()
                if ac.is_recent(max_age_seconds)
            ]

    def get_aircraft_in_range(self, max_distance_miles: float = 10) -> List[AircraftPosition]:
        """Get aircraft within specified distance"""
        with self.lock:
            return [
                ac for ac in self.aircraft.values()
                if (ac.range_miles is not None and
                    ac.range_miles <= max_distance_miles and
                    ac.is_recent())
            ]

    def get_aircraft_below_altitude(self, altitude_ft: int) -> List[AircraftPosition]:
        """Get aircraft below specified altitude"""
        with self.lock:
            return [
                ac for ac in self.aircraft.values()
                if (ac.altitude_ft is not None and
                    ac.altitude_ft <= altitude_ft and
                    ac.is_recent())
            ]

    def get_aircraft_by_callsign(self, callsign: str) -> Optional[AircraftPosition]:
        """Get aircraft by callsign"""
        with self.lock:
            for ac in self.aircraft.values():
                if ac.callsign and callsign.upper() in ac.callsign.upper():
                    return ac
        return None

    def get_statistics(self) -> Dict:
        """Get provider statistics"""
        with self.lock:
            active = [ac for ac in self.aircraft.values() if ac.is_recent()]
            return {
                'total_aircraft_tracked': len(self.aircraft),
                'active_aircraft': len(active),
                'observer_location': {
                    'latitude': self.observer_lat,
                    'longitude': self.observer_lon,
                    'altitude_ft': self.observer_alt_ft,
                },
                'running': self.running,
            }
