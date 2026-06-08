#!/usr/bin/env python3
"""
Web Dashboard Backend - Flask Application

REST API and web interface for Airspace Guard
"""

import logging
import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app)

# Global detector instances
drone_detector = None
ads_b_provider = None


def initialize_detectors(detector, provider):
    """Initialize detector instances"""
    global drone_detector, ads_b_provider
    drone_detector = detector
    ads_b_provider = provider


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get system status"""
    status = {'timestamp': datetime.utcnow().isoformat(), 'running': True, 'components': {}}
    
    if drone_detector:
        status['components']['drone_detector'] = drone_detector.get_statistics()
    if ads_b_provider:
        status['components']['ads_b'] = ads_b_provider.get_statistics()
    
    return jsonify(status)


@app.route('/api/drones')
def api_drones():
    """Get detected drones"""
    if not drone_detector:
        return jsonify({'drones': [], 'error': 'Drone detector not initialized'}), 503
    
    active_only = request.args.get('active', 'true').lower() == 'true'
    timeout_seconds = int(request.args.get('timeout', 30))
    
    drones = drone_detector.get_active_drones(timeout_seconds) if active_only else drone_detector.get_all_detections()
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'drones': [d.to_dict() for d in drones],
        'count': len(drones),
    })


@app.route('/api/drones/closest')
def api_drones_closest():
    """Get closest detected drones"""
    if not drone_detector:
        return jsonify({'drones': [], 'error': 'Drone detector not initialized'}), 503
    
    count = int(request.args.get('count', 5))
    drones = drone_detector.get_closest_drones(count)
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'drones': [d.to_dict() for d in drones],
        'count': len(drones),
    })


@app.route('/api/drones/stats')
def api_drones_stats():
    """Get drone detection statistics"""
    if not drone_detector:
        return jsonify({}, 503)
    return jsonify(drone_detector.get_statistics())


@app.route('/api/aircraft')
def api_aircraft():
    """Get detected aircraft"""
    if not ads_b_provider:
        return jsonify({'aircraft': [], 'error': 'ADS-B provider not initialized'}), 503
    
    active_only = request.args.get('active', 'true').lower() == 'true'
    max_age = int(request.args.get('max_age', 60))
    max_range = float(request.args.get('max_range', 999))
    
    if active_only:
        aircraft = ads_b_provider.get_active_aircraft(max_age)
        aircraft = [ac for ac in aircraft if ac.range_miles is None or ac.range_miles <= max_range]
    else:
        aircraft = list(ads_b_provider.aircraft.values())
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'aircraft': [ac.to_dict() for ac in aircraft],
        'count': len(aircraft),
    })


@app.route('/api/aircraft/proximity')
def api_aircraft_proximity():
    """Get aircraft in proximity"""
    if not ads_b_provider:
        return jsonify({'aircraft': []}, 503)
    
    proximity_distance = float(request.args.get('distance', 10))
    proximity_altitude = int(request.args.get('altitude', 500))
    
    nearby = ads_b_provider.get_aircraft_in_range(proximity_distance)
    low_altitude = ads_b_provider.get_aircraft_below_altitude(proximity_altitude)
    threat_aircraft = list(set(nearby + low_altitude))
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'proximity_distance_miles': proximity_distance,
        'proximity_altitude_feet': proximity_altitude,
        'aircraft': [ac.to_dict() for ac in threat_aircraft],
        'count': len(threat_aircraft),
    })


@app.route('/api/detections')
def api_detections():
    """Get combined detections"""
    detections = {'timestamp': datetime.utcnow().isoformat(), 'drones': [], 'aircraft': []}
    
    if drone_detector:
        active_drones = drone_detector.get_active_drones()
        detections['drones'] = [d.to_dict() for d in active_drones]
    
    if ads_b_provider:
        active_aircraft = ads_b_provider.get_active_aircraft()
        detections['aircraft'] = [ac.to_dict() for ac in active_aircraft]
    
    return jsonify(detections)


@app.route('/api/health')
def api_health():
    """Health check"""
    health = {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'drone_detector': 'ok' if drone_detector and drone_detector.running else 'offline',
            'ads_b_provider': 'ok' if ads_b_provider and ads_b_provider.running else 'offline',
        },
    }
    return jsonify(health)


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=8000, debug=False)
