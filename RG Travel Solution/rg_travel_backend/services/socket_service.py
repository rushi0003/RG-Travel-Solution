
# rg_travel_backend/services/socket_service.py
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect, ConnectionRefusedError
from datetime import datetime, timezone
import logging

# Initialize SocketIO (will be attached to app later)
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

logger = logging.getLogger(__name__)

# Rate limiting for room joins (in-memory)
_socket_join_timestamps = {}  # {session_id: last_join_timestamp}

# Helper to authenticate socket connection or event
def authenticate_socket(data_payload=None):
    """
    Authenticates a socket request.
    Checks 'token' in data_payload OR 'Authorization' header in handshake.
    Returns (user_id, role, error_message).
    """
    token = None
    
    # 1. Try payload (common in emit)
    if data_payload and isinstance(data_payload, dict):
        token = data_payload.get('token')
        
    # 2. Try headers (handshake)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and "Bearer " in auth_header:
            token = auth_header.split(" ")[1]
            
    # 3. Try query params (handshake)
    if not token:
        token = request.args.get('token')

    if not token:
        return None, None, "Missing token"

    try:
        from utils.security import verify_token
        decoded = verify_token(token)
        if not decoded:
            return None, None, "Invalid or expired token"
            
        return decoded.get('user_id'), decoded.get('role'), None
    except Exception as e:
        return None, None, str(e)


def broadcast_driver_location(driver_id, route_no, lat, lng, speed=None, heading=None):
    """
    Broadcasts driver location update to the specific room for the route.
    
    ⚠️ PRIVACY WARNING: ONLY broadcast minimal tracking data.
    DO NOT add employee lists, phone numbers, OTPs, or other sensitive data.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "driverId": driver_id,
        "routeNo": route_no,
        "lat": lat,
        "lng": lng,
        "speed": speed,
        "heading": heading,
        "timestamp": timestamp,
        "serverTime": timestamp
    }
    
    room = f"route:{route_no}"
    
    try:
        socketio.emit('driver_location_update', payload, to=room)
        print(f"DEBUG: Broadcast to {room}: {lat},{lng}", flush=True)
    except Exception as e:
        logger.warning(f"Socket broadcast failed (non-critical): {e}")



@socketio.on('join_route')
def on_join_route(data):
    """
    Client (Admin/Employee) joins a route room to receive updates.
    Expects: {"routeNo": "...", "token": "..."}
    """
    route_no = data.get('routeNo')
    if not route_no:
        emit('tracking_error', {'message': 'Missing routeNo'})
        disconnect()
        return

    # Authenticate
    user_id, role, error = authenticate_socket(data)
    if error:
        from services.audit_service import log_unauthorized_access
        log_unauthorized_access(
            user_id=user_id or "unknown",
            role=role or "unknown",
            route_no=route_no,
            action="socket_join",
            reason=f"Authentication failed: {error}"
        )
        emit('tracking_error', {'message': f'Authentication failed: {error}'})
        disconnect()
        return
        
    # Rate Limiting: Prevent rapid room joins (<1s apart)
    session_id = request.sid
    now = datetime.now(timezone.utc)
    
    if session_id in _socket_join_timestamps:
        last_join = _socket_join_timestamps[session_id]
        time_since_join = (now - last_join).total_seconds()
        
        if time_since_join < 1.0:
            from services.audit_service import log_rate_limit
            log_rate_limit(user_id=user_id, role=role, route_no=route_no)
            emit('tracking_error', {'message': 'Rate limit: Too many room join requests'})
            return
    
    _socket_join_timestamps[session_id] = now
    
    # Authorization / RBAC
    is_authorized = False
    auth_failure_reason = None
    
    if role == 'admin':
        is_authorized = True
        
    elif role == 'employee':
        # Check if employee is assigned to this route's trip
        try:
            from db import get_db
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT 1 
                FROM trip_employees te
                JOIN trips t ON te.trip_id = t.id
                WHERE t.route_no = ?
                  AND CAST(te.employee_id AS TEXT) = CAST(? AS TEXT)
                  AND t.status IN ('created', 'assigned', 'started', 'active', 'in_progress', 'live')
                LIMIT 1
            """, (route_no, user_id))
            if cur.fetchone():
                is_authorized = True
            else:
                auth_failure_reason = "Employee not assigned to this route"
            conn.close()
        except Exception as e:
            auth_failure_reason = f"Authorization check failed: {e}"

    elif role == 'driver':
        try:
            from db import get_db
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT 1
                FROM trips
                WHERE route_no = ?
                  AND CAST(driver_id AS TEXT) = CAST(? AS TEXT)
                  AND status IN ('created', 'assigned', 'started', 'active', 'in_progress', 'live')
                LIMIT 1
            """, (route_no, user_id))
            if cur.fetchone():
                 is_authorized = True
            else:
                auth_failure_reason = "Driver not assigned to this route"
            conn.close()
        except Exception as e:
            auth_failure_reason = f"Authorization check failed: {e}"
    else:
        auth_failure_reason = f"Unknown role: {role}"

    if is_authorized:
        room = f"route:{route_no}"
        join_room(room)
        
        # Audit: Successful socket join
        from services.audit_service import log_socket_join
        log_socket_join(user_id=user_id, role=role, route_no=route_no, success=True)
        
        emit('joined_route', {'routeNo': route_no, 'room': room, 'message': 'Joined successfully'})
        print(f"DEBUG: Socket User {user_id} ({role}) joined room {room}", flush=True)
    else:
        # Audit: Unauthorized socket join attempt
        from services.audit_service import log_socket_join
        log_socket_join(
            user_id=user_id,
            role=role,
            route_no=route_no,
            success=False,
            reason=auth_failure_reason or "Unauthorized"
        )
        
        emit('tracking_error', {'message': 'Unauthorized to view this route'})
        print(f"DEBUG: Socket User {user_id} ({role}) unauthorized for {route_no}: {auth_failure_reason}", flush=True)
        disconnect()


@socketio.on('leave_route')
def on_leave_route(data):
    route_no = data.get('routeNo')
    if route_no:
        room = f"route:{route_no}"
        leave_room(room)
        emit('left_route', {'routeNo': route_no})


def broadcast_trip_assignment(route_no: str, trip_data: dict):
    """
    Broadcast trip assignment notification to driver and employees.
    
    Sent when a new trip is created and assigned.
    
    Args:
        route_no: Route number (e.g., "20264821FE")
        trip_data: Complete trip data including:
            - trip_id
            - driver_name, driver_phone, vehicle_no
            - schedule_time, operation
            - employees (list with stop details)
            - route_summary
            - otps
    """
    from datetime import datetime, timezone
    
    room = f"route:{route_no}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Prepare payload for employees
    employee_payload = {
        "routeNo": route_no,
        "tripId": trip_data.get("trip_id"),
        "status": "assigned",
        "driver": {
            "name": trip_data.get("driver_name"),
            "phone": trip_data.get("driver_phone"),
            "vehicleNo": trip_data.get("vehicle_no")
        },
        "scheduleTime": trip_data.get("schedule_time"),
        "operation": trip_data.get("operation"),
        "timestamp": timestamp
    }
    
    # Prepare payload for driver
    driver_payload = {
        "routeNo": route_no,
        "tripId": trip_data.get("trip_id"),
        "status": "assigned",
        "passengers": trip_data.get("employees", []),
        "routeSummary": trip_data.get("route_summary", {}),
        "otps": trip_data.get("otps", {}),
        "scheduleTime": trip_data.get("schedule_time"),
        "operation": trip_data.get("operation"),
        "timestamp": timestamp
    }
    
    # Broadcast to room (all connected: driver + employees + admin)
    try:
        socketio.emit('trip_assigned', {
            "employee": employee_payload,
            "driver": driver_payload,
            "timestamp": timestamp
        }, to=room)
        
        logger.info(f"Broadcast trip_assigned to {room}: trip {trip_data.get('trip_id')}")
    except Exception as e:
        logger.warning(f"Socket broadcast failed (non-critical): {e}")


def broadcast_trip_update(route_no: str, update_type: str, trip_data: dict):
    """
    Broadcast trip update notification (after override operations).
    
    Sent when trip is modified (employee moved, driver changed, etc).
    
    Args:
        route_no: Route number
        update_type: "employee_moved", "driver_changed", "status_changed"
        trip_data: Updated trip data
    """
    from datetime import datetime, timezone
    
    room = f"route:{route_no}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "routeNo": route_no,
        "tripId": trip_data.get("trip_id"),
        "updateType": update_type,
        "status": trip_data.get("status"),
        "routeRevision": trip_data.get("route_revision"),
        "timestamp": timestamp
    }
    
    # Include relevant updated data based on type
    if update_type == "driver_changed":
        payload["driver"] = {
            "name": trip_data.get("driver_name"),
            "phone": trip_data.get("driver_phone"),
            "vehicleNo": trip_data.get("vehicle_no")
        }
    elif update_type == "employee_moved":
        payload["employees"] = trip_data.get("employees", [])
        payload["routeSummary"] = trip_data.get("route_summary", {})
    
    try:
        socketio.emit('trip_updated', payload, to=room)
        logger.info(f"Broadcast trip_updated to {room}: {update_type}")
    except Exception as e:
        logger.warning(f"Socket broadcast failed (non-critical): {e}")


def broadcast_trip_status_change(route_no: str, new_status: str, trip_id: int):
    """
    Broadcast trip status change (started, completed, cancelled).
    
    Args:
        route_no: Route number
        new_status: New status
        trip_id: Trip ID
    """
    from datetime import datetime, timezone
    
    room = f"route:{route_no}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "routeNo": route_no,
        "tripId": trip_id,
        "status": new_status,
        "timestamp": timestamp
    }
    
    try:
        socketio.emit('trip_status_changed', payload, to=room)
        logger.info(f"Broadcast trip_status_changed to {room}: {new_status}")
    except Exception as e:
        logger.warning(f"Socket broadcast failed (non-critical): {e}")

