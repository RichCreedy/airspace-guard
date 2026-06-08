#!/usr/bin/env python3
"""
DJI Drone Signatures Database

Comprehensive database of DJI drone MAC addresses, SSID patterns, and beacon signatures
for identification and classification. Supports:
- DJI Mini 4
- DJI Avata 360
- DJI Neo / Neo 2
- Other DJI consumer drones
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DroneType(Enum):
    """DJI Drone model classifications"""
    MINI_4 = "DJI_MINI_4"
    MINI_3 = "DJI_MINI_3"
    AVATA_360 = "DJI_AVATA_360"
    AVATA_V1 = "DJI_AVATA_V1"
    NEO = "DJI_NEO"
    NEO_2 = "DJI_NEO_2"
    MAVIC_3 = "DJI_MAVIC_3"
    MAVIC_AIR_3 = "DJI_MAVIC_AIR_3"
    PHANTOM_4 = "DJI_PHANTOM_4"
    INSPIRE_3 = "DJI_INSPIRE_3"
    UNKNOWN_DJI = "DJI_UNKNOWN"
    NOT_DJI = "NOT_DJI"


class ProtocolType(Enum):
    """DJI transmission protocols"""
    OCUSYNC = "OcuSync"          # Standard DJI control protocol
    OCUSYNC_3 = "OcuSync 3"      # Improved version
    OCUSYNC_3_PLUS = "OcuSync 3+"# Newest variant
    LIGHTBRIDGE = "LightBridge"  # Older DJI protocol
    OCUSYNC_3_ENTERPRISE = "OcuSync 3 Enterprise"
    NATIVE_2_4GHZ = "2.4GHz Native"
    NATIVE_5_8GHZ = "5.8GHz Native"


@dataclass
class DroneSignature:
    """Single DJI drone signature record"""
    drone_type: DroneType
    mac_prefix: str              # First 3 octets (e.g., "60:60:1F")
    ssid_pattern: Optional[str]  # Regex pattern for SSID
    protocol: ProtocolType
    frequencies: List[int]       # MHz frequencies used
    control_freq: int            # Primary control frequency (MHz)
    video_freq: int              # Primary video transmission (MHz)
    beacon_interval: int         # ms - WiFi beacon broadcast interval
    typical_power: int           # dBm - typical transmit power
    notes: str


class DJISignatureDatabase:
    """DJI drone signature matching and identification"""

    def __init__(self):
        """Initialize DJI signature database"""
        self.signatures: List[DroneSignature] = self._build_database()
        self.mac_prefix_map = self._build_mac_map()
        self.ssid_patterns = self._build_ssid_patterns()

    def _build_database(self) -> List[DroneSignature]:
        """Build comprehensive DJI signature database"""
        return [
            # DJI Mini 4 Pro
            DroneSignature(
                drone_type=DroneType.MINI_4,
                mac_prefix="28:6C:07",
                ssid_pattern=r"DJI_MINI",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240, 5745, 5800],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=17,
                notes="DJI Mini 4 Pro - Compact drone with 4K camera"
            ),

            # DJI Mini 3 / Mini 3 Pro
            DroneSignature(
                drone_type=DroneType.MINI_3,
                mac_prefix="28:6C:07",
                ssid_pattern=r"DJI_MINI",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240, 5745, 5800],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=17,
                notes="DJI Mini 3 series"
            ),

            # DJI Avata 2 (FPV)
            DroneSignature(
                drone_type=DroneType.AVATA_360,
                mac_prefix="90:3A:E6",
                ssid_pattern=r"DJI_AVATA|Avata",
                protocol=ProtocolType.OCUSYNC_3_PLUS,
                frequencies=[2400, 2450, 5180, 5240, 5745, 5800],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=20,
                notes="DJI Avata 2 - FPV racing drone with 360° camera"
            ),

            # DJI Avata V1 (original FPV)
            DroneSignature(
                drone_type=DroneType.AVATA_V1,
                mac_prefix="3C:15:C2",
                ssid_pattern=r"DJI_AVATA|Avata_v1",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240, 5745],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=18,
                notes="DJI Avata V1 - First generation FPV drone"
            ),

            # DJI Neo
            DroneSignature(
                drone_type=DroneType.NEO,
                mac_prefix="60:60:1F",
                ssid_pattern=r"DJI_NEO",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240],
                control_freq=2400,
                video_freq=2400,
                beacon_interval=100,
                typical_power=10,
                notes="DJI Neo - Ultra-compact drone"
            ),

            # DJI Neo 2
            DroneSignature(
                drone_type=DroneType.NEO_2,
                mac_prefix="60:60:1F",
                ssid_pattern=r"DJI_NEO|Neo_2",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240],
                control_freq=2400,
                video_freq=2400,
                beacon_interval=100,
                typical_power=10,
                notes="DJI Neo 2 - Upgraded compact drone"
            ),

            # DJI Mavic 3 / 3 Classic
            DroneSignature(
                drone_type=DroneType.MAVIC_3,
                mac_prefix="3C:15:C2",
                ssid_pattern=r"DJI_MAVIC",
                protocol=ProtocolType.OCUSYNC_3_ENTERPRISE,
                frequencies=[2400, 2450, 5180, 5240, 5745, 5800],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=20,
                notes="DJI Mavic 3 series - Professional cine camera"
            ),

            # DJI Air 3 / Air 3S
            DroneSignature(
                drone_type=DroneType.MAVIC_AIR_3,
                mac_prefix="94:2F:C6",
                ssid_pattern=r"DJI_AIR",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240, 5745, 5800],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=18,
                notes="DJI Air 3 series - Mid-range prosumer drone"
            ),

            # DJI Phantom 4 Pro / V2.0
            DroneSignature(
                drone_type=DroneType.PHANTOM_4,
                mac_prefix="60:60:1F",
                ssid_pattern=r"Phantom_4",
                protocol=ProtocolType.OCUSYNC_3,
                frequencies=[2400, 2450, 5180, 5240],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=20,
                notes="DJI Phantom 4 Pro - Professional mapping drone"
            ),

            # DJI Inspire 3
            DroneSignature(
                drone_type=DroneType.INSPIRE_3,
                mac_prefix="60:60:1F",
                ssid_pattern=r"DJI_INSPIRE",
                protocol=ProtocolType.OCUSYNC_3_ENTERPRISE,
                frequencies=[2400, 2450, 5180, 5240, 5745, 5800],
                control_freq=2400,
                video_freq=5800,
                beacon_interval=100,
                typical_power=20,
                notes="DJI Inspire 3 - Enterprise cinema drone"
            ),
        ]

    def _build_mac_map(self) -> Dict[str, List[DroneSignature]]:
        """Build MAC address prefix to signatures map"""
        mac_map = {}
        for sig in self.signatures:
            if sig.mac_prefix not in mac_map:
                mac_map[sig.mac_prefix] = []
            mac_map[sig.mac_prefix].append(sig)
        return mac_map

    def _build_ssid_patterns(self) -> List[Tuple[str, DroneSignature]]:
        """Build SSID regex patterns"""
        patterns = []
        for sig in self.signatures:
            if sig.ssid_pattern:
                patterns.append((sig.ssid_pattern, sig))
        return patterns

    def identify_by_mac(self, mac_address: str) -> Optional[DroneType]:
        """
        Identify drone by MAC address prefix
        
        Args:
            mac_address: Full MAC address (e.g., "28:6C:07:AB:CD:EF")
        
        Returns:
            DroneType if identified, None otherwise
        """
        if not mac_address or len(mac_address) < 8:
            return None

        # Extract prefix (first 3 octets)
        prefix = ":".join(mac_address.split(":")[:3]).upper()

        if prefix in self.mac_prefix_map:
            # Return most common/likely model for this prefix
            sigs = self.mac_prefix_map[prefix]
            # Prioritize known models
            for drone_type in [DroneType.MINI_4, DroneType.AVATA_360, DroneType.NEO_2]:
                for sig in sigs:
                    if sig.drone_type == drone_type:
                        return drone_type
            # Return first match if no priority match
            return sigs[0].drone_type

        return None

    def identify_by_ssid(self, ssid: str) -> Optional[DroneType]:
        """
        Identify drone by WiFi SSID using regex patterns
        
        Args:
            ssid: WiFi SSID string
        
        Returns:
            DroneType if identified, None otherwise
        """
        if not ssid:
            return None

        for pattern, sig in self.ssid_patterns:
            if re.search(pattern, ssid, re.IGNORECASE):
                return sig.drone_type

        return None

    def identify_by_beacon(self, beacon_data: Dict) -> Tuple[Optional[DroneType], float]:
        """
        Identify drone by WiFi beacon frame analysis
        Analyzes beacon interval, power levels, and other characteristics
        
        Args:
            beacon_data: Dictionary with beacon information
                - beacon_interval: ms
                - tx_power: dBm
                - supported_rates: List of rates
                - ht_info: HT capability info
                - vht_info: VHT capability info
        
        Returns:
            Tuple of (DroneType, confidence_score 0.0-1.0)
        """
        confidence = 0.0
        best_match = None

        beacon_interval = beacon_data.get('beacon_interval', 0)
        tx_power = beacon_data.get('tx_power', 0)

        # Standard DJI beacon interval is ~100ms
        if 90 <= beacon_interval <= 110:
            confidence += 0.3

        # DJI drones typically transmit at medium power
        if 10 <= tx_power <= 20:
            confidence += 0.2

        # Check supported data rates (DJI-specific patterns)
        rates = beacon_data.get('supported_rates', [])
        if len(rates) >= 8:  # DJI typically supports many rates
            confidence += 0.2

        # Check HT/VHT capabilities (802.11n/ac support)
        if beacon_data.get('ht_info') or beacon_data.get('vht_info'):
            confidence += 0.2

        # If confidence is high enough, it's likely DJI
        if confidence >= 0.7:
            return (DroneType.UNKNOWN_DJI, min(confidence, 1.0))

        return (None, confidence)

    def get_all_dji_mac_prefixes(self) -> List[str]:
        """Get list of all known DJI MAC address prefixes"""
        return list(self.mac_prefix_map.keys())

    def get_all_dji_ssid_patterns(self) -> List[str]:
        """Get list of all known DJI SSID patterns"""
        return [pattern for pattern, _ in self.ssid_patterns]

    def get_drone_info(self, drone_type: DroneType) -> Optional[DroneSignature]:
        """Get detailed information about a drone type"""
        for sig in self.signatures:
            if sig.drone_type == drone_type:
                return sig
        return None

    def is_known_dji_mac(self, mac_address: str) -> bool:
        """Check if MAC address is known DJI prefix"""
        prefix = ":".join(mac_address.split(":")[:3]).upper()
        return prefix in self.mac_prefix_map

    def classify_signal_strength(self, rssi_dbm: float) -> str:
        """
        Classify signal strength for distance estimation
        
        Args:
            rssi_dbm: Signal strength in dBm (typically -30 to -95)
        
        Returns:
            String classification
        """
        if rssi_dbm >= -50:
            return "VERY_CLOSE"
        elif rssi_dbm >= -60:
            return "CLOSE"
        elif rssi_dbm >= -70:
            return "MEDIUM"
        elif rssi_dbm >= -80:
            return "FAR"
        else:
            return "VERY_FAR"

    def estimate_distance_meters(self, rssi_dbm: float, tx_power_dbm: int = 17,
                                path_loss_exponent: float = 2.0) -> float:
        """
        Estimate distance from drone based on RSSI using free-space path loss model
        
        Formula: Distance = 10^((TX_Power - RSSI - 20*log10(f)) / (10 * n))
        where f = frequency (MHz), n = path loss exponent
        
        Args:
            rssi_dbm: Received signal strength in dBm
            tx_power_dbm: Transmit power in dBm (default 17 for DJI)
            path_loss_exponent: Path loss exponent (2.0 for free space, 2.5-3.5 for indoor)
        
        Returns:
            Distance in meters
        """
        import math

        # 2.4 GHz frequency (most common for DJI)
        frequency_mhz = 2400

        # Free space path loss at 1 meter
        free_space_loss = 20 * math.log10(frequency_mhz) + 20 * math.log10(1) - 27.55

        # Calculate path loss
        path_loss = tx_power_dbm - rssi_dbm

        # Calculate distance
        if path_loss <= free_space_loss:
            distance_m = 1.0
        else:
            distance_m = 10 ** ((path_loss - free_space_loss) / (10 * path_loss_exponent))

        return max(distance_m, 0.5)  # Minimum 0.5m

    def estimate_distance_miles(self, rssi_dbm: float, **kwargs) -> float:
        """Estimate distance in miles (wrapper around estimate_distance_meters)"""
        meters = self.estimate_distance_meters(rssi_dbm, **kwargs)
        return meters * 0.000621371  # Convert meters to miles


# Global instance
_db = None


def get_signature_database() -> DJISignatureDatabase:
    """Get or create singleton instance of signature database"""
    global _db
    if _db is None:
        _db = DJISignatureDatabase()
    return _db
