# rg_travel_backend/routes/tracking_routes.py
"""
Live driver tracking endpoints.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone

# Safe imports
try:
    from db import get_db
    from services.tracking_service import (
        update_driver_location,
        get_driver_latest_location,
        get_online_drivers,
        get_assigned_driver_location_by_route_no,
        get_latest_location_for_driver,
    )
except ImportError:
    from db import get_db  # type: ignore
    from services.tracking_service import (  # type: ignore
        update_driver_location,
        get_driver_latest_location,
        get_online_drivers,
        get_assigned_driver_location_by_route_no,
        get_latest_location_for_driver,
    )

tracking_bp = Blueprint("tracking", __name__)

# In-memory cache for route history (replace with Redis in production)
route_history_cache = {}


def _authenticate_request():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, jsonify({"success": False, "message": "Missing Authorization header"}), 401

    from utils.security import verify_token
    token = auth_header.split(" ", 1)[1] if " " in auth_header else auth_header
    try:
        decoded = verify_token(token)
        if not decoded:
            return None, jsonify({"success": False, "message": "Invalid Token"}), 401
        return decoded, None, None
    except Exception:
        return None, jsonify({"success": False, "message": "Invalid Token"}), 401


def _authorize_route_access(conn, user_id: str, role: str, route_no: str):
    cur = conn.cursor()

    if role == "admin":
        return True, None

    if role == "driver":
        cur.execute(
            """
            SELECT 1
            FROM trips
            WHERE route_no = ?
              AND CAST(driver_id AS TEXT) = CAST(? AS TEXT)
              AND status IN ('created', 'assigned', 'started', 'active', 'in_progress', 'live')
            LIMIT 1
            """,
            (route_no, user_id),
        )
        if cur.fetchone():
            return True, None
        return False, "Driver not assigned to this route"

    if role == "employee":
        cur.execute(
            """
            SELECT 1
            FROM trip_employees te
            JOIN trips t ON te.trip_id = t.id
            WHERE t.route_no = ?
              AND CAST(te.employee_id AS TEXT) = CAST(? AS TEXT)
              AND t.status IN ('created', 'assigned', 'started', 'active', 'in_progress', 'live')
            LIMIT 1
            """,
            (route_no, user_id),
        )
        if cur.fetchone():
            return True, None
        return False, "Employee not assigned to this route"

    return False, f"Unsupported role: {role}"


@tracking_bp.route("/api/driver/location", methods=["POST"])
def update_driver_location_v2():
    """
    Step 1: Live Tracking Implementation
    Driver sends high-frequency location updates.
    
    Payload:
      {
        "driverId": "uuid",
        "routeNo": "...",
        "lat": float,
        "lng": float,
        "speed": float,
        "heading": float,
        "accuracy": float,
        "deviceTime": "ISO8601"
      }
    """
    try:
        # 0. Payload Size Check (Max 10KB)
        if request.content_length and request.content_length > 10 * 1024:
            return jsonify({"success": False, "message": "Payload too large"}), 413
        
        # 1. Auth check (Strict)
        auth_header = request.headers.get("Authorization")
        if not auth_header:
             return jsonify({"success": False, "message": "Missing Authorization header"}), 401
        
        # Verify Token
        from utils.security import verify_token
        token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        try:
             decoded = verify_token(token)
             if not decoded:
                 return jsonify({"success": False, "message": "Invalid Token"}), 401
             auth_driver_id = decoded.get('user_id')
        except Exception as e:
             return jsonify({"success": False, "message": "Invalid Token"}), 401

        data = request.json or {}
        
        # 2. Extract Fields & Validate Payload
        route_no = data.get("routeNo")
        lat = data.get("lat")
        lng = data.get("lng")
        speed = data.get("speed")
        heading = data.get("heading")
        accuracy = data.get("accuracy")
        device_time = data.get("deviceTime")
        
        if not all([route_no, lat is not None, lng is not None, device_time]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
            
        # Validate coordinates (Simple range check)
        try:
            lat = float(lat)
            lng = float(lng)
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                 return jsonify({"success": False, "message": "Invalid coordinates"}), 400
        except ValueError:
             return jsonify({"success": False, "message": "Invalid coordinates"}), 400

        # 3. Check Active Trip & Route Assignment
        conn = get_db()
        cur = conn.cursor()
        
        # Verify route belongs to driver and is ACTIVE
        cur.execute(
            "SELECT id, status FROM trips WHERE route_no = ? AND driver_id = ? LIMIT 1",
            (route_no, auth_driver_id)
        )
        trip_row = cur.fetchone()
        
        if not trip_row:
             # Audit: Unauthorized route access attempt
             from services.audit_service import log_unauthorized_access
             log_unauthorized_access(
                 user_id=auth_driver_id,
                 role="driver",
                 route_no=route_no,
                 action="location_update",
                 reason="Route not found or not assigned to driver"
             )
             return jsonify({"success": False, "message": "Route not found or not assigned to you"}), 403
        
        trip_id = trip_row[0]
        trip_status = trip_row[1]
        
        if trip_status not in ('created', 'assigned', 'started', 'active', 'in_progress', 'live'):
             from services.audit_service import log_unauthorized_access
             log_unauthorized_access(
                 user_id=auth_driver_id,
                 role="driver",
                 route_no=route_no,
                 action="location_update",
                 reason=f"Trip not active (status: {trip_status})"
             )
             return jsonify({"success": False, "message": f"Trip is not active (status: {trip_status})"}), 403

        # 4. Rate Limiting (Enforce 2-second minimum between updates)
        cur.execute("SELECT updated_at FROM driver_live_locations WHERE driver_id = ?", (auth_driver_id,))
        last_update_row = cur.fetchone()
        
        if last_update_row:
             last_update_str = last_update_row[0]
             try:
                 # Parse the timestamp (assuming ISO format)
                 last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                 now = datetime.now(timezone.utc)
                 time_delta = (now - last_update).total_seconds()
                 
                 if time_delta < 2.0:
                     # Rate limit exceeded
                     from services.audit_service import log_rate_limit
                     log_rate_limit(user_id=auth_driver_id, role="driver", route_no=route_no)
                     return jsonify({
                         "success": False, 
                         "message": "Rate limit: Please wait at least 2 seconds between updates"
                     }), 429
             except Exception as e:
                 # If parsing fails, allow the update (don't block on error)
                 print(f"Rate limit timestamp parse error: {e}", flush=True)

        # 5. Update Location (call Service)
        result = update_driver_location(
            conn, 
            driver_id=auth_driver_id,
            lat=lat, 
            lng=lng,
            accuracy=accuracy, 
            speed=speed,
            heading=heading,
            route_no=route_no,
            device_time=device_time,
            trip_id=trip_id
        )
        
        server_time = datetime.now(timezone.utc).isoformat()
        
        if result.get("success"):
            # Audit: Successful location update
            from services.audit_service import log_location_update
            log_location_update(
                driver_id=auth_driver_id,
                route_no=route_no,
                success=True
            )
            
            # Location broadcast is handled inside update_driver_location().
            # Do not emit here again to avoid duplicate updates on subscribers.
            try:
                # Cache location for route history (polyline rendering)
                if route_no not in route_history_cache:
                    route_history_cache[route_no] = []
                
                route_history_cache[route_no].append({
                    'lat': lat,
                    'lng': lng,
                    'speed': speed,
                    'timestamp': server_time
                })
                
                # Keep only last 60 mins (memory management)
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=60)
                route_history_cache[route_no] = [
                    point for point in route_history_cache[route_no]
                    if datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')) > cutoff_time
                ]
                
            except Exception as e:
                print(f"Socket Broadcast Failed: {e}", flush=True)

            return jsonify({
                "success": True, 
                "message": "Location updated", 
                "serverTime": server_time,
                "routeNo": route_no,
                "tripId": trip_id
            }), 200
        else:
            # Audit: Failed location update
            from services.audit_service import log_location_update
            log_location_update(
                driver_id=auth_driver_id,
                route_no=route_no,
                success=False,
                reason=result.get("message", "Unknown error")
            )
            return jsonify(result), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
             if 'conn' in locals(): conn.close()
        except: pass

@tracking_bp.route("/api/driver/<driver_id>/gps", methods=["POST"])
def update_gps(driver_id):
    """
    Legacy Endpoint (Keep for backward compatibility for now if needed, or redirect)
    """

@tracking_bp.route("/api/tracking/route/<route_no>/latest", methods=["GET"])
def get_route_driver_tracking(route_no):
    """
    Get latest location of driver assigned to route.
    Used by employee/admin to track assigned driver.
    """
    try:
        decoded, err_resp, err_status = _authenticate_request()
        if err_resp:
            return err_resp, err_status

        conn = get_db()
        user_id = str(decoded.get("user_id") or "")
        role = str(decoded.get("role") or "")

        authorized, reason = _authorize_route_access(conn, user_id, role, route_no)
        if not authorized:
            from services.audit_service import log_unauthorized_access
            log_unauthorized_access(
                user_id=user_id or "unknown",
                role=role or "unknown",
                route_no=route_no,
                action="read_latest_tracking",
                reason=reason or "Unauthorized",
            )
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        cur = conn.cursor()

        # Resolve assigned driver for the route first.
        cur.execute("SELECT driver_id FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
        trip_row = cur.fetchone()
        if not trip_row or trip_row[0] is None:
            return jsonify({"success": False, "message": "No driver assigned to this route."}), 404

        driver_id = str(trip_row[0])

        # Prefer strict route+driver lookup from live table.
        result = get_latest_location_for_driver(conn, driver_id, route_no)
        if not result.get("success"):
            # Backward fallback to existing helper.
            result = get_assigned_driver_location_by_route_no(conn, route_no)
        
        if result.get("success"):
            location = (result.get("data") or {})
            lat = location.get("lat")
            lng = location.get("lng")
            speed = location.get("speed")
            heading = location.get("heading")
            accuracy = location.get("accuracy")
            timestamp = location.get("updated_at") or location.get("recorded_at") or location.get("device_time")

            # Backward + forward compatible response contract:
            # - "location.latitude/longitude" for legacy/mobile consumers
            # - "data.lat/lng" for newer consumers
            return jsonify({
                "success": True,
                "route_no": route_no,
                "driver_id": driver_id,
                "location": {
                    "latitude": lat,
                    "longitude": lng,
                    "speed": speed,
                    "heading": heading,
                    "accuracy": accuracy,
                    "timestamp": timestamp
                },
                "data": {
                    "driver_id": driver_id,
                    "route_no": route_no,
                    "lat": lat,
                    "lng": lng,
                    "speed": speed,
                    "heading": heading,
                    "accuracy": accuracy,
                    "updated_at": location.get("updated_at"),
                    "device_time": location.get("device_time"),
                    "stale": bool(location.get("stale", False))
                }
            }), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
            conn.close()
        except:
            pass


@tracking_bp.route("/api/tracking/route/<route_no>/history", methods=["GET"])
def get_route_history(route_no):
    """
    Get location history for a route (last N minutes).
    Used to render polyline showing driver's path.
    
    Query params:
      - duration: minutes of history to return (default: 30, max: 60)
    
    Returns:
      {
        "success": true,
        "route_no": "R001",
        "duration_minutes": 30,
        "points": [
          {"lat": 37.7749, "lng": -122.4194, "timestamp": "2024-01-01T12:00:00", "speed": 25.5},
          ...
        ]
      }
    """
    try:
        decoded, err_resp, err_status = _authenticate_request()
        if err_resp:
            return err_resp, err_status

        user_id = str(decoded.get("user_id") or "")
        role = str(decoded.get("role") or "")
        conn = get_db()
        authorized, reason = _authorize_route_access(conn, user_id, role, route_no)
        if not authorized:
            from services.audit_service import log_unauthorized_access
            log_unauthorized_access(
                user_id=user_id or "unknown",
                role=role or "unknown",
                route_no=route_no,
                action="read_route_history",
                reason=reason or "Unauthorized",
            )
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        
        # Get duration parameter (default 30 mins, max 60)
        duration = min(int(request.args.get('duration', 30)), 60)
        
        # Get from cache
        history = route_history_cache.get(route_no, [])
        
        # Filter by time (keep only points within duration)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=duration)
        filtered = []
        
        for point in history:
            try:
                point_time = datetime.fromisoformat(str(point['timestamp']).replace('Z', '+00:00'))
                if point_time > cutoff:
                    filtered.append(point)
            except:
                continue
        
        return jsonify({
            "success": True,
            "route_no": route_no,
            "duration_minutes": duration,
            "points": filtered
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
            if "conn" in locals():
                conn.close()
        except Exception:
            pass

