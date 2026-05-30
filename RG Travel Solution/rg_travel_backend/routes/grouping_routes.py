# rg_travel_backend/routes/grouping_routes.py
"""
Grouping + trip assignment compatibility endpoints.

This module keeps legacy endpoints and adds Step-4 contract paths:
- GET  /api/admin/time-slots
- GET  /api/admin/available-vehicles
- GET  /api/admin/available-employees
- POST /api/grouping/preview
- POST /api/trips/create
- POST /api/trips/override
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

from flask import Blueprint, request

try:
    from db import get_db
    from services.hybrid_group_planner import EmployeeNode, VehicleNode, plan_groups_hybrid
    from services.trip_validation_service import filter_eligible_employees
    from services.trip_orchestration_service import (
        TripOrchestrationError,
        create_and_assign_trip,
        preview_and_organize_trip,
    )
    from services.trip_override_service import move_employee_between_trips
    from utils.response import error_response, success_response
except ImportError:
    from db import get_db  # type: ignore
    from services.hybrid_group_planner import EmployeeNode, VehicleNode, plan_groups_hybrid  # type: ignore
    from services.trip_validation_service import filter_eligible_employees  # type: ignore
    from services.trip_orchestration_service import (  # type: ignore
        TripOrchestrationError,
        create_and_assign_trip,
        preview_and_organize_trip,
    )
    from services.trip_override_service import move_employee_between_trips  # type: ignore
    from utils.response import error_response, success_response  # type: ignore


grouping_bp = Blueprint("grouping", __name__, url_prefix="/api")


def _today_key() -> str:
    return datetime.now().strftime("%Y%m%d")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


def _parse_office_coords(conn, admin_id: str = "") -> tuple[float, float]:
    default_lat, default_lng = 19.0760, 72.8777
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(admins)")
    admin_cols = {str(r[1]) for r in cursor.fetchall()}

    select_cols: List[str] = []
    if "office_lat" in admin_cols:
        select_cols.append("office_lat")
    if "office_lng" in admin_cols:
        select_cols.append("office_lng")
    if "office_location" in admin_cols:
        select_cols.append("office_location")
    if not select_cols:
        return default_lat, default_lng

    if admin_id:
        cursor.execute(
            f"SELECT {', '.join(select_cols)} FROM admins WHERE id = ? LIMIT 1",
            (admin_id,),
        )
    else:
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM admins ORDER BY created_at ASC LIMIT 1")

    row = cursor.fetchone()
    if not row:
        return default_lat, default_lng

    row_map = {col: row[idx] for idx, col in enumerate(select_cols)}
    office_lat = row_map.get("office_lat")
    office_lng = row_map.get("office_lng")
    try:
        if office_lat is not None and office_lng is not None:
            lat_val = float(office_lat)
            lng_val = float(office_lng)
            if abs(lat_val) > 0.000001 and abs(lng_val) > 0.000001:
                return lat_val, lng_val
    except Exception:
        pass

    office_location = str(row_map.get("office_location") or "").strip()
    try:
        lat_str, lng_str = office_location.split(",", 1)
        return float(lat_str.strip()), float(lng_str.strip())
    except Exception:
        return default_lat, default_lng


def _resolve_admin_id(conn, admin_id: str) -> Optional[str]:
    cursor = conn.cursor()
    if admin_id:
        cursor.execute("SELECT id FROM admins WHERE id = ? LIMIT 1", (admin_id,))
        if cursor.fetchone():
            return admin_id

    cursor.execute("SELECT id FROM admins ORDER BY created_at ASC LIMIT 1")
    row = cursor.fetchone()
    return str(row[0]) if row else None


def _map_vehicle_ids_to_driver_ids(conn, selected_vehicle_ids: List[int]) -> List[int]:
    if not selected_vehicle_ids:
        return []

    placeholders = ",".join(["?"] * len(selected_vehicle_ids))
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT DISTINCT d.id
        FROM drivers d
        WHERE d.is_approved = 1
          AND (
            d.vehicle_id IN ({placeholders})
            OR d.id IN (
                SELECT CAST(v.vehicle_id AS TEXT)
                FROM vehicles v
                WHERE v.vehicle_id IN ({placeholders})
            )
          )
        """,
        tuple(selected_vehicle_ids + selected_vehicle_ids),
    )

    ids = []
    for row in cursor.fetchall():
        try:
            ids.append(int(row[0]))
        except Exception:
            continue
    return ids


def _normalize_driver_ids(conn, raw_driver_ids: Any, selected_vehicle_ids: Any) -> Optional[List[str]]:
    parsed_driver_ids: List[str] = []
    if isinstance(raw_driver_ids, list):
        for v in raw_driver_ids:
            token = str(v).strip()
            if token:
                parsed_driver_ids.append(token)

    parsed_vehicle_ids: List[int] = []
    if isinstance(selected_vehicle_ids, list):
        for v in selected_vehicle_ids:
            if str(v).isdigit():
                parsed_vehicle_ids.append(int(v))

    cursor = conn.cursor()
    valid_driver_ids: List[str] = []
    if parsed_driver_ids:
        placeholders = ",".join(["?"] * len(parsed_driver_ids))
        cursor.execute(
            f"SELECT id FROM drivers WHERE id IN ({placeholders}) AND is_approved = 1",
            tuple(parsed_driver_ids),
        )
        valid_driver_ids = [str(r[0]) for r in cursor.fetchall() if r and r[0] is not None]

    mapped_from_vehicle = _map_vehicle_ids_to_driver_ids(conn, parsed_vehicle_ids) if parsed_vehicle_ids else []
    mapped_driver_ids = [str(v) for v in mapped_from_vehicle]

    if valid_driver_ids:
        return sorted(set(valid_driver_ids))
    if mapped_driver_ids:
        return sorted(set(mapped_driver_ids))
    # Important: if frontend sends stale/non-matching IDs, do not hard-filter
    # drivers; keep active-trip exclusion logic and allow remaining available drivers.
    return None


@grouping_bp.route("/admin/time-slots", methods=["GET"])
def admin_time_slots():
    """
    Step 1: Return time slots for group creation.
    - Pickup → distinct employees.login_time (HH:MM)
    - Drop   → distinct employees.logout_time (HH:MM)
    Also returns trip_day (YYYYMMDD) for use in later steps.
    """
    trip_type = str(request.args.get("trip_type", "pickup")).strip().lower()
    admin_id = str(request.args.get("admin_id") or "").strip()
    if trip_type not in ("pickup", "drop"):
        return error_response("trip_type must be pickup or drop", 400, "VALIDATION_ERROR")

    time_col = "login_time" if trip_type == "pickup" else "logout_time"
    trip_day = _today_key()

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT DISTINCT {time_col} AS slot
            FROM employees
            WHERE is_active = 1
              AND is_approved = 1
              AND (? = '' OR CAST(COALESCE(admin_id, '') AS TEXT) = ?)
              AND {time_col} IS NOT NULL
              AND TRIM(COALESCE({time_col}, '')) <> ''
            ORDER BY slot ASC
            """
            ,
            (admin_id, admin_id),
        )
        slots = [str(r[0]).strip() for r in cursor.fetchall() if r[0]]

        payload = {
            "trip_type": trip_type,
            "tripType": trip_type,
            "admin_id": admin_id or None,
            "trip_day": trip_day,
            "tripDay": trip_day,
            "slots": slots,
            "step": 1,
        }
        return success_response(payload, "Time slots fetched")
    finally:
        conn.close()


def _go_home_approved_driver_ids(cursor, trip_day: str) -> set:
    """Return set of driver IDs that have approved go-home request (for priority ordering)."""
    try:
        cursor.execute("PRAGMA table_info(driver_hometown_requests)")
        cols = {str(r[1]) for r in cursor.fetchall()}
        if "travel_date" in cols:
            day = str(trip_day or "").replace("-", "")
            day_dash = f"{day[:4]}-{day[4:6]}-{day[6:]}" if len(day) == 8 else day
            cursor.execute(
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
                (day, day_dash),
            )
        else:
            cursor.execute(
                """
                SELECT r.driver_id FROM driver_hometown_requests r
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
        return {str(r[0]) for r in cursor.fetchall() if r[0]}
    except Exception:
        return set()


@grouping_bp.route("/admin/available-vehicles", methods=["GET"])
@grouping_bp.route("/v2/trips/available-vehicles", methods=["GET"])
def admin_available_vehicles():
    """
    Step 2 + Step 3: List available vehicles (drivers) for selected trip type, time slot and day.
    - vehicle_type / vehicle_types: Step 2 — accept "4", "6", or "both" (one or both can be selected).
    - Pickup/drop and time_slot + trip_day exclude drivers already assigned to an active trip.
    - Order: go-home approved first, then 6-seater, then 4-seater.
    - No dependency on vehicles table; uses drivers table only.
    """
    raw_vehicle_type = str(request.args.get("vehicle_type", "")).strip().lower()
    raw_vehicle_types = str(request.args.get("vehicle_types", "")).strip().lower()
    if raw_vehicle_type:
        vehicle_type = raw_vehicle_type
    elif raw_vehicle_types:
        has4 = "4" in raw_vehicle_types
        has6 = "6" in raw_vehicle_types
        if has4 and has6:
            vehicle_type = "both"
        elif has6:
            vehicle_type = "6"
        elif has4:
            vehicle_type = "4"
        else:
            vehicle_type = "both"
    else:
        vehicle_type = "both"
    if vehicle_type not in ("4", "6", "both"):
        return error_response("vehicle_type must be 4, 6 or both", 400, "VALIDATION_ERROR")
    trip_type = str(request.args.get("trip_type", "")).strip().lower()
    time_slot = str(
        request.args.get("time_slot")
        or request.args.get("selected_time")
        or request.args.get("scheduled_time")
        or ""
    ).strip()
    admin_id = str(request.args.get("admin_id") or "").strip()
    trip_day = str(request.args.get("trip_day") or request.args.get("date") or _today_key()).strip().replace("-", "")
    selected_vehicle_ids_raw = str(
        request.args.get("selected_vehicle_ids")
        or request.args.get("selected_driver_ids")
        or ""
    ).strip()

    selected_vehicle_ids: List[Any] = []
    if selected_vehicle_ids_raw:
        for token in selected_vehicle_ids_raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                selected_vehicle_ids.append(int(token) if token.isdigit() else token)
            except Exception:
                selected_vehicle_ids.append(token)
    if trip_type and trip_type not in ("pickup", "drop"):
        return error_response("trip_type must be pickup or drop", 400, "VALIDATION_ERROR")

    conn = get_db()
    try:
        cursor = conn.cursor()
        status_filter = "LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress')"
        trip_predicates = [status_filter, "t.driver_id IS NOT NULL"]
        params: List[Any] = []
        driver_join = ""
        if admin_id:
            driver_join = """
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            """
            params.append(admin_id)
        if trip_type:
            trip_predicates.append("LOWER(COALESCE(t.operation, t.trip_type, '')) = ?")
            params.append(trip_type)
        if time_slot:
            trip_predicates.append("COALESCE(t.time_slot, t.schedule_time, '') = ?")
            params.append(time_slot)
        if trip_day:
            trip_predicates.append("REPLACE(COALESCE(t.trip_day, ''), '-', '') = ?")
            params.append(trip_day)
        vehicle_trip_clause = " AND ".join(trip_predicates)
        driver_exclude = f" AND d.id NOT IN (SELECT t.driver_id FROM trips t WHERE {vehicle_trip_clause})"
        params_driver = list(params)

        driver_where = "WHERE d.is_approved = 1 AND COALESCE(d.is_active, 1) = 1"
        if vehicle_type == "4":
            driver_where += " AND CAST(d.vehicle_type AS TEXT) = '4'"
        elif vehicle_type == "6":
            driver_where += " AND CAST(d.vehicle_type AS TEXT) = '6'"
        if selected_vehicle_ids:
            placeholders = ",".join(["?"] * len(selected_vehicle_ids))
            driver_where += f" AND d.id IN ({placeholders})"
            params_driver.extend([str(x) for x in selected_vehicle_ids])
        driver_where += driver_exclude

        cursor.execute(
            f"""
            SELECT d.id, d.name, d.mobile, d.vehicle_no, d.vehicle_type
            FROM drivers d
            {driver_join}
            {driver_where}
            ORDER BY d.vehicle_type DESC, d.vehicle_no ASC
            """,
            tuple(params_driver),
        )
        rows = cursor.fetchall()
        go_home_ids = _go_home_approved_driver_ids(cursor, trip_day)

        vehicles = []
        for r in rows:
            driver_id = str(r[0])
            vt = r[4]
            vtype_int = int(vt) if (vt is not None and str(vt).isdigit()) else (6 if str(vt) == "6" else 4)
            vehicles.append(
                {
                    "vehicle_id": r[0],
                    "vehicle_no": r[3],
                    "vehicle_type": vtype_int,
                    "is_available": True,
                    "driver": {
                        "driver_id": driver_id,
                        "name": r[1],
                        "phone": r[2],
                        "is_approved": True,
                        "is_active": True,
                    },
                    "go_home_request": driver_id in go_home_ids,
                }
            )
        vehicles.sort(key=lambda v: (0 if v.get("go_home_request") else 1, -v.get("vehicle_type", 4)))

        payload = {
            "vehicle_type": vehicle_type,
            "vehicleType": vehicle_type,
            "trip_type": trip_type or None,
            "time_slot": time_slot or None,
            "trip_day": trip_day or None,
            "admin_id": admin_id or None,
            "selected_vehicle_ids": selected_vehicle_ids,
            "vehicles": vehicles,
            "count": len(vehicles),
        }
        return success_response(payload, "Available vehicles fetched")
    finally:
        conn.close()


@grouping_bp.route("/admin/available-employees", methods=["GET"])
@grouping_bp.route("/v2/trips/available-employees", methods=["GET"])
def admin_available_employees():
    """
    Step 4: List employees eligible for the selected time slot.
    - Pickup: login_time = time_slot; Drop: logout_time = time_slot.
    - Excludes: approved absence on trip_day, approved 'no_trip' request, already in active trip (same day+time).
    - Query: trip_type, time_slot (required), trip_day (optional, default today).
    """
    trip_type = str(request.args.get("trip_type", "")).strip().lower()
    time_slot = str(
        request.args.get("time_slot")
        or request.args.get("selected_time")
        or request.args.get("scheduled_time")
        or ""
    ).strip()
    admin_id = str(request.args.get("admin_id") or "").strip()
    trip_day_param = str(request.args.get("trip_day") or request.args.get("date") or "").strip().replace("-", "")

    if trip_type not in ("pickup", "drop"):
        return error_response("trip_type must be pickup or drop", 400, "VALIDATION_ERROR")
    if not time_slot:
        return error_response("time_slot is required (HH:MM)", 400, "VALIDATION_ERROR")

    day_key = trip_day_param if len(trip_day_param) == 8 and trip_day_param.isdigit() else _today_key()
    time_col = "login_time" if trip_type == "pickup" else "logout_time"

    conn = get_db()
    try:
        eligible_employees, _ = filter_eligible_employees(
            conn,
            trip_type=trip_type,
            selected_time=time_slot,
            trip_day=day_key,
            admin_id=admin_id or None,
        )

        employees = [
            {
                "id": item.get("id"),
                "employee_id": item.get("employee_id") or str(item.get("id") or ""),
                "name": item.get("name") or "",
                "phone": item.get("mobile") or "",
                "address": item.get("home_address")
                or item.get("pickup_address")
                or item.get("drop_location")
                or "",
                "home_lat": item.get("home_lat"),
                "home_lng": item.get("home_lng"),
                "login_time": item.get("login_time"),
                "logout_time": item.get("logout_time"),
            }
            for item in eligible_employees
        ]

        payload = {
            "trip_type": trip_type,
            "tripType": trip_type,
            "time_slot": time_slot,
            "timeSlot": time_slot,
            "trip_day": day_key,
            "tripDay": day_key,
            "admin_id": admin_id or None,
            "employees": employees,
            "count": len(employees),
            "step": 4,
        }
        return success_response(payload, "Available employees fetched")
    finally:
        conn.close()


@grouping_bp.route("/grouping/preview", methods=["POST"])
@grouping_bp.route("/groups/preview", methods=["POST"])
@grouping_bp.route("/admin/groups/auto", methods=["POST"])
def create_auto_groups():
    """
    Step 5 (preview): Preview groups without persisting.
    Body: trip_type, time_slot, vehicle_types, selected_vehicle_ids/driver_ids, selected_employee_ids, admin_id, office_lat/lng.
    Returns groups (nearest employees by capacity), unassigned_employees. Go-home drivers get priority; 6-seater first when both types selected.
    """
    payload = request.get_json(silent=True) or {}
    trip_type = str(payload.get("trip_type") or payload.get("tripType") or "").strip().lower()
    time_slot = str(
        payload.get("time_slot")
        or payload.get("selected_time")
        or payload.get("scheduled_time")
        or payload.get("schedule_time")
        or ""
    ).strip()
    admin_id = str(payload.get("admin_id", "system")).strip() or "system"
    trip_day = str(payload.get("trip_day") or payload.get("tripDay") or _today_key()).replace("-", "").strip()

    vehicle_types = payload.get("vehicle_types", payload.get("vehicle_type", [4, 6]))
    raw_driver_ids = payload.get("selected_driver_ids", payload.get("driver_ids"))
    selected_vehicle_ids = payload.get("selected_vehicle_ids", payload.get("vehicle_ids", []))
    selected_employee_ids = payload.get("selected_employee_ids", payload.get("employee_ids"))

    if trip_type not in ("pickup", "drop"):
        return error_response("trip_type must be pickup or drop", 400, "VALIDATION_ERROR")
    if not time_slot:
        return error_response("time_slot is required", 400, "VALIDATION_ERROR")
    if not isinstance(selected_vehicle_ids, list):
        return error_response("selected_vehicle_ids must be a list", 400, "VALIDATION_ERROR")
    if selected_employee_ids is not None and not isinstance(selected_employee_ids, list):
        return error_response("selected_employee_ids must be a list", 400, "VALIDATION_ERROR")

    if not isinstance(vehicle_types, list):
        vehicle_types = [vehicle_types]
    try:
        parsed_vehicle_types = sorted({int(v) for v in vehicle_types if int(v) in (4, 6)}, reverse=True)
    except Exception:
        return error_response("vehicle_types must contain 4 and/or 6", 400, "VALIDATION_ERROR")
    if not parsed_vehicle_types:
        parsed_vehicle_types = [6, 4]

    conn = get_db()
    try:
        resolved_admin_id = _resolve_admin_id(conn, admin_id) or admin_id
        office_lat, office_lng = _parse_office_coords(conn, resolved_admin_id)
        cursor = conn.cursor()
        go_home_ids = _go_home_approved_driver_ids(cursor, trip_day)

        eligible_employees, exclusions = filter_eligible_employees(
            conn,
            trip_type=trip_type,
            selected_time=time_slot,
            employee_ids=selected_employee_ids if isinstance(selected_employee_ids, list) else None,
            trip_day=trip_day,
            admin_id=resolved_admin_id or None,
        )
        if not eligible_employees:
            return error_response(
                "No eligible employees found for selected slot",
                400,
                "NO_EMPLOYEES",
                {"exclusions": exclusions},
            )

        employee_nodes, unresolved_coords = _build_employee_nodes_strict(
            eligible_employees,
            trip_type,
        )
        if unresolved_coords:
            exclusions = list(exclusions or [])
            exclusions.append(
                f"Excluded {len(unresolved_coords)} employees due to missing/invalid coordinates"
            )
        if not employee_nodes:
            return error_response(
                "No employees with valid coordinates found",
                400,
                "NO_VALID_COORDINATES",
                {"exclusions": exclusions, "unresolved_coordinates": unresolved_coords},
            )

        normalized_driver_ids = _normalize_driver_ids(conn, raw_driver_ids, selected_vehicle_ids)

        cursor.execute("PRAGMA table_info(drivers)")
        driver_cols = {str(r[1]) for r in cursor.fetchall()}
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

        params: List[Any] = []
        driver_join = ""
        if resolved_admin_id:
            driver_join = """
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            """
            params.append(resolved_admin_id)
        where_parts = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "d.id NOT IN (SELECT t.driver_id FROM trips t WHERE REPLACE(COALESCE(t.trip_day, ''), '-', '') = ? AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ? AND COALESCE(t.time_slot, t.schedule_time, '') = ? AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress') AND t.driver_id IS NOT NULL)",
        ]
        params.extend([trip_day, trip_type, time_slot])

        if parsed_vehicle_types:
            ph = ",".join(["?"] * len(parsed_vehicle_types))
            where_parts.append(f"CAST(d.vehicle_type AS INTEGER) IN ({ph})")
            params.extend(parsed_vehicle_types)

        if normalized_driver_ids is not None and len(normalized_driver_ids) > 0:
            ph = ",".join(["?"] * len(normalized_driver_ids))
            where_parts.append(f"CAST(d.id AS TEXT) IN ({ph})")
            params.extend(normalized_driver_ids)

        cursor.execute(
            f"""
            SELECT d.id, d.name, d.vehicle_no, CAST(d.vehicle_type AS INTEGER) AS vtype,
                   {lat_expr} AS home_lat, {lng_expr} AS home_lng
            FROM drivers d
            {driver_join}
            WHERE {" AND ".join(where_parts)}
            ORDER BY vtype DESC, d.id ASC
            """,
            tuple(params),
        )
        driver_rows = cursor.fetchall()
        if not driver_rows:
            return error_response("No available drivers/vehicles for selected slot", 400, "NO_VEHICLES")

        vehicle_nodes: List[VehicleNode] = []
        for row in driver_rows:
            d_id = str(row[0])
            vt = int(row[3]) if str(row[3]).isdigit() else 4
            if vt not in (4, 6):
                continue
            vehicle_nodes.append(
                VehicleNode(
                    driver_id=d_id,
                    driver_name=str(row[1] or ""),
                    vehicle_no=str(row[2] or ""),
                    vehicle_type=vt,
                    go_home_approved=d_id in go_home_ids,
                    home_lat=float(row[4] or 0.0),
                    home_lng=float(row[5] or 0.0),
                )
            )

        if not vehicle_nodes:
            return error_response("No valid selected vehicles found", 400, "NO_VEHICLES")

        plan = plan_groups_hybrid(
            employees=employee_nodes,
            vehicles=vehicle_nodes,
            office=(float(office_lat), float(office_lng)),
            prioritize_6_when_mixed=True,
            strict_hybrid=True,
        )

        groups_out: List[Dict[str, Any]] = []
        for group in plan.get("groups", []):
            normalized_members = []
            for idx, m in enumerate(group.get("members", []), start=1):
                normalized_members.append(
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "phone": m.get("mobile"),
                        "address": m.get("address"),
                        "home_lat": m.get("lat"),
                        "home_lng": m.get("lng"),
                        "sequence_no": idx,
                    }
                )

            groups_out.append(
                {
                    "capacity": int(group.get("vehicle_type", 4)),
                    "employees": normalized_members,
                    "suggested_vehicle": {
                        "driver_id": group.get("driver_id"),
                        "driver_name": group.get("driver_name"),
                        "vehicle_no": group.get("vehicle_no"),
                        "vehicle_type": int(group.get("vehicle_type", 4)),
                        "go_home_approved": bool(group.get("go_home_approved")),
                    },
                }
            )

        unassigned = [
            {
                "id": x.get("id"),
                "name": x.get("name"),
                "phone": x.get("mobile"),
                "address": x.get("address"),
                "home_lat": x.get("lat"),
                "home_lng": x.get("lng"),
            }
            for x in plan.get("unassigned_employees", [])
            if isinstance(x, dict)
        ]

        warnings = list(exclusions or [])
        if bool(plan.get("hybrid_fallback_used")):
            warnings.append(
                "Road provider unavailable; used haversine fallback for grouping estimates."
            )
            fallback_reason = str(plan.get("hybrid_fallback_reason") or "").strip()
            if fallback_reason:
                warnings.append(fallback_reason)

        out = {
            "trip_type": trip_type,
            "tripType": trip_type,
            "trip_day": trip_day,
            "tripDay": trip_day,
            "time_slot": time_slot,
            "timeSlot": time_slot,
            "vehicle_types": parsed_vehicle_types,
            "groups": groups_out,
            "unassigned_employees": unassigned,
            "unassignedEmployees": unassigned,
            "unassigned_vehicles": plan.get("unassigned_vehicles", []),
            "hybrid_provider": plan.get("hybrid_provider"),
            "hybrid_strict": bool(plan.get("hybrid_strict", True)),
            "hybrid_degraded_edges": int(plan.get("hybrid_degraded_edges", 0)),
            "warnings": warnings,
            "unresolved_coordinates": unresolved_coords,
        }
        return success_response(out, "Grouping preview generated (mandatory hybrid)")
    except ValueError as exc:
        return error_response(
            f"Hybrid provider configuration error: {exc}",
            503,
            "HYBRID_PROVIDER_UNAVAILABLE",
            {"hint": "Check /api/health/hybrid and HYBRID_ROUTE_PROVIDER config."},
        )
    except RuntimeError as exc:
        return error_response(
            f"Hybrid provider unavailable: {exc}",
            503,
            "HYBRID_PROVIDER_UNAVAILABLE",
            {"hint": "Check /api/health/hybrid and route provider health."},
        )
    except Exception as exc:
        return error_response(f"Preview failed: {exc}", 500, "INTERNAL_ERROR")
    finally:
        conn.close()


@grouping_bp.route("/grouping/create", methods=["POST"])
@grouping_bp.route("/grouping/createGroups", methods=["POST"])  # camelCase compatibility
@grouping_bp.route("/admin/groups/create", methods=["POST"])  # fallback path used by Flutter
@grouping_bp.route("/admin/groups/createGroups", methods=["POST"])  # camelCase fallback
def create_groups_main():
    """
    Step 5: Create groups (mandatory hybrid: Haversine + OSRM/ORS road distance).
    Accepts: admin_id, trip_type, selected_time, vehicle_types, driver_ids/selected_vehicle_ids,
             employee_ids/selected_employee_ids, vehicle_priority_enabled.
             Note: office coordinates are always resolved from admin profile.
    Returns: groups (with members, capacity, distance_km_estimate), warnings, trip_metadata, unassigned_employees.
    Go-home drivers get nearest trip first; 6-seater priority when both types selected.
    """
    payload = request.get_json(silent=True) or {}
    admin_id = str(payload.get("admin_id", "")).strip()
    trip_type = str(payload.get("trip_type") or payload.get("tripType") or "").strip().lower()
    selected_time = str(
        payload.get("selected_time")
        or payload.get("time_slot")
        or payload.get("scheduled_time")
        or payload.get("schedule_time")
        or ""
    ).strip()
    trip_day = str(payload.get("trip_day") or payload.get("tripDay") or _today_key()).replace("-", "").strip()
    vehicle_types = payload.get("vehicle_types", payload.get("vehicle_type", []))
    raw_driver_ids = payload.get("driver_ids", payload.get("selected_driver_ids"))
    selected_vehicle_ids = payload.get("selected_vehicle_ids", payload.get("vehicle_ids"))
    employee_ids = payload.get("employee_ids", payload.get("selected_employee_ids"))
    vehicle_priority_enabled = bool(payload.get("vehicle_priority_enabled", True))
    try:
        requested_batch_size = int(payload.get("batch_size") or payload.get("vehicle_batch_size") or 0)
    except Exception:
        requested_batch_size = 0
    vehicle_batch_size = max(0, min(requested_batch_size, 1000))

    if not admin_id or trip_type not in ("pickup", "drop") or not selected_time:
        return success_response(
            {"groups": [], "warnings": ["Missing or invalid required fields"]},
            "Invalid input",
            200,
        )

    if not isinstance(vehicle_types, list) or not vehicle_types:
        vehicle_types = [6, 4]

    try:
        parsed_vehicle_types = sorted({int(v) for v in vehicle_types if int(v) in (4, 6)}, reverse=True)
    except Exception:
        parsed_vehicle_types = [6, 4]
    if not parsed_vehicle_types:
        parsed_vehicle_types = [6, 4]

    conn = get_db()
    try:
        try:
            from services.route_no_service import generate_unique_route_no
        except Exception:
            generate_unique_route_no = None

        resolved_admin_id = _resolve_admin_id(conn, admin_id) or admin_id
        office_lat, office_lng = _parse_office_coords(conn, resolved_admin_id)
        normalized_driver_ids = _normalize_driver_ids(conn, raw_driver_ids, selected_vehicle_ids)
        cursor = conn.cursor()
        go_home_ids = _go_home_approved_driver_ids(cursor, trip_day)

        eligible_employees, exclusions = filter_eligible_employees(
            conn,
            trip_type=trip_type,
            selected_time=selected_time,
            employee_ids=employee_ids if isinstance(employee_ids, list) else None,
            trip_day=trip_day,
            admin_id=resolved_admin_id or None,
        )
        if not eligible_employees:
            return success_response(
                {"groups": [], "warnings": ["No eligible employees found"] + list(exclusions or [])},
                "No groups generated",
                200,
            )

        employee_nodes, unresolved_coords = _build_employee_nodes_strict(
            eligible_employees,
            trip_type,
        )
        fallback_added = 0
        if unresolved_coords and employee_ids:
            unresolved_ids = {
                int(x.get("id"))
                for x in unresolved_coords
                if x.get("id") is not None and str(x.get("id")).isdigit()
            }
            if unresolved_ids:
                by_id = {
                    int(e.get("id")): e
                    for e in eligible_employees
                    if e.get("id") is not None and str(e.get("id")).isdigit()
                }
                for emp_id in sorted(unresolved_ids):
                    src = by_id.get(emp_id)
                    if not src:
                        continue
                    employee_nodes.append(
                        EmployeeNode(
                            id=int(src.get("id")),
                            name=str(src.get("name") or ""),
                            mobile=str(src.get("mobile") or ""),
                            address=str(
                                src.get("pickup_address")
                                or src.get("home_address")
                                or src.get("drop_location")
                                or ""
                            ),
                            lat=float(office_lat),
                            lng=float(office_lng),
                        )
                    )
                    fallback_added += 1
                if fallback_added > 0:
                    unresolved_coords = [
                        x
                        for x in unresolved_coords
                        if not (x.get("id") is not None and str(x.get("id")).isdigit() and int(x.get("id")) in unresolved_ids)
                    ]
        if unresolved_coords:
            exclusions = list(exclusions or [])
            exclusions.append(
                f"Excluded {len(unresolved_coords)} employees due to missing/invalid coordinates"
            )
        if fallback_added > 0:
            exclusions = list(exclusions or [])
            exclusions.append(
                f"Included {fallback_added} selected employees using office-location coordinate fallback."
            )
        if not employee_nodes:
            return success_response(
                {
                    "groups": [],
                    "warnings": list(exclusions or []) + ["No employees with valid coordinates"],
                    "unresolved_coordinates": unresolved_coords,
                },
                "No groups generated",
                200,
            )

        cursor.execute("PRAGMA table_info(drivers)")
        driver_cols = {str(r[1]) for r in cursor.fetchall()}
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
        params: List[Any] = []
        driver_join = ""
        if resolved_admin_id:
            driver_join = """
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            """
            params.append(resolved_admin_id)
        where_parts = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "d.id NOT IN (SELECT t.driver_id FROM trips t WHERE REPLACE(COALESCE(t.trip_day, ''), '-', '') = ? AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ? AND COALESCE(t.time_slot, t.schedule_time, '') = ? AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress') AND t.driver_id IS NOT NULL)",
        ]
        params.extend([trip_day, trip_type, selected_time])

        if parsed_vehicle_types:
            ph = ",".join(["?"] * len(parsed_vehicle_types))
            where_parts.append(f"CAST(d.vehicle_type AS INTEGER) IN ({ph})")
            params.extend(parsed_vehicle_types)
        if normalized_driver_ids is not None and len(normalized_driver_ids) > 0:
            ph = ",".join(["?"] * len(normalized_driver_ids))
            where_parts.append(f"CAST(d.id AS TEXT) IN ({ph})")
            params.extend(normalized_driver_ids)

        cursor.execute(
            f"""
            SELECT d.id, d.name, d.vehicle_no, CAST(d.vehicle_type AS INTEGER) AS vtype,
                   {lat_expr} AS home_lat, {lng_expr} AS home_lng
            FROM drivers d
            {driver_join}
            WHERE {" AND ".join(where_parts)}
            ORDER BY vtype DESC, d.id ASC
            """,
            tuple(params),
        )
        driver_rows = cursor.fetchall()
        if not driver_rows:
            return success_response(
                {"groups": [], "warnings": ["No available vehicles/drivers for selected slot"]},
                "No groups generated",
                200,
            )

        vehicle_nodes: List[VehicleNode] = []
        for row in driver_rows:
            d_id = str(row[0])
            vt = int(row[3]) if str(row[3]).isdigit() else 4
            if vt not in (4, 6):
                continue
            vehicle_nodes.append(
                VehicleNode(
                    driver_id=d_id,
                    driver_name=str(row[1] or ""),
                    vehicle_no=str(row[2] or ""),
                    vehicle_type=vt,
                    go_home_approved=d_id in go_home_ids,
                    home_lat=float(row[4] or 0.0),
                    home_lng=float(row[5] or 0.0),
                )
            )

        if not vehicle_nodes:
            return success_response(
                {"groups": [], "warnings": ["No valid selected vehicles found"]},
                "No groups generated",
                200,
            )

        plan = plan_groups_hybrid(
            employees=employee_nodes,
            vehicles=vehicle_nodes,
            office=(float(office_lat), float(office_lng)),
            prioritize_6_when_mixed=vehicle_priority_enabled,
            strict_hybrid=True,
            vehicle_batch_size=vehicle_batch_size if vehicle_batch_size > 0 else None,
        )

        groups: List[Dict[str, Any]] = []
        selected_vehicle_types = set(parsed_vehicle_types)

        def _resolve_group_vehicle_type(raw_type: Any, members_count: int) -> int:
            try:
                parsed = int(raw_type)
            except Exception:
                parsed = 0
            if parsed in selected_vehicle_types:
                return parsed
            preferred = sorted(selected_vehicle_types)
            for cap in preferred:
                if members_count <= cap:
                    return int(cap)
            return int(preferred[-1]) if preferred else 4

        warnings = list(exclusions or [])
        unassigned_employees_raw = cast(List[Dict[str, Any]], plan.get("unassigned_employees", []))
        if unassigned_employees_raw:
            eligible_next_trip = sum(
                1 for e in unassigned_employees_raw if bool(e.get("eligible_for_next_trip", False))
            )
            if eligible_next_trip > 0:
                warnings.append(
                    f"{eligible_next_trip} unassigned employee(s) remain eligible for next trip assignment."
                )
        unassigned_vehicles = cast(List[Dict[str, Any]], plan.get("unassigned_vehicles", []))
        if unassigned_vehicles:
            eligible_next_group = sum(
                1 for v in unassigned_vehicles if bool(v.get("eligible_for_next_group_creation", False))
            )
            if eligible_next_group > 0:
                warnings.append(
                    f"{eligible_next_group} unassigned vehicle(s) are kept eligible for next group creation."
                )
        if int(plan.get("vehicle_batches") or 1) > 1:
            warnings.append(
                f"Grouped in {int(plan.get('vehicle_batches') or 1)} vehicle batches (batch size {int(plan.get('vehicle_batch_size') or 0)})."
            )
        if bool(plan.get("hybrid_fallback_used")):
            warnings.append(
                "Road provider unavailable; used haversine fallback for grouping estimates."
            )
            fallback_reason = str(plan.get("hybrid_fallback_reason") or "").strip()
            if fallback_reason:
                warnings.append(fallback_reason)
        for g_idx, g in enumerate(plan.get("groups", []), start=1):
            members: List[Dict[str, Any]] = []
            for seq, m in enumerate(g.get("members", []), start=1):
                members.append(
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "mobile": m.get("mobile"),
                        "phone": m.get("mobile"),
                        "address": m.get("address"),
                        "lat": m.get("lat"),
                        "lng": m.get("lng"),
                        "drop_location": m.get("address"),
                        "sequence_no": seq,
                    }
                )
            group_vehicle_type = _resolve_group_vehicle_type(
                g.get("vehicle_type", 4),
                len(members),
            )
            groups.append(
                {
                    "group_index": g_idx,
                    "capacity": group_vehicle_type,
                    "vehicle_type": group_vehicle_type,
                    "members": members,
                    "employees": members,
                    "distance_km_estimate": g.get("route_distance_km", g.get("anchor_distance_km")),
                    "eta_min_estimate": None,
                    "assigned_driver_id": g.get("driver_id"),
                    "assigned_cab_no": g.get("vehicle_no"),
                    "go_home_approved": bool(g.get("go_home_approved")),
                }
            )

        unassigned_employees = [
            {
                "id": x.get("id"),
                "name": x.get("name"),
                "phone": x.get("mobile"),
                "address": x.get("address"),
                "home_lat": x.get("lat"),
                "home_lng": x.get("lng"),
                "reason": x.get("reason"),
                "eligible_for_next_trip": bool(x.get("eligible_for_next_trip", False)),
            }
            for x in unassigned_employees_raw
            if isinstance(x, dict)
        ]

        preview_route_no = None
        if generate_unique_route_no:
            try:
                preview_route_no = generate_unique_route_no(conn)
            except Exception:
                preview_route_no = None

        return success_response(
            {
                "groups": groups,
                "route_no": preview_route_no,
                "routeNo": preview_route_no,
                "warnings": warnings,
                "unresolved_coordinates": unresolved_coords,
                "unassigned_employees": unassigned_employees,
                "unassignedEmployees": unassigned_employees,
                "unassigned_vehicles": unassigned_vehicles,
                "vehicle_batch_size": plan.get("vehicle_batch_size"),
                "vehicle_batches": int(plan.get("vehicle_batches", 1) or 1),
                "trip_metadata": {
                    "trip_type": trip_type,
                    "selected_time": selected_time,
                    "trip_day": trip_day,
                    "vehicle_types": parsed_vehicle_types,
                    "group_fill_rule": "full_capacity_first_then_last_partial",
                    "hybrid_provider": plan.get("hybrid_provider"),
                    "hybrid_strict": bool(plan.get("hybrid_strict", True)),
                    "vehicle_batch_size": plan.get("vehicle_batch_size"),
                    "vehicle_batches": int(plan.get("vehicle_batches", 1) or 1),
                },
            },
            "Groups created",
            200,
        )
    except ValueError as exc:
        return success_response(
            {
                "groups": [],
                "warnings": [
                    f"Hybrid provider unavailable: {exc}",
                    "Check /api/health/hybrid and route provider config.",
                ],
            },
            "Groups creation failed",
            200,
        )
    except RuntimeError as exc:
        return success_response(
            {
                "groups": [],
                "warnings": [
                    f"Hybrid provider unavailable: {exc}",
                    "Check /api/health/hybrid and route provider health.",
                ],
            },
            "Groups creation failed",
            200,
        )
    except Exception as exc:
        return success_response({"groups": [], "warnings": [str(exc)]}, "Groups creation failed", 200)
    finally:
        conn.close()


@grouping_bp.route("/trips/create", methods=["POST"])
def create_trips_step4():
    """
    Step-4 compatible finalization endpoint.

    Body:
    {
      "trip_type": "pickup"|"drop",
      "time_slot": "HH:MM",
      "groups": [
        {"capacity": 6, "employee_ids": [1,2], "vehicle_id": 10, "driver_id": "DRV001"}
      ],
      "admin_id": "optional"
    }
    """
    payload = request.get_json(silent=True) or {}
    trip_type = str(payload.get("trip_type", "")).strip().lower()
    time_slot = str(payload.get("time_slot") or payload.get("schedule_time") or "").strip()
    groups = payload.get("groups", [])
    admin_id = str(payload.get("admin_id", "")).strip()

    if trip_type not in ("pickup", "drop"):
        return error_response("trip_type must be pickup or drop", 400, "VALIDATION_ERROR")
    if not time_slot:
        return error_response("time_slot is required", 400, "VALIDATION_ERROR")
    if not isinstance(groups, list) or not groups:
        return error_response("groups must be a non-empty list", 400, "VALIDATION_ERROR")

    conn = get_db()
    try:
        resolved_admin_id = _resolve_admin_id(conn, admin_id) or admin_id or "system"
        office_lat, office_lng = _parse_office_coords(conn, resolved_admin_id)

        groups_to_create: List[Dict[str, Any]] = []
        driver_assignments: Dict[int, Dict[str, str]] = {}

        cursor = conn.cursor()

        for idx, g in enumerate(groups):
            employee_ids = g.get("employee_ids", [])
            if not isinstance(employee_ids, list) or not employee_ids:
                return error_response(f"groups[{idx}].employee_ids must be non-empty list", 400, "VALIDATION_ERROR")

            placeholders = ",".join(["?"] * len(employee_ids))
            employee_params: List[Any] = list(employee_ids)
            employee_admin_filter = ""
            if resolved_admin_id:
                employee_admin_filter = " AND CAST(COALESCE(admin_id, '') AS TEXT) = ?"
                employee_params.append(resolved_admin_id)
            cursor.execute(
                f"""
                SELECT id, name, mobile,
                       COALESCE(home_address, pickup_address, drop_location, '') AS address,
                       COALESCE(home_lat, pickup_lat, drop_lat, 0) AS lat,
                       COALESCE(home_lng, pickup_lng, drop_lng, 0) AS lng
                FROM employees
                WHERE id IN ({placeholders})
                {employee_admin_filter}
                """,
                tuple(employee_params),
            )
            rows = cursor.fetchall()
            row_map = {r[0]: r for r in rows}

            members = []
            for emp_id in employee_ids:
                row = row_map.get(emp_id)
                if not row:
                    return error_response(f"Employee not found: {emp_id}", 404, "EMPLOYEE_NOT_FOUND")
                members.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "mobile": row[2],
                        "address": row[3],
                        "lat": float(row[4] or 0) if not (abs(float(row[4] or 0)) < 0.001 and abs(float(row[5] or 0)) < 0.001) else float(office_lat),
                        "lng": float(row[5] or 0) if not (abs(float(row[4] or 0)) < 0.001 and abs(float(row[5] or 0)) < 0.001) else float(office_lng),
                    }
                )

            groups_to_create.append(
                {
                    "group_index": idx + 1,
                    "members": members,
                    "vehicle_type": int(g.get("capacity") or (6 if len(employee_ids) > 4 else 4)),
                    "vehicle_id": g.get("vehicle_id"),
                }
            )

            if g.get("driver_id"):
                driver_assignments[idx] = {
                    "driver_id": str(g.get("driver_id")),
                    "cab_id": str(g.get("vehicle_id") or g.get("driver_id")),
                }

        preview_data = {
            "trip_preview": {
                "trip_type": trip_type,
                "selected_time": time_slot,
                "vehicle_types": sorted({int(x.get("vehicle_type", 4)) for x in groups_to_create}, reverse=True),
                "vehicle_type": int(groups_to_create[0].get("vehicle_type", 4)),
                "trip_day": _today_key(),
                "office_lat": office_lat,
                "office_lng": office_lng,
            }
        }

        result = create_and_assign_trip(
            conn,
            admin_id=resolved_admin_id,
            preview_data=preview_data,
            groups_to_create=groups_to_create,
            driver_assignments=driver_assignments,
        )

        if not result.get("success"):
            conn.rollback()
            return error_response(result.get("message", "Trip creation failed"), 400, "TRIP_CREATE_FAILED")

        created = result.get("data", {}).get("trips_created", [])
        groups_saved = len(created)
        routes_saved = len(created)

        groups_payload: List[Dict[str, Any]] = []
        trips_payload: List[Dict[str, Any]] = []

        for idx, trip in enumerate(created):
            trip_id = int(trip.get("trip_id"))
            route_no = str(trip.get("route_no"))
            input_group = groups[idx] if idx < len(groups) else {}
            created_group = groups_to_create[idx] if idx < len(groups_to_create) else {}

            capacity = int(input_group.get("capacity") or created_group.get("vehicle_type", 4))
            members = []
            for seq, m in enumerate(created_group.get("members", []), start=1):
                members.append(
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "phone": m.get("mobile"),
                        "address": m.get("address"),
                        "sequence_no": seq,
                    }
                )

            trip_item = {
                "trip_id": trip_id,
                "route_no": route_no,
                "routeNo": route_no,
                "time_slot": time_slot,
                "timeSlot": time_slot,
                "trip_type": trip_type,
                "tripType": trip_type,
                "driver": {
                    "driver_id": trip.get("driver_id"),
                    "name": trip.get("driver_name"),
                    "phone": trip.get("driver_mobile"),
                },
                "vehicle": {
                    "vehicle_id": input_group.get("vehicle_id"),
                    "vehicle_no": trip.get("vehicle_no"),
                    "vehicle_type": trip.get("vehicle_type"),
                },
                "group": {
                    "capacity": capacity,
                    "members": members,
                },
                "total_km": trip.get("total_distance_km"),
                "polyline": trip.get("polyline", ""),
            }
            trips_payload.append(trip_item)
            groups_payload.append(trip_item["group"])

        conn.commit()

        route_nos = [t.get("route_no") for t in created]
        out = {
            "route_no": route_nos[0] if route_nos else None,
            "routeNo": route_nos[0] if route_nos else None,
            "route_nos": route_nos,
            "routeNos": route_nos,
            "time_slot": time_slot,
            "timeSlot": time_slot,
            "trip_type": trip_type,
            "tripType": trip_type,
            "trips_created": True,
            "groups_saved": groups_saved,
            "routes_saved": routes_saved,
            "trips": trips_payload,
            "groups": groups_payload,
        }
        return success_response(out, "Trips created successfully", 201)

    except Exception as exc:
        conn.rollback()
        return error_response(f"Trip creation failed: {exc}", 500, "INTERNAL_ERROR")
    finally:
        conn.close()


@grouping_bp.route("/trips/override", methods=["POST"])
def admin_override_trip():
    """
    Generic override endpoint for Step 4.

    Body (swap employee):
    {
      "action": "swap_employee",
      "employee_id": 1,
      "source_trip_id": 10,
      "destination_trip_id": 11,
      "admin_id": "ADM001",
      "reason": "manual override"
    }

    Body (change vehicle):
    {
      "action": "change_vehicle",
      "trip_id": 10,
      "vehicle_id": 5,
      "admin_id": "ADM001"
    }
    """
    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action", "")).strip().lower()

    conn = get_db()
    try:
        if action in ("swap_employee", "swap-employee"):
            required = ["employee_id", "source_trip_id", "destination_trip_id", "admin_id"]
            missing = [k for k in required if payload.get(k) in (None, "")]
            if missing:
                return error_response(f"Missing fields: {', '.join(missing)}", 400, "VALIDATION_ERROR")

            result = move_employee_between_trips(
                conn,
                employee_id=int(payload["employee_id"]),
                source_trip_id=int(payload["source_trip_id"]),
                destination_trip_id=int(payload["destination_trip_id"]),
                admin_id=str(payload["admin_id"]),
                reason=str(payload.get("reason", "")),
            )

            if result.get("success"):
                return success_response(result.get("data"), "Override applied")
            return error_response(result.get("message", "Override failed"), 400, "OVERRIDE_FAILED")

        if action in ("change_vehicle", "change-vehicle"):
            required = ["trip_id", "vehicle_id", "admin_id"]
            missing = [k for k in required if payload.get(k) in (None, "")]
            if missing:
                return error_response(f"Missing fields: {', '.join(missing)}", 400, "VALIDATION_ERROR")

            trip_id = int(payload["trip_id"])
            vehicle_id = int(payload["vehicle_id"])

            cursor = conn.cursor()
            cursor.execute("SELECT id, route_no FROM trips WHERE id = ?", (trip_id,))
            trip = cursor.fetchone()
            if not trip:
                return error_response("Trip not found", 404, "TRIP_NOT_FOUND")

            cursor.execute(
                "UPDATE trips SET vehicle_id = ?, updated_at = ? WHERE id = ?",
                (vehicle_id, _now_iso(), trip_id),
            )
            cursor.execute(
                "UPDATE trip_groups SET vehicle_id = ? WHERE trip_id = ?",
                (vehicle_id, trip_id),
            )
            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='admin_audit' LIMIT 1")
            if cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO admin_audit (admin_id, action, target_type, target_id, details, created_at)
                    VALUES (?, 'change_vehicle', 'trip', ?, ?, ?)
                    """,
                    (str(payload["admin_id"]), str(trip_id), f"vehicle_id={vehicle_id}", _now_iso()),
                )

            conn.commit()
            return success_response(
                {
                    "trip_id": trip_id,
                    "route_no": trip[1],
                    "routeNo": trip[1],
                    "vehicle_id": vehicle_id,
                    "rerouted": False,
                },
                "Vehicle changed",
            )

        return error_response(
            "action must be swap_employee or change_vehicle",
            400,
            "VALIDATION_ERROR",
        )

    except Exception as exc:
        conn.rollback()
        return error_response(f"Override failed: {exc}", 500, "INTERNAL_ERROR")
    finally:
        conn.close()


# Legacy alias retained for old clients
@grouping_bp.route("/trips/assign", methods=["POST"])
@grouping_bp.route("/admin/trips/assign-group", methods=["POST"])
def assign_group_trip():
    try:
        data = request.get_json(silent=True) or {}
        group_data = data.get("group_data", data.get("group", {}))
        driver_id = str(data.get("driver_id", "")).strip()
        admin_id = str(data.get("admin_id", "")).strip()
        trip_type = str(data.get("trip_type", "")).strip().lower()
        scheduled_time = str(data.get("scheduled_time", "")).strip()
        vehicle_type = int(data.get("vehicle_type", 4))

        if not driver_id or not admin_id:
            return error_response("Missing required fields (driver_id, admin_id)", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            from services.trip_service import TripService

            service = TripService(conn)
            trip_data = service.create_trip_from_group(
                group_data=group_data,
                driver_id=driver_id,
                admin_id=admin_id,
                trip_type=trip_type,
                scheduled_time=scheduled_time,
                vehicle_type=vehicle_type,
            )
            return success_response(trip_data, "Trip created successfully", 201)
        finally:
            conn.close()

    except Exception as exc:
        return error_response(str(exc), 500, "INTERNAL_ERROR")
