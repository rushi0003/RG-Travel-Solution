# backend/routes/trip_creation_v2_routes.py
"""
RG Travel Solution - Trip Creation V2 Routes
Production-grade endpoints for Steps 1-10

Endpoints:
  POST /api/v2/trips/preview
  POST /api/v2/trips/create
  POST /api/v2/trips/assign
  POST /api/v2/trips/override/move-employee
  POST /api/v2/trips/override/swap-driver
  GET /api/v2/trips/{trip_id}
  GET /api/v2/trips/active
"""

from flask import Blueprint, request, jsonify, Response, g
from datetime import datetime
import csv
import io
import logging
import json
from typing import Dict, Any, List, Optional, cast

logger = logging.getLogger(__name__)

try:
    from db import get_db
except ImportError:
    from db import get_db

from typing import Dict, Any, List, Optional, cast
from datetime import datetime

from services.trip_orchestration_service import (
    preview_and_organize_trip,
    create_and_assign_trip,
    TripOrchestrationError
)
from services.trip_validation_service import filter_eligible_employees
from services.hybrid_group_planner import EmployeeNode, VehicleNode, plan_groups_hybrid
from services.otp_service import get_pending_employee_otp_ids
from services.trip_lifecycle_service import mark_trip_completed
from services.trip_history_service import list_trip_history
from services.trip_schedule_guard import evaluate_trip_start_gate
from utils.logger import log_trip_event
from utils.security import require_auth

trip_v2_bp = Blueprint("trip_v2", __name__, url_prefix="/api/v2/trips")


def _today_trip_day() -> str:
    return datetime.now().strftime("%Y%m%d")


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


def _optional_id_param(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _driver_admin_join_sql(admin_id: Optional[str], alias: str = "d") -> str:
    if not admin_id:
        return ""
    return f"""
        INNER JOIN driver_admin_assignments daa
          ON daa.driver_id = {alias}.id
         AND daa.admin_id = ?
         AND daa.is_active = 1
    """


def _resolve_trip_duration_minutes(cursor, trip_id: int, fallback_total_km=None) -> int:
    try:
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trip_routes' LIMIT 1")
        if cursor.fetchone():
            cursor.execute(
                """
                SELECT duration_mins
                FROM trip_routes
                WHERE trip_id = ?
                ORDER BY route_index ASC, id DESC
                LIMIT 1
                """,
                (int(trip_id),),
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                return max(0, int(round(float(row[0]))))
    except Exception:
        pass

    try:
        return max(0, int(round(float(fallback_total_km or 0) * 2.0)))
    except Exception:
        return 0


def _build_employee_nodes_strict(
    eligible_employees: List[Dict[str, Any]],
    trip_type: str,
) -> tuple[List[EmployeeNode], List[Dict[str, Any]]]:
    nodes: List[EmployeeNode] = []
    unresolved: List[Dict[str, Any]] = []
    for e in eligible_employees:
        if trip_type == "pickup":
            lat = _to_float_or_none(e.get("pickup_lat")) or _to_float_or_none(e.get("home_lat"))
            lng = _to_float_or_none(e.get("pickup_lng")) or _to_float_or_none(e.get("home_lng"))
            address = str(e.get("pickup_address") or e.get("home_address") or "")
        else:
            lat = _to_float_or_none(e.get("home_lat")) or _to_float_or_none(e.get("pickup_lat"))
            lng = _to_float_or_none(e.get("home_lng")) or _to_float_or_none(e.get("pickup_lng"))
            address = str(e.get("home_address") or e.get("pickup_address") or "")

        if not _is_valid_coord_pair(lat, lng):
            unresolved.append(
                {
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "mobile": e.get("mobile"),
                    "address": address,
                    "reason": "missing_or_invalid_lat_lng",
                }
            )
            continue

        nodes.append(
            EmployeeNode(
                id=int(e.get("id")),
                name=str(e.get("name") or ""),
                mobile=str(e.get("mobile") or ""),
                address=address,
                lat=float(lat),
                lng=float(lng),
            )
        )
    return nodes, unresolved


def _resolve_admin_id(db_conn, admin_id: str) -> Optional[str]:
    cursor = db_conn.cursor()
    if admin_id:
        cursor.execute("SELECT id FROM admins WHERE id = ? LIMIT 1", (admin_id,))
        row = cursor.fetchone()
        if row:
            return str(row[0])
    cursor.execute("SELECT id FROM admins ORDER BY created_at ASC LIMIT 1")
    row = cursor.fetchone()
    return str(row[0]) if row else None


def _parse_office_coords(db_conn, admin_id: str = "") -> tuple[float, float]:
    default_lat, default_lng = 19.0760, 72.8777
    cursor = db_conn.cursor()
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


def _fetch_available_drivers_rows(
    db_conn,
    scheduled_time: str,
    vehicle_type: Optional[str],
    trip_type: Optional[str],
    trip_day: Optional[str],
    admin_id: Optional[str] = None,
):
    cursor = db_conn.cursor()

    query = """
        SELECT drivers.id, drivers.name, drivers.mobile, drivers.vehicle_no, drivers.vehicle_type
        FROM drivers
    """
    params: List[Any] = []
    where_parts = ["drivers.is_approved = 1"]

    join_sql = _driver_admin_join_sql(admin_id, alias="drivers")
    if admin_id:
        params.append(admin_id)

    if vehicle_type:
        where_parts.append("CAST(drivers.vehicle_type AS TEXT) = ?")
        params.append(str(vehicle_type))

    trip_predicates = [
        "driver_id IS NOT NULL",
        "LOWER(COALESCE(status, 'created')) IN ('created', 'assigned', 'started', 'active', 'in_progress')",
    ]
    if trip_type in ("pickup", "drop"):
        trip_predicates.append("LOWER(COALESCE(operation, trip_type, '')) = ?")
        params.append(trip_type)
    if scheduled_time:
        trip_predicates.append("COALESCE(time_slot, schedule_time, '') = ?")
        params.append(scheduled_time)
    if trip_day:
        trip_predicates.append("REPLACE(COALESCE(trip_day, ''), '-', '') = ?")
        params.append(str(trip_day).replace("-", ""))

    where_parts.append(
        "drivers.id NOT IN (SELECT driver_id FROM trips WHERE " + " AND ".join(trip_predicates) + ")"
    )
    query += f"""
        {join_sql}
        WHERE {" AND ".join(where_parts)}
        ORDER BY CAST(drivers.vehicle_type AS INTEGER) DESC, drivers.vehicle_no ASC
    """

    cursor.execute(query, tuple(params))
    return cursor.fetchall()


def _go_home_approved_driver_ids(cursor, trip_day: str) -> set[str]:
    """Return approved go-home driver ids, preferring same day when travel_date exists."""
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
        return {str(r[0]) for r in cursor.fetchall() if r and r[0] is not None}
    except Exception:
        return set()


@trip_v2_bp.route("/preview", methods=["POST"])
def preview_trip():
    """
    STEP 1-6: Preview trip groups without creating records.
    
    Request Body:
    {
        "admin_id": "admin_123",
        "trip_type": "pickup" | "drop",
        "selected_time": "09:00",
        "vehicle_types": [4, 6],
        "employee_ids": [1, 2, 3] (optional),
        "driver_ids": [5, 7, 9] (optional - selected drivers from vehicle selection),
        "vehicle_priority_enabled": true (optional - prioritize 6-seaters),
        "trip_day": "20260219" (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Preview ready: 3 groups for 12 employees",
        "data": {
            "trip_preview": {...},
            "validated_employees": [...],
            "resource_check": {...},
            "groups": [...],
            "optimization_summary": {...},
            "warnings": []
        }
    }
    """
    db_conn = None
    try:
        data = dict(request.json or {})

        if "vehicle_type" in data and "vehicle_types" not in data:
            data["vehicle_types"] = [int(cast(Any, data["vehicle_type"]))]

        admin_id = str(data.get("admin_id", "")).strip()
        trip_type = str(data.get("trip_type", "")).strip().lower()
        selected_time = str(data.get("selected_time", "")).strip()
        trip_day = str(data.get("trip_day") or data.get("tripDay") or _today_trip_day()).replace("-", "").strip()
        raw_v_types = data.get("vehicle_types", [6, 4])
        raw_employee_ids = data.get("employee_ids")
        raw_driver_ids = data.get("driver_ids")
        vehicle_priority_enabled = bool(data.get("vehicle_priority_enabled", True))

        if not admin_id or not trip_type or not selected_time:
            return jsonify(
                {
                    "success": False,
                    "message": "Missing required fields: admin_id, trip_type, selected_time",
                    "error_code": "MISSING_FIELDS",
                }
            ), 400

        if trip_type not in ("pickup", "drop"):
            return jsonify(
                {
                    "success": False,
                    "message": "trip_type must be 'pickup' or 'drop'",
                    "error_code": "INVALID_TRIP_TYPE",
                }
            ), 400

        if not isinstance(raw_v_types, list):
            raw_v_types = [raw_v_types]
        try:
            vehicle_types = sorted({int(v) for v in raw_v_types if int(v) in (4, 6)}, reverse=True)
        except Exception:
            vehicle_types = []
        if not vehicle_types:
            vehicle_types = [6, 4]

        def _coerce_int_list(raw: Any) -> Optional[List[int]]:
            if raw is None:
                return None
            if not isinstance(raw, list):
                return None
            out: List[int] = []
            for v in raw:
                try:
                    out.append(int(v))
                except Exception:
                    continue
            return out if out else None

        employee_ids = _coerce_int_list(raw_employee_ids)
        driver_ids_raw = [str(v).strip() for v in (raw_driver_ids or []) if str(v).strip()] if isinstance(raw_driver_ids, list) else []

        db_conn = get_db()
        cursor = db_conn.cursor()
        resolved_admin_id = _resolve_admin_id(db_conn, admin_id) or admin_id
        office_lat, office_lng = _parse_office_coords(db_conn, resolved_admin_id)
        go_home_ids = _go_home_approved_driver_ids(cursor, trip_day)

        eligible_employees, exclusions = filter_eligible_employees(
            db_conn,
            trip_type=trip_type,
            selected_time=selected_time,
            employee_ids=employee_ids,
            trip_day=trip_day,
        )
        if not eligible_employees:
            return jsonify(
                {
                    "success": False,
                    "message": "No eligible employees found",
                    "data": {"exclusions": exclusions},
                    "error_code": "NO_ELIGIBLE_EMPLOYEES",
                }
            ), 400

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
            return jsonify(
                {
                    "success": False,
                    "message": "No employees with valid coordinates found",
                    "data": {"exclusions": exclusions, "unresolved_coordinates": unresolved_coords},
                    "error_code": "NO_VALID_COORDINATES",
                }
            ), 400

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

        params: List[Any] = [trip_day, trip_type, selected_time]
        where_parts = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "d.id NOT IN (SELECT t.driver_id FROM trips t WHERE REPLACE(COALESCE(t.trip_day, ''), '-', '') = ? AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ? AND COALESCE(t.time_slot, t.schedule_time, '') = ? AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress') AND t.driver_id IS NOT NULL)",
        ]
        if vehicle_types:
            ph = ",".join(["?"] * len(vehicle_types))
            where_parts.append(f"CAST(d.vehicle_type AS INTEGER) IN ({ph})")
            params.extend(vehicle_types)
        if driver_ids_raw:
            cursor.execute("SELECT id FROM drivers")
            existing = {str(r[0]) for r in cursor.fetchall() if r and r[0] is not None}
            exact = sorted({d for d in driver_ids_raw if d in existing})
            if exact:
                ph = ",".join(["?"] * len(exact))
                where_parts.append(f"CAST(d.id AS TEXT) IN ({ph})")
                params.extend(exact)

        cursor.execute(
            f"""
            SELECT d.id, d.name, d.vehicle_no, CAST(d.vehicle_type AS INTEGER) AS vtype,
                   {lat_expr} AS home_lat, {lng_expr} AS home_lng
            FROM drivers d
            WHERE {" AND ".join(where_parts)}
            ORDER BY vtype DESC, d.id ASC
            """,
            tuple(params),
        )
        driver_rows = cursor.fetchall()
        if not driver_rows:
            return jsonify(
                {
                    "success": False,
                    "message": "No available vehicles for selected vehicle types",
                    "error_code": "NO_AVAILABLE_VEHICLES",
                }
            ), 400

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

        plan = plan_groups_hybrid(
            employees=employee_nodes,
            vehicles=vehicle_nodes,
            office=(float(office_lat), float(office_lng)),
            prioritize_6_when_mixed=vehicle_priority_enabled,
            strict_hybrid=True,
        )

        preview_groups: List[Dict[str, Any]] = []
        for idx, g in enumerate(plan.get("groups", []), start=1):
            members = g.get("members", [])
            preview_groups.append(
                {
                    "group_index": idx,
                    "members_count": len(members),
                    "members": members,
                    "route_distance_km": g.get("route_distance_km", g.get("anchor_distance_km")),
                    "estimated_duration_min": None,
                    "vehicle_type": int(g.get("vehicle_type", 4)),
                    "assigned_driver_id": g.get("driver_id"),
                    "assigned_cab_no": g.get("vehicle_no"),
                    "go_home_approved": bool(g.get("go_home_approved")),
                }
            )

        unassigned_emps = plan.get("unassigned_employees", [])
        unassigned_ids = [int(x.get("id")) for x in unassigned_emps if isinstance(x, dict) and x.get("id") is not None]
        total_4 = sum(1 for v in vehicle_nodes if int(v.vehicle_type) == 4)
        total_6 = sum(1 for v in vehicle_nodes if int(v.vehicle_type) == 6)
        selected_capacity = (total_4 * 4) + (total_6 * 6)

        result = {
            "success": True,
            "message": f"Preview ready: {len(preview_groups)} groups for {len(employee_nodes) - len(unassigned_emps)} employees",
            "data": {
                "trip_preview": {
                    "trip_type": trip_type,
                    "selected_time": selected_time,
                    "vehicle_types": vehicle_types,
                    "vehicle_type": vehicle_types[0] if vehicle_types else 4,
                    "trip_day": trip_day,
                    "office_lat": office_lat,
                    "office_lng": office_lng,
                    "hybrid_provider": plan.get("hybrid_provider"),
                    "hybrid_strict": bool(plan.get("hybrid_strict", True)),
                },
                "validated_employees": eligible_employees,
                "unassigned_employees": unassigned_emps,
                "unassigned_employee_ids": unassigned_ids,
                "resource_check": {
                    "available_4_count": total_4,
                    "available_6_count": total_6,
                    "available_driver_count": len(vehicle_nodes),
                    "total_capacity": selected_capacity,
                    "usable_cabs": len(vehicle_nodes),
                    "selected_capacity": selected_capacity,
                    "assignable_employees": len(employee_nodes) - len(unassigned_emps),
                    "unassigned_count": len(unassigned_emps),
                    "unassigned_vehicle_count": len(plan.get("unassigned_vehicles", [])),
                },
                "groups": preview_groups,
                "optimization_summary": {
                    "use_4_seaters": sum(1 for g in preview_groups if int(g.get("vehicle_type", 4)) == 4),
                    "use_6_seaters": sum(1 for g in preview_groups if int(g.get("vehicle_type", 4)) == 6),
                    "total_cabs": len(preview_groups),
                    "total_seats": sum(int(g.get("vehicle_type", 4)) for g in preview_groups),
                    "empty_seats": sum(max(0, int(g.get("vehicle_type", 4)) - int(g.get("members_count", 0))) for g in preview_groups),
                    "strategy": "mandatory_hybrid",
                },
                "validation_summary": {
                    "eligible_count": len(eligible_employees),
                    "excluded_count": len(exclusions),
                },
                "unresolved_coordinates": unresolved_coords,
                "unassigned_vehicles": plan.get("unassigned_vehicles", []),
                "warnings": exclusions,
            },
        }
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid parameter value: {str(e)}", "error_code": "INVALID_PARAMETER"}), 400
    except RuntimeError as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "error_code": "HYBRID_PROVIDER_UNAVAILABLE",
            "data": {"hint": "Check /api/health/hybrid and route provider configuration."},
        }), 503
    except Exception as e:
        logger.error(f"Preview failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error during trip preview", "error_code": "INTERNAL_ERROR"}), 500
    finally:
        try:
            if db_conn is not None:
                db_conn.close()
        except Exception:
            pass


@trip_v2_bp.route("/create", methods=["POST"])
def create_trip():
    """
    STEP 8: Create trip records with driver assignment (route no + OTP).
    
    Request Body:
    {
        "admin_id": "admin_123",
        "preview_data": { ... },  (from /preview response)
        "groups_to_create": [
            {
                "group_index": 1,
                "members": [...],
                "route_distance_km": 15.5
            }
        ],
        "driver_assignments": {
            "0": {"driver_id": "drv_001", "cab_id": "drv_001"}
        } (optional - auto-assign if not provided)
    }
    
    Response:
    {
        "success": true,
        "message": "Created 3 trips successfully",
        "data": {
            "trips_created": [
                {
                    "route_no": "20264821FE",
                    "trip_id": 123,
                    "driver_id": "drv_001",
                    "driver_name": "John Doe",
                    "vehicle_no": "MH12AB1234",
                    "employee_count": 4,
                    "total_distance_km": 15.5,
                    "start_otp": "123456",
                    "start_otp_expiry": "2026-02-19T10:30:00",
                    "end_otp": "654321",
                    "end_otp_expiry": "2026-02-19T12:30:00",
                    ...
                }
            ],
            "summary": {...}
        }
    }
    """
    db_conn = None
    try:
        data = request.json or {}
        
        # Validate required fields: admin_id and groups_to_create required; preview_data optional
        required = ["admin_id", "groups_to_create"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing)}",
                "error_code": "MISSING_FIELDS"
            }), 400

        admin_id = str(data.get("admin_id", "")).strip()
        preview_data = cast(Dict[str, Any], data.get("preview_data", {}))
        groups_to_create = cast(List[Dict[str, Any]], data.get("groups_to_create", []))
        driver_assignments = cast(Dict[str, Any], data.get("driver_assignments", {}))
        db_conn = get_db()
        resolved_admin_id = _resolve_admin_id(db_conn, admin_id) or admin_id
        resolved_office_lat, resolved_office_lng = _parse_office_coords(db_conn, resolved_admin_id)
        
        # Convert string keys to int for driver_assignments
        driver_assignments_int = {int(k): v for k, v in driver_assignments.items()} if driver_assignments else {}
        
        # If preview_data missing, synthesize minimal preview_data from provided fields
        if not preview_data or not isinstance(preview_data, dict) or not preview_data.get("trip_preview"):
            trip_type = data.get("trip_type") or data.get("tripType") or (groups_to_create[0].get("vehicle_type") if groups_to_create else "pickup")
            selected_time = data.get("selected_time") or data.get("scheduled_time") or data.get("scheduledTime") or ""
            vehicle_types = data.get("vehicle_types") or data.get("vehicleType") or []
            trip_day = data.get("trip_day") or data.get("tripDay")
            try:
                vt_list = [int(v) for v in vehicle_types] if isinstance(vehicle_types, list) else ([int(vehicle_types)] if vehicle_types else [4])
            except Exception:
                vt_list = [4]
            preview_data = {
                "trip_preview": {
                    "trip_type": trip_type,
                    "selected_time": selected_time,
                    "vehicle_types": vt_list,
                    "vehicle_type": vt_list[0] if vt_list else 4,
                    "trip_day": str(trip_day).replace("-", "") if trip_day else datetime.now().strftime("%Y%m%d"),
                    "office_lat": float(resolved_office_lat),
                    "office_lng": float(resolved_office_lng),
                }
            }
        else:
            trip_preview = preview_data.get("trip_preview")
            if isinstance(trip_preview, dict):
                # Enforce admin-profile office location even when client sends preview_data.
                trip_preview["office_lat"] = float(resolved_office_lat)
                trip_preview["office_lng"] = float(resolved_office_lng)
        cursor = db_conn.cursor()

        # Normalize groups_to_create if it comes in the wrapped Flutter format:
        # [{"group_data": {...}, "driver_id": "...", "cab_no": "..."}]
        normalized_groups = []
        normalized_assignments = driver_assignments_int.copy()
        
        for idx, g in enumerate(groups_to_create):
            if "group_data" in g and isinstance(g["group_data"], dict):
                # Extract members and other group info from group_data wrapper
                inner_group = g["group_data"]
                normalized_groups.append(inner_group)
                
                # Extract driver info if provided in the wrapper
                if g.get("driver_id") and idx not in normalized_assignments:
                    normalized_assignments[idx] = {
                        "driver_id": str(g.get("driver_id")),
                        "cab_id": str(g.get("cab_no") or g.get("cab_id") or g.get("driver_id"))
                    }
                elif idx not in normalized_assignments:
                    # Hybrid preview/group-create compatibility:
                    # consume pre-assigned hints from group_data payload.
                    hinted_driver = (
                        inner_group.get("assigned_driver_id")
                        or inner_group.get("driver_id")
                        or (inner_group.get("suggested_vehicle") or {}).get("driver_id")
                    )
                    hinted_cab = (
                        inner_group.get("assigned_cab_no")
                        or inner_group.get("vehicle_no")
                        or (inner_group.get("suggested_vehicle") or {}).get("vehicle_no")
                        or hinted_driver
                    )
                    if hinted_driver:
                        normalized_assignments[idx] = {
                            "driver_id": str(hinted_driver),
                            "cab_id": str(hinted_cab),
                        }
            else:
                normalized_groups.append(g)
                if idx not in normalized_assignments and isinstance(g, dict):
                    hinted_driver = (
                        g.get("assigned_driver_id")
                        or g.get("driver_id")
                        or (g.get("suggested_vehicle") or {}).get("driver_id")
                    )
                    hinted_cab = (
                        g.get("assigned_cab_no")
                        or g.get("vehicle_no")
                        or (g.get("suggested_vehicle") or {}).get("vehicle_no")
                        or hinted_driver
                    )
                    if hinted_driver:
                        normalized_assignments[idx] = {
                            "driver_id": str(hinted_driver),
                            "cab_id": str(hinted_cab),
                        }

        def _employee_rows_by_ids(emp_ids: List[int]) -> Dict[int, Dict[str, Any]]:
            if not emp_ids:
                return {}
            placeholders = ",".join(["?"] * len(emp_ids))
            cursor.execute(
                f"""
                SELECT id, name, mobile,
                       COALESCE(home_address, pickup_address, drop_location, '') AS address,
                       COALESCE(home_lat, pickup_lat, drop_lat, 0) AS lat,
                       COALESCE(home_lng, pickup_lng, drop_lng, 0) AS lng
                FROM employees
                WHERE id IN ({placeholders})
                """,
                tuple(emp_ids),
            )
            out: Dict[int, Dict[str, Any]] = {}
            for r in cursor.fetchall():
                out[int(r[0])] = {
                    "id": int(r[0]),
                    "name": r[1],
                    "mobile": r[2],
                    "address": r[3],
                    "lat": r[4],
                    "lng": r[5],
                }
            return out

        def _normalize_members(group_data: Dict[str, Any]) -> Dict[str, Any]:
            members = group_data.get("members")
            if members is None:
                members = group_data.get("employees")
            if isinstance(members, list):
                normalized = []
                for m in members:
                    if not isinstance(m, dict):
                        continue
                    mid = m.get("id") or m.get("employee_id")
                    try:
                        mid = int(mid)
                    except Exception:
                        continue
                    lat = m.get("lat")
                    lng = m.get("lng")
                    if lat in (None, 0, 0.0) or lng in (None, 0, 0.0):
                        lat = preview_data.get("trip_preview", {}).get("office_lat")
                        lng = preview_data.get("trip_preview", {}).get("office_lng")
                    normalized.append(
                        {
                            "id": mid,
                            "name": m.get("name"),
                            "mobile": m.get("mobile") or m.get("phone"),
                            "address": m.get("address") or m.get("drop_location"),
                            "lat": lat,
                            "lng": lng,
                        }
                    )
                group_data["members"] = normalized
                return group_data

            emp_ids = group_data.get("employee_ids") or group_data.get("employeeIds")
            if isinstance(emp_ids, list) and emp_ids:
                ids: List[int] = []
                for v in emp_ids:
                    try:
                        ids.append(int(v))
                    except Exception:
                        continue
                row_map = _employee_rows_by_ids(ids)
                normalized = []
                for eid in ids:
                    row = row_map.get(eid)
                    if not row:
                        continue
                    lat = row.get("lat")
                    lng = row.get("lng")
                    if lat in (None, 0, 0.0) or lng in (None, 0, 0.0):
                        lat = preview_data.get("trip_preview", {}).get("office_lat")
                        lng = preview_data.get("trip_preview", {}).get("office_lng")
                    row["lat"] = lat
                    row["lng"] = lng
                    normalized.append(row)
                group_data["members"] = normalized
            return group_data

        normalized_groups = [_normalize_members(g) for g in normalized_groups]

        result = create_and_assign_trip(
            db_conn,
            admin_id=resolved_admin_id,
            preview_data=preview_data,
            groups_to_create=normalized_groups,
            driver_assignments=normalized_assignments
        )
        
        if result["success"]:
            trip_preview = preview_data.get("trip_preview", {}) if isinstance(preview_data, dict) else {}
            _mark_groups_assigned_after_trip_create(
                cursor,
                normalized_groups,
                resolved_admin_id,
                str(trip_preview.get("trip_type") or data.get("trip_type") or "").strip().lower(),
                str(
                    trip_preview.get("selected_time")
                    or data.get("selected_time")
                    or data.get("scheduled_time")
                    or ""
                ).strip(),
                str(
                    trip_preview.get("trip_day")
                    or data.get("trip_day")
                    or _today_trip_day()
                ).replace("-", "").strip(),
            )
            db_conn.commit()
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    except TripOrchestrationError as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "error_code": "ORCHESTRATION_ERROR"
        }), 400
    except Exception as e:
        logger.error(f"Create failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error during trip creation",
            "error_code": "INTERNAL_ERROR"
        }), 500
    finally:
        try:
            if db_conn is not None:
                db_conn.close()
        except Exception:
            pass


@trip_v2_bp.route("/<int:trip_id>", methods=["GET"])
def get_trip_details(trip_id: int):
    """
    Get complete trip details including route, employees, OTP status.
    
    Response:
    {
        "success": true,
        "data": {
            "trip_id": 123,
            "route_no": "20264821FE",
            "trip_type": "pickup",
            "schedule_time": "09:00",
            "status": "assigned",
            "driver_id": "drv_001",
            "driver_name": "John Doe",
            "driver_mobile": "9876543210",
            "vehicle_no": "MH12AB1234",
            "vehicle_type": 4,
            "employee_count": 4,
            "employees": [
                {
                    "id": 1,
                    "name": "Alice",
                    "mobile": "9876543211",
                    "sequence": 1,
                    "address": "Home A",
                    "no_show": false
                }
            ],
            "route_summary": {
                "total_distance_km": 15.5,
                "estimated_duration_min": 25
            },
            "otp_status": {
                "start_otp_used": false,
                "start_otp_expires_at": "2026-02-19T10:30:00",
                "end_otp_used": false,
                "end_otp_expires_at": "2026-02-19T12:30:00"
            },
            "created_at": "2026-02-19T09:15:00",
            "updated_at": "2026-02-19T09:15:00"
        }
    }
    """
    try:
        db_conn = get_db()
        cursor = db_conn.cursor()
        
        # Fetch trip
        cursor.execute(
            """
            SELECT id, route_no, operation, trip_type, trip_day, schedule_time, status,
                   driver_id, vehicle_type, total_km, created_at, updated_at,
                   office_lat, office_lng
            FROM trips WHERE id = ?
            """,
            (trip_id,)
        )
        trip = cursor.fetchone()
        
        if not trip:
            db_conn.close()
            return jsonify({
                "success": False,
                "message": f"Trip #{trip_id} not found",
                "error_code": "NOT_FOUND"
            }), 404
        
        # Fetch driver details
        driver_id = trip[7]
        cursor.execute(
            "SELECT id, name, mobile, vehicle_no FROM drivers WHERE id = ?",
            (driver_id,)
        )
        driver = cursor.fetchone()
        
        # Fetch employees
        cursor.execute("PRAGMA table_info(trip_employees)")
        te_cols = {str(r[1]) for r in cursor.fetchall()}
        no_show_reason_sql = ", te.no_show_reason" if "no_show_reason" in te_cols else ", ''"
        cursor.execute(
            f"""
            SELECT te.employee_id, e.name, e.mobile, te.sequence_no, 
                   COALESCE(e.home_address, e.pickup_address, ''), te.is_no_show,
                   e.pickup_lat, e.pickup_lng, e.drop_lat, e.drop_lng
                   {no_show_reason_sql}
            FROM trip_employees te
            JOIN employees e ON te.employee_id = e.id
            WHERE te.trip_id = ?
            ORDER BY te.sequence_no
            """,
            (trip_id,)
        )
        employees = cursor.fetchall()
        
        # Fetch OTP status
        cursor.execute(
            """
            SELECT otp_type, is_used, expires_at
            FROM trip_otps WHERE trip_id = ?
            """,
            (trip_id,)
        )
        otps = cursor.fetchall()
        
        # Fetch approved swap context for history/detail view
        cursor.execute(
            """
            SELECT
                sr.id,
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
            LEFT JOIN drivers od ON CAST(od.id AS TEXT) = CAST(sr.old_driver_id AS TEXT)
            LEFT JOIN drivers nd ON CAST(nd.id AS TEXT) = CAST(sr.new_driver_id AS TEXT)
            WHERE sr.trip_id = ?
              AND LOWER(COALESCE(sr.status, '')) = 'approved'
            ORDER BY COALESCE(sr.reviewed_at, sr.updated_at, sr.created_at) DESC, sr.id DESC
            LIMIT 1
            """,
            (trip_id,),
        )
        swap = cursor.fetchone()

        db_conn.close()

        current_driver = {
            "id": str(driver_id or ""),
            "name": driver[1] if driver else "Unknown",
            "mobile": driver[2] if driver else "",
            "cab_no": driver[3] if driver else "Unknown",
            "role": "current",
        }
        original_driver = dict(current_driver)
        all_drivers = [current_driver]
        if swap:
            original_driver = {
                "id": str(swap[1] or ""),
                "name": swap[6] or current_driver["name"],
                "mobile": swap[7] or "",
                "cab_no": swap[8] or current_driver["cab_no"],
                "role": "original",
            }
            replacement_driver = {
                "id": str(swap[2] or current_driver["id"]),
                "name": swap[9] or swap[3] or current_driver["name"],
                "mobile": swap[10] or swap[4] or current_driver["mobile"],
                "cab_no": swap[5] or swap[11] or current_driver["cab_no"],
                "role": "replacement",
            }
            current_driver = replacement_driver
            all_drivers = [original_driver, replacement_driver]

        status_text = str(trip[6] or "").lower()
        visible_total_km = trip[9] if status_text == "completed" else None
        # Build response
        trip_data = {
            "trip_id": trip[0],
            "id": trip[0],
            "route_no": trip[1],
            "trip_type": trip[3],
            "trip_date": trip[4],
            "schedule_time": trip[5],
            "status": trip[6],
            "driver_id": driver_id,
            "driver_name": driver[1] if driver else "Unknown",
            "driver_mobile": driver[2] if driver else "",
            "vehicle_no": driver[3] if driver else "Unknown",
            "cab_no": driver[3] if driver else "Unknown",
            "vehicle_type": trip[8],
            "employee_count": len(employees),
            "no_show_count": len([emp for emp in employees if emp[5] == 1]),
            "no_show_members": [
                {
                    "employee_id": emp[0],
                    "name": emp[1],
                    "mobile": emp[2],
                }
                for emp in employees
                if emp[5] == 1
            ],
            "show_total_km": status_text == "completed",
            "total_km": visible_total_km,
            "employees": [
                {
                    "id": emp[0],
                    "name": emp[1],
                    "mobile": emp[2],
                    "sequence": emp[3],
                    "address": emp[4],
                    "no_show": emp[5] == 1,
                    "pickup_lat": emp[6],
                    "pickup_lng": emp[7],
                    "drop_lat": emp[8],
                    "drop_lng": emp[9],
                    "no_show_reason": emp[10] if len(emp) > 10 else "",
                }
                for emp in employees
            ],
            "office_location": {
                "lat": trip[12],
                "lng": trip[13]
            },
            "route_summary": {
                "total_distance_km": visible_total_km,
                "estimated_duration_min": int((visible_total_km or 0) / 20 * 60) if visible_total_km is not None else None
            },
            "otp_status": {
                "start_otp_used": any(o[0] == "start" and o[1] == 1 for o in otps),
                "end_otp_used": any(o[0] == "end" and o[1] == 1 for o in otps),
            },
            "has_emergency_swap": len(all_drivers) > 1,
            "original_driver": original_driver,
            "current_driver": current_driver,
            "all_drivers": all_drivers,
            "original_vehicle_no": original_driver["cab_no"],
            "current_vehicle_no": current_driver["cab_no"],
            "created_at": trip[10],
            "updated_at": trip[11]
        }
        
        return jsonify({
            "success": True,
            "data": trip_data
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to fetch trip: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error fetching trip details",
            "error_code": "INTERNAL_ERROR"
        }), 500


@trip_v2_bp.route("/active", methods=["GET"])
def get_active_trips():
    """
    Get all active trips (status in created, assigned, started).
    
    Query params:
    - trip_type: "pickup" | "drop" (optional)
    - status: comma-separated statuses (optional)
    - limit: default 50, max 500
    - offset: default 0
    
    Response:
    {
        "success": true,
        "data": {
            "trips": [...],
            "total_count": 15,
            "limit": 50,
            "offset": 0
        }
    }
    """
    try:
        trip_type = request.args.get("trip_type", "").strip().lower()
        status_filter = request.args.get("status", "created,assigned,started")
        limit = min(int(request.args.get("limit", "50")), 500)
        offset = int(request.args.get("offset", "0"))
        
        db_conn = get_db()
        cursor = db_conn.cursor()
        
        # Build query
        query = "SELECT id, route_no, operation, schedule_time, status, driver_id, vehicle_type, total_km, created_at FROM trips WHERE 1=1"
        params = []
        
        if trip_type in ("pickup", "drop"):
            query += " AND operation = ?"
            params.append(trip_type)
        
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
        if statuses:
            placeholders = ",".join(["?" for _ in statuses])
            query += f" AND status IN ({placeholders})"
            params.extend(statuses)
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
        total = cursor.fetchone()[0]
        
        # Get paginated results
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        trips = cursor.fetchall()
        
        db_conn.close()
        
        trip_list = [
            {
                "trip_id": t[0],
                "route_no": t[1],
                "trip_type": t[2],
                "schedule_time": t[3],
                "status": t[4],
                "driver_id": t[5],
                "vehicle_type": t[6],
                "total_distance_km": t[7] or 0,
                "created_at": t[8]
            }
            for t in trips
        ]
        
        return jsonify({
            "success": True,
            "data": {
                "trips": trip_list,
                "total_count": total,
                "limit": limit,
                "offset": offset
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to fetch active trips: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error fetching active trips",
            "error_code": "INTERNAL_ERROR"
        }), 500


@trip_v2_bp.route("/<int:trip_id>/start", methods=["POST"]) 
def start_trip(trip_id: int):
    """
    Mark a trip as started/live. Called by admin or driver when trip goes live.
    Body: { "by": "admin" | "driver", "note": "optional" }
    """
    try:
        data = request.json or {}
        by = str(data.get("by", "")).strip().lower()

        db_conn = get_db()
        cursor = db_conn.cursor()

        cursor.execute(
            """
            SELECT status, route_no, trip_type, operation,
                   COALESCE(time_slot, schedule_time) AS scheduled_time,
                   trip_day,
                   total_km
            FROM trips
            WHERE id = ?
            """,
            (trip_id,),
        )
        row = cursor.fetchone()
        if not row:
            db_conn.close()
            return jsonify({"success": False, "message": "Trip not found"}), 404

        status, route_no, trip_type, operation, scheduled_time, trip_day, total_km = row
        trip_kind = str(trip_type or operation or "").strip().lower()
        if status in ('started', 'live'):
            db_conn.close()
            return jsonify({"success": True, "message": "Trip already started", "data": {"trip_id": trip_id}}), 200

        # Backward-compatible actor handling:
        # allow admin/manual start from admin dashboard as operational override.
        started_by = by if by in {"admin", "driver"} else "system"

        gate = evaluate_trip_start_gate(
            trip_day,
            scheduled_time,
            trip_type=trip_kind,
            route_duration_minutes=_resolve_trip_duration_minutes(cursor, trip_id, total_km),
        )
        if not bool(gate.get("can_start_now", True)):
            log_trip_event(
                "trip_start_blocked_preassigned",
                trip_id=trip_id,
                start_allowed_after=gate.get("start_allowed_after"),
            )
            db_conn.close()
            return jsonify({
                "success": False,
                "message": "Trip is pre-assigned. Start allowed only at scheduled date/time.",
                "error_code": "TRIP_NOT_STARTED_YET",
                "data": {
                    "start_allowed_after": gate.get("start_allowed_after"),
                    "seconds_until_start": int(gate.get("seconds_until_start", 0) or 0),
                    "server_now": gate.get("server_now"),
                },
            }), 400

        # Strict pickup rule: all employee start OTPs must be verified before start.
        # Admin mark-live is an operational override and can bypass start OTP gate.
        admin_override = started_by == "admin"
        if trip_kind == "pickup" and not admin_override:
            gate = get_pending_employee_otp_ids(db_conn, trip_id=trip_id, otp_type="start")
            pending = ((gate.get("data") or {}).get("pending_employee_ids") or [])
            if pending:
                db_conn.close()
                return jsonify({
                    "success": False,
                    "message": "Cannot start pickup trip. Employee start OTP pending.",
                    "data": {"pending_employee_ids": pending},
                }), 400
        elif trip_kind == "pickup" and admin_override:
            log_trip_event(
                "trip_start_admin_override",
                trip_id=trip_id,
                started_by=started_by,
            )

        start_time = datetime.now().isoformat()
        cursor.execute(
            "UPDATE trips SET status = 'started', start_time = ?, updated_at = ? WHERE id = ?",
            (start_time, start_time, trip_id)
        )

        db_conn.commit()
        db_conn.close()
        log_trip_event("trip_started", trip_id=trip_id, started_by=started_by)

        # Broadcast via socket service
        try:
            from services.socket_service import broadcast_trip_status_change
            if route_no:
                broadcast_trip_status_change(route_no, 'started', trip_id)
        except Exception:
            logger.exception("Failed to broadcast trip start (non-critical)")

        return jsonify({"success": True, "message": "Trip started", "data": {"trip_id": trip_id, "start_time": start_time}}), 200

    except Exception as e:
        logger.error(f"Start trip failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error starting trip"}), 500


@trip_v2_bp.route("/history", methods=["GET"])
@require_auth(roles=["admin", "driver", "employee"])
def get_trip_history_v2():
    """
    Get trip history with filters.
    """
    try:
        search = (request.args.get("search") or request.args.get("q") or "").strip().lower()
        status = request.args.get("status", "").strip().lower()
        trip_type = request.args.get("type", "").strip().lower()
        from_date = request.args.get("from", "").strip()
        to_date = request.args.get("to", "").strip()
        driver_id = _optional_id_param(request.args.get("driver_id"))
        employee_id = _optional_id_param(request.args.get("employee_id"))
        limit = min(int(request.args.get("limit", "50")), 500)
        offset = int(request.args.get("offset", "0"))
        role = str(getattr(g, "role", "") or "").strip().lower()
        user_id = _optional_id_param(getattr(g, "user_id", None))

        admin_id: Optional[str] = None
        viewer_driver_id: Optional[str] = None
        viewer_employee_id: Optional[str] = None
        if role == "admin":
            admin_id = user_id
        elif role == "driver":
            viewer_driver_id = user_id
        elif role == "employee":
            viewer_employee_id = user_id

        db_conn = get_db()
        trips, total = list_trip_history(
            db_conn,
            driver_id=driver_id,
            employee_id=employee_id,
            viewer_driver_id=viewer_driver_id,
            viewer_employee_id=viewer_employee_id,
            admin_id=admin_id,
            search=search,
            status=status,
            trip_type=trip_type,
            from_date=from_date,
            to_date=to_date,
            sort=request.args.get("sort"),
            limit=limit,
            offset=offset,
        )
        db_conn.close()

        return jsonify({
            "success": True,
            "data": {
                "trips": trips,
                "total_count": total,
                "limit": limit,
                "offset": offset,
            }
        }), 200

    except Exception as e:
        logger.error(f"History fetch failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@trip_v2_bp.route("/history/export", methods=["GET"])
@require_auth(roles=["admin", "driver", "employee"])
def export_trip_history_v2():
    try:
        search = (request.args.get("search") or request.args.get("q") or "").strip().lower()
        status = request.args.get("status", "").strip().lower()
        trip_type = request.args.get("type", "").strip().lower()
        from_date = request.args.get("from", "").strip()
        to_date = request.args.get("to", "").strip()
        driver_id = _optional_id_param(request.args.get("driver_id"))
        employee_id = _optional_id_param(request.args.get("employee_id"))
        role = str(getattr(g, "role", "") or "").strip().lower()
        user_id = _optional_id_param(getattr(g, "user_id", None))

        admin_id: Optional[str] = None
        viewer_driver_id: Optional[str] = None
        viewer_employee_id: Optional[str] = None
        if role == "admin":
            admin_id = user_id
        elif role == "driver":
            viewer_driver_id = user_id
        elif role == "employee":
            viewer_employee_id = user_id

        db_conn = get_db()
        trips, _ = list_trip_history(
            db_conn,
            driver_id=driver_id,
            employee_id=employee_id,
            viewer_driver_id=viewer_driver_id,
            viewer_employee_id=viewer_employee_id,
            admin_id=admin_id,
            search=search,
            status=status,
            trip_type=trip_type,
            from_date=from_date,
            to_date=to_date,
            sort=request.args.get("sort"),
            limit=10000,
            offset=0,
        )
        db_conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "trip_id",
            "route_no",
            "trip_date",
            "schedule_time",
            "status",
            "trip_type",
            "current_driver",
            "original_driver",
            "current_vehicle",
            "original_vehicle",
            "employee_count",
            "no_show_count",
            "no_show_members",
            "total_km",
            "cancel_reason",
            "has_emergency_swap",
            "history_visible_at",
        ])
        for trip in trips:
            no_show_members = ", ".join(
                [
                    str(member.get("name") or member.get("employee_id") or "").strip()
                    for member in (trip.get("no_show_members") or [])
                    if isinstance(member, dict)
                ]
            )
            writer.writerow([
                trip.get("trip_id"),
                trip.get("route_no"),
                trip.get("trip_date"),
                trip.get("schedule_time"),
                trip.get("status"),
                trip.get("trip_type"),
                (trip.get("current_driver") or {}).get("name", ""),
                (trip.get("original_driver") or {}).get("name", ""),
                trip.get("current_vehicle_no"),
                trip.get("original_vehicle_no"),
                trip.get("employee_count"),
                trip.get("no_show_count"),
                no_show_members,
                trip.get("total_km") if trip.get("show_total_km") else "",
                trip.get("cancel_reason"),
                "yes" if trip.get("has_emergency_swap") else "no",
                trip.get("history_visible_at"),
            ])

        filename = f"trip_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        logger.error(f"History export failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@trip_v2_bp.route("/<int:trip_id>/override/move-employee", methods=["POST"])
def override_move_employee(trip_id: int):
    """
    STEP 10: Admin override - Move employee from one trip to another.
    
    Request Body:
    {
        "admin_id": "admin_123",
        "employee_id": 1,
        "from_trip_id": 123,
        "to_trip_id": 124
    }
    
    Response:
    {
        "success": true,
        "message": "Employee moved successfully",
        "data": {
            "route_revision": "v2",
            "from_trip": {...},
            "to_trip": {...},
            "audit_entry_id": 456
        }
    }
    """
    try:
        data = request.json or {}
        admin_id = data.get("admin_id", "").strip()
        employee_id = int(data.get("employee_id", 0))
        from_trip_id = trip_id
        to_trip_id = int(data.get("to_trip_id", 0))
        
        if not admin_id or not employee_id or not to_trip_id:
            return jsonify({
                "success": False,
                "message": "Missing required fields",
                "error_code": "MISSING_FIELDS"
            }), 400
        
        db_conn = get_db()
        cursor = db_conn.cursor()
        
        # Check employee in from_trip
        cursor.execute(
            "SELECT id FROM trip_employees WHERE trip_id = ? AND employee_id = ?",
            (from_trip_id, employee_id)
        )
        if not cursor.fetchone():
            db_conn.close()
            return jsonify({
                "success": False,
                "message": f"Employee {employee_id} not in trip {from_trip_id}",
                "error_code": "NOT_FOUND"
            }), 400
        
        # Check capacity in to_trip
        cursor.execute(
            """
            SELECT COUNT(*) FROM trip_employees WHERE trip_id = ? AND is_no_show = 0
            """,
            (to_trip_id,)
        )
        current_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT vehicle_type FROM trips WHERE id = ?", (to_trip_id,))
        trip = cursor.fetchone()
        if not trip:
            db_conn.close()
            return jsonify({
                "success": False,
                "message": f"Trip {to_trip_id} not found",
                "error_code": "NOT_FOUND"
            }), 400
        
        vehicle_capacity = trip[0]
        if current_count >= vehicle_capacity:
            db_conn.close()
            return jsonify({
                "success": False,
                "message": f"Trip {to_trip_id} is at full capacity",
                "error_code": "CAPACITY_FULL"
            }), 400
        
        # Move employee
        cursor.execute(
            "UPDATE trip_employees SET trip_id = ? WHERE trip_id = ? AND employee_id = ?",
            (to_trip_id, from_trip_id, employee_id)
        )
        
        # Increment route revision
        cursor.execute(
            "UPDATE trips SET route_revision = route_revision + 1 WHERE id IN (?, ?)",
            (from_trip_id, to_trip_id)
        )
        
        # Log audit entry
        cursor.execute(
            """
            INSERT INTO admin_audit (admin_id, trip_id, action, old_data, new_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                admin_id, from_trip_id, "move_employee",
                f"employee_id={employee_id}",
                f"moved_to_trip={to_trip_id}",
                datetime.now().isoformat()
            )
        )
        
        db_conn.commit()
        db_conn.close()
        
        return jsonify({
            "success": True,
            "message": "Employee moved successfully",
            "data": {
                "from_trip_id": from_trip_id,
                "to_trip_id": to_trip_id,
                "employee_id": employee_id
            }
        }), 200
    
    except ValueError as e:
        return jsonify({
            "success": False,
            "message": f"Invalid parameter value: {str(e)}",
            "error_code": "INVALID_PARAMETER"
        }), 400
    except Exception as e:
        logger.error(f"Override move failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error during move operation",
            "error_code": "INTERNAL_ERROR"
        }), 500


@trip_v2_bp.route("/<int:trip_id>/override/swap-driver", methods=["POST"])
def override_swap_driver(trip_id: int):
    """
    STEP 10: Admin override - Swap driver/cab for a group.
    
    Request Body:
    {
        "admin_id": "admin_123",
        "new_driver_id": "drv_002"
    }
    
    Response:
    {
        "success": true,
        "message": "Driver swapped successfully",
        "data": {
            "trip_id": 123,
            "route_revision": "v2",
            "old_driver_id": "drv_001",
            "new_driver_id": "drv_002"
        }
    }
    """
    try:
        data = request.json or {}
        admin_id = data.get("admin_id", "").strip()
        new_driver_id = data.get("new_driver_id", "").strip()
        
        if not admin_id or not new_driver_id:
            return jsonify({
                "success": False,
                "message": "Missing required fields",
                "error_code": "MISSING_FIELDS"
            }), 400
        
        db_conn = get_db()
        cursor = db_conn.cursor()
        
        # Get current trip
        cursor.execute("SELECT driver_id FROM trips WHERE id = ?", (trip_id,))
        trip = cursor.fetchone()
        if not trip:
            db_conn.close()
            return jsonify({
                "success": False,
                "message": f"Trip {trip_id} not found",
                "error_code": "NOT_FOUND"
            }), 404
        
        old_driver_id = trip[0]
        
        # Verify new driver exists and is approved
        cursor.execute(
            "SELECT name FROM drivers WHERE id = ? AND is_approved = 1",
            (new_driver_id,)
        )
        if not cursor.fetchone():
            db_conn.close()
            return jsonify({
                "success": False,
                "message": f"Driver {new_driver_id} not found or not approved",
                "error_code": "INVALID_DRIVER"
            }), 400
        
        # Update trip
        cursor.execute(
            """
            UPDATE trips
            SET driver_id = ?, route_revision = route_revision + 1, updated_at = ?
            WHERE id = ?
            """,
            (new_driver_id, datetime.now().isoformat(), trip_id)
        )
        
        # Log audit entry
        cursor.execute(
            """
            INSERT INTO admin_audit (admin_id, trip_id, action, old_data, new_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                admin_id, trip_id, "swap_driver",
                f"driver_id={old_driver_id}",
                f"driver_id={new_driver_id}",
                datetime.now().isoformat()
            )
        )
        
        db_conn.commit()
        db_conn.close()
        
        return jsonify({
            "success": True,
            "message": "Driver swapped successfully",
            "data": {
                "trip_id": trip_id,
                "old_driver_id": old_driver_id,
                "new_driver_id": new_driver_id
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Override swap failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error during swap operation",
            "error_code": "INTERNAL_ERROR"
        }), 500


@trip_v2_bp.route("/<int:trip_id>/complete", methods=["POST"])
def complete_trip_admin(trip_id: int):
    """
    Force complete a trip by Admin.
    Calculates duration and final stats.
    """
    try:
        data = request.json or {}
        admin_id = data.get("admin_id", "").strip()
        # Optional payload from driver/client containing final route summary
        total_km = data.get("total_km")
        polyline = data.get("polyline")
        route_json = data.get("route_json")
        
        db_conn = get_db()
        cursor = db_conn.cursor()
        
        # Check trip
        cursor.execute("SELECT status, start_time FROM trips WHERE id = ?", (trip_id,))
        trip = cursor.fetchone()
        
        if not trip:
            db_conn.close()
            return jsonify({"success": False, "message": "Trip not found"}), 404
        
        status, start_time = trip
        if status == 'completed':
            db_conn.close()
            return jsonify({"success": True, "message": "Trip already completed"}), 200
            
        total_km_value = None
        if total_km not in (None, ""):
            total_km_value = float(total_km)

        outcome = mark_trip_completed(
            db_conn,
            trip_id,
            actor_role="admin",
            actor_id=admin_id or "admin",
            total_km=total_km_value,
            polyline=str(polyline) if polyline is not None else None,
            route_json=str(route_json) if route_json is not None else None,
        )

        db_conn.commit()
        db_conn.close()
        
        # Broadcast status change to connected clients
        try:
            from services.socket_service import broadcast_trip_status_change
            # Fetch route_no for broadcasting
            cursor = get_db().cursor()
            cursor.execute("SELECT route_no FROM trips WHERE id = ?", (trip_id,))
            r = cursor.fetchone()
            route_no = r[0] if r else None
            if route_no:
                broadcast_trip_status_change(route_no, 'completed', trip_id)
        except Exception:
            logger.exception("Failed to broadcast trip completion (non-critical)")

        return jsonify({
            "success": True,
            "message": "Trip force-completed successfully",
            "data": outcome
        }), 200
        
    except Exception as e:
        logger.error(f"Force complete failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@trip_v2_bp.route("/available-drivers", methods=["GET"])
def get_available_drivers():
    """
    Get available drivers for a specific time slot and vehicle type.
    """
    try:
        trip_type = request.args.get("trip_type", "").lower()
        scheduled_time = request.args.get("scheduled_time", "")
        vehicle_type = request.args.get("vehicle_type")
        admin_id = request.args.get("admin_id", "").strip()
        trip_day = request.args.get("trip_day", "").strip() or _today_trip_day()
        
        if not scheduled_time:
            return jsonify({
                "success": False,
                "message": "scheduled_time is required",
                "error_code": "MISSING_PARAM"
            }), 400

        db_conn = get_db()
        cursor = db_conn.cursor()

        drivers = _fetch_available_drivers_rows(
            db_conn,
            scheduled_time=scheduled_time,
            vehicle_type=str(vehicle_type) if vehicle_type is not None else None,
            trip_type=trip_type,
            trip_day=trip_day,
            admin_id=admin_id or None,
        )
        db_conn.close()

        result = [
            {
                "id": d[0],
                "name": d[1],
                "mobile": d[2],
                "cab_no": d[3],
                "vehicle_type": d[4]
            }
            for d in drivers
        ]

        return jsonify({
            "success": True,
            "data": result
        }), 200

    except Exception as e:
        logger.error(f"Failed to fetch available drivers: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@trip_v2_bp.route("/available-drivers", methods=["POST"])
def post_available_drivers():
    """
    POST version: accept JSON body with optional group_data/admin_id/trip_type/selected_time
    Keeps compatibility with clients that send complex group payloads.
    """
    try:
        body = request.get_json(force=True) or {}
        trip_type = (body.get("trip_type") or body.get("tripType") or "").lower()
        scheduled_time = body.get("selected_time") or body.get("scheduled_time") or body.get("selectedTime") or ""
        trip_day = str(body.get("trip_day") or body.get("tripDay") or _today_trip_day()).strip()
        admin_id = str(body.get("admin_id") or "").strip()

        # vehicle type can be provided at top-level or inside group_data
        vehicle_type = body.get("vehicle_type") or body.get("vehicleType")
        group = body.get("group_data") or body.get("groupData") or {}
        if not vehicle_type and isinstance(group, dict):
            vehicle_type = group.get("assigned_cab_type") or group.get("vehicle_type")

        if not scheduled_time:
            return jsonify({
                "success": False,
                "message": "selected_time / scheduled_time is required",
                "error_code": "MISSING_PARAM"
            }), 400

        db_conn = get_db()
        drivers = _fetch_available_drivers_rows(
            db_conn,
            scheduled_time=str(scheduled_time),
            vehicle_type=str(vehicle_type) if vehicle_type is not None else None,
            trip_type=trip_type,
            trip_day=trip_day,
            admin_id=admin_id or None,
        )
        db_conn.close()

        result = [
            {
                "id": d[0],
                "name": d[1],
                "mobile": d[2],
                "cab_no": d[3],
                "vehicle_type": d[4]
            }
            for d in drivers
        ]

        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Failed to fetch available drivers (POST): {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


# --- New Request Management Endpoints ---

@trip_v2_bp.route("/drivers/go-home-requests", methods=["GET"])
def list_go_home_requests():
    """List pending/approved hometown requests for drivers."""
    db_conn = None
    try:
        db_conn = get_db()
        cursor = db_conn.cursor()
        admin_id = str(request.args.get("admin_id") or "").strip()
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
        driver_join = ""
        params: List[Any] = []
        if admin_id:
            driver_join = """
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            """
            params.append(admin_id)
        cursor.execute("""
            SELECT r.id, r.driver_id, d.name, d.mobile, r.requested_home_town, r.status, r.created_at,
                   {lat_expr} AS home_lat,
                   {lng_expr} AS home_lng
            FROM driver_hometown_requests r
            JOIN drivers d ON r.driver_id = d.id
            {driver_join}
            WHERE r.status = 'pending'
               OR (
                    r.status = 'approved'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM trips t
                        WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                          AND LOWER(COALESCE(t.status, 'created')) IN
                              ('created','assigned','started','active','in_progress','live','completed')
                          AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                              datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                    )
               )
            ORDER BY r.created_at DESC
        """.format(lat_expr=lat_expr, lng_expr=lng_expr, driver_join=driver_join), tuple(params))
        rows = cursor.fetchall()

        result = [{
            "id": r[0],
            "request_id": r[0],
            "driver_id": r[1],
            "driver_name": r[2],
            "mobile": r[3],
            "home_town": r[4],
            "status": r[5],
            "date": r[6],
            "home_lat": float(r[7] or 0),
            "home_lng": float(r[8] or 0),
            "home_location_lat": float(r[7] or 0),
            "home_location_lng": float(r[8] or 0),
        } for r in rows]
        
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Failed to list go-home requests: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if db_conn is not None:
            db_conn.close()


@trip_v2_bp.route("/employees/no-trip-requests", methods=["GET"])
def list_no_trip_requests():
    """List employees who have requested 'No Trip' for today."""
    try:
        db_conn = get_db()
        cursor = db_conn.cursor()
        admin_id = str(request.args.get("admin_id") or "").strip()
        params: List[Any] = []
        admin_filter = ""
        if admin_id:
            admin_filter = " AND CAST(COALESCE(e.admin_id, '') AS TEXT) = ?"
            params.append(admin_id)
        try:
            cursor.execute("""
                SELECT e.id, e.name, e.mobile, r.reason, r.request_date
                FROM emp_no_trip_requests r
                JOIN employees e ON r.employee_id = e.id
                WHERE date(r.request_date) = date('now')
                {admin_filter}
            """.format(admin_filter=admin_filter), tuple(params))
            rows = cursor.fetchall()
        except Exception:
            try:
                cursor.execute("""
                    SELECT e.id, e.name, e.mobile, r.reason, r.request_date
                    FROM employee_no_trip_requests r
                    JOIN employees e ON r.employee_id = e.id
                    WHERE date(r.request_date) = date('now')
                    {admin_filter}
                """.format(admin_filter=admin_filter), tuple(params))
                rows = cursor.fetchall()
            except Exception:
                rows = []
        db_conn.close()
        
        result = [{
            "employee_id": r[0],
            "name": r[1],
            "mobile": r[2],
            "reason": r[3],
            "date": r[4]
        } for r in rows]
        
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Failed to list no-trip requests: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
        logger.error(f"Failed to fetch available drivers: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error fetching drivers",
            "error_code": "INTERNAL_ERROR"
        }), 500


@trip_v2_bp.route("/scheduled-times", methods=["GET"])
def get_scheduled_times():
    """
    Get distinct scheduled times from employee requests/data.
    Useful for populating the time dropdown.
    """
    try:
        trip_type = request.args.get("trip_type", "pickup").lower()
        admin_id = request.args.get("admin_id", "").strip()
        
        db_conn = get_db()
        cursor = db_conn.cursor()
        
        column = "login_time" if trip_type == "pickup" else "logout_time"
        
        # Get distinct times from employees where they are active
        params: List[Any] = []
        admin_filter = ""
        if admin_id:
            admin_filter = " AND CAST(COALESCE(admin_id, '') AS TEXT) = ?"
            params.append(admin_id)

        cursor.execute(f"""
            SELECT DISTINCT {column} 
            FROM employees 
            WHERE is_active = 1 AND {column} IS NOT NULL AND {column} != ''{admin_filter}
            ORDER BY {column}
        """, params)
        
        times = [r[0] for r in cursor.fetchall()]
        db_conn.close()
        
        return jsonify({
            "success": True,
            "data": times
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch scheduled times: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal error fetching times",
            "error_code": "INTERNAL_ERROR"
        }), 500


@trip_v2_bp.route("/vehicles/search/nlp", methods=["GET"])
def search_vehicles_nlp():
    """
    STEP 5: NLP-powered vehicle/driver search.
    
    Query Parameters:
    - q: Search query (searches driver name, cab no, vehicle type, location)
    - admin_id: Admin ID (optional - for filtering)
    - trip_type: "pickup" or "drop" (optional - for filtering by availability)
    - limit: Max results (default 10)
    
    Response:
    {
        "success": true,
        "data": {
            "results": [
                {
                    "id": 5,
                    "driver_name": "John Doe",
                    "cab_no": "DL-01-AB-1234",
                    "vehicle_type": 6,
                    "is_available": true,
                    "current_location": "Andheri",
                    "go_home_request": true,
                    "relevance_score": 0.95
                }
            ]
        }
    }
    """
    try:
        search_query = request.args.get("q", "").strip().lower()
        admin_id = request.args.get("admin_id", "").strip()
        trip_type = request.args.get("trip_type", "").strip().lower()
        limit = int(request.args.get("limit", 10))
        
        if not search_query:
            return jsonify({
                "success": False,
                "message": "Search query 'q' is required",
                "error_code": "MISSING_QUERY"
            }), 400
        
        db_conn = get_db()
        
        # Get all active drivers
        cursor = db_conn.cursor()
        join_sql = _driver_admin_join_sql(admin_id, alias="drivers")
        params: List[Any] = [admin_id] if admin_id else []
        cursor.execute(f"""
            SELECT 
                drivers.id, drivers.name, drivers.mobile, drivers.vehicle_no, drivers.vehicle_type, 
                drivers.home_town as current_location, drivers.is_online
            FROM drivers
            {join_sql}
            WHERE drivers.is_approved = 1 AND drivers.is_online = 1
            LIMIT 100
        """, params)
        drivers = cursor.fetchall()
        
        # Get go-home requests for highlighting
        try:
            cursor.execute("""
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
                LIMIT 50
            """)
            go_home_drivers = {row[0] for row in cursor.fetchall()}
        except Exception:
            go_home_drivers = set()
        
        cursor.close()
        db_conn.close()
        
        # NLP-style fuzzy matching
        from difflib import SequenceMatcher
        
        results = []
        for driver in drivers:
            driver_id, name, mobile, cab_no, vehicle_type, location, is_online = driver
            
            # Calculate relevance scores for different fields
            name_score = SequenceMatcher(None, search_query, name.lower()).ratio() if name else 0
            cab_score = SequenceMatcher(None, search_query, str(cab_no).lower()).ratio() if cab_no else 0
            location_score = SequenceMatcher(None, search_query, str(location).lower()).ratio() if location else 0
            vehicle_score = SequenceMatcher(None, search_query, str(vehicle_type)).ratio()
            
            # Get highest match score
            max_score = max(name_score, cab_score, location_score, vehicle_score)
            
            # Only include if relevance > 0.3 (30% match)
            if max_score > 0.3:
                results.append({
                    "id": driver_id,
                    "driver_name": name,
                    "mobile": mobile,
                    "cab_no": cab_no,
                    "vehicle_type": vehicle_type,
                    "current_location": location,
                    "is_available": bool(is_online),
                    "go_home_request": driver_id in go_home_drivers,
                    "relevance_score": round(max_score, 2)
                })
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Apply limit
        results = results[:limit]
        
        return jsonify({
            "success": True,
            "message": f"Found {len(results)} vehicles matching '{search_query}'",
            "data": {
                "search_query": search_query,
                "results_count": len(results),
                "results": results
            }
        }), 200
    
    except ValueError as e:
        return jsonify({
            "success": False,
            "message": f"Invalid parameter: {str(e)}",
            "error_code": "INVALID_PARAMETER"
        }), 400


@trip_v2_bp.route("/employees/search/nlp", methods=["GET"])
def search_employees_nlp():
    """
    STEP 6: NLP-powered employee search for selected time slot.

    Query Params:
    - q: search query
    - admin_id: optional
    - trip_type: optional
    - selected_time: optional
    - limit: optional
    """
    try:
        search_query = request.args.get("q", "").strip().lower()
        trip_type = request.args.get("trip_type", "").strip().lower()
        selected_time = request.args.get("selected_time", "").strip()
        trip_day = request.args.get("trip_day", "").strip() or _today_trip_day()
        admin_id = request.args.get("admin_id", "").strip()
        limit = int(request.args.get("limit", 20))

        if not search_query:
            return jsonify({"success": False, "message": "Search query 'q' is required"}), 400
        if trip_type not in ("pickup", "drop"):
            return jsonify({"success": False, "message": "trip_type must be 'pickup' or 'drop'"}), 400
        if not selected_time:
            return jsonify({"success": False, "message": "selected_time is required"}), 400

        db_conn = get_db()
        eligible_employees, _ = filter_eligible_employees(
            db_conn,
            trip_type=trip_type,
            selected_time=selected_time,
            employee_ids=None,
            trip_day=trip_day,
            admin_id=admin_id or None,
        )

        from difflib import SequenceMatcher

        results = []
        for emp in eligible_employees:
            emp_id = emp.get("id")
            name = str(emp.get("name") or "")
            mobile = str(emp.get("mobile") or "")
            home_loc = str(emp.get("home_address") or emp.get("pickup_address") or emp.get("drop_location") or "")

            name_score = SequenceMatcher(None, search_query, name.lower()).ratio() if name else 0
            mobile_score = SequenceMatcher(None, search_query, mobile.lower()).ratio() if mobile else 0
            home_score = SequenceMatcher(None, search_query, home_loc.lower()).ratio() if home_loc else 0

            max_score = max(name_score, mobile_score, home_score)
            if max_score > 0.25:
                results.append({
                    "id": emp_id,
                    "name": name,
                    "mobile": mobile,
                    "home_location": home_loc,
                    "login_time": emp.get("login_time"),
                    "logout_time": emp.get("logout_time"),
                    "relevance_score": round(max_score, 2),
                })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        results = results[:limit]

        db_conn.close()

        return jsonify({"success": True, "message": f"Found {len(results)} employees matching '{search_query}'", "data": {"results": results}}), 200

    except Exception as e:
        logger.error(f"Employee NLP search failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error performing search"}), 500


@trip_v2_bp.route('/assigned-employees', methods=['GET'])
@trip_v2_bp.route('/trips/assigned-employees', methods=['GET'])  # legacy path compatibility
def get_assigned_employees():
    """Return list of employee ids already assigned for the selected time/trip_type"""
    try:
        admin_id = request.args.get('admin_id', '').strip()
        trip_type = request.args.get('trip_type', '').strip().lower()
        selected_time = request.args.get('selected_time', '').strip()
        trip_day = request.args.get('trip_day', '').strip() or _today_trip_day()

        if trip_type not in ("pickup", "drop"):
            return jsonify({"success": False, "message": "trip_type must be 'pickup' or 'drop'"}), 400
        if not selected_time:
            return jsonify({"success": False, "message": "selected_time is required"}), 400

        db_conn = get_db()
        cursor = db_conn.cursor()
        params: List[Any] = [trip_type, selected_time, trip_day, trip_day]
        admin_filter = ""
        if admin_id:
            admin_filter = " AND CAST(COALESCE(t.admin_id, '') AS TEXT) = ?"
            params.append(admin_id)

        cursor.execute(
            """
            SELECT DISTINCT te.employee_id
            FROM trip_employees te
            JOIN trips t ON te.trip_id = t.id
            WHERE LOWER(COALESCE(t.operation, t.trip_type, '')) = ?
              AND COALESCE(t.time_slot, t.schedule_time, '') = ?
              AND COALESCE(t.trip_day, ?) = ?
              AND LOWER(COALESCE(t.status, 'created')) IN ('created', 'assigned', 'started')
            """ + admin_filter + """
            ORDER BY te.employee_id
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        ids = [r[0] for r in rows]

        cursor.close()
        db_conn.close()
        return jsonify({"success": True, "data": ids}), 200
    except Exception as e:
        logger.error(f"Failed to fetch assigned employees: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500


@trip_v2_bp.route('/create-groups', methods=['POST'])
@trip_v2_bp.route('/createGroups', methods=['POST'])  # Flutter compatibility alias
def create_groups():
    """Create groups using mandatory hybrid distance (Haversine + OSRM/ORS)."""
    db_conn = None
    try:
        data = request.get_json(force=True)
        admin_id = str(data.get("admin_id") or "").strip()
        trip_type = str(data.get("trip_type") or data.get("tripType") or "").strip().lower()
        selected_time = str(
            data.get("selected_time")
            or data.get("time_slot")
            or data.get("scheduled_time")
            or data.get("schedule_time")
            or ""
        ).strip()
        trip_day = str(data.get("trip_day") or data.get("tripDay") or _today_trip_day()).replace("-", "").strip()
        vehicle_types = data.get("vehicle_types", data.get("vehicle_type", []))
        raw_driver_ids = data.get("selected_driver_ids", data.get("driver_ids", []))
        selected_vehicle_ids = data.get("selected_vehicle_ids", data.get("vehicle_ids", []))
        employee_ids = data.get("employee_ids", data.get("selected_employee_ids", []))
        vehicle_priority_enabled = bool(data.get("vehicle_priority_enabled", True))
        try:
            requested_batch_size = int(data.get("batch_size") or data.get("vehicle_batch_size") or 0)
        except Exception:
            requested_batch_size = 0
        vehicle_batch_size = max(0, min(requested_batch_size, 1000))

        if not admin_id or trip_type not in ("pickup", "drop") or not selected_time:
            return jsonify(
                {
                    "success": False,
                    "message": "Missing required parameters",
                    "data": {"groups": [], "warnings": ["admin_id, trip_type and selected_time are required"]},
                }
            ), 200

        def _coerce_int_list(raw: Any) -> List[int]:
            if not isinstance(raw, list):
                return []
            out: List[int] = []
            for v in raw:
                try:
                    out.append(int(v))
                except Exception:
                    continue
            return out

        employee_ids = _coerce_int_list(employee_ids)

        if not isinstance(vehicle_types, list):
            vehicle_types = [vehicle_types]
        try:
            parsed_vehicle_types = sorted({int(v) for v in vehicle_types if int(v) in (4, 6)}, reverse=True)
        except Exception:
            parsed_vehicle_types = []
        if not parsed_vehicle_types:
            parsed_vehicle_types = [6, 4]

        if not isinstance(selected_vehicle_ids, list):
            selected_vehicle_ids = []
        if not isinstance(raw_driver_ids, list):
            raw_driver_ids = []

        db_conn = get_db()
        cursor = db_conn.cursor()
        resolved_admin_id = _resolve_admin_id(db_conn, admin_id) or admin_id
        office_lat, office_lng = _parse_office_coords(db_conn, resolved_admin_id)
        go_home_ids = _go_home_approved_driver_ids(cursor, trip_day)

        def _normalize_driver_ids_local(raw: Any) -> Optional[List[str]]:
            tokens = [str(v).strip() for v in (raw or []) if str(v).strip()]
            if not tokens:
                return None
            params: List[Any] = []
            join_sql = _driver_admin_join_sql(resolved_admin_id, alias="drivers")
            if resolved_admin_id:
                params.append(resolved_admin_id)
            cursor.execute(f"SELECT drivers.id FROM drivers {join_sql}", tuple(params))
            existing_ids = {str(r[0]) for r in cursor.fetchall() if r and r[0] is not None}
            exact = [t for t in tokens if t in existing_ids]
            return sorted(set(exact)) if exact else None

        normalized_driver_ids = _normalize_driver_ids_local(raw_driver_ids)

        eligible_employees, exclusions = filter_eligible_employees(
            db_conn,
            trip_type=trip_type,
            selected_time=selected_time,
            employee_ids=employee_ids if employee_ids else None,
            trip_day=trip_day,
            admin_id=resolved_admin_id,
        )
        if not eligible_employees:
            return jsonify(
                {
                    "success": False,
                    "message": "No eligible employees found",
                    "data": {"groups": [], "warnings": exclusions or ["No eligible employees"]},
                }
            ), 200

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
            return jsonify(
                {
                    "success": False,
                    "message": "No employees with valid coordinates found",
                    "data": {
                        "groups": [],
                        "warnings": list(exclusions or []) + ["No employees with valid coordinates"],
                        "unresolved_coordinates": unresolved_coords,
                    },
                }
            ), 200

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

        params: List[Any] = [resolved_admin_id, trip_day, trip_type, selected_time]
        where_parts = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "d.id NOT IN (SELECT t.driver_id FROM trips t WHERE REPLACE(COALESCE(t.trip_day, ''), '-', '') = ? AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ? AND COALESCE(t.time_slot, t.schedule_time, '') = ? AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress') AND t.driver_id IS NOT NULL)",
        ]
        if parsed_vehicle_types:
            ph = ",".join(["?"] * len(parsed_vehicle_types))
            where_parts.append(f"CAST(d.vehicle_type AS INTEGER) IN ({ph})")
            params.extend(parsed_vehicle_types)
        if normalized_driver_ids is not None and len(normalized_driver_ids) > 0:
            ph = ",".join(["?"] * len(normalized_driver_ids))
            where_parts.append(f"CAST(d.id AS TEXT) IN ({ph})")
            params.extend(normalized_driver_ids)
        elif selected_vehicle_ids:
            selected_driver_ids = [str(v) for v in selected_vehicle_ids if str(v).strip()]
            if selected_driver_ids:
                ph = ",".join(["?"] * len(selected_driver_ids))
                where_parts.append(f"CAST(d.id AS TEXT) IN ({ph})")
                params.extend(selected_driver_ids)

        cursor.execute(
            f"""
            SELECT d.id, d.name, d.vehicle_no, CAST(d.vehicle_type AS INTEGER) AS vtype,
                   {lat_expr} AS home_lat, {lng_expr} AS home_lng
            FROM drivers d
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            WHERE {" AND ".join(where_parts)}
            ORDER BY vtype DESC, d.id ASC
            """,
            tuple(params),
        )
        driver_rows = cursor.fetchall()
        if not driver_rows:
            return jsonify(
                {
                    "success": False,
                    "message": "No available drivers/vehicles",
                    "data": {"groups": [], "warnings": ["No available drivers/vehicles for selected slot"]},
                }
            ), 200

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

            # Keep behavior safe: if planner returns an unexpected type, map it to
            # selected types without breaking current flow.
            preferred = sorted(selected_vehicle_types)
            for cap in preferred:
                if members_count <= cap:
                    return int(cap)
            return int(preferred[-1]) if preferred else 4

        for idx, g in enumerate(plan.get("groups", []), start=1):
            members = []
            for seq, m in enumerate(g.get("members", []), start=1):
                members.append(
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "mobile": m.get("mobile"),
                        "address": m.get("address"),
                        "lat": m.get("lat"),
                        "lng": m.get("lng"),
                        "sequence_no": seq,
                    }
                )
            group_vehicle_type = _resolve_group_vehicle_type(
                g.get("vehicle_type", 4),
                len(members),
            )
            groups.append(
                {
                    "group_index": idx,
                    "members": members,
                    "employees": members,
                    "vehicle_type": group_vehicle_type,
                    "assigned_cab_type": group_vehicle_type,
                    "assigned_driver_id": g.get("driver_id"),
                    "assigned_cab_no": g.get("vehicle_no"),
                    "distance_km_estimate": g.get("route_distance_km", g.get("anchor_distance_km")),
                    "eta_min_estimate": None,
                    "go_home_approved": bool(g.get("go_home_approved")),
                }
            )

        now_iso = datetime.now().isoformat(timespec="seconds")
        try:
            persist_conn = get_db()
            persist_cur = persist_conn.cursor()
            _ensure_groups_table_for_v2(persist_cur)
            persist_cur.execute("PRAGMA table_info(groups)")
            cols = {row[1] for row in persist_cur.fetchall()}

            if {"admin_id", "trip_type", "schedule_time", "status"} <= cols:
                persist_cur.execute(
                    "DELETE FROM groups WHERE admin_id = ? AND trip_type = ? AND schedule_time = ? AND status = 'pending'",
                    (str(admin_id), str(trip_type), str(selected_time)),
                )

            for idx, g in enumerate(groups, start=1):
                members = g.get("members") or []
                members_json = json.dumps(members if isinstance(members, list) else [])
                vehicle_type = int(g.get("assigned_cab_type") or g.get("vehicle_type") or 4)
                row_payload = {
                    "group_index": int(g.get("group_index") or idx),
                    "assigned_driver_id": g.get("assigned_driver_id"),
                    "assigned_cab_type": vehicle_type,
                    "members": members_json,
                    "members_json": members_json,
                    "distance_km_estimate": g.get("distance_km_estimate"),
                    "eta_min_estimate": g.get("eta_min_estimate"),
                    "admin_id": str(admin_id),
                    "trip_day": trip_day,
                    "trip_type": str(trip_type),
                    "schedule_time": str(selected_time),
                    "vehicle_type": vehicle_type,
                    "assigned_cab_no": g.get("assigned_cab_no"),
                    "status": "pending",
                    "created_at": now_iso,
                    "updated_at": now_iso,
                    "deleted_at": None,
                }
                insert_data = {k: v for k, v in row_payload.items() if k in cols}
                if insert_data:
                    col_clause = ", ".join(insert_data.keys())
                    val_clause = ", ".join(["?"] * len(insert_data))
                    persist_cur.execute(
                        f"INSERT INTO groups ({col_clause}) VALUES ({val_clause})",
                        tuple(insert_data.values()),
                    )
            persist_conn.commit()
            persist_cur.close()
            persist_conn.close()
        except Exception as persist_exc:
            logger.error(f"Group persistence failed: {persist_exc}", exc_info=True)
            return jsonify(
                {
                    "success": True,
                    "message": "Groups created (preview only)",
                    "data": {"groups": groups, "warnings": [f"Persistence warning: {persist_exc}"]},
                }
            ), 200

        warnings = list(exclusions or [])
        unassigned_employees = cast(List[Dict[str, Any]], plan.get("unassigned_employees", []))
        if unassigned_employees:
            eligible_next_trip = sum(
                1
                for e in unassigned_employees
                if bool(e.get("eligible_for_next_trip", False))
            )
            if eligible_next_trip > 0:
                warnings.append(
                    f"{eligible_next_trip} unassigned employee(s) remain eligible for next trip assignment."
                )
        unassigned_vehicles = cast(List[Dict[str, Any]], plan.get("unassigned_vehicles", []))
        if unassigned_vehicles:
            eligible_next = sum(
                1
                for v in unassigned_vehicles
                if bool(v.get("eligible_for_next_group_creation", False))
            )
            if eligible_next > 0:
                warnings.append(
                    f"{eligible_next} unassigned vehicle(s) are kept eligible for next group creation."
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
        return jsonify(
            {
                "success": True,
                "message": "Groups created",
                "data": {
                    "groups": groups,
                    "warnings": warnings,
                    "unresolved_coordinates": unresolved_coords,
                    "unassigned_employees": unassigned_employees,
                    "unassigned_vehicles": unassigned_vehicles,
                    "hybrid_provider": plan.get("hybrid_provider"),
                    "hybrid_strict": bool(plan.get("hybrid_strict", True)),
                    "vehicle_batch_size": plan.get("vehicle_batch_size"),
                    "vehicle_batches": int(plan.get("vehicle_batches", 1) or 1),
                },
            }
        ), 200
    except RuntimeError as e:
        return jsonify(
            {
                "success": False,
                "message": str(e),
                "error_code": "HYBRID_PROVIDER_UNAVAILABLE",
                "data": {
                    "groups": [],
                    "warnings": [str(e), "Check /api/health/hybrid and route provider configuration."],
                },
            }
        ), 503
    except Exception as e:
        logger.error(f"Failed to create groups: {e}", exc_info=True)
        return jsonify(
            {
                "success": False,
                "message": "Internal server error",
                "data": {"groups": [], "warnings": [str(e)]},
            }
        ), 200
    finally:
        try:
            if db_conn is not None:
                db_conn.close()
        except Exception:
            pass


def _ensure_groups_table_for_v2(cursor) -> None:
    """
    Ensures groups table exists for v2 create-groups persistence.
    Safe and idempotent.
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
    if cursor.fetchone():
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_index INTEGER,
          assigned_driver_id TEXT,
          assigned_cab_type INTEGER,
          members TEXT,
          members_json TEXT,
          distance_km_estimate REAL,
          eta_min_estimate INTEGER,
          admin_id TEXT NOT NULL,
          trip_day TEXT NOT NULL,
          trip_type TEXT NOT NULL,
          schedule_time TEXT NOT NULL,
          vehicle_type INTEGER,
          assigned_cab_no TEXT,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          deleted_at TEXT
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_trip_day ON groups(trip_day, schedule_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_admin ON groups(admin_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_status ON groups(status)")


@trip_v2_bp.route('/groups', methods=['GET'])
def list_groups():
    """
    Step 6: View groups for selected admin/time slot/day.
    - Filters by admin_id, trip_type, selected_time, trip_day (defaults to today when context is provided).
    - Returns members + assigned vehicle + distance/ETA estimates.
    """
    try:
        admin_id = str(request.args.get("admin_id", "")).strip()
        trip_type = str(request.args.get("trip_type", "")).strip().lower()
        selected_time = str(
            request.args.get("selected_time")
            or request.args.get("schedule_time")
            or ""
        ).strip()
        trip_day = str(request.args.get("trip_day", "")).strip()
        editable_only = str(request.args.get("editable_only", "")).strip().lower() in ("1", "true", "yes")

        db_conn = get_db()
        cursor = db_conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
            if not cursor.fetchone():
                cursor.close()
                db_conn.close()
                return jsonify({"success": True, "data": []}), 200

            cursor.execute("PRAGMA table_info(groups)")
            cols = [row[1] for row in cursor.fetchall()]
            where_clauses = []
            params = []
            if "deleted_at" in cols:
                where_clauses.append("deleted_at IS NULL")
            if "status" in cols:
                if editable_only:
                    # View & Modify should not show already-assigned/running groups.
                    where_clauses.append("LOWER(COALESCE(status, 'pending')) IN ('pending', 'created')")
                else:
                    where_clauses.append("LOWER(COALESCE(status, 'pending')) NOT IN ('cancelled', 'deleted')")
            if admin_id and "admin_id" in cols:
                where_clauses.append("admin_id = ?")
                params.append(admin_id)
            if trip_type and "trip_type" in cols:
                where_clauses.append("LOWER(COALESCE(trip_type, '')) = ?")
                params.append(trip_type)
            if selected_time:
                if "schedule_time" in cols:
                    where_clauses.append("schedule_time = ?")
                    params.append(selected_time)
                elif "selected_time" in cols:
                    where_clauses.append("selected_time = ?")
                    params.append(selected_time)
            if "trip_day" in cols:
                if not trip_day and (admin_id or trip_type or selected_time):
                    trip_day = _today_trip_day()
                if trip_day:
                    where_clauses.append("trip_day = ?")
                    params.append(trip_day)
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            order_sql = " ORDER BY group_index" if "group_index" in cols else (" ORDER BY id" if "id" in cols else "")
            if "updated_at" in cols:
                order_sql = " ORDER BY updated_at DESC"

            cursor.execute(f"SELECT * FROM groups{where_sql}{order_sql}", tuple(params))
        except Exception as e:
            # Handle fresh DBs (or non-SQLite engines) where groups table may not exist yet.
            msg = str(e).lower()
            if ("no such table" in msg) or ("doesn't exist" in msg) or ("does not exist" in msg):
                cursor.close()
                db_conn.close()
                return jsonify({"success": True, "data": []}), 200
            raise
        rows = cursor.fetchall()
        col_names = [d[0] for d in cursor.description] if cursor.description else []
        groups = []
        for i, r in enumerate(rows, start=1):
            rec = dict(zip(col_names, r))
            gid = rec.get("id", i)
            gidx = rec.get("group_index", i)
            did = rec.get("assigned_driver_id")
            cab = rec.get("assigned_cab_type", rec.get("vehicle_type"))
            members_json = rec.get("members_json", rec.get("members"))
            created_at = rec.get("created_at")
            dist = rec.get("distance_km_estimate")
            eta = rec.get("eta_min_estimate")
            try:
                members = json.loads(members_json) if members_json else []
            except Exception:
                members = []
            groups.append({
                'id': gid,
                'group_index': gidx,
                'assigned_driver_id': did,
                'assigned_cab_type': cab,
                'members': members,
                'trip_type': rec.get("trip_type"),
                'schedule_time': rec.get("schedule_time"),
                'trip_day': rec.get("trip_day"),
                'status': rec.get("status", "pending"),
                'created_at': created_at,
                'distance_km_estimate': dist,
                'eta_min_estimate': eta,
            })
        cursor.close(); db_conn.close()
        return jsonify({"success": True, "data": groups}), 200
    except Exception as e:
        logger.error(f"Failed to list groups: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500


@trip_v2_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@trip_v2_bp.route('/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id: int):
    """
    Step 7: Delete a preview group before final trip assignment.

    Delete a preview group before final trip assignment.
    - Soft delete if groups.status column exists (status='cancelled')
    - Tracks deleted_at if available
    - Falls back to hard delete if status column is absent
    """
    try:
        db_conn = get_db()
        cursor = db_conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
        if not cursor.fetchone():
            cursor.close()
            db_conn.close()
            return jsonify({"success": False, "message": "Groups table not found"}), 404

        cols = _load_groups_table_columns(cursor)
        resolved_group_id = _resolve_group_id(cursor, cols, group_id)
        if not resolved_group_id:
            cursor.close()
            db_conn.close()
            return jsonify({"success": False, "message": "Group not found"}), 404

        if "status" in cols or "deleted_at" in cols:
            select_cols = ["id"]
            if "status" in cols:
                select_cols.append("status")
            if "deleted_at" in cols:
                select_cols.append("deleted_at")
            cursor.execute(f"SELECT {', '.join(select_cols)} FROM groups WHERE id = ?", (resolved_group_id,))
            row = cursor.fetchone()
            rec = dict(zip(select_cols, row)) if row else {}
            if not _group_editable(rec):
                cursor.close()
                db_conn.close()
                return jsonify({"success": False, "message": "Group is not editable"}), 400

        now_iso = datetime.now().isoformat(timespec="seconds")
        updates = {}
        if "status" in cols:
            updates["status"] = "cancelled"
        if "deleted_at" in cols:
            updates["deleted_at"] = now_iso
        if "updated_at" in cols:
            updates["updated_at"] = now_iso

        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(
                f"UPDATE groups SET {set_clause} WHERE id = ?",
                tuple(updates.values()) + (resolved_group_id,),
            )
            action = "soft_deleted"
        else:
            cursor.execute("DELETE FROM groups WHERE id = ?", (resolved_group_id,))
            action = "hard_deleted"

        db_conn.commit()
        cursor.close()
        db_conn.close()
        return jsonify({
            "success": True,
            "message": "Group deleted",
            "data": {"group_id": resolved_group_id, "action": action},
        }), 200
    except Exception as e:
        logger.error(f"Failed to delete group: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500


def _recalculate_estimates_for_members(members, office_lat=None, office_lng=None):
    # Lightweight estimate: distance = members_count * 2.5 km, eta = members_count * 3 min
    count = len(members) if members else 0
    return round(count * 2.5, 2), int(count * 3)


def _load_groups_table_columns(cursor) -> set:
    cursor.execute("PRAGMA table_info(groups)")
    return {row[1] for row in cursor.fetchall()}


def _members_column(cols: set) -> str:
    return "members_json" if "members_json" in cols else "members"


def _safe_load_members(raw_json: Any) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(raw_json) if raw_json else []
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _group_capacity(rec: Dict[str, Any]) -> int:
    for key in ("assigned_cab_type", "vehicle_type"):
        val = rec.get(key)
        if val in (4, 6, "4", "6"):
            return int(val)
    return 4


def _member_ids(members: List[Dict[str, Any]]) -> set:
    out = set()
    for m in members:
        try:
            out.add(int(m.get("id")))
        except Exception:
            continue
    return out


def _resolve_group_id(cursor, cols: set, group_ref: int) -> Optional[int]:
    cursor.execute("SELECT id FROM groups WHERE id = ?", (group_ref,))
    row = cursor.fetchone()
    if row:
        return int(row[0])
    if "group_index" in cols:
        cursor.execute(
            "SELECT id FROM groups WHERE group_index = ? ORDER BY id DESC LIMIT 1",
            (group_ref,),
        )
        row = cursor.fetchone()
        if row:
            return int(row[0])
    return None


def _group_editable(rec: Dict[str, Any]) -> bool:
    status = str(rec.get("status", "pending")).lower()
    if status not in ("pending", "created", "assigned"):
        return False
    if rec.get("deleted_at"):
        return False
    return True


def _mark_groups_assigned_after_trip_create(
    cursor,
    groups: List[Dict[str, Any]],
    admin_id: Optional[str],
    trip_type: str,
    schedule_time: str,
    trip_day: str,
) -> None:
    """Hide successfully assigned preview groups from the editable list."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
    if not cursor.fetchone():
        return

    cols = _load_groups_table_columns(cursor)
    if "status" not in cols:
        return

    normalized_day = str(trip_day or "").replace("-", "").strip()
    now_iso = datetime.now().isoformat(timespec="seconds")

    for idx, group in enumerate(groups):
        target_id: Optional[int] = None

        raw_group_id = group.get("id")
        try:
            if raw_group_id is not None:
                target_id = int(raw_group_id)
        except Exception:
            target_id = None

        if target_id is None and "group_index" in cols:
            raw_group_index = group.get("group_index", idx + 1)
            try:
                group_index = int(raw_group_index)
            except Exception:
                continue

            where_clauses = ["group_index = ?"]
            params: List[Any] = [group_index]
            if admin_id and "admin_id" in cols:
                where_clauses.append("admin_id = ?")
                params.append(admin_id)
            if trip_type and "trip_type" in cols:
                where_clauses.append("LOWER(COALESCE(trip_type, '')) = ?")
                params.append(trip_type.lower())
            if schedule_time:
                if "schedule_time" in cols:
                    where_clauses.append("schedule_time = ?")
                    params.append(schedule_time)
                elif "selected_time" in cols:
                    where_clauses.append("selected_time = ?")
                    params.append(schedule_time)
            if normalized_day and "trip_day" in cols:
                where_clauses.append("REPLACE(COALESCE(trip_day, ''), '-', '') = ?")
                params.append(normalized_day)
            if "deleted_at" in cols:
                where_clauses.append("deleted_at IS NULL")

            cursor.execute(
                f"""
                SELECT id
                FROM groups
                WHERE {' AND '.join(where_clauses)}
                ORDER BY id DESC
                LIMIT 1
                """,
                tuple(params),
            )
            row = cursor.fetchone()
            if row:
                target_id = int(row[0])

        if target_id is None:
            continue

        updates = {"status": "assigned"}
        if "updated_at" in cols:
            updates["updated_at"] = now_iso
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        cursor.execute(
            f"UPDATE groups SET {set_clause} WHERE id = ?",
            tuple(updates.values()) + (target_id,),
        )


@trip_v2_bp.route('/groups/<int:group_id>/remove-employee', methods=['POST'])
def remove_employee_from_group(group_id):
    """Step 7: Remove an employee from a pending group and recalculate estimates."""
    try:
        data = request.get_json(force=True)
        emp_id = int(data.get('employee_id'))
        db_conn = get_db(); cursor = db_conn.cursor()
        cols = _load_groups_table_columns(cursor)
        mcol = _members_column(cols)
        resolved_group_id = _resolve_group_id(cursor, cols, group_id)
        if not resolved_group_id:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group not found"}), 404
        select_cols = [mcol, "id"]
        for optional in ("status", "deleted_at"):
            if optional in cols:
                select_cols.append(optional)
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM groups WHERE id = ?", (resolved_group_id,))
        row = cursor.fetchone()
        rec = dict(zip(select_cols, row))
        if not _group_editable(rec):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group is not editable"}), 400
        members = _safe_load_members(rec.get(mcol))
        if emp_id not in _member_ids(members):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Employee not found in group"}), 404
        members = [m for m in members if m.get('id') != emp_id]
        dist, eta = _recalculate_estimates_for_members(members)
        updates = {mcol: json.dumps(members)}
        if "distance_km_estimate" in cols:
            updates["distance_km_estimate"] = dist
        if "eta_min_estimate" in cols:
            updates["eta_min_estimate"] = eta
        if "updated_at" in cols:
            updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        cursor.execute(f"UPDATE groups SET {set_clause} WHERE id = ?", tuple(updates.values()) + (resolved_group_id,))
        db_conn.commit()
        cursor.close(); db_conn.close()
        return jsonify({"success": True, "data": {"group_id": resolved_group_id, "members": members, "distance_km_estimate": dist, "eta_min_estimate": eta}}), 200
    except Exception as e:
        logger.error(f"Failed to remove employee: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500


@trip_v2_bp.route('/groups/<int:group_id>/add-employee', methods=['POST'])
def add_employee_to_group(group_id):
    """Step 7: Add an eligible employee to a pending group (capacity + eligibility enforced)."""
    try:
        data = request.get_json(force=True)
        emp_id = int(data.get('employee_id'))
        db_conn = get_db(); cursor = db_conn.cursor()
        cols = _load_groups_table_columns(cursor)
        mcol = _members_column(cols)
        resolved_group_id = _resolve_group_id(cursor, cols, group_id)
        if not resolved_group_id:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group not found"}), 404
        select_cols = [mcol, "id"]
        for optional in ("trip_type", "schedule_time", "trip_day", "admin_id", "assigned_cab_type", "vehicle_type", "status", "deleted_at"):
            if optional in cols:
                select_cols.append(optional)
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM groups WHERE id = ?", (resolved_group_id,))
        row = cursor.fetchone()

        rec = dict(zip(select_cols, row))
        if str(rec.get("status", "pending")).lower() not in ("pending", "created", "assigned"):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group is not editable"}), 400
        if "deleted_at" in rec and rec.get("deleted_at"):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group is deleted"}), 400

        members = _safe_load_members(rec.get(mcol))
        if emp_id in _member_ids(members):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Employee already exists in group"}), 400

        capacity = _group_capacity(rec)
        if len(members) >= capacity:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": f"Group is at full capacity ({len(members)}/{capacity})"}), 400

        # Prevent duplicates across sibling pending groups in same slot.
        if all(k in cols for k in ("admin_id", "trip_type", "schedule_time", "trip_day", "status")):
            sibling_member_cols = ["id"]
            if "members_json" in cols:
                sibling_member_cols.append("members_json")
            if "members" in cols:
                sibling_member_cols.append("members")
            cursor.execute(
                f"""
                SELECT {', '.join(sibling_member_cols)}
                FROM groups
                WHERE id != ?
                  AND admin_id = ?
                  AND trip_type = ?
                  AND schedule_time = ?
                  AND trip_day = ?
                  AND LOWER(COALESCE(status, 'pending')) = 'pending'
                """,
                (
                    resolved_group_id,
                    rec.get("admin_id"),
                    rec.get("trip_type"),
                    rec.get("schedule_time"),
                    rec.get("trip_day"),
                ),
            )
            for sibling in cursor.fetchall():
                sibling_rec = dict(zip(sibling_member_cols, sibling))
                sibling_raw = sibling_rec.get("members_json")
                if not sibling_raw:
                    sibling_raw = sibling_rec.get("members")
                sibling_members = _safe_load_members(sibling_raw)
                if emp_id in _member_ids(sibling_members):
                    cursor.close(); db_conn.close()
                    return jsonify({"success": False, "message": "Employee already mapped in another group for this slot"}), 400

        # Validate employee basic status + eligibility for this group slot.
        cursor.execute(
            """
            SELECT id, name, mobile, is_active, is_approved,
                   home_address, pickup_address, drop_location,
                   home_lat, home_lng, pickup_lat, pickup_lng, drop_lat, drop_lng
            FROM employees
            WHERE id = ?
            """,
            (emp_id,),
        )
        e = cursor.fetchone()
        if not e:
            cursor.close(); db_conn.close();
            return jsonify({"success": False, "message": "Employee not found"}), 404
        if int(e[3] or 0) != 1 or int(e[4] or 0) != 1:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Employee is not active/approved"}), 400

        trip_type = str(rec.get("trip_type") or "").strip().lower()
        selected_time = str(rec.get("schedule_time") or "").strip()
        trip_day = str(rec.get("trip_day") or _today_trip_day()).strip()
        if trip_type in ("pickup", "drop") and selected_time:
            eligible, _ = filter_eligible_employees(
                db_conn,
                trip_type=trip_type,
                selected_time=selected_time,
                employee_ids=[emp_id],
                trip_day=trip_day,
            )
            if not eligible:
                cursor.close(); db_conn.close()
                return jsonify({"success": False, "message": "Employee is not eligible for selected slot"}), 400

        is_pickup = trip_type == "pickup"
        emp_lat = e[10] if is_pickup else (e[8] if e[8] is not None else e[12])
        emp_lng = e[11] if is_pickup else (e[9] if e[9] is not None else e[13])
        coord_source = "employee"
        if not _is_valid_coord_pair(_to_float_or_none(emp_lat), _to_float_or_none(emp_lng)):
            # Do not block group edit on missing employee coordinates.
            # Use office coordinates fallback so flow remains operational.
            office_lat, office_lng = _parse_office_coords(db_conn, str(rec.get("admin_id") or ""))
            emp_lat, emp_lng = office_lat, office_lng
            coord_source = "office_fallback"
        emp_obj = {
            'id': e[0],
            'name': e[1],
            'mobile': e[2],
            'address': e[6] if is_pickup else (e[5] or e[7] or ""),
            'lat': emp_lat,
            'lng': emp_lng,
        }
        members.append(emp_obj)
        dist, eta = _recalculate_estimates_for_members(members)
        updates = {mcol: json.dumps(members)}
        if "distance_km_estimate" in cols:
            updates["distance_km_estimate"] = dist
        if "eta_min_estimate" in cols:
            updates["eta_min_estimate"] = eta
        if "updated_at" in cols:
            updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        cursor.execute(f"UPDATE groups SET {set_clause} WHERE id = ?", tuple(updates.values()) + (resolved_group_id,))
        db_conn.commit()
        cursor.close(); db_conn.close()
        resp = {
            "group_id": resolved_group_id,
            "members": members,
            "distance_km_estimate": dist,
            "eta_min_estimate": eta,
        }
        if coord_source != "employee":
            resp["warnings"] = ["Employee coordinates unavailable; used office coordinates fallback."]
        return jsonify({"success": True, "data": resp}), 200
    except Exception as e:
        logger.error(f"Failed to add employee: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500


@trip_v2_bp.route('/groups/<int:group_id>/change-vehicle', methods=['POST'])
def change_group_vehicle(group_id):
    """Step 7: Change group vehicle type (4/6) with capacity + driver reassignment validation."""
    try:
        data = request.get_json(force=True)
        vehicle_type = int(data.get('vehicle_type'))
        if vehicle_type not in (4, 6):
            return jsonify({"success": False, "message": "vehicle_type must be 4 or 6"}), 400
        db_conn = get_db(); cursor = db_conn.cursor()
        cols = _load_groups_table_columns(cursor)
        mcol = _members_column(cols)
        resolved_group_id = _resolve_group_id(cursor, cols, group_id)
        if not resolved_group_id:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group not found"}), 404
        select_cols = [mcol, "id"]
        for optional in ("status", "deleted_at", "assigned_driver_id", "trip_type", "schedule_time", "trip_day"):
            if optional in cols:
                select_cols.append(optional)
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM groups WHERE id = ?", (resolved_group_id,))
        row = cursor.fetchone()
        rec = dict(zip(select_cols, row))
        if not _group_editable(rec):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Group is not editable"}), 400
        members = _safe_load_members(rec.get(mcol))
        if len(members) > vehicle_type:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": f"Cannot assign {vehicle_type}-seater to group with {len(members)} members"}), 400

        requested_trip_type = str(
            data.get("trip_type")
            or data.get("operation")
            or rec.get("trip_type")
            or ""
        ).strip().lower()
        requested_time = str(
            data.get("selected_time")
            or data.get("time_slot")
            or data.get("schedule_time")
            or rec.get("schedule_time")
            or ""
        ).strip()
        requested_day = str(data.get("trip_day") or rec.get("trip_day") or _today_trip_day()).replace("-", "").strip()

        def _pick_driver_for_type() -> Optional[Dict[str, Any]]:
            current_driver_id = rec.get("assigned_driver_id")
            if current_driver_id is not None and str(current_driver_id).strip():
                cursor.execute(
                    """
                    SELECT id, vehicle_no
                    FROM drivers
                    WHERE id = ?
                      AND is_approved = 1
                      AND CAST(vehicle_type AS TEXT) = ?
                      AND id NOT IN (
                        SELECT driver_id
                        FROM trips
                        WHERE driver_id IS NOT NULL
                          AND LOWER(COALESCE(status, 'created')) IN ('created', 'assigned', 'started', 'active', 'in_progress')
                          AND (? = '' OR LOWER(COALESCE(operation, trip_type, '')) = ?)
                          AND (? = '' OR COALESCE(time_slot, schedule_time, '') = ?)
                          AND (? = '' OR REPLACE(COALESCE(trip_day, ''), '-', '') = ?)
                      )
                    LIMIT 1
                    """,
                    (
                        str(current_driver_id),
                        str(vehicle_type),
                        requested_trip_type, requested_trip_type,
                        requested_time, requested_time,
                        requested_day, requested_day,
                    ),
                )
                current_row = cursor.fetchone()
                if current_row:
                    return {"id": str(current_row[0]), "vehicle_no": current_row[1]}

            available_rows = _fetch_available_drivers_rows(
                db_conn,
                requested_time,
                str(vehicle_type),
                requested_trip_type if requested_trip_type in ("pickup", "drop") else None,
                requested_day or None,
                str(rec.get("admin_id") or "").strip() or None,
            )
            if not available_rows:
                return None
            first = available_rows[0]
            return {"id": str(first[0]), "vehicle_no": first[3]}

        selected_driver = _pick_driver_for_type()
        if not selected_driver:
            cursor.close(); db_conn.close()
            return jsonify({
                "success": False,
                "message": f"No available {vehicle_type}-seater driver for selected slot/day"
            }), 400

        dist, eta = _recalculate_estimates_for_members(members)
        updates = {}
        if "assigned_cab_type" in cols:
            updates["assigned_cab_type"] = vehicle_type
        if "vehicle_type" in cols:
            updates["vehicle_type"] = vehicle_type
        if "assigned_driver_id" in cols:
            updates["assigned_driver_id"] = selected_driver["id"]
        if "assigned_cab_no" in cols:
            updates["assigned_cab_no"] = selected_driver["vehicle_no"]
        if "distance_km_estimate" in cols:
            updates["distance_km_estimate"] = dist
        if "eta_min_estimate" in cols:
            updates["eta_min_estimate"] = eta
        if "updated_at" in cols:
            updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if not updates:
            return jsonify({"success": False, "message": "Group schema not supported"}), 500
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        cursor.execute(f"UPDATE groups SET {set_clause} WHERE id = ?", tuple(updates.values()) + (resolved_group_id,))
        db_conn.commit()
        cursor.close(); db_conn.close()
        return jsonify({
            "success": True,
            "message": "Vehicle changed successfully",
            "data": {
                "group_id": resolved_group_id,
                "assigned_cab_type": vehicle_type,
                "assigned_driver_id": selected_driver["id"],
                "assigned_cab_no": selected_driver["vehicle_no"],
                "distance_km_estimate": dist,
                "eta_min_estimate": eta
            }
        }), 200
    except Exception as e:
        logger.error(f"Failed to change vehicle: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500


@trip_v2_bp.route('/groups/swap-employees', methods=['POST'])
def swap_employees():
    """Step 7: Swap employees between two pending groups (no duplicates)."""
    try:
        data = request.get_json(force=True)
        ga = int(data.get('group_a'))
        ea = int(data.get('employee_a'))
        gb = int(data.get('group_b'))
        eb = int(data.get('employee_b'))
        db_conn = get_db(); cursor = db_conn.cursor()
        cols = _load_groups_table_columns(cursor)
        mcol = _members_column(cols)
        has_group_index = "group_index" in cols

        def _fetch_group_row(group_ref: int):
            select_cols = ["id", mcol]
            for optional in ("status", "deleted_at"):
                if optional in cols:
                    select_cols.append(optional)
            if has_group_index:
                cursor.execute(
                    f"SELECT {', '.join(select_cols)} FROM groups WHERE group_index = ? ORDER BY id DESC LIMIT 1",
                    (group_ref,),
                )
                hit = cursor.fetchone()
                if hit:
                    return dict(zip(select_cols, hit))
            cursor.execute(f"SELECT {', '.join(select_cols)} FROM groups WHERE id = ?", (group_ref,))
            row = cursor.fetchone()
            return dict(zip(select_cols, row)) if row else None

        rowa = _fetch_group_row(ga)
        rowb = _fetch_group_row(gb)
        if not rowa or not rowb:
            cursor.close(); db_conn.close();
            return jsonify({"success": False, "message": "One or both groups not found"}), 404
        if not _group_editable(rowa) or not _group_editable(rowb):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "One or both groups are not editable"}), 400
        ida, mema_json = rowa["id"], rowa[mcol]
        idb, memb_json = rowb["id"], rowb[mcol]
        if ida == idb:
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Source and destination groups must be different"}), 400
        mema = _safe_load_members(mema_json)
        memb = _safe_load_members(memb_json)
        # swap
        idx_a = next((i for i, x in enumerate(mema) if x.get('id') == ea), None)
        idx_b = next((i for i, x in enumerate(memb) if x.get('id') == eb), None)
        if idx_a is None or idx_b is None:
            cursor.close(); db_conn.close();
            return jsonify({"success": False, "message": "Employee not found in group(s)"}), 404
        mema[idx_a], memb[idx_b] = memb[idx_b], mema[idx_a]
        if len(_member_ids(mema)) != len(mema) or len(_member_ids(memb)) != len(memb):
            cursor.close(); db_conn.close()
            return jsonify({"success": False, "message": "Swap creates duplicate employees in group"}), 400
        da, ea_time = _recalculate_estimates_for_members(mema)
        db, eb_time = _recalculate_estimates_for_members(memb)
        updates_a = {mcol: json.dumps(mema)}
        updates_b = {mcol: json.dumps(memb)}
        if "distance_km_estimate" in cols:
            updates_a["distance_km_estimate"] = da
            updates_b["distance_km_estimate"] = db
        if "eta_min_estimate" in cols:
            updates_a["eta_min_estimate"] = ea_time
            updates_b["eta_min_estimate"] = eb_time
        if "updated_at" in cols:
            now_iso = datetime.now().isoformat(timespec="seconds")
            updates_a["updated_at"] = now_iso
            updates_b["updated_at"] = now_iso
        seta = ", ".join([f"{k} = ?" for k in updates_a.keys()])
        setb = ", ".join([f"{k} = ?" for k in updates_b.keys()])
        cursor.execute(f"UPDATE groups SET {seta} WHERE id = ?", tuple(updates_a.values()) + (ida,))
        cursor.execute(f"UPDATE groups SET {setb} WHERE id = ?", tuple(updates_b.values()) + (idb,))
        db_conn.commit(); cursor.close(); db_conn.close()
        return jsonify({"success": True, "message": "Employees swapped", "data": {"group_a": {'members': mema, 'distance_km_estimate': da}, 'group_b': {'members': memb, 'distance_km_estimate': db}}}), 200
    except Exception as e:
        logger.error(f"Failed to swap employees: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Internal error"}), 500
