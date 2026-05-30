"""
RG Travel Solution - Vehicle Selection Backend APIs
Complete implementation for Go-Home Requests, Trip Finding, and Auto-Assignment

This module handles:
1. Driver go-home request management (approve/reject/assign)
2. Nearest trip finding using Haversine distance calculation
3. Trip auto-assignment to drivers from go-home requests
4. Vehicle availability tracking
5. Real-time socket events for live dashboard updates
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from datetime import datetime, timedelta
import math
from decimal import Decimal
from typing import List, Dict, Tuple, Optional

# Import your existing database and models
# Adjust these imports based on your project structure
try:
    from config import db, socketio
    from models import (
        Driver, Trip, Employee, Admin, Group,
        DriverGoHomeRequest, GoHomeTripAssignment, 
        VehicleAvailability, TripProximityCache
    )
except ImportError:
    print("Note: Database models need to be created - see schema guide")
    db = None
    socketio = None

# Blueprint for vehicle selection APIs
vehicle_selection_bp = Blueprint('vehicle_selection', __name__, url_prefix='/api/v2')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2) * math.sin(delta_phi/2) + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2) * math.sin(delta_lambda/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def get_trip_start_location(trip: Dict) -> Tuple[float, float]:
    """Extract start location (pickup point) from trip data."""
    # Try multiple possible field names for latitude and longitude
    lat = trip.get('pickup_lat') or trip.get('start_lat') or trip.get('office_lat') or 19.0760
    lng = trip.get('pickup_lng') or trip.get('start_lng') or trip.get('office_lng') or 72.8777
    
    try:
        return float(lat), float(lng)
    except (ValueError, TypeError):
        return 19.0760, 72.8777  # Default Mumbai coordinates


def format_time_to_hhmm(time_str: str) -> str:
    """Format time to HH:mm format."""
    if not time_str:
        return ""
    try:
        if 'T' in time_str:  # ISO format
            return time_str.split('T')[1][:5]
        elif ':' in time_str:
            return time_str[:5]
        return time_str
    except:
        return time_str


def serialize_driver(driver: Dict) -> Dict:
    """Serialize driver data with all necessary fields."""
    return {
        'id': driver.get('id') or driver.get('driver_id'),
        'driver_id': driver.get('driver_id') or driver.get('id'),
        'driver_name': driver.get('name') or driver.get('driver_name'),
        'name': driver.get('name') or driver.get('driver_name'),
        'mobile': driver.get('mobile') or driver.get('mo_no'),
        'cab_no': driver.get('cab_no') or driver.get('cab_number'),
        'cab_number': driver.get('cab_no') or driver.get('cab_number'),
        'vehicle_type': int(driver.get('vehicle_type') or driver.get('seats') or 4),
        'status': driver.get('status') or 'available',
        'home_location_lat': float(driver.get('home_location_lat') or driver.get('home_lat') or 0),
        'home_location_lng': float(driver.get('home_location_lng') or driver.get('home_lng') or 0),
        'home_address': driver.get('home_address') or driver.get('hometown') or '',
    }


# ============================================================================
# 1. GET DRIVER GO-HOME REQUESTS
# ============================================================================

@vehicle_selection_bp.route('/drivers/go-home-requests', methods=['GET'])
@cross_origin()
def get_go_home_requests():
    """
    Retrieve all go-home requests for admin with optional filtering.
    
    Query Parameters:
    - admin_id: Filter by admin ID
    - status: Filter by status (pending, approved, rejected, assigned)
    - driver_id: Filter by specific driver
    """
    try:
        admin_id = request.args.get('admin_id')
        status = request.args.get('status')
        driver_id = request.args.get('driver_id')
        
        # This is placeholder - replace with your actual DB query
        # Example using SQLAlchemy:
        query = DriverGoHomeRequest.query
        
        if admin_id:
            query = query.filter_by(admin_id=int(admin_id))
        if status:
            query = query.filter_by(status=status)
        if driver_id:
            query = query.filter_by(driver_id=int(driver_id))
        
        requests = query.order_by(DriverGoHomeRequest.created_at.desc()).all()
        
        # Serialize with driver information
        data = []
        for req in requests:
            # Fetch driver details (adjust based on your model structure)
            driver = Driver.query.get(req.driver_id) if hasattr(Driver, 'query') else {}
            
            data.append({
                'id': req.id,
                'driver_id': req.driver_id,
                'driver_name': getattr(driver, 'name', 'Unknown'),
                'cab_number': getattr(driver, 'cab_no', 'N/A'),
                'home_location_lat': float(req.home_location_lat) if req.home_location_lat else None,
                'home_location_lng': float(req.home_location_lng) if req.home_location_lng else None,
                'home_address': req.home_address,
                'status': req.status,
                'request_reason': req.request_reason,
                'created_at': req.created_at.isoformat() if req.created_at else None,
                'approval_timestamp': req.approval_timestamp.isoformat() if req.approval_timestamp else None,
            })
        
        return jsonify({'success': True, 'data': data}), 200
    
    except Exception as e:
        print(f"Error fetching go-home requests: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# 2. APPROVE GO-HOME REQUEST
# ============================================================================

@vehicle_selection_bp.route('/drivers/go-home-requests/<int:request_id>/approve', methods=['POST'])
@cross_origin()
def approve_go_home_request(request_id: int):
    """
    Admin approves a driver's go-home request.
    After approval, the system will find nearest available trip.
    """
    try:
        data = request.get_json() or {}
        admin_id = data.get('admin_id')
        approval_notes = data.get('approval_notes', '')
        
        if not admin_id:
            return jsonify({'success': False, 'message': 'admin_id required'}), 400
        
        # Find and update the request
        gh_request = DriverGoHomeRequest.query.get(request_id)
        if not gh_request:
            return jsonify({'success': False, 'message': 'Request not found'}), 404
        
        gh_request.status = 'approved'
        gh_request.approval_timestamp = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'id': gh_request.id,
                'driver_id': gh_request.driver_id,
                'status': 'approved',
                'approval_timestamp': gh_request.approval_timestamp.isoformat(),
                'message': f'Request approved. Ready to find nearest trip for Driver ID {gh_request.driver_id}'
            }
        }), 200
    
    except Exception as e:
        print(f"Error approving go-home request: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# 3. REJECT GO-HOME REQUEST
# ============================================================================

@vehicle_selection_bp.route('/drivers/go-home-requests/<int:request_id>/reject', methods=['POST'])
@cross_origin()
def reject_go_home_request(request_id: int):
    """
    Admin rejects a driver's go-home request with optional reason.
    """
    try:
        data = request.get_json() or {}
        admin_id = data.get('admin_id')
        rejection_reason = data.get('rejection_reason', 'Admin decision')
        
        if not admin_id:
            return jsonify({'success': False, 'message': 'admin_id required'}), 400
        
        gh_request = DriverGoHomeRequest.query.get(request_id)
        if not gh_request:
            return jsonify({'success': False, 'message': 'Request not found'}), 404
        
        gh_request.status = 'rejected'
        gh_request.rejection_reason = rejection_reason
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'id': gh_request.id,
                'driver_id': gh_request.driver_id,
                'status': 'rejected',
                'rejection_reason': rejection_reason
            }
        }), 200
    
    except Exception as e:
        print(f"Error rejecting go-home request: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# 4. FIND NEAREST AVAILABLE TRIP FOR DRIVER
# ============================================================================

@vehicle_selection_bp.route('/drivers/<driver_id>/find-nearest-trip', methods=['POST'])
@cross_origin()
def find_nearest_trip_for_driver(driver_id: str):
    """
    Find the nearest available trip to a driver's home location.
    Uses Haversine distance calculation.
    
    Request body:
    {
        "home_lat": 19.1234,
        "home_lng": 72.5678,
        "trip_type": "pickup",
        "max_distance_km": 15,
        "exclude_trip_ids": [1, 2, 3],
        "admin_id": 1
    }
    """
    try:
        data = request.get_json() or {}
        home_lat = float(data.get('home_lat', 0))
        home_lng = float(data.get('home_lng', 0))
        trip_type = data.get('trip_type', 'pickup').lower()
        max_distance = float(data.get('max_distance_km', 20))
        exclude_ids = data.get('exclude_trip_ids', [])
        admin_id = data.get('admin_id')
        
        if home_lat == 0 or home_lng == 0:
            return jsonify({
                'success': False,
                'message': 'Valid home location coordinates required'
            }), 400
        
        # Query available trips
        # This is placeholder - adjust based on your trip model
        available_trips = Trip.query.filter(
            Trip.status.in_(['pending', 'assigned']),
            Trip.trip_type == trip_type,
            ~Trip.id.in_(exclude_ids) if exclude_ids else True
        ).all()
        
        # Calculate distances for each trip
        trip_distances = []
        for trip in available_trips:
            if not trip:
                continue
            
            # Get trip start location
            trip_start_lat, trip_start_lng = get_trip_start_location({
                'pickup_lat': getattr(trip, 'pickup_lat', None),
                'pickup_lng': getattr(trip, 'pickup_lng', None),
                'office_lat': getattr(trip, 'office_lat', None),
                'office_lng': getattr(trip, 'office_lng', None),
            })
            
            # Calculate distance
            dist = haversine_distance(home_lat, home_lng, trip_start_lat, trip_start_lng)
            
            if dist <= max_distance:
                trip_distances.append({
                    'trip': trip,
                    'distance': dist,
                    'trip_start_lat': trip_start_lat,
                    'trip_start_lng': trip_start_lng,
                })
        
        # Sort by distance (nearest first)
        trip_distances.sort(key=lambda x: x['distance'])
        
        if not trip_distances:
            return jsonify({
                'success': False,
                'message': f'No trips found within {max_distance} km',
                'data': []
            }), 404
        
        # Return top 3-5 options
        results = []
        for item in trip_distances[:5]:
            trip = item['trip']
            results.append({
                'trip_id': trip.id,
                'route_no': getattr(trip, 'route_no', 'N/A'),
                'distance_from_home_km': round(item['distance'], 2),
                'eta_minutes': int(item['distance'] * 1.5),  # Rough estimate: 1 km = 1.5 min
                'employee_count': len(getattr(trip, 'employees', [])) if hasattr(trip, 'employees') else 0,
                'trip_type': trip_type,
                'scheduled_time': format_time_to_hhmm(getattr(trip, 'scheduled_time', '')),
                'status': getattr(trip, 'status', 'pending'),
                'pickup_location': getattr(trip, 'office_name', 'Office'),
            })
        
        return jsonify({
            'success': True,
            'data': results
        }), 200
    
    except Exception as e:
        print(f"Error finding nearest trip: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# 5. AUTO-ASSIGN TRIP TO DRIVER (GO-HOME RESPONSE)
# ============================================================================

@vehicle_selection_bp.route('/drivers/<driver_id>/assign-go-home-trip', methods=['POST'])
@cross_origin()
def assign_go_home_trip(driver_id: str):
    """
    Auto-assign a found trip to a driver from go-home request.
    Updates go-home request status and creates assignment record.
    Emits real-time socket event to driver dashboard.
    
    Request body:
    {
        "go_home_request_id": 1,
        "trip_id": 45,
        "admin_id": 1,
        "override_original_driver": false
    }
    """
    try:
        data = request.get_json() or {}
        gh_request_id = data.get('go_home_request_id')
        trip_id = data.get('trip_id')
        admin_id = data.get('admin_id')
        override_driver = data.get('override_original_driver', False)
        
        if not all([gh_request_id, trip_id, admin_id]):
            return jsonify({
                'success': False,
                'message': 'go_home_request_id, trip_id, and admin_id required'
            }), 400
        
        # Get the go-home request
        gh_request = DriverGoHomeRequest.query.get(gh_request_id)
        if not gh_request:
            return jsonify({'success': False, 'message': 'Go-home request not found'}), 404
        
        # Get the trip
        trip = Trip.query.get(trip_id)
        if not trip:
            return jsonify({'success': False, 'message': 'Trip not found'}), 404
        
        # Update trip's driver if needed
        original_driver_id = getattr(trip, 'driver_id', None)
        if override_driver or not original_driver_id:
            trip.driver_id = int(driver_id)
        
        # Update go-home request status
        gh_request.status = 'assigned'
        gh_request.assigned_trip_id = trip_id
        
        # Create assignment record
        assignment = GoHomeTripAssignment(
            go_home_request_id=gh_request_id,
            driver_id=int(driver_id),
            trip_id=trip_id,
            origin_trip_id=original_driver_id,
            distance_from_home_km=data.get('distance_from_home_km', 0),
            assignment_timestamp=datetime.utcnow(),
            status='assigned',
            admin_id=int(admin_id)
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        # Emit real-time socket event to driver dashboard
        if socketio:
            socketio.emit('trip_assigned_to_driver', {
                'trip_id': trip_id,
                'driver_id': int(driver_id),
                'assignment_type': 'go_home_request',
                'go_home_request_id': gh_request_id,
                'route_no': getattr(trip, 'route_no', ''),
                'scheduled_time': format_time_to_hhmm(getattr(trip, 'scheduled_time', '')),
                'status': 'assigned',
                'timestamp': datetime.utcnow().isoformat(),
            }, broadcast=True, skip_sid=True)
        
        return jsonify({
            'success': True,
            'data': {
                'assignment_id': assignment.id,
                'driver_id': int(driver_id),
                'trip_id': trip_id,
                'status': 'assigned',
                'assignment_timestamp': assignment.assignment_timestamp.isoformat(),
                'message': f'Trip assigned to driver. Trip will appear on driver dashboard shortly.'
            }
        }), 200
    
    except Exception as e:
        print(f"Error assigning go-home trip: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# 6. GET ALL AVAILABLE VEHICLES WITH DRIVER INFO
# ============================================================================

@vehicle_selection_bp.route('/trips/available-vehicles', methods=['GET'])
@cross_origin()
def get_available_vehicles():
    """
    Get all available vehicles/drivers for a specific trip type and time slot.
    
    Query Parameters:
    - admin_id (required)
    - trip_type: pickup/drop
    - scheduled_time: HH:mm
    - vehicle_types: comma-separated (4,6)
    - date: YYYY-MM-DD
    - exclude_assigned: true/false
    """
    try:
        admin_id = request.args.get('admin_id')
        trip_type = request.args.get('trip_type', 'pickup')
        scheduled_time = request.args.get('scheduled_time')
        vehicle_types_str = request.args.get('vehicle_types', '4,6')
        exclude_assigned = request.args.get('exclude_assigned', 'false').lower() == 'true'
        
        if not admin_id:
            return jsonify({'success': False, 'message': 'admin_id required'}), 400
        
        # Parse vehicle types
        try:
            vehicle_types = [int(x.strip()) for x in vehicle_types_str.split(',')]
        except:
            vehicle_types = [4, 6]
        
        # Query drivers/vehicles
        # This is placeholder - adjust based on your driver model
        drivers = Driver.query.filter(
            Driver.vehicle_type.in_(vehicle_types),
            Driver.status.in_(['available', 'active'])
        ).all()
        
        results = []
        for driver in drivers:
            # Check if driver is already assigned (optional)
            is_assigned = False
            if exclude_assigned:
                assigned_trip = Trip.query.filter_by(
                    driver_id=driver.id,
                    status='in_progress'
                ).first()
                is_assigned = assigned_trip is not None
            
            if not is_assigned:
                results.append({
                    'id': driver.id,
                    'driver_id': driver.id,
                    'driver_name': driver.name,
                    'name': driver.name,
                    'mobile': driver.mobile,
                    'cab_no': driver.cab_no,
                    'cab_number': driver.cab_no,
                    'vehicle_type': driver.vehicle_type,
                    'status': driver.status,
                    'home_location_lat': float(getattr(driver, 'home_location_lat', 0)),
                    'home_location_lng': float(getattr(driver, 'home_location_lng', 0)),
                    'home_address': getattr(driver, 'home_address', ''),
                })
        
        return jsonify({
            'success': True,
            'data': results
        }), 200
    
    except Exception as e:
        print(f"Error fetching available vehicles: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# 7. REGISTER ROUTES
# ============================================================================

def register_vehicle_selection_routes(app):
    """Register vehicle selection blueprint with the Flask app."""
    app.register_blueprint(vehicle_selection_bp)
    print("✓ Vehicle Selection Routes Registered")


if __name__ == '__main__':
    print("""
    Vehicle Selection Backend Module
    
    This module provides APIs for:
    1. Managing driver go-home requests
    2. Finding nearest available trips using geographic proximity
    3. Auto-assigning trips to drivers
    4. Real-time dashboard updates via Socket.io
    
    Integration Steps:
    1. Import register_vehicle_selection_routes() in your main app file
    2. Call register_vehicle_selection_routes(app) after creating Flask app
    3. Ensure database models are created with schema from companion guide
    4. Update model imports at the top of this file to match your project
    """)
