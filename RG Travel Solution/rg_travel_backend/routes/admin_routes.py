# rg_travel_backend/routes/admin_routes.py
"""
RG Travel Solution — admin_routes.py
===================================

This file contains **Admin APIs** for:
✅ Admin profile (view/update)
✅ Driver/Employee requests (approve/reject)
✅ Drivers & Employees list (CRUD-lite)
✅ Create groups + assign trips (AUTO grouping default + Manual override support)
✅ Route number reserve (10-char unique)
✅ Generate OTPs for trip start/end
✅ Trips: list live trips, trip history, cancel, mark completed
✅ Live tracking: online drivers + assigned driver live location (for Admin & Employee view)

IMPORTANT (your Flutter error):
Your Flutter logs call:
  http://10.0.2.2:5000/admin/profile
But your new structure is:
  /api/admin/...

So this file exposes BOTH:
  /admin/...      (legacy for your current Flutter code)
  /api/admin/...  (recommended)

------------------------------------------------------------
ASSUMED MINIMUM TABLES (adjust SQL if your schema differs)
------------------------------------------------------------

admins(id, name, email, mobile, office_name, office_address, office_lat, office_lng)

drivers(id, name, mobile, dl_no, cab_no, vehicle_type, home_town, is_online, last_seen, approved)
driver_requests(id, name, mobile, dl_no, cab_no, vehicle_type, home_town, status, created_at)

employees(id, name, mobile, employee_code, login_time, logout_time, address, lat, lng, approved)
employee_requests(id, name, mobile, login_time, logout_time, address, lat, lng, status, created_at)

trips(
  id, route_no, admin_id,
  operation,          -- "pickup" or "drop"
  trip_time,          -- "HH:MM" (selected)
  driver_id, cab_no, vehicle_type,
  status,             -- "active"|"in_progress"|"completed"|"cancelled"
  total_km,
  polyline,
  created_at, start_time, end_time,
  cancel_reason
)

trip_employees(trip_id, employee_id, is_no_show)

------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import sqlite3
import secrets
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta

# Safe DB import
try:
    from db import get_db  # type: ignore
except Exception:
    from db import get_db  # type: ignore

# Services
try:
    from services.route_no_service import reserve_route_no_for_trip
    from services.otp_service import create_trip_otps
    from services.routing_service import compute_round_trip_km
    from services.hybrid_group_planner import EmployeeNode, VehicleNode, plan_groups_hybrid
    from services.trip_validation_service import filter_eligible_employees
    from services.trip_orchestration_service import create_and_assign_trip
    from services.trip_lifecycle_service import (
        apply_swap_approval,
        mark_trip_cancelled,
        mark_trip_completed,
    )
    from services.trip_schedule_guard import evaluate_trip_start_gate, derive_pickup_timing, build_pickup_time_note
    from services.tracking_service import get_online_drivers, get_assigned_driver_location_by_route_no
    from services.absence_flow_service import (
        AbsenceFlowError,
        admin_remove_approved_absence,
        list_admin_requests as list_admin_absence_requests,
        list_approved_absence_ranges,
        review_request as review_absence_request_flow,
    )
    from services.validation_service import (
        validate_admin_profile_payload,
        validate_driver_payload,
        validate_employee_payload,
        validate_hhmm,
    )
    from services.nominatim_geocoding_service import geocode_address_nominatim
    from services.admin_billing_service import (
        create_billing_record,
        get_billing_prefill,
        get_billing_record,
        list_billable_trips,
        list_billable_vehicle_assignments,
        list_billing_records,
        save_billing_settings,
    )
except Exception:
    # flat imports fallback (if running without package context)
    from services.route_no_service import reserve_route_no_for_trip
    from services.otp_service import create_trip_otps
    from services.routing_service import compute_round_trip_km
    from services.hybrid_group_planner import EmployeeNode, VehicleNode, plan_groups_hybrid
    from services.trip_validation_service import filter_eligible_employees
    from services.trip_orchestration_service import create_and_assign_trip
    from services.trip_lifecycle_service import (
        apply_swap_approval,
        mark_trip_cancelled,
        mark_trip_completed,
    )
    from services.trip_schedule_guard import evaluate_trip_start_gate, derive_pickup_timing, build_pickup_time_note
    from services.tracking_service import get_online_drivers, get_assigned_driver_location_by_route_no
    from services.absence_flow_service import (
        AbsenceFlowError,
        admin_remove_approved_absence,
        list_admin_requests as list_admin_absence_requests,
        list_approved_absence_ranges,
        review_request as review_absence_request_flow,
    )
    from services.validation_service import (
        validate_admin_profile_payload,
        validate_driver_payload,
        validate_employee_payload,
        validate_hhmm,
    )
    from services.nominatim_geocoding_service import geocode_address_nominatim
    from services.admin_billing_service import (
        create_billing_record,
        get_billing_prefill,
        get_billing_record,
        list_billable_trips,
        list_billable_vehicle_assignments,
        list_billing_records,
        save_billing_settings,
    )

try:
    from repositories.admin_repo import AdminRepo
except Exception:
    from repositories.admin_repo import AdminRepo

try:
    from repositories import RepoError
except Exception:
    from repositories import RepoError

try:
    from utils.security import hash_password, require_auth
except Exception:
    from utils.security import hash_password, require_auth

# Grouping service is project-specific; keep import flexible.
try:
    from services.grouping_service import create_groups  # type: ignore
except Exception:
    try:
        from services.grouping_service import create_groups  # type: ignore
    except Exception:
        create_groups = None  # will handle gracefully

# Import Request Repo
try:
    from repositories.request_repo import RequestRepo
except ImportError:
    pass

admin_bp = Blueprint("admin_bp", __name__)

# Expose BOTH prefixes:
PREFIXES = ["/admin", "/api/admin"]


# =========================================================
# Helpers
# =========================================================

def _ok(data: Any = None, message: str = "OK", **extra) -> Any:
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload), 200

def _bad(message: str = "Bad request", status: int = 400, **extra) -> Any:
    payload = {"success": False, "message": message}
    payload.update(extra)
    return jsonify(payload), status

def _row_to_dict(cursor, row) -> Dict[str, Any]:
    # sqlite3.Row compatible
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        cols = [d[0] for d in cursor.description]
        return {cols[i]: row[i] for i in range(len(cols))}

def _path(p: str) -> List[str]:
    return [f"{pref}{p}" for pref in PREFIXES]


def _normalize_mobile(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip() if ch.isdigit())


def _generate_admin_id() -> str:
    return f'admin_{secrets.token_hex(6)}'


def _current_admin_id() -> str:
    admin_id = str(getattr(g, "user_id", "") or "").strip()
    if not admin_id:
        raise ValueError("Authenticated admin session is required.")
    return admin_id


def _employee_belongs_to_admin(cur, employee_id: Any, admin_id: str) -> bool:
    cur.execute("PRAGMA table_info(employees)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "admin_id" not in cols:
        return False
    cur.execute(
        """
        SELECT 1
        FROM employees
        WHERE CAST(id AS TEXT) = CAST(? AS TEXT)
          AND CAST(admin_id AS TEXT) = CAST(? AS TEXT)
        LIMIT 1
        """,
        (str(employee_id), str(admin_id)),
    )
    return cur.fetchone() is not None


def _driver_belongs_to_admin(cur, driver_id: Any, admin_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM driver_admin_assignments
        WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
          AND CAST(admin_id AS TEXT) = CAST(? AS TEXT)
          AND is_active = 1
        LIMIT 1
        """,
        (str(driver_id), str(admin_id)),
    )
    return cur.fetchone() is not None


def _trip_belongs_to_admin(cur, trip_id: Any, admin_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM trips
        WHERE CAST(id AS TEXT) = CAST(? AS TEXT)
          AND CAST(COALESCE(admin_id, '') AS TEXT) = CAST(? AS TEXT)
        LIMIT 1
        """,
        (str(trip_id), str(admin_id)),
    )
    return cur.fetchone() is not None


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ''):
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


# =========================================================
# ADMIN ACCESS MANAGEMENT
# =========================================================
@admin_bp.route('/admin/admins', methods=['GET'])
@admin_bp.route('/api/admin/admins', methods=['GET'])
@require_auth(roles=['admin'])
def list_admin_accounts():
    conn = get_db()
    try:
        repo = AdminRepo(conn)
        return _ok(repo.list_admins())
    except Exception as e:
        return _bad(f'Failed to load admins: {e}', 500)
    finally:
        conn.close()


@admin_bp.route('/admin/admins', methods=['POST'])
@admin_bp.route('/api/admin/admins', methods=['POST'])
@require_auth(roles=['admin'])
def create_admin_account():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get('name') or '').strip()
    mobile = _normalize_mobile(payload.get('mobile'))
    password = str(payload.get('password') or '').strip()
    email = str(payload.get('email') or '').strip() or None
    office_name = str(payload.get('office_name') or payload.get('officeName') or '').strip() or None
    office_location = str(payload.get('office_location') or payload.get('officeLocation') or '').strip() or None
    office_address = str(payload.get('office_address') or payload.get('officeAddress') or '').strip() or None
    office_lat = _to_float_or_none(payload.get('office_lat'))
    office_lng = _to_float_or_none(payload.get('office_lng'))

    if len(name) < 2:
        return _bad('Admin name must be at least 2 characters.', 400)
    if len(mobile) != 10:
        return _bad('Mobile must be exactly 10 digits.', 400)
    if len(password) < 6:
        return _bad('Password must be at least 6 characters.', 400)
    if (office_lat is None) != (office_lng is None):
        return _bad('Both office_lat and office_lng are required together.', 400)
    if office_lat is not None and not (-90 <= office_lat <= 90):
        return _bad('office_lat must be between -90 and 90.', 400)
    if office_lng is not None and not (-180 <= office_lng <= 180):
        return _bad('office_lng must be between -180 and 180.', 400)

    conn = get_db()
    try:
        repo = AdminRepo(conn)
        if repo.get_admin_by_mobile(mobile):
            return _bad('Admin mobile already exists.', 409)

        salt, password_hash = hash_password(password)
        admin = repo.create_admin(
            admin_id=_generate_admin_id(),
            name=name,
            mobile=mobile,
            email=email,
            office_name=office_name,
            office_location=office_location,
            office_address=office_address,
            office_lat=office_lat,
            office_lng=office_lng,
            password_salt=salt,
            password_hash=password_hash,
        )
        return _ok(admin, 'Admin created successfully')
    except sqlite3.IntegrityError:
        return _bad('Admin mobile already exists.', 409)
    except Exception as e:
        return _bad(f'Failed to create admin: {e}', 500)
    finally:
        conn.close()


@admin_bp.route('/admin/admins/<admin_id>', methods=['DELETE'])
@admin_bp.route('/api/admin/admins/<admin_id>', methods=['DELETE'])
@require_auth(roles=['admin'])
def delete_admin_account(admin_id: str):
    requester_id = str(getattr(g, 'user_id', '') or '').strip()
    target_id = str(admin_id or '').strip()
    if not target_id:
        return _bad('admin_id is required.', 400)
    if requester_id and requester_id == target_id:
        return _bad('Logged-in admin cannot delete their own account.', 400)

    conn = get_db()
    try:
        repo = AdminRepo(conn)
        repo.delete_admin(target_id)
        return _ok({'admin_id': target_id}, 'Admin removed successfully')
    except RepoError as e:
        return _bad(str(e), 404)
    except Exception as e:
        return _bad(f'Failed to delete admin: {e}', 500)
    finally:
        conn.close()


def _ensure_temporary_driver_column(cur) -> bool:
    """Ensure drivers.is_temporary exists; return True if available."""
    cur.execute("PRAGMA table_info(drivers)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "is_temporary" in cols:
        return True
    try:
        cur.execute("ALTER TABLE drivers ADD COLUMN is_temporary INTEGER DEFAULT 0")
        return True
    except Exception:
        return False


def _is_temporary_driver(cur, driver_id: str) -> bool:
    has_temp_col = _ensure_temporary_driver_column(cur)
    if has_temp_col:
        cur.execute(
            "SELECT COALESCE(is_temporary, 0) AS is_temporary, COALESCE(dl_no, '') AS dl_no FROM drivers WHERE id = ? LIMIT 1",
            (driver_id,),
        )
    else:
        cur.execute(
            "SELECT 0 AS is_temporary, COALESCE(dl_no, '') AS dl_no FROM drivers WHERE id = ? LIMIT 1",
            (driver_id,),
        )
    row = cur.fetchone()
    if not row:
        return False
    r = _row_to_dict(cur, row)
    return int(r.get("is_temporary") or 0) == 1 or str(r.get("dl_no") or "").upper() == "ADHOC_SWAP"


def _cleanup_temp_swap_driver(conn, trip_id: int) -> None:
    """
    Remove temporary swap driver after trip is completed/cancelled.
    Trip history remains (driver_id may become NULL due FK ON DELETE SET NULL).
    """
    cur = conn.cursor()
    cur.execute("SELECT driver_id FROM trips WHERE id = ? LIMIT 1", (trip_id,))
    row = cur.fetchone()
    if not row:
        return
    driver_id = str((_row_to_dict(cur, row).get("driver_id") or "")).strip()
    if not driver_id:
        return
    if not _is_temporary_driver(cur, driver_id):
        return
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM trips
        WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
          AND status IN ('assigned','active','in_progress','started','live')
        """,
        (driver_id,),
    )
    active_count = int((_row_to_dict(cur, cur.fetchone()).get("c") or 0))
    if active_count == 0:
        cur.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))


def _build_driver_snapshot(
    *,
    driver_id: Any = None,
    name: Any = None,
    mobile: Any = None,
    cab_no: Any = None,
    role: str = "current",
) -> Dict[str, Any]:
    return {
        "id": "" if driver_id is None else str(driver_id),
        "name": str(name or "").strip(),
        "mobile": str(mobile or "").strip(),
        "cab_no": str(cab_no or "").strip(),
        "role": role,
    }


def _attach_emergency_swap_context(cur, trip_data: Dict[str, Any]) -> Dict[str, Any]:
    trip_id = trip_data.get("id") or trip_data.get("trip_id")
    current_driver = _build_driver_snapshot(
        driver_id=trip_data.get("driver_id"),
        name=trip_data.get("driver_name"),
        mobile=trip_data.get("driver_mobile"),
        cab_no=trip_data.get("cab_no") or trip_data.get("vehicle_no"),
        role="current",
    )

    trip_data["current_driver"] = current_driver
    trip_data["original_driver"] = current_driver
    trip_data["all_drivers"] = [current_driver]
    trip_data["has_emergency_swap"] = False

    if not trip_id:
        return trip_data

    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='swap_requests' LIMIT 1"
    )
    if not cur.fetchone():
        return trip_data

    cur.execute(
        """
        SELECT
            sr.id AS swap_request_id,
            sr.status AS swap_status,
            sr.old_driver_id,
            sr.new_driver_id,
            sr.new_driver_name,
            sr.new_driver_mobile,
            sr.new_cab_no,
            od.name AS old_driver_name,
            od.mobile AS old_driver_mobile,
            od.vehicle_no AS old_driver_cab_no,
            nd.name AS approved_new_driver_name,
            nd.mobile AS approved_new_driver_mobile,
            nd.vehicle_no AS approved_new_driver_cab_no
        FROM swap_requests sr
        LEFT JOIN drivers od
          ON CAST(od.id AS TEXT) = CAST(sr.old_driver_id AS TEXT)
        LEFT JOIN drivers nd
          ON CAST(nd.id AS TEXT) = CAST(sr.new_driver_id AS TEXT)
        WHERE sr.trip_id = ?
          AND LOWER(COALESCE(sr.status, '')) = 'approved'
        ORDER BY COALESCE(sr.reviewed_at, sr.updated_at, sr.created_at) DESC, sr.id DESC
        LIMIT 1
        """,
        (trip_id,),
    )
    row = cur.fetchone()
    if not row:
        return trip_data

    swap = _row_to_dict(cur, row)
    original_driver = _build_driver_snapshot(
        driver_id=swap.get("old_driver_id"),
        name=swap.get("old_driver_name") or current_driver.get("name"),
        mobile=swap.get("old_driver_mobile"),
        cab_no=swap.get("old_driver_cab_no"),
        role="original",
    )
    swapped_driver = _build_driver_snapshot(
        driver_id=swap.get("new_driver_id") or current_driver.get("id"),
        name=swap.get("approved_new_driver_name")
        or swap.get("new_driver_name")
        or current_driver.get("name"),
        mobile=swap.get("approved_new_driver_mobile")
        or swap.get("new_driver_mobile")
        or current_driver.get("mobile"),
        cab_no=trip_data.get("cab_no")
        or trip_data.get("vehicle_no")
        or swap.get("approved_new_driver_cab_no")
        or swap.get("new_cab_no"),
        role="replacement",
    )

    drivers = [original_driver]
    if (
        swapped_driver.get("id") != original_driver.get("id")
        or swapped_driver.get("name") != original_driver.get("name")
        or swapped_driver.get("mobile") != original_driver.get("mobile")
    ):
        drivers.append(swapped_driver)

    trip_data["swap_request_id"] = swap.get("swap_request_id")
    trip_data["swap_status"] = swap.get("swap_status")
    trip_data["has_emergency_swap"] = len(drivers) > 1
    trip_data["original_driver"] = original_driver
    trip_data["current_driver"] = swapped_driver
    trip_data["all_drivers"] = drivers
    trip_data["original_driver_name"] = original_driver.get("name")
    trip_data["original_driver_mobile"] = original_driver.get("mobile")
    trip_data["original_cab_no"] = original_driver.get("cab_no")
    trip_data["replacement_driver_name"] = swapped_driver.get("name")
    trip_data["replacement_driver_mobile"] = swapped_driver.get("mobile")
    trip_data["replacement_cab_no"] = swapped_driver.get("cab_no")
    return trip_data


def _ensure_trip_cancel_requests_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trip_cancel_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            driver_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            admin_note TEXT,
            reviewed_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_trip_cancel_requests_trip_status ON trip_cancel_requests(trip_id, status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_trip_cancel_requests_driver_status ON trip_cancel_requests(driver_id, status)"
    )


def _generate_default_password() -> Tuple[str, str, str]:
    """
    Generate a secure random password for admin-created drivers.
    Returns: (password, salt, hash)
    """
    import secrets
    import hashlib
    
    # Generate 16-character random password
    password = secrets.token_hex(8)
    salt = secrets.token_hex(16)
    hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    return (password, salt, hash_val)


def _normalize_driver_response(driver_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize driver response to match Flutter expectations:
    - vehicle_no → cab_no
    - is_approved → approved
    """
    if 'vehicle_no' in driver_dict:
        driver_dict['cab_no'] = driver_dict.pop('vehicle_no')
    if 'is_approved' in driver_dict:
        driver_dict['approved'] = driver_dict.pop('is_approved')
    return driver_dict


def _normalize_status(status: Optional[str]) -> str:
    """
    Normalize status to match DB CHECK constraint (capitalized).
    Examples: 'pending' → 'Pending', 'approved' → 'Approved'
    """
    if not status:
        return 'Pending'
    return status.capitalize()


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _is_valid_coord_pair(lat: Optional[float], lng: Optional[float]) -> bool:
    if lat is None or lng is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0 and not (lat == 0.0 and lng == 0.0)


def _resolve_trip_duration_minutes(cur, trip_id: Optional[int], fallback_total_km=None) -> int:
    # Prefer persisted route duration, fallback to total_km approximation (2 min per km).
    try:
        if trip_id is not None:
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trip_routes' LIMIT 1")
            if cur.fetchone():
                cur.execute(
                    """
                    SELECT duration_mins
                    FROM trip_routes
                    WHERE trip_id = ?
                    ORDER BY route_index ASC, id DESC
                    LIMIT 1
                    """,
                    (int(trip_id),),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    return max(0, int(round(float(row[0]))))
    except Exception:
        pass

    try:
        return max(0, int(round(float(fallback_total_km or 0) * 2.0)))
    except Exception:
        return 0


def _attach_trip_timing_fields(cur, trip_data: Dict[str, Any]) -> Dict[str, Any]:
    mode = str(trip_data.get("trip_type") or trip_data.get("operation") or "").strip().lower()
    schedule_time = (
        trip_data.get("schedule_time")
        or trip_data.get("scheduled_time")
        or trip_data.get("trip_time")
        or ""
    )
    trip_id = trip_data.get("id") if trip_data.get("id") is not None else trip_data.get("trip_id")
    travel_min = _resolve_trip_duration_minutes(
        cur,
        int(trip_id) if str(trip_id or "").strip().isdigit() else None,
        trip_data.get("total_km"),
    )
    timing_meta = derive_pickup_timing(
        schedule_time,
        travel_min,
        extra_buffer_minutes=0,
    ) if mode == "pickup" else {
        "login_time": str(schedule_time or ""),
        "pickup_time": None,
        "route_duration_minutes": travel_min,
        "extra_buffer_minutes": 0,
        "total_lead_minutes": travel_min,
        "day_offset": 0,
    }
    trip_data["login_time"] = timing_meta.get("login_time")
    trip_data["pickup_time"] = timing_meta.get("pickup_time")
    trip_data["travel_time_min"] = int(timing_meta.get("route_duration_minutes", travel_min) or 0)
    trip_data["extra_buffer_min"] = int(timing_meta.get("extra_buffer_minutes", 0) or 0)
    trip_data["total_travel_with_buffer_min"] = int(timing_meta.get("total_lead_minutes", travel_min) or 0)
    trip_data["pickup_day_offset"] = int(timing_meta.get("day_offset", 0) or 0)
    trip_data["pickup_time_note"] = build_pickup_time_note(timing_meta) if mode == "pickup" else ""
    return trip_data


def _resolve_address_coords(
    conn: Any,
    *,
    address: Any,
    lat: Any = None,
    lng: Any = None,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Coordinate resolution with UI-map priority.
    1) Use provided lat/lng if valid (map-picked final point).
    2) Geocode from address via Nominatim.
    3) Return unresolved.
    """
    addr = str(address or "").strip()
    provided_lat = _to_float_or_none(lat)
    provided_lng = _to_float_or_none(lng)

    # Respect explicit map-picked coordinates from UI as the final source.
    if _is_valid_coord_pair(provided_lat, provided_lng):
        return provided_lat, provided_lng, "provided"

    if addr:
        geo = geocode_address_nominatim(addr, conn=conn, use_cache=True)
        if geo.get("success") is True:
            g = geo.get("data") or {}
            g_lat = _to_float_or_none(g.get("lat"))
            g_lng = _to_float_or_none(g.get("lng"))
            if _is_valid_coord_pair(g_lat, g_lng):
                return g_lat, g_lng, "nominatim"
    return None, None, "unresolved"


def _resolve_office_coords(conn: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Resolve default office coordinates from first admin profile.
    Used as a safe fallback when employee address geocoding is unavailable.
    """
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(admins)")
        cols = {str(r[1]) for r in cur.fetchall()}

        select_cols: List[str] = []
        if "office_lat" in cols:
            select_cols.append("office_lat")
        if "office_lng" in cols:
            select_cols.append("office_lng")
        if "office_location" in cols:
            select_cols.append("office_location")
        if not select_cols:
            return None, None

        cur.execute(f"SELECT {', '.join(select_cols)} FROM admins ORDER BY created_at ASC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None, None

        row_map = {select_cols[idx]: row[idx] for idx in range(len(select_cols))}
        lat = _to_float_or_none(row_map.get("office_lat"))
        lng = _to_float_or_none(row_map.get("office_lng"))
        if _is_valid_coord_pair(lat, lng):
            return lat, lng

        office_location = str(row_map.get("office_location") or "").strip()
        if office_location and "," in office_location:
            left, right = office_location.split(",", 1)
            lat = _to_float_or_none(left.strip())
            lng = _to_float_or_none(right.strip())
            if _is_valid_coord_pair(lat, lng):
                return lat, lng
    except Exception:
        pass
    return None, None


def _sync_employee_location_fields(
    cur: Any,
    conn: Any,
    *,
    employee_id: int,
    address: Any,
    lat: Optional[float],
    lng: Optional[float],
) -> None:
    """
    Keep location fields consistent for downstream consumers (grouping/trips).
    Home fields remain source-of-truth; pickup/drop are synchronized when columns exist.
    """
    if not _is_valid_coord_pair(lat, lng):
        return
    cur.execute("PRAGMA table_info(employees)")
    ecols = {str(r[1]) for r in cur.fetchall()}

    updates: List[str] = []
    params: List[Any] = []

    if "pickup_lat" in ecols:
        updates.append("pickup_lat = ?")
        params.append(lat)
    if "pickup_lng" in ecols:
        updates.append("pickup_lng = ?")
        params.append(lng)
    if "drop_lat" in ecols:
        updates.append("drop_lat = ?")
        params.append(lat)
    if "drop_lng" in ecols:
        updates.append("drop_lng = ?")
        params.append(lng)
    if "pickup_address" in ecols:
        updates.append("pickup_address = ?")
        params.append(address)
    if "drop_location" in ecols:
        updates.append("drop_location = ?")
        params.append(address)

    if not updates:
        return
    params.append(employee_id)
    cur.execute(
        f"UPDATE employees SET {', '.join(updates)} WHERE id = ?",
        tuple(params),
    )


def _build_employee_nodes_strict(
    eligible_employees: List[Dict[str, Any]],
    trip_type: str,
) -> Tuple[List[EmployeeNode], List[Dict[str, Any]]]:
    nodes: List[EmployeeNode] = []
    unresolved: List[Dict[str, Any]] = []
    for e in eligible_employees:
        if trip_type == "pickup":
            lat = _to_float_or_none(e.get("pickup_lat")) or _to_float_or_none(e.get("home_lat"))
            lng = _to_float_or_none(e.get("pickup_lng")) or _to_float_or_none(e.get("home_lng"))
            addr = str(e.get("pickup_address") or e.get("home_address") or "")
        else:
            lat = _to_float_or_none(e.get("home_lat")) or _to_float_or_none(e.get("pickup_lat"))
            lng = _to_float_or_none(e.get("home_lng")) or _to_float_or_none(e.get("pickup_lng"))
            addr = str(e.get("home_address") or e.get("pickup_address") or "")

        if not _is_valid_coord_pair(lat, lng):
            unresolved.append(
                {
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "mobile": e.get("mobile"),
                    "address": addr,
                    "reason": "missing_or_invalid_lat_lng",
                }
            )
            continue

        nodes.append(
            EmployeeNode(
                id=int(e.get("id")),
                name=str(e.get("name") or ""),
                mobile=str(e.get("mobile") or ""),
                address=addr,
                lat=float(lat),
                lng=float(lng),
            )
        )
    return nodes, unresolved


# =========================================================
# Health / Ping
# =========================================================
@admin_bp.route("/api/admin/ping", methods=["GET"])
@admin_bp.route("/admin/ping", methods=["GET"])
def admin_ping():
    return _ok({"service": "admin_routes"}, "pong")


# =========================================================
# ADMIN PROFILE
# =========================================================
for _r in _path("/profile/<admin_id>"):
    pass

@admin_bp.route("/admin/profile/<admin_id>", methods=["GET"])
@admin_bp.route("/api/admin/profile/<admin_id>", methods=["GET"])
@require_auth(roles=['admin'])
def get_admin_profile(admin_id: str):
    if str(admin_id) != _current_admin_id():
        return _bad("Forbidden for this admin.", 403)
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(admins)")
        admin_cols = {str(r[1]) for r in cur.fetchall()}
        select_cols = [
            "id",
            "name",
            "email",
            "mobile",
            "office_name",
            "office_address",
        ]
        if "office_lat" in admin_cols:
            select_cols.append("office_lat")
        if "office_lng" in admin_cols:
            select_cols.append("office_lng")
        cur.execute(
            f"""
            SELECT {", ".join(select_cols)}
            FROM admins
            WHERE id = ?
            """,
            (admin_id,),
        )
        row = cur.fetchone()
        if not row:
            return _bad("Admin not found.", 404)
        return _ok(_row_to_dict(cur, row))
    except Exception as e:
        return _bad(f"Failed to load admin profile: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/profile/<admin_id>", methods=["PUT"])
@admin_bp.route("/api/admin/profile/<admin_id>", methods=["PUT"])
@require_auth(roles=['admin'])
def update_admin_profile(admin_id: str):
    if str(admin_id) != _current_admin_id():
        return _bad("Forbidden for this admin.", 403)
    data = request.get_json(silent=True) or {}

    ok, msg = validate_admin_profile_payload(data)
    if not ok:
        return _bad(msg, 400)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(admins)")
        admin_cols = {str(r[1]) for r in cur.fetchall()}
        cur.execute("SELECT id FROM admins WHERE id = ? LIMIT 1", (admin_id,))
        if not cur.fetchone():
            return _bad("Admin not found.", 404)
        set_parts = [
            "name = ?",
            "mobile = ?",
            "office_name = ?",
            "office_address = ?",
        ]
        params = [
            data.get("name"),
            data.get("mobile"),
            data.get("office_name"),
            data.get("office_address"),
        ]
        if "office_lat" in admin_cols:
            set_parts.append("office_lat = ?")
            params.append(data.get("office_lat"))
        if "office_lng" in admin_cols:
            set_parts.append("office_lng = ?")
            params.append(data.get("office_lng"))
        params.append(admin_id)
        cur.execute(
            f"""
            UPDATE admins
            SET {", ".join(set_parts)}
            WHERE id = ?
            """,
            tuple(params),
        )
        conn.commit()
        return _ok({"admin_id": admin_id}, "Profile updated.")
    except Exception as e:
        return _bad(f"Failed to update profile: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass




# (Duplicate DRIVER PROFILE CHANGE REQUESTS section removed - kept complete implementation at line ~1745)

# =========================================================
# EMPLOYEE PROFILE CHANGE REQUESTS
# =========================================================

@admin_bp.route("/admin/employee-change-requests", methods=["GET"])
@admin_bp.route("/api/admin/employee-change-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_employee_change_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        status_filter = (request.args.get("status") or "pending").strip().lower()

        cur.execute("PRAGMA table_info(employee_change_requests)")
        req_cols = {str(r[1]) for r in cur.fetchall()}

        select_cols = ["id", "employee_id"]
        for c in ("name", "mobile", "home_address", "login_time", "logout_time",
                  "home_lat", "home_lng", "reason", "status", "created_at", "updated_at"):
            if c in req_cols:
                select_cols.append(c)

        if "status" in req_cols and status_filter != "all":
            where_clause = "WHERE LOWER(COALESCE(status, 'pending')) = ?"
            params: Tuple[Any, ...] = (status_filter,)
        else:
            where_clause = ""
            params = ()

        order_col = "created_at" if "created_at" in req_cols else "id"
        cur.execute(
            f"""
            SELECT {", ".join(select_cols)}
            FROM employee_change_requests
            {where_clause}
            ORDER BY {order_col} DESC
            """,
            params,
        )
        rows = cur.fetchall() or []
        result = []
        for r in rows:
            item = _row_to_dict(cur, r)
            if not _employee_belongs_to_admin(cur, item.get("employee_id"), admin_id):
                continue
            item["status"] = str(item.get("status") or "pending").strip().lower()
            result.append(item)
        return _ok(result)
    except Exception as e:
        return _bad(f"Failed to load employee change requests: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/employee-change-requests/<int:req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/employee-change-requests/<int:req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_employee_change_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM employee_change_requests WHERE id = ? LIMIT 1", (req_id,))
        req = cur.fetchone()
        if not req:
            return _bad("Request not found.", 404)
        
        reqd = _row_to_dict(cur, req)
        if not _employee_belongs_to_admin(cur, reqd.get("employee_id"), admin_id):
            return _bad("Request not found.", 404)
        req_status = str(reqd.get("status") or "pending").strip().lower()
        if req_status != "pending":
            return _bad(f"Request is already {req_status}.", 400)

        if str(reqd.get("home_address") or "").strip():
            g_lat, g_lng, _ = _resolve_address_coords(
                conn,
                address=reqd.get("home_address"),
                lat=reqd.get("home_lat"),
                lng=reqd.get("home_lng"),
            )
            if _is_valid_coord_pair(g_lat, g_lng):
                reqd["home_lat"] = g_lat
                reqd["home_lng"] = g_lng

        cur.execute("PRAGMA table_info(employees)")
        emp_cols = {str(r[1]) for r in cur.fetchall()}

        field_map = {
            "name": reqd.get("name"),
            "mobile": reqd.get("mobile"),
            "home_address": reqd.get("home_address"),
            "login_time": reqd.get("login_time"),
            "logout_time": reqd.get("logout_time"),
            "home_lat": reqd.get("home_lat"),
            "home_lng": reqd.get("home_lng"),
        }
        updates = []
        params = []
        for col, value in field_map.items():
            if col not in emp_cols:
                continue
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            updates.append(f"{col} = ?")
            params.append(value)

        if updates:
            if "updated_at" in emp_cols:
                updates.append("updated_at = datetime('now')")
            params.append(reqd.get("employee_id"))
            cur.execute(
                f"UPDATE employees SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )

        cur.execute("PRAGMA table_info(employee_change_requests)")
        req_cols = {str(r[1]) for r in cur.fetchall()}
        req_updates = ["status = 'approved'"]
        if "updated_at" in req_cols:
            req_updates.append("updated_at = datetime('now')")
        cur.execute(
            f"UPDATE employee_change_requests SET {', '.join(req_updates)} WHERE id = ?",
            (req_id,),
        )
        conn.commit()
        return _ok({"request_id": req_id}, "Employee profile updated successfully.")
    except Exception as e:
        return _bad(f"Failed to approve request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/employee-change-requests/<int:req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/employee-change-requests/<int:req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_employee_change_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, employee_id, status FROM employee_change_requests WHERE id = ? LIMIT 1", (req_id,))
        row = cur.fetchone()
        if not row:
            return _bad("Request not found.", 404)

        reqd = _row_to_dict(cur, row)
        if not _employee_belongs_to_admin(cur, reqd.get("employee_id"), admin_id):
            return _bad("Request not found.", 404)
        req_status = str(reqd.get("status") or "pending").strip().lower()
        if req_status != "pending":
            return _bad(f"Request is already {req_status}.", 400)

        data = request.get_json(silent=True) or {}
        reason = str(data.get("reason") or "").strip()

        cur.execute("PRAGMA table_info(employee_change_requests)")
        req_cols = {str(r[1]) for r in cur.fetchall()}
        updates = ["status = 'rejected'"]
        params: List[Any] = []
        if reason and "reason" in req_cols:
            updates.append("reason = ?")
            params.append(reason)
        if "updated_at" in req_cols:
            updates.append("updated_at = datetime('now')")
        params.append(req_id)
        cur.execute(
            f"UPDATE employee_change_requests SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        conn.commit()
        return _ok({"request_id": req_id}, "Request rejected.")
    except Exception as e:
        return _bad(f"Failed to reject request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# DRIVER REQUESTS + DRIVERS
# =========================================================

@admin_bp.route("/admin/driver-requests", methods=["GET"])
@admin_bp.route("/api/admin/driver-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_driver_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        repo = RequestRepo(conn)
        results = repo.list_pending_driver_requests(
            admin_id=admin_id,
            selected_columns="id, name, mobile, dl_no, cab_no, vehicle_type, home_town, status, created_at",
        )
        return _ok(results)
    except Exception as e:
        return _bad(f"Failed to load driver requests: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/driver-requests/<req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/driver-requests/<req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_driver_request(req_id):
    admin_id = _current_admin_id()
    try:
        req_id = int(req_id)
    except ValueError:
        return _bad("Invalid Request ID", 400)

    print(f"DEBUG: approve_driver_request hit for {req_id}")
    conn = get_db()
    try:
        cur = conn.cursor()
        repo = RequestRepo(conn)
        reqd = repo.get_driver_request_by_id(req_id, admin_id=admin_id)
        if not reqd:
            return _bad("Driver request not found.", 404)
        repo.claim_request_admin(table_name="driver_requests", req_id=req_id, admin_id=admin_id)


        # Merge DB data with Request Body to allow patching missing fields (like vehicle_type)
        data = request.get_json(silent=True) or {}
        
        # Priority: Request Body > DB Record
        merged_data = {
            "name": data.get("name") or reqd.get("name"),
            "mobile": data.get("mobile") or reqd.get("mobile"),
            "dl_no": data.get("dl_no") or reqd.get("dl_no"),
            "cab_no": data.get("cab_no") or reqd.get("cab_no"),
            "vehicle_type": data.get("vehicle_type") or reqd.get("vehicle_type") or "4", # Default to 4 (Sedan) if missing
            "home_town": data.get("home_town") or reqd.get("home_town"),
            "home_lat": data.get("home_lat") if data.get("home_lat") is not None else reqd.get("lat"),
            "home_lng": data.get("home_lng") if data.get("home_lng") is not None else reqd.get("lng"),
        }

        # Validate merged payload
        ok, msg = validate_driver_payload(merged_data)
        if not ok:
            return _bad(f"Invalid driver request data: {msg}", 400)

        # Generate default password for the driver
        password, salt, hash_val = _generate_default_password()
        
        # Generate driver ID (TEXT UUID-style)
        import uuid
        driver_id = str(uuid.uuid4())
        
        # Insert into drivers - use vehicle_no (DB column) not cab_no
        cur.execute(
            """
            INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, 
                               primary_admin_id, is_approved, is_online, last_seen, password_salt, password_hash, 
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, NULL, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                driver_id,
                merged_data.get("name"),
                merged_data.get("mobile"),
                merged_data.get("dl_no"),
                merged_data.get("cab_no"),  # Maps to vehicle_no column
                merged_data.get("vehicle_type"),
                merged_data.get("home_town"),
                admin_id,
                salt,
                hash_val,
            ),
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO driver_admin_assignments (driver_id, admin_id, is_active)
            VALUES (?, ?, 1)
            """,
            (driver_id, admin_id),
        )

        resolved_lat, resolved_lng, _ = _resolve_address_coords(
            conn,
            address=merged_data.get("home_town"),
            lat=merged_data.get("home_lat"),
            lng=merged_data.get("home_lng"),
        )
        if _is_valid_coord_pair(resolved_lat, resolved_lng):
            cur.execute("PRAGMA table_info(drivers)")
            dcols = {str(r[1]) for r in cur.fetchall()}
            updates: List[str] = []
            params: List[Any] = []
            if "hometown_lat" in dcols:
                updates.append("hometown_lat = ?")
                params.append(resolved_lat)
            if "hometown_lng" in dcols:
                updates.append("hometown_lng = ?")
                params.append(resolved_lng)
            if "home_lat" in dcols:
                updates.append("home_lat = ?")
                params.append(resolved_lat)
            if "home_lng" in dcols:
                updates.append("home_lng = ?")
                params.append(resolved_lng)
            if updates:
                params.append(driver_id)
                cur.execute(f"UPDATE drivers SET {', '.join(updates)} WHERE id = ?", tuple(params))

        # Update request status (use capitalized)
        cur.execute(
            "UPDATE driver_requests SET status = 'Approved', admin_id = COALESCE(NULLIF(admin_id, ''), ?) WHERE id = ?",
            (admin_id, req_id),
        )
        conn.commit()
        
        # Log the temporary password (in production, send via SMS/email)
        print(f"Temp password for driver {reqd.get('name')} (mobile: {reqd.get('mobile')}): {password}")
        
        return _ok({"request_id": req_id, "driver_id": driver_id}, "Driver approved and added.")
    except Exception as e:
        return _bad(f"Failed to approve driver: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/driver-requests/<req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/driver-requests/<req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_driver_request(req_id):
    admin_id = _current_admin_id()
    try:
        req_id = int(req_id)
    except ValueError:
        return _bad("Invalid Request ID", 400)
    
    conn = get_db()
    try:
        repo = RequestRepo(conn)
        req = repo.get_driver_request_by_id(req_id, admin_id=admin_id)
        if not req:
            return _bad("Driver request not found.", 404)
        repo.claim_request_admin(table_name="driver_requests", req_id=req_id, admin_id=admin_id)

        # Get rejection reason
        data = request.get_json(silent=True) or {}
        reason = data.get("reason", "").strip()
        
        # Use Repo to update status & note
        repo = RequestRepo(conn)
        repo.update_driver_request_status(req_id, "Rejected", note=reason)
        
        return _ok({"request_id": req_id}, "Driver request rejected.")
    except Exception as e:
        return _bad(f"Failed to reject driver request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/drivers", methods=["GET"])
@admin_bp.route("/api/admin/drivers", methods=["GET"])
@require_auth(roles=['admin'])
def list_drivers():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        has_temp_col = _ensure_temporary_driver_column(cur)
        temp_filter = "AND COALESCE(is_temporary, 0) = 0" if has_temp_col else "AND UPPER(COALESCE(dl_no, '')) <> 'ADHOC_SWAP'"
        cur.execute("PRAGMA table_info(drivers)")
        dcols = {str(r[1]) for r in cur.fetchall()}
        lat_expr = "NULL"
        lng_expr = "NULL"
        if "hometown_lat" in dcols and "home_lat" in dcols:
            lat_expr = "COALESCE(hometown_lat, home_lat)"
        elif "hometown_lat" in dcols:
            lat_expr = "hometown_lat"
        elif "home_lat" in dcols:
            lat_expr = "home_lat"
        if "hometown_lng" in dcols and "home_lng" in dcols:
            lng_expr = "COALESCE(hometown_lng, home_lng)"
        elif "hometown_lng" in dcols:
            lng_expr = "hometown_lng"
        elif "home_lng" in dcols:
            lng_expr = "home_lng"
        # Use correct DB column names: vehicle_no, is_approved
        cur.execute(
            f"""
            SELECT drivers.id, drivers.name, drivers.mobile, drivers.dl_no, drivers.vehicle_no, drivers.vehicle_type, drivers.home_town,
                   {lat_expr} AS home_lat, {lng_expr} AS home_lng,
                   drivers.is_approved, drivers.is_online, drivers.last_seen
            FROM drivers
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = drivers.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            WHERE 1=1
            {temp_filter}
            ORDER BY drivers.id DESC
            """,
            (admin_id,),
        )
        rows = cur.fetchall() or []
        # Normalize response: vehicle_no → cab_no, is_approved → approved
        results = [_normalize_driver_response(_row_to_dict(cur, r)) for r in rows]
        return _ok(results)
    except Exception as e:
        return _bad(f"Failed to load drivers: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/drivers/<string:driver_id>", methods=["PUT"])
@admin_bp.route("/api/admin/drivers/<string:driver_id>", methods=["PUT"])
@require_auth(roles=['admin'])
def update_driver(driver_id: str):
    admin_id = _current_admin_id()
    data = request.get_json(silent=True) or {}
    ok, msg = validate_driver_payload(data)
    if not ok:
        return _bad(msg, 400)
    provided_lat = _to_float_or_none(data.get("home_lat"))
    provided_lng = _to_float_or_none(data.get("home_lng"))
    if (data.get("home_lat") is None) ^ (data.get("home_lng") is None):
        return _bad("Both home_lat and home_lng are required together.", 400)
    if (data.get("home_lat") is not None or data.get("home_lng") is not None) and not _is_valid_coord_pair(provided_lat, provided_lng):
        return _bad("home_lat/home_lng invalid.", 400)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.id
            FROM drivers d
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            WHERE d.id = ?
            LIMIT 1
            """,
            (admin_id, driver_id),
        )
        if not cur.fetchone():
            return _bad("Driver not found.", 404)

        # Use correct DB column names: vehicle_no (not cab_no), is_approved (not approved)
        cur.execute(
            """
            UPDATE drivers
            SET name = ?, mobile = ?, dl_no = ?, vehicle_no = ?, vehicle_type = ?, home_town = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                data.get("name"),
                data.get("mobile"),
                data.get("dl_no"),
                data.get("cab_no"),  # Maps to vehicle_no column
                data.get("vehicle_type"),
                data.get("home_town"),
                driver_id,
            ),
        )

        resolved_lat, resolved_lng, _ = _resolve_address_coords(
            conn,
            address=data.get("home_town"),
            lat=provided_lat,
            lng=provided_lng,
        )
        if _is_valid_coord_pair(resolved_lat, resolved_lng):
            cur.execute("PRAGMA table_info(drivers)")
            dcols = {str(r[1]) for r in cur.fetchall()}
            updates: List[str] = []
            params: List[Any] = []
            if "hometown_lat" in dcols:
                updates.append("hometown_lat = ?")
                params.append(resolved_lat)
            if "hometown_lng" in dcols:
                updates.append("hometown_lng = ?")
                params.append(resolved_lng)
            if "home_lat" in dcols:
                updates.append("home_lat = ?")
                params.append(resolved_lat)
            if "home_lng" in dcols:
                updates.append("home_lng = ?")
                params.append(resolved_lng)
            if updates:
                params.append(driver_id)
                cur.execute(f"UPDATE drivers SET {', '.join(updates)} WHERE id = ?", tuple(params))

        conn.commit()
        return _ok({"driver_id": driver_id}, "Driver updated.")
    except Exception as e:
        return _bad(f"Failed to update driver: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/drivers", methods=["POST"])
@admin_bp.route("/api/admin/drivers", methods=["POST"])
@require_auth(roles=['admin'])
def create_driver_by_admin():
    """
    Admin creates a new driver directly (automatically approved).
    Body:
    {
      "name": "Driver Name",
      "mobile": "1234567890",
      "dl_no": "MH1420200012345",
      "cab_no": "MH12AB1234",
      "vehicle_type": "4",
      "home_town": "Pune, Maharashtra"
    }
    """
    data = request.get_json(silent=True) or {}
    admin_id = _current_admin_id()
    ok, msg = validate_driver_payload(data)
    if not ok:
        return _bad(msg, 400)
    provided_lat = _to_float_or_none(data.get("home_lat"))
    provided_lng = _to_float_or_none(data.get("home_lng"))
    if (data.get("home_lat") is None) ^ (data.get("home_lng") is None):
        return _bad("Both home_lat and home_lng are required together.", 400)
    if (data.get("home_lat") is not None or data.get("home_lng") is not None) and not _is_valid_coord_pair(provided_lat, provided_lng):
        return _bad("home_lat/home_lng invalid.", 400)

    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check for duplicates
        mobile = data.get("mobile")
        dl_no = data.get("dl_no")
        cab_no = data.get("cab_no")
        
        cur.execute("SELECT id FROM drivers WHERE mobile = ? LIMIT 1", (mobile,))
        if cur.fetchone():
            return _bad("Driver with this mobile number already exists.", 400)
        
        cur.execute("SELECT id FROM drivers WHERE dl_no = ? LIMIT 1", (dl_no,))
        if cur.fetchone():
            return _bad("Driver with this license number already exists.", 400)
        
        cur.execute("SELECT id FROM drivers WHERE vehicle_no = ? LIMIT 1", (cab_no,))
        if cur.fetchone():
            return _bad("Driver with this vehicle number already exists.", 400)

        # Generate driver ID and password
        import uuid
        driver_id = str(uuid.uuid4())
        password, salt, hash_val = _generate_default_password()

        # Insert new driver (approved by default) - use vehicle_no column
        cur.execute(
            """
            INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, 
                               primary_admin_id, is_approved, is_online, last_seen, password_salt, password_hash,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, NULL, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                driver_id,
                data.get("name"),
                data.get("mobile"),
                data.get("dl_no"),
                data.get("cab_no"),  # Maps to vehicle_no column
                data.get("vehicle_type"),
                data.get("home_town"),
                admin_id,
                salt,
                hash_val,
            ),
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO driver_admin_assignments (driver_id, admin_id, is_active)
            VALUES (?, ?, 1)
            """,
            (driver_id, admin_id),
        )

        resolved_lat, resolved_lng, _ = _resolve_address_coords(
            conn,
            address=data.get("home_town"),
            lat=provided_lat,
            lng=provided_lng,
        )
        if _is_valid_coord_pair(resolved_lat, resolved_lng):
            cur.execute("PRAGMA table_info(drivers)")
            dcols = {str(r[1]) for r in cur.fetchall()}
            updates: List[str] = []
            params: List[Any] = []
            if "hometown_lat" in dcols:
                updates.append("hometown_lat = ?")
                params.append(resolved_lat)
            if "hometown_lng" in dcols:
                updates.append("hometown_lng = ?")
                params.append(resolved_lng)
            if "home_lat" in dcols:
                updates.append("home_lat = ?")
                params.append(resolved_lat)
            if "home_lng" in dcols:
                updates.append("home_lng = ?")
                params.append(resolved_lng)
            if updates:
                params.append(driver_id)
                cur.execute(f"UPDATE drivers SET {', '.join(updates)} WHERE id = ?", tuple(params))

        conn.commit()
        
        # Log the temporary password (in production, send via SMS/email)
        print(f"Temp password for new driver {data.get('name')} (mobile: {data.get('mobile')}): {password}")
        
        return _ok({"driver_id": driver_id, "cab_no": cab_no}, "Driver created successfully.")
    except Exception as e:
        return _bad(f"Failed to create driver: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/drivers/<string:driver_id>", methods=["DELETE"])
@admin_bp.route("/api/admin/drivers/<string:driver_id>", methods=["DELETE"])
@require_auth(roles=['admin'])
def delete_driver(driver_id: str):
    """
    Delete a driver from the current admin company.
    Global driver row is deleted only when no admin links remain.
    """
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT d.id
            FROM drivers d
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            WHERE d.id = ?
            LIMIT 1
            """,
            (admin_id, driver_id),
        )
        if not cur.fetchone():
            return _bad("Driver not found.", 404)

        cur.execute(
            """
            SELECT id FROM trips
            WHERE driver_id = ? AND status IN ('active', 'in_progress', 'assigned')
            LIMIT 1
            """,
            (driver_id,),
        )
        if cur.fetchone():
            return _bad("Cannot delete driver with active trips. Please complete or cancel trips first.", 400)

        cur.execute(
            "DELETE FROM driver_admin_assignments WHERE driver_id = ? AND admin_id = ?",
            (driver_id, admin_id),
        )
        cur.execute(
            "SELECT COUNT(*) AS c FROM driver_admin_assignments WHERE driver_id = ? AND is_active = 1",
            (driver_id,),
        )
        remaining_links = int(_row_to_dict(cur, cur.fetchone()).get("c") or 0)
        if remaining_links == 0:
            cur.execute("DELETE FROM driver_live_locations WHERE driver_id = ?", (driver_id,))
            cur.execute("DELETE FROM driver_change_requests WHERE driver_id = ?", (driver_id,))
            cur.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))
        conn.commit()
        return _ok({"driver_id": driver_id}, "Driver deleted successfully.")
    except Exception as e:
        return _bad(f"Failed to delete driver: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/drivers/search", methods=["GET"])
@admin_bp.route("/api/admin/drivers/search", methods=["GET"])
@require_auth(roles=['admin'])
def search_drivers():
    """
    Search for drivers by name, mobile, dl_no, vehicle_no, or home_town.
    Query parameter: ?query=searchterm
    Returns normalized response with cab_no and approved fields.
    """
    query = (request.args.get("query") or "").strip().lower()
    admin_id = _current_admin_id()
    
    if not query:
        return _bad("Query parameter is required", 400)
    
    conn = get_db()
    try:
        cur = conn.cursor()
        has_temp_col = _ensure_temporary_driver_column(cur)
        temp_filter = "AND COALESCE(is_temporary, 0) = 0" if has_temp_col else "AND UPPER(COALESCE(dl_no, '')) <> 'ADHOC_SWAP'"
        # Fuzzy search on multiple fields
        like_pattern = f"%{query}%"
        cur.execute(
            f"""
            SELECT drivers.id, drivers.name, drivers.mobile, drivers.dl_no, drivers.vehicle_no, drivers.vehicle_type, drivers.home_town,
                   drivers.is_approved, drivers.is_online, drivers.last_seen
            FROM drivers
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = drivers.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            WHERE (
                   LOWER(name) LIKE ? 
                OR LOWER(mobile) LIKE ?
                OR LOWER(dl_no) LIKE ?
                OR LOWER(vehicle_no) LIKE ?
                OR LOWER(home_town) LIKE ?
            )
            {temp_filter}
            ORDER BY name ASC
            LIMIT 50
            """,
            (admin_id, like_pattern, like_pattern, like_pattern, like_pattern, like_pattern)
        )
        rows = cur.fetchall() or []
        # Normalize response: vehicle_no → cab_no, is_approved → approved
        results = [_normalize_driver_response(_row_to_dict(cur, r)) for r in rows]
        return _ok(results)
    except Exception as e:
        return _bad(f"Failed to search drivers: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# EMPLOYEE REQUESTS + EMPLOYEES
# =========================================================

@admin_bp.route("/admin/employee-requests", methods=["GET"])
@admin_bp.route("/api/admin/employee-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_employee_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        repo = RequestRepo(conn)
        results = repo.list_pending_employee_requests(
            admin_id=admin_id,
            selected_columns="id, name, mobile, login_time, logout_time, home_address as address, lat, lng, status, created_at",
        )
        return _ok(results)
    except Exception as e:
        return _bad(f"Failed to load employee requests: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/employee-requests/<req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/employee-requests/<req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_employee_request(req_id):
    admin_id = _current_admin_id()
    try:
        req_id = int(req_id)
    except ValueError:
        return _bad("Invalid Request ID", 400)

    conn = get_db()
    try:
        cur = conn.cursor()
        repo = RequestRepo(conn)
        reqd = repo.get_employee_request_by_id(req_id, admin_id=admin_id)
        if not reqd:
            return _bad("Employee request not found.", 404)
        repo.claim_request_admin(table_name="employee_requests", req_id=req_id, admin_id=admin_id)

        # Check for duplicate mobile FIRST
        cur.execute("SELECT id FROM employees WHERE mobile = ? LIMIT 1", (reqd.get("mobile"),))
        if cur.fetchone():
             return _bad("Employee with this mobile number already exists.", 400)

        ok, msg = validate_employee_payload(
            {
                "name": reqd.get("name"),
                "mobile": reqd.get("mobile"),
                "login_time": reqd.get("login_time"),
                "logout_time": reqd.get("logout_time"),
                "address": reqd.get("home_address"),  # Fixed: DB column is home_address
            }
        )
        if not ok:
            return _bad(f"Invalid employee request data: {msg}", 400)

        # employee_code should be generated elsewhere; keep simple here
        employee_code = reqd.get("employee_code") or f"EMP{req_id:05d}"

        resolved_lat, resolved_lng, _ = _resolve_address_coords(
            conn,
            address=reqd.get("home_address"),
            lat=reqd.get("lat"),
            lng=reqd.get("lng"),
        )
        if not _is_valid_coord_pair(resolved_lat, resolved_lng):
            return _bad("Unable to resolve employee coordinates from address.", 400)

        cur.execute(
            """
            INSERT INTO employees (name, mobile, employee_code, login_time, logout_time, home_address, home_lat, home_lng, admin_id, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                reqd.get("name"),
                reqd.get("mobile"),
                employee_code,
                reqd.get("login_time"),
                reqd.get("logout_time"),
                reqd.get("home_address"),  # Fixed: map home_address correctly
                resolved_lat,
                resolved_lng,
                admin_id,
            ),
        )
        _sync_employee_location_fields(
            cur,
            conn,
            employee_id=int(cur.lastrowid),
            address=reqd.get("home_address"),
            lat=resolved_lat,
            lng=resolved_lng,
        )

        # Capitalize status for consistency
        cur.execute(
            "UPDATE employee_requests SET status = 'Approved', admin_id = COALESCE(NULLIF(admin_id, ''), ?) WHERE id = ?",
            (admin_id, req_id),
        )
        conn.commit()
        return _ok({"request_id": req_id, "employee_code": employee_code}, "Employee approved and added.")
    except Exception as e:
        return _bad(f"Failed to approve employee: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/employee-requests/<req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/employee-requests/<req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_employee_request(req_id):
    admin_id = _current_admin_id()
    try:
        req_id = int(req_id)
    except ValueError:
        return _bad("Invalid Request ID", 400)

    conn = get_db()
    try:
        repo = RequestRepo(conn)
        req = repo.get_employee_request_by_id(req_id, admin_id=admin_id)
        if not req:
            return _bad("Employee request not found.", 404)
        repo.claim_request_admin(table_name="employee_requests", req_id=req_id, admin_id=admin_id)

        # Get rejection reason
        data = request.get_json(silent=True) or {}
        reason = data.get("reason", "").strip()

        # Update status & note using Repo or direct SQL
        # Using direct SQL here to match existing style in this block, or switch to Repo if preferred.
        # Matching existing code style but adding review_note and reviewed_at
        cur.execute(
            """
            UPDATE employee_requests 
            SET status = 'Rejected', review_note = ?, reviewed_at = datetime('now') 
            WHERE id = ?
            """, 
            (reason, req_id)
        )
        conn.commit()
        return _ok({"request_id": req_id}, "Employee request rejected.")
    except Exception as e:
        return _bad(f"Failed to reject employee request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/employees", methods=["GET"])
@admin_bp.route("/api/admin/employees", methods=["GET"])
@require_auth(roles=['admin'])
def list_employees():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        search = (request.args.get("search") or "").strip().lower()
        
        if search:
            # NLP-like multi-term search
            # Split query into terms: "Rohit Pune" -> ["Rohit", "Pune"]
            # Match if ALL terms are present in ANY column (name OR mobile OR code OR address)
            terms = search.split()
            conditions = []
            params = []
            
            for term in terms:
                pat = f"%{term}%"
                conditions.append(
                    "(LOWER(name) LIKE ? OR LOWER(mobile) LIKE ? OR LOWER(employee_code) LIKE ? OR LOWER(home_address) LIKE ?)"
                )
                params.extend([pat, pat, pat, pat])
            
            where_clause = " AND ".join(conditions)
            
            cur.execute(
                f"""
                SELECT id, name, mobile, employee_code, login_time, logout_time, home_address as address, home_lat as lat, home_lng as lng, is_approved
                FROM employees
                WHERE admin_id = ? AND {where_clause}
                ORDER BY id DESC
                """,
                [admin_id, *params]
            )
        else:
            cur.execute(
                """
                SELECT id, name, mobile, employee_code, login_time, logout_time, home_address as address, home_lat as lat, home_lng as lng, is_approved
                FROM employees
                WHERE admin_id = ?
                ORDER BY id DESC
                """,
                (admin_id,),
            )
            
        rows = cur.fetchall() or []
        return _ok([_row_to_dict(cur, r) for r in rows])
    except Exception as e:
        return _bad(f"Failed to load employees: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass

@admin_bp.route("/admin/employees/<int:emp_id>", methods=["DELETE"])
@admin_bp.route("/api/admin/employees/<int:emp_id>", methods=["DELETE"])
@require_auth(roles=['admin'])
def delete_employee(emp_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check existence
        cur.execute(
            "SELECT id, mobile FROM employees WHERE id = ? AND admin_id = ?",
            (emp_id, admin_id),
        )
        emp_row = cur.fetchone()
        if not emp_row:
            return _bad("Employee not found.", 404)
        employee_mobile = emp_row["mobile"] if isinstance(emp_row, sqlite3.Row) else emp_row[1]

        # Check for active trips
        cur.execute(
            """
            SELECT t.id FROM trips t
            JOIN trip_employees tm ON tm.trip_id = t.id
            WHERE tm.employee_id = ? AND t.status IN ('active', 'in_progress', 'assigned')
            LIMIT 1
            """, 
            (emp_id,)
        )
        if cur.fetchone():
             return _bad("Cannot delete employee with active trips.", 400)

        # Cleanup dependent records for legacy DBs that may still have NO ACTION FKs.
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_rows = cur.fetchall() or []
        table_names = [r["name"] if isinstance(r, sqlite3.Row) else r[0] for r in table_rows]

        for table_name in table_names:
            if table_name == "employees":
                continue
            cur.execute(f"PRAGMA foreign_key_list({table_name})")
            fk_rows = cur.fetchall() or []
            for fk in fk_rows:
                parent_table = fk["table"] if isinstance(fk, sqlite3.Row) else fk[2]
                from_col = fk["from"] if isinstance(fk, sqlite3.Row) else fk[3]
                on_delete = (fk["on_delete"] if isinstance(fk, sqlite3.Row) else fk[6] or "").upper()
                if parent_table != "employees":
                    continue
                if on_delete in {"SET NULL", "SET DEFAULT"}:
                    cur.execute(
                        f'UPDATE "{table_name}" SET "{from_col}" = NULL WHERE "{from_col}" = ?',
                        (emp_id,),
                    )
                else:
                    cur.execute(
                        f'DELETE FROM "{table_name}" WHERE "{from_col}" = ?',
                        (emp_id,),
                    )

        # Explicit request cleanup for mobile-based request records.
        if employee_mobile:
            cur.execute("DELETE FROM employee_requests WHERE mobile = ?", (employee_mobile,))

        # Delete employee after dependent cleanup.
        cur.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        
        conn.commit()
        return _ok({"employee_id": emp_id}, "Employee removed.")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return _bad(f"Cannot delete employee due to linked records: {e}", 400)
    except Exception as e:
        conn.rollback()
        return _bad(f"Failed to delete employee: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/employees/<int:emp_id>", methods=["PUT"])
@admin_bp.route("/api/admin/employees/<int:emp_id>", methods=["PUT"])
@require_auth(roles=['admin'])
def update_employee(emp_id: int):
    admin_id = _current_admin_id()
    data = request.get_json(silent=True) or {}
    ok, msg = validate_employee_payload(data)
    if not ok:
        return _bad(msg, 400)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, home_lat, home_lng FROM employees WHERE id = ? AND admin_id = ? LIMIT 1",
            (emp_id, admin_id),
        )
        row = cur.fetchone()
        if not row:
            return _bad("Employee not found.", 404)

        resolved_lat, resolved_lng, coord_source = _resolve_address_coords(
            conn,
            address=data.get("address"),
            lat=data.get("lat"),
            lng=data.get("lng"),
        )
        coordinate_warning: Optional[str] = None
        if not _is_valid_coord_pair(resolved_lat, resolved_lng):
            old = _row_to_dict(cur, row)
            old_lat = _to_float_or_none(old.get("home_lat"))
            old_lng = _to_float_or_none(old.get("home_lng"))
            if _is_valid_coord_pair(old_lat, old_lng):
                resolved_lat, resolved_lng = old_lat, old_lng
                coord_source = "existing"
                coordinate_warning = "Address geocode unavailable; kept existing employee coordinates."
            else:
                office_lat, office_lng = _resolve_office_coords(conn)
                if _is_valid_coord_pair(office_lat, office_lng):
                    resolved_lat, resolved_lng = office_lat, office_lng
                    coord_source = "office_fallback"
                    coordinate_warning = "Address geocode unavailable; used office coordinates as fallback."
                else:
                    # Do not hard-fail profile update if geocoding service is unavailable.
                    # Keep unresolved values so non-location fields can still be updated.
                    resolved_lat, resolved_lng = old_lat, old_lng
                    coord_source = "unresolved"
                    coordinate_warning = (
                        "Address geocode unavailable and no fallback coordinates found. "
                        "Employee saved without valid coordinates."
                    )

        cur.execute(
            """
            UPDATE employees
            SET name = ?, mobile = ?, login_time = ?, logout_time = ?,
                home_address = ?, home_lat = ?, home_lng = ?
            WHERE id = ?
            """,
            (
                data.get("name"),
                data.get("mobile"),
                data.get("login_time"),
                data.get("logout_time"),
                data.get("address"),
                resolved_lat,
                resolved_lng,
                emp_id,
            ),
        )
        _sync_employee_location_fields(
            cur,
            conn,
            employee_id=emp_id,
            address=data.get("address"),
            lat=resolved_lat,
            lng=resolved_lng,
        )
        conn.commit()
        payload = {"employee_id": emp_id, "coordinate_source": coord_source}
        if coordinate_warning:
            return _ok(payload, "Employee updated.", warnings=[coordinate_warning])
        return _ok(payload, "Employee updated.")
    except Exception as e:
        return _bad(f"Failed to update employee: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass

@admin_bp.route("/admin/employees", methods=["POST"])
@admin_bp.route("/api/admin/employees", methods=["POST"])
@require_auth(roles=['admin'])
def create_employee_by_admin():
    """
    Admin creates a new employee directly (automatically approved).
    Body:
    {
      "name": "Employee Name",
      "mobile": "1234567890",
      "login_time": "09:00",
      "logout_time": "18:00",
      "address": "Full Address",
      "lat": 0.0,
      "lng": 0.0
    }
    """
    data = request.get_json(silent=True) or {}
    admin_id = _current_admin_id()
    ok, msg = validate_employee_payload(data)
    if not ok:
        return _bad(msg, 400)

    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check for duplicates
        mobile = data.get("mobile")
        cur.execute("SELECT id FROM employees WHERE mobile = ? LIMIT 1", (mobile,))
        if cur.fetchone():
            return _bad("Employee with this mobile number already exists.", 400)

        resolved_lat, resolved_lng, coord_source = _resolve_address_coords(
            conn,
            address=data.get("address"),
            lat=data.get("lat"),
            lng=data.get("lng"),
        )
        coordinate_warning: Optional[str] = None
        if not _is_valid_coord_pair(resolved_lat, resolved_lng):
            office_lat, office_lng = _resolve_office_coords(conn)
            if _is_valid_coord_pair(office_lat, office_lng):
                resolved_lat, resolved_lng = office_lat, office_lng
                coord_source = "office_fallback"
                coordinate_warning = "Address geocode unavailable; used office coordinates as fallback."
            else:
                # Do not block employee creation due to geocode outage/input ambiguity.
                # Save with unresolved coordinates and return warning to UI.
                resolved_lat, resolved_lng = None, None
                coord_source = "unresolved"
                coordinate_warning = (
                    "Address geocode unavailable and no fallback coordinates found. "
                    "Employee created without valid coordinates."
                )
        
        # Insert
        # Generates employee_code after ID is known, or use a temp one then update?
        # Better: use a simple random/sequence code for now or MAX(id)+1
        
        # Let's insert first to get ID
        cur.execute(
            """
            INSERT INTO employees (name, mobile, employee_code, login_time, logout_time, home_address, home_lat, home_lng, admin_id, is_approved)
            VALUES (?, ?, 'TEMP', ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                data.get("name"),
                data.get("mobile"),
                data.get("login_time"),
                data.get("logout_time"),
                data.get("address"),
                resolved_lat,
                resolved_lng,
                admin_id,
            ),
        )
        emp_id = cur.lastrowid
        _sync_employee_location_fields(
            cur,
            conn,
            employee_id=int(emp_id),
            address=data.get("address"),
            lat=resolved_lat,
            lng=resolved_lng,
        )
        
        # Generate code: EMP + 5 digit ID
        code = f"EMP{emp_id:05d}"
        cur.execute("UPDATE employees SET employee_code = ? WHERE id = ?", (code, emp_id))
        
        conn.commit()
        payload = {
            "employee_id": emp_id,
            "employee_code": code,
            "coordinate_source": coord_source,
        }
        if coordinate_warning:
            return _ok(payload, "Employee created successfully.", warnings=[coordinate_warning])
        return _ok(payload, "Employee created successfully.")
    except Exception as e:
        return _bad(f"Failed to create employee: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass
# GROUPING + ASSIGN TRIP
# =========================================================

@admin_bp.route("/admin/groups/create-and-assign", methods=["POST"])
@admin_bp.route("/api/admin/groups/create-and-assign", methods=["POST"])
def create_group_and_assign_trip():
    """
    Creates groups and assigns trips.

    Payload supports AUTO or MANUAL:

    AUTO (default):
    {
      "admin_id": 1,
      "operation": "pickup"|"drop",
      "trip_time": "09:30",
      "vehicle_type": 4|6,
      "driver_id": 12,              # optional
      "origin_office": {"lat":..,"lng":..},   # required for routing km
      "optimize_route": true
    }

    MANUAL override:
    {
      "admin_id": 1,
      "operation": "pickup",
      "trip_time": "09:30",
      "vehicle_type": 6,
      "driver_id": 12,
      "employee_ids": [1,2,3,4,5,6],   # admin-selected employees
      "manual_override": true,
      "origin_office": {"lat":..,"lng":..}
    }

    Response returns created trip(s) with route_no, otp info, route polyline, total_km.
    """
    payload = request.get_json(silent=True) or {}

    admin_id = str(payload.get("admin_id") or "").strip()
    operation = (payload.get("operation") or payload.get("trip_type") or "").lower().strip()
    trip_time = str(payload.get("trip_time") or payload.get("selected_time") or payload.get("time_slot") or "").strip()
    raw_vehicle_type = payload.get("vehicle_type")
    raw_vehicle_types = payload.get("vehicle_types")
    driver_id = payload.get("driver_id")
    manual_override = bool(payload.get("manual_override", False))
    employee_ids = payload.get("employee_ids") or []
    origin_office = payload.get("origin_office") or {}
    trip_day = str(payload.get("trip_day") or datetime.now().strftime("%Y%m%d")).replace("-", "")

    if not admin_id:
        return _bad("admin_id is required.")
    if operation not in ("pickup", "drop"):
        return _bad("operation must be 'pickup' or 'drop'.")
    ok, msg = validate_hhmm(trip_time)
    if not ok:
        return _bad(msg)

    vehicle_types: List[int] = []
    if isinstance(raw_vehicle_types, list):
        for v in raw_vehicle_types:
            try:
                iv = int(v)
                if iv in (4, 6) and iv not in vehicle_types:
                    vehicle_types.append(iv)
            except Exception:
                continue
    if not vehicle_types:
        try:
            iv = int(raw_vehicle_type)
            if iv in (4, 6):
                vehicle_types = [iv]
        except Exception:
            pass
    if not vehicle_types:
        return _bad("vehicle_type/vehicle_types must contain 4 and/or 6.")

    conn = get_db()
    try:
        cur = conn.cursor()
        office_lat = _to_float_or_none(
            origin_office.get("lat") if isinstance(origin_office, dict) else None
        )
        office_lng = _to_float_or_none(
            origin_office.get("lng") if isinstance(origin_office, dict) else None
        )
        if not _is_valid_coord_pair(office_lat, office_lng):
            # Prefer admin-specific saved office coordinates.
            try:
                cur.execute(
                    "SELECT office_lat, office_lng FROM admins WHERE CAST(id AS TEXT) = ? LIMIT 1",
                    (admin_id,),
                )
                row = cur.fetchone()
                if row:
                    office_lat = _to_float_or_none(row[0])
                    office_lng = _to_float_or_none(row[1])
            except Exception:
                pass

        if not _is_valid_coord_pair(office_lat, office_lng):
            # Last fallback: first available admin profile office coordinates.
            office_lat, office_lng = _resolve_office_coords(conn)

        if not _is_valid_coord_pair(office_lat, office_lng):
            return _bad(
                "Office coordinates are missing. Set admin office location on map first or send origin_office.lat/lng."
            )

        # Resolve optional manual employee override.
        selected_employee_ids: Optional[List[int]] = None
        if manual_override:
            if not isinstance(employee_ids, list) or not employee_ids:
                return _bad("manual_override requires employee_ids.")
            selected_employee_ids = []
            for eid in employee_ids:
                try:
                    selected_employee_ids.append(int(eid))
                except Exception:
                    continue
            if not selected_employee_ids:
                return _bad("manual employee_ids must contain valid integers.")

        eligible_employees, exclusions = filter_eligible_employees(
            conn,
            trip_type=operation,
            selected_time=trip_time,
            employee_ids=selected_employee_ids,
            trip_day=trip_day,
            admin_id=admin_id,
        )
        if not eligible_employees:
            return _bad("No eligible employees for selected slot.", exclusions=exclusions)

        employee_nodes, unresolved_coords = _build_employee_nodes_strict(
            eligible_employees,
            operation,
        )
        if unresolved_coords:
            exclusions = list(exclusions or [])
            exclusions.append(
                f"Excluded {len(unresolved_coords)} employees due to missing/invalid coordinates"
            )
        if not employee_nodes:
            return _bad(
                "No employees with valid coordinates for selected slot.",
                exclusions=exclusions,
                unresolved_coordinates=unresolved_coords,
            )

        # Build go-home approved set.
        go_home_ids: set[str] = set()
        try:
            cur.execute("PRAGMA table_info(driver_hometown_requests)")
            cols = {str(r[1]) for r in cur.fetchall()}
            if "travel_date" in cols:
                day_dash = f"{trip_day[:4]}-{trip_day[4:6]}-{trip_day[6:]}" if len(trip_day) == 8 else trip_day
                cur.execute(
                    """
                    SELECT r.driver_id
                    FROM driver_hometown_requests r
                    WHERE r.status = 'approved'
                      AND (
                        REPLACE(COALESCE(r.travel_date, ''), '-', '') = ?
                        OR COALESCE(r.travel_date, '') = ?
                        OR COALESCE(r.travel_date, '') = ''
                      )
                      AND NOT EXISTS (
                        SELECT 1
                        FROM trips t
                        WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                          AND LOWER(COALESCE(t.status, 'created')) IN
                              ('created','assigned','started','active','in_progress','live','completed')
                          AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                              datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                      )
                    ORDER BY r.id DESC
                    """,
                    (trip_day, day_dash),
                )
            else:
                cur.execute(
                    """
                    SELECT r.driver_id
                    FROM driver_hometown_requests r
                    WHERE r.status = 'approved'
                      AND NOT EXISTS (
                        SELECT 1
                        FROM trips t
                        WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                          AND LOWER(COALESCE(t.status, 'created')) IN
                              ('created','assigned','started','active','in_progress','live','completed')
                          AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                              datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                      )
                    ORDER BY r.id DESC
                    """
                )
            go_home_ids = {str(r[0]) for r in cur.fetchall() if r[0] is not None}
        except Exception:
            go_home_ids = set()

        # Fetch available selected drivers/vehicles.
        params: List[Any] = [admin_id, trip_day, operation, trip_time]
        where = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "d.id NOT IN (SELECT t.driver_id FROM trips t WHERE REPLACE(COALESCE(t.trip_day, ''), '-', '') = ? AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ? AND COALESCE(t.time_slot, t.schedule_time, '') = ? AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress') AND t.driver_id IS NOT NULL)",
        ]
        ph = ",".join(["?"] * len(vehicle_types))
        where.append(f"CAST(d.vehicle_type AS INTEGER) IN ({ph})")
        params.extend(vehicle_types)

        if driver_id is not None and str(driver_id).strip() != "":
            where.append("CAST(d.id AS TEXT) = ?")
            params.append(str(driver_id).strip())

        cur.execute("PRAGMA table_info(drivers)")
        driver_cols = {str(r[1]) for r in cur.fetchall()}
        lat_expr = (
            "COALESCE(d.hometown_lat, d.home_lat, 0)"
            if ("hometown_lat" in driver_cols and "home_lat" in driver_cols)
            else ("COALESCE(d.hometown_lat, 0)" if "hometown_lat" in driver_cols else "0")
        )
        lng_expr = (
            "COALESCE(d.hometown_lng, d.home_lng, 0)"
            if ("hometown_lng" in driver_cols and "home_lng" in driver_cols)
            else ("COALESCE(d.hometown_lng, 0)" if "hometown_lng" in driver_cols else "0")
        )
        cur.execute(
            f"""
            SELECT d.id, d.name, d.vehicle_no, CAST(d.vehicle_type AS INTEGER), {lat_expr}, {lng_expr}
            FROM drivers d
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            WHERE {" AND ".join(where)}
            ORDER BY CAST(d.vehicle_type AS INTEGER) DESC, d.id ASC
            """,
            tuple(params),
        )
        rows = cur.fetchall()
        if not rows:
            return _bad("No available drivers/vehicles for selected slot.")

        vehicle_nodes: List[VehicleNode] = []
        for r in rows:
            d_id = str(r[0])
            vt = int(r[3]) if str(r[3]).isdigit() else 4
            if vt not in (4, 6):
                continue
            vehicle_nodes.append(
                VehicleNode(
                    driver_id=d_id,
                    driver_name=str(r[1] or ""),
                    vehicle_no=str(r[2] or ""),
                    vehicle_type=vt,
                    go_home_approved=d_id in go_home_ids,
                    home_lat=float(r[4] or 0.0),
                    home_lng=float(r[5] or 0.0),
                )
            )
        if not vehicle_nodes:
            return _bad("No valid vehicles after filtering.")

        plan = plan_groups_hybrid(
            employees=employee_nodes,
            vehicles=vehicle_nodes,
            office=(office_lat, office_lng),
            prioritize_6_when_mixed=(4 in vehicle_types and 6 in vehicle_types),
            strict_hybrid=True,
        )
        planned_groups = plan.get("groups", [])
        if not planned_groups:
            return _bad("No groups created for selected constraints.")

        groups_to_create: List[Dict[str, Any]] = []
        driver_assignments: Dict[int, Dict[str, str]] = {}
        for idx, g in enumerate(planned_groups):
            members = g.get("members", [])
            normalized_members: List[Dict[str, Any]] = []
            for m in members:
                normalized_members.append(
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "mobile": m.get("mobile"),
                        "address": m.get("address"),
                        "lat": m.get("lat"),
                        "lng": m.get("lng"),
                    }
                )
            groups_to_create.append(
                {
                    "group_index": idx + 1,
                    "members": normalized_members,
                    "vehicle_type": int(g.get("vehicle_type", 4)),
                    "assigned_driver_id": g.get("driver_id"),
                    "assigned_cab_no": g.get("vehicle_no"),
                }
            )
            if g.get("driver_id"):
                driver_assignments[idx] = {
                    "driver_id": str(g.get("driver_id")),
                    "cab_id": str(g.get("vehicle_no") or g.get("driver_id")),
                }

        preview_data = {
            "trip_preview": {
                "trip_type": operation,
                "selected_time": trip_time,
                "vehicle_types": vehicle_types,
                "vehicle_type": vehicle_types[0] if vehicle_types else 4,
                "trip_day": trip_day,
                "office_lat": office_lat,
                "office_lng": office_lng,
                "hybrid_provider": plan.get("hybrid_provider"),
                "hybrid_strict": bool(plan.get("hybrid_strict", True)),
            }
        }

        result = create_and_assign_trip(
            conn,
            admin_id=admin_id,
            preview_data=preview_data,
            groups_to_create=groups_to_create,
            driver_assignments=driver_assignments,
        )
        if not result.get("success"):
            return _bad(result.get("message", "Trip creation failed"), 400, data=result.get("data"))

        trips_created = ((result.get("data") or {}).get("trips_created") or [])
        return _ok(
            trips_created,
            "Trips created & assigned.",
            warnings=exclusions,
            unresolved_coordinates=unresolved_coords,
            unassigned_employees=plan.get("unassigned_employees", []),
            unassigned_vehicles=plan.get("unassigned_vehicles", []),
            hybrid_provider=plan.get("hybrid_provider"),
        )
    except RuntimeError as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _bad(
            f"Hybrid provider unavailable: {e}. Check /api/health/hybrid and route provider configuration.",
            503,
        )
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _bad(f"Failed to create group/assign trip: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# TRIPS: Live trips, history, cancel, complete
# =========================================================

# @admin_bp.route("/admin/trips", methods=["GET"])
# @admin_bp.route("/api/admin/trips", methods=["GET"])
# def list_all_trips():
#     conn = get_db()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             SELECT id, route_no, operation, schedule_time as scheduled_time, driver_id, vehicle_type, status, total_km, created_at, start_time, end_time
#             FROM trips
#             ORDER BY id DESC
#             """
#         )
#         rows = cur.fetchall() or []
#         return _ok([_row_to_dict(cur, r) for r in rows])
#     except Exception as e:
#         return _bad(f"Failed to load trips: {e}", 500)
#     finally:
#         try:
#             conn.close()
#         except Exception:
#             pass


@admin_bp.route("/admin/trips/live", methods=["GET"])
@admin_bp.route("/api/admin/trips/live", methods=["GET"])
@require_auth(roles=['admin'])
def list_live_trips():
    """
    Step 9: Admin Live Trips visibility.
    Optional query: trip_day=YYYYMMDD to scope live trips by day (if column exists).
    """
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        trip_day = str(request.args.get("trip_day", "")).strip().replace("-", "")
        cur.execute("PRAGMA table_info(trips)")
        cols = {row[1] for row in cur.fetchall()}
        cur.execute("PRAGMA table_info(drivers)")
        driver_cols = {row[1] for row in cur.fetchall()}
        where_sql = "WHERE status IN ('created','assigned','started','active','in_progress') AND CAST(COALESCE(t.admin_id, '') AS TEXT) = ?"
        trip_day_select = "t.trip_day AS trip_day," if "trip_day" in cols else "'' AS trip_day,"
        cab_expr = "d.vehicle_no"
        if "vehicle_no" in cols:
            cab_expr = "COALESCE(t.vehicle_no, d.vehicle_no)"
        driver_join = "CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)"
        if "driver_id" in driver_cols:
            driver_join += " OR (d.driver_id IS NOT NULL AND CAST(d.driver_id AS TEXT) = CAST(t.driver_id AS TEXT))"
        params = [admin_id]
        if trip_day and "trip_day" in cols:
            where_sql += " AND REPLACE(COALESCE(trip_day, ''), '-', '') = ?"
            params.append(trip_day)
        cur.execute(
            f"""
            SELECT t.id,
                   t.route_no,
                   t.operation,
                   {trip_day_select}
                   t.schedule_time as scheduled_time,
                   t.driver_id,
                   t.vehicle_type,
                   t.status,
                   t.total_km,
                   d.name AS driver_name,
                   d.mobile AS driver_mobile,
                   {cab_expr} AS cab_no
            FROM trips t
            LEFT JOIN drivers d
              ON {driver_join}
            {where_sql}
            ORDER BY t.id DESC
            """,
            tuple(params),
        )
        trips = cur.fetchall() or []

        data = []
        for t in trips:
            td = _row_to_dict(cur, t)
            td = _attach_trip_timing_fields(cur, td)
            td = _attach_emergency_swap_context(cur, td)
            gate = evaluate_trip_start_gate(
                td.get("trip_day"),
                td.get("scheduled_time"),
                trip_type=td.get("trip_type") or td.get("operation"),
                route_duration_minutes=td.get("travel_time_min"),
            )
            td["can_start_now"] = bool(gate.get("can_start_now", True))
            td["is_preassigned"] = bool(gate.get("is_preassigned", False))
            td["start_allowed_after"] = gate.get("start_allowed_after")
            td["seconds_until_start"] = int(gate.get("seconds_until_start", 0) or 0)
            td["server_now"] = gate.get("server_now")
            # fetch members
            cur.execute(
                """
                SELECT e.id, e.name, e.mobile, e.home_address as address, tm.is_no_show
                FROM trip_employees tm
                JOIN employees e ON e.id = tm.employee_id
                WHERE tm.trip_id = ?
                """,
                (td["id"],),
            )
            members = cur.fetchall() or []
            td["members"] = [_row_to_dict(cur, m) for m in members]
            data.append(td)

        return _ok(data)
    except Exception as e:
        return _bad(f"Failed to load live trips: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/trips/<int:trip_id>/cancel", methods=["POST"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/cancel", methods=["POST"])
@require_auth(roles=['admin'])
def cancel_trip(trip_id: int):
    payload = request.get_json(silent=True) or {}
    reason = (payload.get("reason") or "").strip()
    admin_id = _current_admin_id()
    if len(reason) < 3:
        return _bad("Cancel reason required (min 3 chars).")

    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found.", 404)
        result = mark_trip_cancelled(
            conn,
            trip_id,
            reason=reason,
            actor_role="admin",
            actor_id=admin_id,
        )
        _cleanup_temp_swap_driver(conn, trip_id)
        conn.commit()
        return _ok(result, "Trip cancelled.")
    except Exception as e:
        return _bad(f"Failed to cancel trip: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass



@admin_bp.route("/admin/trips/<int:trip_id>/complete", methods=["POST"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/complete", methods=["POST"])
@require_auth(roles=['admin'])
def admin_mark_trip_complete(trip_id: int):
    """
    Admin override to complete trip (normally driver should complete via END OTP).
    """
    payload = request.get_json(silent=True) or {}
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found.", 404)
        total_km_raw = payload.get("total_km")
        total_km = None
        if total_km_raw not in (None, ""):
            total_km = float(total_km_raw)
        result = mark_trip_completed(
            conn,
            trip_id,
            actor_role="admin",
            actor_id=admin_id,
            total_km=total_km,
            polyline=payload.get("polyline"),
            route_json=payload.get("route_json"),
        )
        _cleanup_temp_swap_driver(conn, trip_id)
        conn.commit()
        return _ok(result, "Trip marked completed.")
    except Exception as e:
        return _bad(f"Failed to complete trip: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/trips/<int:trip_id>/swap-cab", methods=["POST"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/swap-cab", methods=["POST"])
@require_auth(roles=['admin'])
def swap_trip_cab(trip_id: int):
    """
    Swap cab/driver for an active trip.
    Payload: { "cab_no": "MH12...", "admin_id": "..." }
    """
    payload = request.get_json(silent=True) or {}
    cab_no = (payload.get("cab_no") or "").strip()
    admin_id = _current_admin_id()
    
    if not cab_no:
        return _bad("cab_no is required.")

    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found.", 404)
        from services.trip_service import TripService
        service = TripService(conn)
        
        # We need new_driver_id for the service.
        # Lookup driver by cab_no first (this logic could be in service but okay here)
        # Actually simplest to ask service to do it if we passed cab_no, but service expects driver_id.
        # Let's do a quick lookup helper or just use repo here?
        # Service encapsulation is better.
        # But for now, let's keep the lookup here using Repo.
        from repositories.driver_repository import DriverRepository
        driver_repo = DriverRepository(conn)
        
        # We need a method to get driver by cab_no? 
        # DriverRepo has `get_cab_by_reg_no` but that returns cab info.
        # We need driver associated with cab. 
        # Existing code did: SELECT id FROM drivers WHERE vehicle_no = ?
        cur.execute("SELECT id FROM drivers WHERE vehicle_no = ? LIMIT 1", (cab_no,))
        row = cur.fetchone()
        if not row:
             return _bad("Cab/Driver not found.", 404)
        driver_id = row[0]
        if not _driver_belongs_to_admin(cur, driver_id, admin_id):
            return _bad("Cab/Driver not found.", 404)
        
        trip_data = service.swap_driver(trip_id, driver_id, admin_id)
        return _ok(trip_data, "Cab swapped successfully.")
        
    except ValueError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f"Failed to swap cab: {e}", 500)
    finally:
        try:
            conn.close()
        except:
            pass


@admin_bp.route("/admin/trips/<int:trip_id>/remove-employee", methods=["POST"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/remove-employee", methods=["POST"])
@require_auth(roles=['admin'])
def remove_employee_from_trip(trip_id: int):
    """
    Remove an employee from a trip.
    Payload: { "employee_id": 123, "admin_id": "..." }
    """
    payload = request.get_json(silent=True) or {}
    emp_id = payload.get("employee_id")
    admin_id = _current_admin_id()
    
    if not emp_id:
        return _bad("employee_id is required.")

    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found.", 404)
        if not _employee_belongs_to_admin(cur, emp_id, admin_id):
            return _bad("Employee not found.", 404)
        from services.trip_service import TripService
        service = TripService(conn)
        
        data = service.remove_employee(trip_id, str(emp_id), admin_id)
        return _ok(data, "Employee removed from trip.")
    except Exception as e:
        return _bad(f"Failed to remove employee: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/trips/<int:trip_id>/add-employee", methods=["POST"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/add-employee", methods=["POST"])
@require_auth(roles=['admin'])
def add_employee_to_trip(trip_id: int):
    """
    Add an employee to an active trip.
    Payload: { "employee_id": 123, "admin_id": "..." }
    """
    payload = request.get_json(silent=True) or {}
    emp_id = payload.get("employee_id")
    admin_id = _current_admin_id()
    
    if not emp_id:
        return _bad("employee_id is required.")

    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found.", 404)
        if not _employee_belongs_to_admin(cur, emp_id, admin_id):
            return _bad("Employee not found.", 404)
        from services.trip_service import TripService
        service = TripService(conn)
        
        data = service.add_employee(trip_id, str(emp_id), admin_id)
        return _ok(data, "Employee added to trip.")
    except ValueError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f"Failed to add employee: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# OTP generation endpoint (optional for admin UI)
# =========================================================
@admin_bp.route("/admin/trips/<int:trip_id>/otps/generate", methods=["POST", "GET"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/otps/generate", methods=["POST", "GET"])
@require_auth(roles=['admin'])
def admin_generate_otps(trip_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found.", 404)
        data = create_trip_otps(conn, trip_id)
        if not data.get("success"):
            return _bad(data.get("message", "OTP generation failed"), 400)
        return _ok(data.get("data"), "OTPs generated.")
    except Exception as e:
        return _bad(f"Failed to generate OTPs: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# LIVE DRIVER TRACKING (ADMIN)
# =========================================================
@admin_bp.route("/admin/drivers/online", methods=["GET"])
@admin_bp.route("/api/admin/drivers/online", methods=["GET"])
@require_auth(roles=['admin'])
def admin_online_drivers():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        resp = get_online_drivers(conn)
        if not resp.get("success"):
            return _bad(resp.get("message", "Failed"), 400)
        raw_data = resp.get("data") or {}
        if isinstance(raw_data, dict):
            data = raw_data.get("online_drivers") or []
        elif isinstance(raw_data, list):
            data = raw_data
        else:
            data = []
        cur = conn.cursor()
        has_temp_col = _ensure_temporary_driver_column(cur)
        filtered = []
        for item in data:
            row = dict(item or {})
            d_id = row.get("driver_id") or row.get("id")
            if not d_id:
                filtered.append(row)
                continue
            if has_temp_col:
                cur.execute(
                    "SELECT COALESCE(is_temporary, 0) AS is_temporary, COALESCE(dl_no, '') AS dl_no FROM drivers WHERE id = ? LIMIT 1",
                    (str(d_id),),
                )
            else:
                cur.execute(
                    "SELECT 0 AS is_temporary, COALESCE(dl_no, '') AS dl_no FROM drivers WHERE id = ? LIMIT 1",
                    (str(d_id),),
                )
            d = cur.fetchone()
            if not d:
                filtered.append(row)
                continue
            dd = _row_to_dict(cur, d)
            if not _driver_belongs_to_admin(cur, d_id, admin_id):
                continue
            if int(dd.get("is_temporary") or 0) == 1 or str(dd.get("dl_no") or "").upper() == "ADHOC_SWAP":
                continue
            filtered.append(row)
        return _ok(
            {
                "count": len(filtered),
                "online_drivers": filtered,
            }
        )
    except Exception as e:
        return _bad(f"Failed to load online drivers: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/routes/<route_no>/driver-location", methods=["GET"])
@admin_bp.route("/api/admin/routes/<route_no>/driver-location", methods=["GET"])
@require_auth(roles=['admin'])
def admin_route_driver_location(route_no: str):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM trips
            WHERE route_no = ?
              AND CAST(COALESCE(admin_id, '') AS TEXT) = CAST(? AS TEXT)
            LIMIT 1
            """,
            (route_no, admin_id),
        )
        if not cur.fetchone():
            return _bad("Trip not found.", 404)
        resp = get_assigned_driver_location_by_route_no(conn, route_no)
        if not resp.get("success"):
            return _bad(resp.get("message", "No location"), 404)
        return _ok(resp.get("data"))
    except Exception as e:
        return _bad(f"Failed to load driver location: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# PREASSIGN TRIP CANCEL REQUESTS (Admin manage)
# =========================================================
@admin_bp.route("/admin/trip-cancel-requests", methods=["GET"])
@admin_bp.route("/api/admin/trip-cancel-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_trip_cancel_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        _ensure_trip_cancel_requests_table(cur)
        cur.execute(
            """
            SELECT
                r.id,
                r.trip_id,
                r.driver_id,
                r.reason,
                r.status,
                r.admin_note,
                r.reviewed_by,
                r.created_at,
                r.updated_at,
                t.route_no,
                t.status AS trip_status,
                d.name AS driver_name,
                d.mobile AS driver_mobile
            FROM trip_cancel_requests r
            LEFT JOIN trips t
              ON t.id = r.trip_id
            LEFT JOIN drivers d
              ON CAST(d.id AS TEXT) = CAST(r.driver_id AS TEXT)
              OR (d.driver_id IS NOT NULL AND CAST(d.driver_id AS TEXT) = CAST(r.driver_id AS TEXT))
            ORDER BY
              CASE WHEN LOWER(COALESCE(r.status, '')) = 'pending' THEN 0 ELSE 1 END,
              r.created_at DESC
            """
        )
        rows = cur.fetchall() or []
        scoped = []
        for r in rows:
            item = _row_to_dict(cur, r)
            if not _trip_belongs_to_admin(cur, item.get("trip_id"), admin_id):
                continue
            scoped.append(item)
        return _ok(scoped)
    except Exception as e:
        return _bad(f"Failed to load trip cancel requests: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/vehicles", methods=["GET"])
@admin_bp.route("/api/admin/billing/vehicles", methods=["GET"])
@require_auth(roles=['admin'])
def list_billing_vehicle_assignments():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        data = list_billable_vehicle_assignments(
            conn,
            admin_id=admin_id,
            search=request.args.get('search'),
        )
        return _ok(data)
    except Exception as e:
        return _bad(f'Failed to load billing vehicles: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/trips", methods=["GET"])
@admin_bp.route("/api/admin/billing/trips", methods=["GET"])
@require_auth(roles=['admin'])
def list_billing_trips():
    admin_id = _current_admin_id()
    requested_trip_id = request.args.get('trip_id')
    trip_id = _optional_int(requested_trip_id)
    if requested_trip_id not in (None, '') and trip_id is None:
        return _bad('trip_id must be numeric.', 400)

    conn = get_db()
    try:
        data = list_billable_trips(
            conn,
            admin_id=admin_id,
            driver_id=request.args.get('driver_id'),
            vehicle_no=request.args.get('vehicle_no'),
            from_date=request.args.get('from'),
            to_date=request.args.get('to'),
            trip_id=trip_id,
            search=request.args.get('search'),
        )
        return _ok(data)
    except Exception as e:
        return _bad(f'Failed to load billing trips: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/prefill", methods=["GET"])
@admin_bp.route("/api/admin/billing/prefill", methods=["GET"])
@require_auth(roles=['admin'])
def get_admin_billing_prefill():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        data = get_billing_prefill(conn, admin_id=admin_id)
        return _ok(data)
    except Exception as e:
        return _bad(f'Failed to load billing prefill: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/settings", methods=["PUT"])
@admin_bp.route("/api/admin/billing/settings", methods=["PUT"])
@require_auth(roles=['admin'])
def update_admin_billing_settings():
    admin_id = _current_admin_id()
    payload = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        data = save_billing_settings(conn, admin_id=admin_id, payload=payload)
        return _ok(data, 'Billing settings updated.')
    except Exception as e:
        return _bad(f'Failed to update billing settings: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/records", methods=["POST"])
@admin_bp.route("/api/admin/billing/records", methods=["POST"])
@require_auth(roles=['admin'])
def create_admin_billing_record():
    admin_id = _current_admin_id()
    payload = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        record = create_billing_record(conn, admin_id=admin_id, payload=payload)
        return _ok(record, 'Billing record created.')
    except ValueError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f'Failed to create billing record: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/records", methods=["GET"])
@admin_bp.route("/api/admin/billing/records", methods=["GET"])
@require_auth(roles=['admin'])
def list_admin_billing_records():
    admin_id = _current_admin_id()
    limit = _optional_int(request.args.get('limit')) or 50
    conn = get_db()
    try:
        data = list_billing_records(conn, admin_id=admin_id, limit=limit)
        return _ok(data)
    except Exception as e:
        return _bad(f'Failed to load billing history: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/billing/records/<int:record_id>", methods=["GET"])
@admin_bp.route("/api/admin/billing/records/<int:record_id>", methods=["GET"])
@require_auth(roles=['admin'])
def get_admin_billing_record(record_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        record = get_billing_record(conn, admin_id=admin_id, record_id=record_id)
        if not record:
            return _bad('Billing record not found.', 404)
        return _ok(record)
    except Exception as e:
        return _bad(f'Failed to load billing record: {e}', 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/trip-cancel-requests/<int:req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/trip-cancel-requests/<int:req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_trip_cancel_request(req_id: int):
    payload = request.get_json(silent=True) or {}
    admin_note = str(payload.get("note") or "").strip()
    reviewed_by = _current_admin_id()

    conn = get_db()
    try:
        cur = conn.cursor()
        _ensure_trip_cancel_requests_table(cur)
        cur.execute(
            "SELECT * FROM trip_cancel_requests WHERE id = ? LIMIT 1",
            (req_id,),
        )
        row = cur.fetchone()
        if not row:
            return _bad("Cancel request not found", 404)
        req = _row_to_dict(cur, row)
        if not _trip_belongs_to_admin(cur, req.get("trip_id"), reviewed_by):
            return _bad("Cancel request not found", 404)
        req_status = str(req.get("status") or "").strip().lower()
        if req_status != "pending":
            return _bad(f"Request already {req_status or 'processed'}", 400)

        trip_id = int(req.get("trip_id") or 0)
        reason = str(req.get("reason") or "").strip()
        final_reason = (
            f"Driver cancel request approved: {reason}"
            if reason
            else "Driver cancel request approved by admin"
        )
        if admin_note:
            final_reason = f"{final_reason} | Admin note: {admin_note}"

        mark_trip_cancelled(
            conn,
            trip_id,
            reason=final_reason,
            actor_role="admin",
            actor_id=reviewed_by,
        )

        cur.execute(
            """
            UPDATE trip_cancel_requests
            SET status='approved',
                admin_note=?,
                reviewed_by=?,
                updated_at=datetime('now')
            WHERE id=?
            """,
            (admin_note, reviewed_by, req_id),
        )
        _cleanup_temp_swap_driver(conn, trip_id)
        conn.commit()
        return _ok(
            {"request_id": req_id, "trip_id": trip_id},
            "Trip cancel request approved and trip cancelled.",
        )
    except Exception as e:
        return _bad(f"Failed to approve trip cancel request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/trip-cancel-requests/<int:req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/trip-cancel-requests/<int:req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_trip_cancel_request(req_id: int):
    payload = request.get_json(silent=True) or {}
    admin_note = str(payload.get("note") or "").strip()
    reviewed_by = _current_admin_id()

    conn = get_db()
    try:
        cur = conn.cursor()
        _ensure_trip_cancel_requests_table(cur)
        cur.execute(
            "SELECT status, trip_id FROM trip_cancel_requests WHERE id = ? LIMIT 1",
            (req_id,),
        )
        row = cur.fetchone()
        if not row:
            return _bad("Cancel request not found", 404)
        row_data = _row_to_dict(cur, row)
        if not _trip_belongs_to_admin(cur, row_data.get("trip_id"), reviewed_by):
            return _bad("Cancel request not found", 404)
        current_status = str(row_data.get("status") or "").strip().lower()
        if current_status != "pending":
            return _bad(f"Request already {current_status or 'processed'}", 400)

        cur.execute(
            """
            UPDATE trip_cancel_requests
            SET status='rejected',
                admin_note=?,
                reviewed_by=?,
                updated_at=datetime('now')
            WHERE id=?
            """,
            (admin_note, reviewed_by, req_id),
        )
        conn.commit()
        return _ok({"request_id": req_id}, "Trip cancel request rejected.")
    except Exception as e:
        return _bad(f"Failed to reject trip cancel request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# SWAP REQUESTS (Admin manage emergency swaps)
# =========================================================

@admin_bp.route("/admin/swap-requests", methods=["GET"])
@admin_bp.route("/api/admin/swap-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_swap_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sr.id, sr.trip_id, sr.old_driver_id as driver_id, sr.new_driver_name, sr.new_driver_mobile, 
                   sr.new_cab_no, sr.note as reason, sr.proof_image_path as photo_base_path, sr.status, sr.created_at,
                   d.name as original_driver_name, t.route_no
            FROM swap_requests sr
            JOIN drivers d ON d.id = sr.old_driver_id
            JOIN trips t ON t.id = sr.trip_id
            ORDER BY sr.created_at DESC
            """
        )
        rows = cur.fetchall() or []
        # Frontend expects 'reason' and 'photo_base_path' keys, so aliasing in SQL is good.
        scoped = []
        for r in rows:
            item = _row_to_dict(cur, r)
            if not _trip_belongs_to_admin(cur, item.get("trip_id"), admin_id):
                continue
            scoped.append(item)
        return _ok(scoped)
    except Exception as e:
        return _bad(f"Failed to load swap requests: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/swap-requests/<int:req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/swap-requests/<int:req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_swap_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM swap_requests WHERE id=? LIMIT 1", (req_id,))
        row = cur.fetchone()
        if not row:
            return _bad("Swap request not found", 404)
        
        req = _row_to_dict(cur, row)
        if not _trip_belongs_to_admin(cur, req.get("trip_id"), admin_id):
            return _bad("Swap request not found", 404)
        req_status = str(req.get("status") or "").strip().lower()
        if req_status != "pending":
             return _bad(f"Request already {req.get('status')}", 400)

        # 1. Create new driver account (or find existing?)
        # For simplicity, we'll create a new driver if mobile doesn't exist, 
        # OR just update the trip to use a temporary 'adhoc' driver?
        # A better approach for "Emergency":
        # Create a new driver record for this adhoc driver so tracking works.
        
        new_mobile = req["new_driver_mobile"]
        new_cab = req["new_cab_no"]
        
        has_temp_col = _ensure_temporary_driver_column(cur)

        # Check if driver exists by mobile
        cur.execute("SELECT id FROM drivers WHERE mobile=?", (new_mobile,))
        existing = cur.fetchone()
        
        if existing:
            new_driver_id = existing[0]
            # Update cab no if different?
            cur.execute("UPDATE drivers SET vehicle_no=? WHERE id=?", (new_cab, new_driver_id))
        else:
            # Create new driver
            import uuid
            new_driver_id = str(uuid.uuid4())
            password, salt, hash_val = _generate_default_password()
            if has_temp_col:
                cur.execute(
                    """
                    INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, 
                                       is_approved, is_online, is_temporary, password_salt, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, 'ADHOC_SWAP', ?, '4', 'Unknown', 0, 0, 1, ?, ?, datetime('now'), datetime('now'))
                    """,
                    (new_driver_id, req["new_driver_name"], new_mobile, new_cab, salt, hash_val)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, 
                                       is_approved, is_online, password_salt, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, 'ADHOC_SWAP', ?, '4', 'Unknown', 0, 0, ?, ?, datetime('now'), datetime('now'))
                    """,
                    (new_driver_id, req["new_driver_name"], new_mobile, new_cab, salt, hash_val)
                )

        # 2. Update Trip
        # Ensure 'vehicle_no' column exists in trips (if not, migration needed). 
        # Assuming 'vehicle_no' based on repo usage.
        cur.execute(
            "UPDATE trips SET driver_id=?, vehicle_no=? WHERE id=?",
            (new_driver_id, new_cab, req["trip_id"])
        )
        
        # 3. Update Request Status
        apply_swap_approval(
            conn,
            int(req["trip_id"]),
            request_id=req_id,
            old_driver_id=str(req.get("old_driver_id") or ""),
            new_driver_id=str(new_driver_id),
            new_cab_no=new_cab,
            reviewed_by="admin",
        )
        
        conn.commit()
        return _ok({"request_id": req_id, "new_driver_id": new_driver_id}, "Swap approved, trip updated.")

    except Exception as e:
        return _bad(f"Failed to approve swap: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/swap-requests/<int:req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/swap-requests/<int:req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_swap_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT trip_id FROM swap_requests WHERE id=? LIMIT 1", (req_id,))
        row = cur.fetchone()
        if not row:
            return _bad("Swap request not found", 404)
        if not _trip_belongs_to_admin(cur, _row_to_dict(cur, row).get("trip_id"), admin_id):
            return _bad("Swap request not found", 404)
        cur.execute("UPDATE swap_requests SET status='rejected' WHERE id=?", (req_id,))
        conn.commit()
        return _ok({"request_id": req_id}, "Swap request rejected.")
    except Exception as e:
        return _bad(f"Failed to reject swap: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# DRIVER PROFILE CHANGE REQUESTS
# =========================================================

@admin_bp.route("/admin/driver-change-requests", methods=["GET"])
@admin_bp.route("/api/admin/driver-change-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_driver_change_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.driver_id, r.name, r.mobile, r.dl_no, r.vehicle_no AS cab_no, r.home_town, r.status, r.created_at,
                   d.name as current_name, d.mobile as current_mobile
            FROM driver_change_requests r
            JOIN drivers d ON d.id = r.driver_id
            ORDER BY r.created_at DESC
            """
        )
        rows = cur.fetchall() or []
        scoped = []
        for r in rows:
            item = _row_to_dict(cur, r)
            if not _driver_belongs_to_admin(cur, item.get("driver_id"), admin_id):
                continue
            scoped.append(item)
        return _ok(scoped)
    except Exception as e:
        return _bad(f"Failed to load driver change requests: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/driver-change-requests/<int:req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/driver-change-requests/<int:req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_driver_change_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM driver_change_requests WHERE id=? LIMIT 1", (req_id,))
        row = cur.fetchone()
        if not row:
            return _bad("Request not found", 404)
        
        req = _row_to_dict(cur, row)
        if not _driver_belongs_to_admin(cur, req.get("driver_id"), admin_id):
            return _bad("Request not found", 404)
        req_status = str(req.get("status") or "").strip().lower()
        if req_status != "pending":
             return _bad(f"Request already {req.get('status')}", 400)

        # Update driver profile with non-null values from request
        # Use COALESCE logic in python before query or update query directly?
        # Using separate UPDATE logic to be safe with COALESCE in SQL
        
        # We need to map:
        # req['cab_no'] -> drivers.vehicle_no
        # req['hometown'] -> drivers.home_town
        
        update_fields = []
        params = []
        
        if req.get("name"): 
            update_fields.append("name = ?")
            params.append(req["name"])
            
        if req.get("mobile"): 
            update_fields.append("mobile = ?")
            params.append(req["mobile"])
            
        if req.get("dl_no"): 
            update_fields.append("dl_no = ?")
            params.append(req["dl_no"])
            
        requested_vehicle_no = (req.get("cab_no") or req.get("vehicle_no"))
        if requested_vehicle_no: 
            update_fields.append("vehicle_no = ?")
            params.append(requested_vehicle_no)
            
        if req.get("home_town"): 
            update_fields.append("home_town = ?")
            params.append(req["home_town"])
            
        if update_fields:
            update_fields.append("updated_at = datetime('now')")
            sql = f"UPDATE drivers SET {', '.join(update_fields)} WHERE id = ?"
            params.append(req["driver_id"])
            cur.execute(sql, tuple(params))

        resolved_lat, resolved_lng, _ = _resolve_address_coords(
            conn,
            address=req.get("home_town"),
            lat=req.get("home_lat"),
            lng=req.get("home_lng"),
        )
        if _is_valid_coord_pair(resolved_lat, resolved_lng):
            cur.execute("PRAGMA table_info(drivers)")
            dcols = {str(r[1]) for r in cur.fetchall()}
            updates: List[str] = []
            cparams: List[Any] = []
            if "hometown_lat" in dcols:
                updates.append("hometown_lat = ?")
                cparams.append(resolved_lat)
            if "hometown_lng" in dcols:
                updates.append("hometown_lng = ?")
                cparams.append(resolved_lng)
            if "home_lat" in dcols:
                updates.append("home_lat = ?")
                cparams.append(resolved_lat)
            if "home_lng" in dcols:
                updates.append("home_lng = ?")
                cparams.append(resolved_lng)
            if updates:
                cparams.append(req["driver_id"])
                cur.execute(f"UPDATE drivers SET {', '.join(updates)} WHERE id = ?", tuple(cparams))
        
        # Update request status
        cur.execute("UPDATE driver_change_requests SET status='approved' WHERE id=?", (req_id,))
        
        conn.commit()
        return _ok({"request_id": req_id}, "Driver profile updated successfully.")

    except Exception as e:
        return _bad(f"Failed to approve details change: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@admin_bp.route("/admin/driver-change-requests/<int:req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/driver-change-requests/<int:req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_driver_change_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT driver_id FROM driver_change_requests WHERE id=? LIMIT 1", (req_id,))
        row = cur.fetchone()
        if not row:
            return _bad("Request not found", 404)
        if not _driver_belongs_to_admin(cur, _row_to_dict(cur, row).get("driver_id"), admin_id):
            return _bad("Request not found", 404)
        cur.execute("UPDATE driver_change_requests SET status='rejected' WHERE id=?", (req_id,))
        conn.commit()
        return _ok({"request_id": req_id}, "Request rejected.")
    except Exception as e:
        return _bad(f"Failed to reject request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# HELPDESK
# =========================================================
@admin_bp.route("/admin/helpdesk", methods=["GET"])
@admin_bp.route("/api/admin/helpdesk", methods=["GET"])
@require_auth(roles=['admin'])
def list_helpdesk_tickets():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT h.*, 
                   d.name as driver_name, e.name as employee_name
            FROM helpdesk_tickets h
            LEFT JOIN drivers d ON h.user_type='driver' AND h.user_id=d.id
            LEFT JOIN employees e ON h.user_type='employee' AND h.user_id=e.id
            ORDER BY 
                CASE WHEN h.status='open' THEN 1 ELSE 2 END,
                h.created_at DESC
            """
        )
        rows = cur.fetchall()
        results = [dict(r) for r in rows]
        # enhance with user name
        scoped = []
        for r in results:
            if r["user_type"] == "driver":
                r["user_name"] = r.get("driver_name") or "Unknown Driver"
                if not _driver_belongs_to_admin(cur, r.get("user_id"), admin_id):
                    continue
            else:
                r["user_name"] = r.get("employee_name") or "Unknown Employee"
                if not _employee_belongs_to_admin(cur, r.get("user_id"), admin_id):
                    continue
            scoped.append(r)
        return _ok(scoped)
    except Exception as e:
        return _bad(f"Failed to load helpdesk tickets: {e}", 500)
    finally:
        conn.close()


@admin_bp.route("/admin/helpdesk/<int:ticket_id>/resolve", methods=["POST"])
@admin_bp.route("/api/admin/helpdesk/<int:ticket_id>/resolve", methods=["POST"])
@require_auth(roles=['admin'])
def resolve_helpdesk_ticket(ticket_id: int):
    data = request.json or {}
    note = data.get("note", "").strip()
    admin_id = _current_admin_id()

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, user_type FROM helpdesk_tickets WHERE id = ? LIMIT 1", (ticket_id,))
        row = cur.fetchone()
        if not row:
            return _bad("Ticket not found.", 404)
        row_data = _row_to_dict(cur, row)
        if row_data.get("user_type") == "driver":
            if not _driver_belongs_to_admin(cur, row_data.get("user_id"), admin_id):
                return _bad("Ticket not found.", 404)
        else:
            if not _employee_belongs_to_admin(cur, row_data.get("user_id"), admin_id):
                return _bad("Ticket not found.", 404)
        cur.execute(
            """
            UPDATE helpdesk_tickets 
            SET status = 'resolved', 
                admin_notes = ?, 
                resolved_by = ?,
                resolved_at = ?
            WHERE id = ?
            """,
            (note, admin_id, datetime.utcnow().isoformat(), ticket_id)
        )
        conn.commit()
        return _ok({"ticket_id": ticket_id}, "Ticket resolved.")
    except Exception as e:
        return _bad(f"Failed to resolve ticket: {e}", 500)
    finally:
        conn.close()


# =========================================================
# TRIP DETAILS & OVERRIDES (Standardized)
# =========================================================

@admin_bp.route("/admin/trips/<int:trip_id>", methods=["GET"])
@admin_bp.route("/api/admin/trips/<int:trip_id>", methods=["GET"])
@require_auth(roles=['admin'])
def get_trip_details(trip_id: int):
    """
    Get standardized trip details.
    """
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found", 404)
        from services.trip_service import TripService
        service = TripService(conn)
        data = service.get_trip_details(trip_id)
        
        if not data:
            return _bad("Trip not found", 404)
        data = _attach_trip_timing_fields(conn.cursor(), data)
        return _ok(data)
    except Exception as e:
        return _bad(f"Failed to load trip: {e}", 500)
    finally:
        try:
            conn.close()
        except:
            pass

@admin_bp.route("/admin/trips/<int:trip_id>/override", methods=["POST"])
@admin_bp.route("/api/admin/trips/<int:trip_id>/override", methods=["POST"])
@require_auth(roles=['admin'])
def override_trip(trip_id: int):
    """
    Manual override wrapper (Step 12).
    Dispatches to specific override services based on action type.
    """
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    admin_id = _current_admin_id()
    
    conn = get_db()
    try:
        cur = conn.cursor()
        if not _trip_belongs_to_admin(cur, trip_id, admin_id):
            return _bad("Trip not found", 404)
        from services.trip_override_service import change_trip_driver, move_employee_between_trips
        from services.trip_service import serialize_trip
        
        result = None
        
        if action == "change_driver":
            new_driver_id = payload.get("new_driver_id")
            reason = payload.get("reason", "Manual override")
            result = change_trip_driver(conn, trip_id, new_driver_id, admin_id, reason)
            
        elif action == "move_employee":
            # Just move out for now, or move between?
            # If payload has target_trip_id, it's a move.
            pass # TODO: Implement complex moves if needed.
            return _bad("Generic override for move_employee not fully implemented in this endpoint yet. Use specific endpoints.")
            
        else:
            return _bad(f"Unknown override action: {action}")
            
        if result and result.get("success"):
            # Return full standardized trip
            updated_trip = serialize_trip(conn, trip_id)
            return _ok(updated_trip, "Override successful")
        else:
            return _bad(result.get("message", "Override failed"))
            
    except Exception as e:
        return _bad(f"Failed to override trip: {e}", 500)
    finally:
        try:
            conn.close()
        except:
            pass

# =========================================================
# SOS ALERTS
# =========================================================
@admin_bp.route("/admin/sos-alerts", methods=["GET"])
@admin_bp.route("/api/admin/sos-alerts", methods=["GET"])
@require_auth(roles=['admin'])
def list_sos_alerts():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.*, e.name as employee_name, e.mobile as employee_mobile, t.route_no
            FROM sos_alerts s
            JOIN employees e ON s.employee_id = e.id
            LEFT JOIN trips t ON s.trip_id = t.id
            ORDER BY s.resolved ASC, s.created_at DESC
            """
        )
        rows = cur.fetchall()
        scoped = []
        for row in rows:
            item = dict(row)
            if not _employee_belongs_to_admin(cur, item.get("employee_id"), admin_id):
                continue
            scoped.append(item)
        return _ok(scoped)
    except Exception as e:
        return _bad(f"Failed to load SOS alerts: {e}", 500)
    finally:
        conn.close()

@admin_bp.route("/admin/sos-alerts/<int:alert_id>/resolve", methods=["POST"])
@admin_bp.route("/api/admin/sos-alerts/<int:alert_id>/resolve", methods=["POST"])
@require_auth(roles=['admin'])
def resolve_sos_alert(alert_id: int):
    admin_id = _current_admin_id()
    
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT employee_id FROM sos_alerts WHERE id = ? LIMIT 1", (alert_id,))
        row = cur.fetchone()
        if not row:
            return _bad("SOS alert not found.", 404)
        if not _employee_belongs_to_admin(cur, _row_to_dict(cur, row).get("employee_id"), admin_id):
            return _bad("SOS alert not found.", 404)
        cur.execute(
            """
            UPDATE sos_alerts
            SET resolved = 1, resolved_by = ?, resolved_at = datetime('now')
            WHERE id = ?
            """,
            (admin_id, alert_id)
        )
        conn.commit()
        return _ok({"alert_id": alert_id}, "SOS alert resolved.")
    except Exception as e:
        return _bad(f"Failed to resolve SOS alert: {e}", 500)
    finally:
        conn.close()

# =========================================================
# EMPLOYEE ABSENCE REQUESTS
# =========================================================
@admin_bp.route("/admin/absence-requests", methods=["GET"])
@admin_bp.route("/api/admin/absence-requests", methods=["GET"])
@require_auth(roles=['admin'])
def list_absence_requests():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        items = list_admin_absence_requests(conn)
        scoped = [item for item in items if _employee_belongs_to_admin(conn.cursor(), item.get("employee_id"), admin_id)]
        return _ok(scoped)
    except Exception as e:
        return _bad(f"Failed to load absence requests: {e}", 500)
    finally:
        conn.close()

@admin_bp.route("/admin/absence-requests/<int:req_id>/approve", methods=["POST"])
@admin_bp.route("/api/admin/absence-requests/<int:req_id>/approve", methods=["POST"])
@require_auth(roles=['admin'])
def approve_absence_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        from services.absence_flow_service import get_request_details
        details = get_request_details(conn, req_id)
        if not _employee_belongs_to_admin(conn.cursor(), details.get("employee_id"), admin_id):
            return _bad("Absence request not found", 404)
        result = review_absence_request_flow(
            conn,
            req_id,
            decision="approve",
            admin_reason=str(body.get("reason") or body.get("admin_reason") or "").strip(),
            reviewed_by=admin_id,
        )
        return _ok(
            {
                "request_id": result.request_id,
                "request_kind": result.request_kind,
                "status": result.status,
                "employee_id": result.employee_id,
                "dates": result.dates,
            },
            "Absence request approved.",
        )
    except AbsenceFlowError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f"Failed to approve absence: {e}", 500)
    finally:
        conn.close()


@admin_bp.route("/admin/absence-requests/<int:req_id>/reject", methods=["POST"])
@admin_bp.route("/api/admin/absence-requests/<int:req_id>/reject", methods=["POST"])
@require_auth(roles=['admin'])
def reject_absence_request(req_id: int):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        from services.absence_flow_service import get_request_details
        details = get_request_details(conn, req_id)
        if not _employee_belongs_to_admin(conn.cursor(), details.get("employee_id"), admin_id):
            return _bad("Absence request not found", 404)
        result = review_absence_request_flow(
            conn,
            req_id,
            decision="reject",
            admin_reason=str(body.get("reason") or body.get("admin_reason") or "").strip(),
            reviewed_by=admin_id,
        )
        return _ok(
            {
                "request_id": result.request_id,
                "request_kind": result.request_kind,
                "status": result.status,
                "employee_id": result.employee_id,
                "dates": result.dates,
            },
            "Absence request rejected.",
        )
    except AbsenceFlowError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f"Failed to reject absence: {e}", 500)
    finally:
        conn.close()


@admin_bp.route("/admin/absent-employees", methods=["GET"])
@admin_bp.route("/api/admin/absent-employees", methods=["GET"])
@require_auth(roles=['admin'])
def list_absent_employees():
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        on_or_after = str(request.args.get("on_or_after") or datetime.now().strftime("%Y-%m-%d")).strip()
        items = list_approved_absence_ranges(conn, on_or_after=on_or_after)
        scoped = [item for item in items if _employee_belongs_to_admin(conn.cursor(), item.get("employee_id"), admin_id)]
        return _ok(scoped)
    except AbsenceFlowError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f"Failed to load absent employees: {e}", 500)
    finally:
        conn.close()


@admin_bp.route("/admin/absent-employees/<employee_id>/remove", methods=["POST"])
@admin_bp.route("/api/admin/absent-employees/<employee_id>/remove", methods=["POST"])
@require_auth(roles=['admin'])
def remove_absent_employee(employee_id: str):
    admin_id = _current_admin_id()
    conn = get_db()
    try:
        emp_id = int(str(employee_id).strip())
    except Exception:
        return _bad("employee_id must be an integer", 400)

    try:
        body = request.get_json(silent=True) or {}
        if not _employee_belongs_to_admin(conn.cursor(), emp_id, admin_id):
            return _bad("Employee not found", 404)
        dates = body.get("dates") or []
        if not isinstance(dates, list) or not dates:
            single_date = str(body.get("date") or "").strip()
            from_date = str(body.get("from_date") or "").strip()
            to_date = str(body.get("to_date") or "").strip()
            if single_date:
                dates = [single_date]
            elif from_date and to_date:
                start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                dates = []
                current = start_dt
                while current <= end_dt:
                    dates.append(current.isoformat())
                    current = current + timedelta(days=1)
        result = admin_remove_approved_absence(
            conn,
            emp_id,
            dates,
            reviewed_by=admin_id,
            reason=str(body.get("reason") or "").strip(),
        )
        return _ok(result, "Absent employee removed from approved absence.")
    except AbsenceFlowError as e:
        return _bad(str(e), 400)
    except Exception as e:
        return _bad(f"Failed to remove approved absence: {e}", 500)
    finally:
        conn.close()
