# rg_travel_backend/services/tracking_service.py
"""
RG Travel Solution — tracking_service.py
=======================================

This service provides **Live Driver Tracking** for Admin and Employee dashboards.

✅ Project requirements covered:
1) Live driver tracking visible to Admin and Employee.
2) Driver app sends GPS (lat,lng) every X seconds.
3) Backend stores latest driver location + history (optional).
4) Admin and Employee can fetch:
   - all online drivers (for Live Tracking screen)
   - location of assigned driver for a given route/trip
5) Prevents common errors:
   - validates coordinates
   - marks driver online/offline
   - stores last_seen timestamp
6) Designed to support:
   - AJAX polling (every 5-10 seconds)
   - WebSocket later (same service can be reused)

------------------------------------------------------------
Expected DB tables (recommended minimum)
------------------------------------------------------------

drivers:
    id INTEGER PK
    name TEXT
    mobile TEXT
    cab_no TEXT
    is_online INTEGER DEFAULT 0
    last_seen TEXT

driver_locations:   (latest + history)
    id INTEGER PK
    driver_id INTEGER
    lat REAL
    lng REAL
    accuracy REAL NULL
    speed REAL NULL
    bearing REAL NULL
    recorded_at TEXT

trips:
    id INTEGER PK
    route_no TEXT UNIQUE
    driver_id INTEGER NULL
    status TEXT ("active"|"in_progress"|"completed"|"cancelled")

------------------------------------------------------------
Public APIs for routes
------------------------------------------------------------

Core service functions:
- update_driver_location(conn, driver_id, lat, lng, **meta) -> dict
- set_driver_online_status(conn, driver_id, is_online: bool) -> dict
- get_driver_latest_location(conn, driver_id) -> dict
- get_online_drivers(conn) -> dict
- get_assigned_driver_location_by_trip(conn, trip_id) -> dict
- get_assigned_driver_location_by_route_no(conn, route_no) -> dict
- get_driver_location_history(conn, driver_id, limit=100) -> dict

Routes-friendly wrappers (optional):
- api_update_location(payload: dict) -> dict
- api_get_online_drivers() -> dict
- api_get_driver_latest(driver_id) -> dict
- api_get_trip_driver_location(trip_id) -> dict
- api_get_route_driver_location(route_no) -> dict

------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Safe imports for DB
try:
    from ..db import get_db  # type: ignore
except Exception:
    from db import get_db  # type: ignore


# =========================
# Time helpers
# =========================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =========================
# Validation helpers
# =========================

def _is_valid_coord(lat: float, lng: float) -> bool:
    return (
        isinstance(lat, (int, float))
        and isinstance(lng, (int, float))
        and -90.0 <= float(lat) <= 90.0
        and -180.0 <= float(lng) <= 180.0
        and not (float(lat) == 0.0 and float(lng) == 0.0)
    )


# ============================================================
# Core functions
# ============================================================

def update_driver_location(
    conn,
    driver_id: Any,
    lat: float,
    lng: float,
    accuracy: Optional[float] = None,
    speed: Optional[float] = None,
    bearing: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Stores a driver location update:
    - inserts into driver_locations (history)
    - updates drivers table: is_online=1, last_seen
    """
    try:
        # driver_id = int(driver_id) # Removed: IDs are UUID strings
        lat = float(lat)
        lng = float(lng)
    except Exception:
        return {"success": False, "message": "Invalid lat/lng."}

    if not _is_valid_coord(lat, lng):
        return {"success": False, "message": "Invalid GPS coordinates."}

    cur = conn.cursor()

    # Ensure driver exists
    cur.execute("SELECT id FROM drivers WHERE id = ? LIMIT 1", (driver_id,))
    if not cur.fetchone():
        return {"success": False, "message": "Driver not found."}

    t = now_iso()

    # Insert location history (Keep as is for history)
    cur.execute(
        """
        INSERT INTO driver_location_history (driver_id, latitude, longitude, accuracy, speed, recorded_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (driver_id, lat, lng, accuracy, speed, t, t),
    )

    # ------------------------------------------------------------
    # NEW: UPSERT into driver_live_locations for real-time state
    # ------------------------------------------------------------
    # Using SQLite UPSERT (ON CONFLICT DO UPDATE)
    # Target constraint: UNIQUE(driver_id, route_no)
    
    route_no = kwargs.get("route_no")
    trip_id = kwargs.get("trip_id") # Optional/Nullable
    heading = kwargs.get("heading")
    device_time = kwargs.get("device_time") or t

    if route_no:
        # Try to find trip_id if not provided? 
        # For now, insert what we have. API usually provides route_no.
        
        cur.execute(
            """
            INSERT INTO driver_live_locations (driver_id, route_no, trip_id, latitude, longitude, speed, heading, accuracy, device_time, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(driver_id, route_no) DO UPDATE SET
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                trip_id=COALESCE(excluded.trip_id, driver_live_locations.trip_id),
                speed=excluded.speed,
                heading=excluded.heading,
                accuracy=excluded.accuracy,
                device_time=excluded.device_time,
                updated_at=excluded.updated_at
            """,
            (driver_id, route_no, trip_id, lat, lng, speed, heading, accuracy, device_time, t)
        )

        # ------------------------------------------------------------
        # NEW: Broadcast via SocketIO
        # ------------------------------------------------------------
        try:
            from services.socket_service import broadcast_driver_location, socketio
            broadcast_driver_location(driver_id, route_no, lat, lng, speed, heading)
        except Exception as e:
            print(f"Socket broadcast failed: {e}")

    # Update driver online + last_seen (Existing logic)
    cur.execute(
        """
        UPDATE drivers
        SET is_online = 1,
        last_seen = ?
        WHERE id = ?
        """,
        (t, driver_id),
    )

    conn.commit()

    return {
        "success": True,
        "message": "Location updated.",
        "data": {"driver_id": driver_id, "lat": lat, "lng": lng, "recorded_at": t},
    }


def set_driver_online_status(conn, driver_id: int, is_online: bool) -> Dict[str, Any]:
    """
    Mark driver online/offline manually.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM drivers WHERE id = ? LIMIT 1", (driver_id,))
    if not cur.fetchone():
        return {"success": False, "message": "Driver not found."}

    cur.execute(
        "UPDATE drivers SET is_online = ?, last_seen = ? WHERE id = ?",
        (1 if is_online else 0, now_iso(), driver_id),
    )
    conn.commit()
    return {"success": True, "message": "Status updated.", "data": {"driver_id": driver_id, "is_online": bool(is_online)}}


def get_driver_latest_location(conn, driver_id: int) -> Dict[str, Any]:
    """
    Returns latest known location of a driver (from live table or history).
    Prefer live table if available.
    """
    cur = conn.cursor()
    
    # Try live table first (any route)
    cur.execute(
        """
        SELECT latitude, longitude, accuracy, speed, updated_at, route_no
        FROM driver_live_locations
        WHERE driver_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (driver_id,)
    )
    row = cur.fetchone()
    
    if row:
        return {
            "success": True,
            "data": {
                "driver_id": driver_id,
                "lat": float(row[0]),
                "lng": float(row[1]),
                "accuracy": row[2],
                "speed": row[3],
                "recorded_at": row[4],
                "route_no": row[5]
            },
        }

    # Fallback to history
    cur.execute(
        """
        SELECT latitude, longitude, accuracy, speed, recorded_at
        FROM driver_location_history
        WHERE driver_id = ?
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        (driver_id,),
    )
    row = cur.fetchone()
    if not row:
        return {"success": False, "message": "No location found for driver."}

    return {
        "success": True,
        "data": {
            "driver_id": driver_id,
            "lat": float(row[0]),
            "lng": float(row[1]),
            "accuracy": row[2],
            "speed": row[3],
            "recorded_at": row[4],
        },
    }


def get_driver_location_history(conn, driver_id: int, limit: int = 100) -> Dict[str, Any]:
    """
    Returns location history (latest first).
    """
    limit = max(1, min(int(limit), 500))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT latitude, longitude, accuracy, speed, recorded_at
        FROM driver_location_history
        WHERE driver_id = ?
        ORDER BY recorded_at DESC
        LIMIT ?
        """,
        (driver_id, limit),
    )
    rows = cur.fetchall()

    data = []
    for r in rows:
        data.append(
            {
                "lat": float(r[0]),
                "lng": float(r[1]),
                "accuracy": r[2],
                "speed": r[3],
                "recorded_at": r[4],
            }
        )

    return {"success": True, "data": {"driver_id": driver_id, "history": data, "count": len(data)}}


def get_online_drivers(conn) -> Dict[str, Any]:
    """
    Returns all online drivers with their latest location.
    Used in Admin "Live Driver Tracking" screen.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, mobile, vehicle_no as cab_no, last_seen
        FROM drivers
        WHERE COALESCE(is_online, 0) = 1
        ORDER BY last_seen DESC
        """
    )
    drivers = cur.fetchall()

    result: List[Dict[str, Any]] = []
    for d in drivers:
        # driver_id might be string UUID now
        driver_id = d[0] 
        latest = get_driver_latest_location(conn, driver_id)
        loc = latest.get("data") if latest.get("success") else None

        result.append(
            {
                "driver_id": driver_id,
                "name": d[1],
                "mobile": d[2],
                "cab_no": d[3],
                "last_seen": d[4],
                "location": loc,
            }
        )

    return {"success": True, "data": {"online_drivers": result, "count": len(result)}}


def get_assigned_driver_location_by_trip(conn, trip_id: int) -> Dict[str, Any]:
    """
    Returns latest location of the driver assigned to the trip.
    Used for Employee + Admin tracking.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT driver_id, route_no FROM trips WHERE id = ? LIMIT 1",
        (trip_id,),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return {"success": False, "message": "No driver assigned to this trip."}

    driver_id = row[0] # Keep as is (string/int)
    route_no = row[1]
    
    # Use specific getter for driver+route if possible
    latest = get_latest_location_for_driver(conn, driver_id, route_no)
    if latest.get("success"):
        return latest
        
    return get_driver_latest_location(conn, driver_id)


def get_assigned_driver_location_by_route_no(conn, route_no: str) -> Dict[str, Any]:
    """
    Same as above but by route number.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT driver_id FROM trips WHERE route_no = ? LIMIT 1",
        (route_no,),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return {"success": False, "message": "No driver assigned to this route."}

    driver_id = row[0]
    
    # Use specific getter
    latest = get_latest_location_for_driver(conn, driver_id, route_no)
    if latest.get("success"):
        return latest

    return get_driver_latest_location(conn, driver_id)

# ============================================================
# NEW READ FUNCTIONS (Requested by User)
# ============================================================

def get_latest_locations_by_route(conn, route_no: str) -> Dict[str, Any]:
    """
    Returns the most recent coordinate for that route.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT driver_id, latitude, longitude, speed, heading, accuracy, device_time, updated_at
        FROM driver_live_locations
        WHERE route_no = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (route_no,)
    )
    row = cur.fetchone()
    if not row:
        return {"success": False, "message": "No active tracking data for this route."}
        
    return {
        "success": True,
        "data": {
            "driver_id": row[0],
            "lat": row[1],
            "lng": row[2],
            "speed": row[3],
            "heading": row[4],
            "accuracy": row[5],
            "device_time": row[6],
            "updated_at": row[7]
        }
    }

def get_latest_location_for_driver(conn, driver_id: str, route_no: str) -> Dict[str, Any]:
    """
    Returns latest location for specific driver on specific route.
    Includes stale detection: adds "stale": true if location is older than 60 seconds.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT latitude, longitude, speed, heading, accuracy, device_time, updated_at
        FROM driver_live_locations
        WHERE driver_id = ? AND route_no = ?
        LIMIT 1
        """,
        (driver_id, route_no)
    )
    row = cur.fetchone()
    if not row:
        return {"success": False, "message": "No tracking data found for this driver on this route."}
    
    # Check staleness (60 second threshold)
    from datetime import datetime, timezone, timedelta
    updated_at_str = row[6]  # updated_at column
    is_stale = False
    
    try:
        updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        time_since_update = (now - updated_at).total_seconds()
        
        if time_since_update > 60:
            is_stale = True
    except Exception:
        # If timestamp parsing fails, don't mark as stale (fail-safe)
        pass
        
    return {
        "success": True,
        "data": {
            "driver_id": driver_id,
            "route_no": route_no,
            "lat": row[0],
            "lng": row[1],
            "speed": row[2],
            "heading": row[3],
            "accuracy": row[4],
            "device_time": row[5],
            "updated_at": row[6],
            "stale": is_stale
        }
    }

# ============================================================
# Routes-friendly API wrappers
# ============================================================

def api_update_location(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Driver sends:
      POST /api/driver/location
    """
    conn = get_db()
    try:
        # driver_id in payload might be string UUID. Ensure update_driver_location handles it.
        # Payload comes from tracking_routes.py which extracts "driverId"
        
        return update_driver_location(
            conn,
            driver_id=payload.get("driver_id"), # Ensure string for UUIDs
            lat=float(payload.get("lat")),
            lng=float(payload.get("lng")),
            accuracy=payload.get("accuracy"),
            speed=payload.get("speed"),
            heading=payload.get("heading"),
            route_no=payload.get("route_no"),
            device_time=payload.get("device_time"),
            trip_id=payload.get("trip_id")
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def api_get_online_drivers() -> Dict[str, Any]:
    """
    GET /api/admin/drivers/online
    """
    conn = get_db()
    try:
        return get_online_drivers(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def api_get_driver_latest(driver_id: int) -> Dict[str, Any]:
    """
    GET /api/admin/driver/<id>/latest-location
    """
    conn = get_db()
    try:
        return get_driver_latest_location(conn, driver_id)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def api_get_trip_driver_location(trip_id: int) -> Dict[str, Any]:
    """
    GET /api/employee/trips/<id>/driver-location
    """
    conn = get_db()
    try:
        return get_assigned_driver_location_by_trip(conn, trip_id)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def api_get_route_driver_location(route_no: str) -> Dict[str, Any]:
    """
    GET /api/employee/routes/<route_no>/driver-location
    """
    conn = get_db()
    try:
        return get_assigned_driver_location_by_route_no(conn, route_no)
    finally:
        try:
            conn.close()
        except Exception:
            pass
