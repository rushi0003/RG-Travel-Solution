# backend/routes/employee_routes.py
from __future__ import annotations

from flask import Blueprint, request, g
from datetime import datetime, date, timedelta

from db import get_db
from utils.response import ok, fail
from services.validation_service import (
    require_int,
    require_str,
    validate_mobile10,
    validate_employee_code,
    validate_time_hhmm,
    validate_lat_lng,
    validate_route_no_10,
)
from services.otp_service import (
    get_or_create_trip_otp_for_employee,
)
from services.tracking_service import (
    get_assigned_driver_location_by_trip,
)
from services.nominatim_geocoding_service import geocode_address_nominatim
from services.trip_schedule_guard import (
    evaluate_trip_start_gate,
    derive_pickup_timing,
    build_pickup_time_note,
)
from services.trip_history_service import list_trip_history
from services.absence_flow_service import (
    AbsenceFlowError,
    create_absence_request,
    create_cancel_request,
    list_employee_requests,
    normalize_request_dates,
)
from utils.security import require_auth

employee_bp = Blueprint("employee_bp", __name__, url_prefix="/api/employee")

# -------------------------------------------------------------------
# DB SCHEMA ASSUMPTIONS (EDIT IF YOUR TABLES DIFFER)
# -------------------------------------------------------------------
# employees:
#   id, name, mobile, employee_code, login_time, logout_time,
#   home_address, home_lat, home_lng, is_approved, created_at
#
# admins:
#   id, name, mobile, office_name, office_address, office_lat, office_lng
#
# employee_change_requests (optional but recommended):
#   id, employee_id, payload_json, status(pending/approved/rejected), reason, created_at
#
# employee_absence_requests:
#   id, employee_id, absent_date, reason, status(pending/approved/rejected), created_at
#
# trips:
#   id, route_no, trip_type(pickup/drop), trip_date, trip_time,
#   status(created/assigned/in_progress/completed/cancelled),
#   driver_id, vehicle_no, vehicle_type, total_km, created_at, updated_at
#
# trip_members:
#   id, trip_id, employee_id, pickup_order, status(assigned/no_show/absent), created_at
#
# drivers:
#   id, name, mobile, dl_no, vehicle_no, vehicle_type, hometown, is_approved
#
# gps_latest (or driver_locations):
#   id, driver_id, trip_id, lat, lng, speed, heading, updated_at
# -------------------------------------------------------------------


def _parse_office_location_text(raw: object):
    try:
        text = str(raw or "").strip()
        if not text:
            return None, None
        lat_s, lng_s = text.split(",", 1)
        return float(lat_s.strip()), float(lng_s.strip())
    except Exception:
        return None, None


def _fetch_admin_office_context(cur, admin_id=None):
    cur.execute("PRAGMA table_info(admins)")
    admin_cols = {str(r[1]) for r in cur.fetchall()}

    select_cols = []
    if "office_lat" in admin_cols:
        select_cols.append("office_lat")
    if "office_lng" in admin_cols:
        select_cols.append("office_lng")
    if "office_location" in admin_cols:
        select_cols.append("office_location")
    if "office_address" in admin_cols:
        select_cols.append("office_address")
    if "office_name" in admin_cols:
        select_cols.append("office_name")
    if not select_cols:
        return None

    row = None
    if admin_id is not None:
        cur.execute(
            f"SELECT {', '.join(select_cols)} FROM admins WHERE id = ? LIMIT 1",
            (admin_id,),
        )
        row = cur.fetchone()

    if not row:
        cur.execute(
            f"SELECT {', '.join(select_cols)} FROM admins ORDER BY created_at ASC LIMIT 1"
        )
        row = cur.fetchone()

    if not row:
        return None

    row_map = {col: row[idx] for idx, col in enumerate(select_cols)}
    office_address = str(
        row_map.get("office_address")
        or row_map.get("office_name")
        or row_map.get("office_location")
        or ""
    ).strip()
    office_location = str(row_map.get("office_location") or "").strip()
    lat_raw = row_map.get("office_lat")
    lng_raw = row_map.get("office_lng")

    lat = None
    lng = None
    try:
        if lat_raw is not None and lng_raw is not None:
            lat_val = float(lat_raw)
            lng_val = float(lng_raw)
            if abs(lat_val) > 0.000001 and abs(lng_val) > 0.000001:
                lat, lng = lat_val, lng_val
    except Exception:
        lat, lng = None, None

    if lat is None or lng is None:
        p_lat, p_lng = _parse_office_location_text(office_location)
        lat = lat if lat is not None else p_lat
        lng = lng if lng is not None else p_lng

    return {
        "office_lat": float(lat) if lat is not None else None,
        "office_lng": float(lng) if lng is not None else None,
        "office_address": office_address,
        "office_location": office_location,
    }


def _get_employee_admin_id(cur, employee_id: int):
    cur.execute("PRAGMA table_info(employees)")
    employee_cols = {str(r[1]) for r in cur.fetchall()}
    if "admin_id" not in employee_cols:
        return None
    cur.execute(
        """
        SELECT admin_id
        FROM employees
        WHERE id = ?
        LIMIT 1
        """,
        (employee_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    admin_id = str(row["admin_id"] or "").strip()
    return admin_id or None


def _ensure_employee_identity(employee_id: int):
    current_user_id = str(getattr(g, "user_id", "") or "").strip()
    if current_user_id != str(employee_id):
        return fail("Forbidden for this employee.", 403)
    return None


def _resolve_trip_duration_minutes(cur, trip_id: int, fallback_total_km=None) -> int:
    # Prefer persisted route duration, fallback to total_km approximation (2 min per km).
    try:
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


def _build_driver_snapshot(
    driver_id=None,
    name=None,
    mobile=None,
    cab_no=None,
    role="current",
):
    return {
        "id": "" if driver_id is None else str(driver_id),
        "name": str(name or "").strip(),
        "mobile": str(mobile or "").strip(),
        "cab_no": str(cab_no or "").strip(),
        "role": role,
    }


def _attach_emergency_swap_context(cur, trip_data):
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

    swap = dict(row)
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


# =========================================================
# EMPLOYEE PROFILE
# =========================================================
@employee_bp.get("/<employee_id>/profile")
@require_auth(roles=["employee"])
def get_employee_profile(employee_id: str):
    emp_id = require_int(employee_id, "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id, name, mobile, employee_code,
            login_time, logout_time,
            home_address, home_lat, home_lng, admin_id,
            is_approved
        FROM employees
        WHERE id = ?
        """,
        (emp_id,),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return fail("Employee not found", 404)

    profile = dict(row)
    office_ctx = _fetch_admin_office_context(cur, profile.get("admin_id"))
    if office_ctx:
        profile["office_lat"] = office_ctx.get("office_lat")
        profile["office_lng"] = office_ctx.get("office_lng")
        profile["office_address"] = office_ctx.get("office_address")
        profile["office_location"] = office_ctx.get("office_location")

    conn.close()
    return ok(profile)


@employee_bp.put("/<employee_id>/profile")
@employee_bp.post("/<employee_id>/profile-change-request")
@require_auth(roles=["employee"])
def request_employee_profile_update(employee_id: str):
    """
    Employee profile update should go as REQUEST (admin approves).
    This endpoint creates a "change request" record.
    If you want direct update for dev, pass ?direct=true (NOT recommended).
    """
    emp_id = require_int(employee_id, "employee_id")
    data = request.json or {}
    direct = (request.args.get("direct") or "").lower() == "true"

    name = data.get("name")
    mobile = data.get("mobile")
    login_time = data.get("login_time")
    logout_time = data.get("logout_time")
    home_address = data.get("home_address")
    home_lat = data.get("home_lat")
    home_lng = data.get("home_lng")
    reason = data.get("reason", "")  # optional

    # validations (only validate if field exists)
    if mobile is not None and not validate_mobile10(str(mobile)):
        return fail("Mobile must be exactly 10 digits", 400)

    if login_time is not None and not validate_time_hhmm(str(login_time)):
        return fail("login_time must be HH:MM (24h)", 400)

    if logout_time is not None and not validate_time_hhmm(str(logout_time)):
        return fail("logout_time must be HH:MM (24h)", 400)

    if (home_lat is not None) or (home_lng is not None):
        if not validate_lat_lng(home_lat, home_lng):
            return fail("home_lat/home_lng invalid", 400)

    conn = get_db()
    cur = conn.cursor()

    # ensure employee exists
    cur.execute("SELECT id FROM employees WHERE id = ?", (emp_id,))
    if not cur.fetchone():
        conn.close()
        return fail("Employee not found", 404)

    resolved_home_lat = home_lat
    resolved_home_lng = home_lng
    clean_home_address = str(home_address or "").strip()
    if clean_home_address:
        geo = geocode_address_nominatim(clean_home_address, conn=conn, use_cache=True)
        if geo.get("success") is True:
            g = geo.get("data") or {}
            resolved_home_lat = g.get("lat")
            resolved_home_lng = g.get("lng")
        elif direct and not ((home_lat is not None) and (home_lng is not None)):
            conn.close()
            return fail("Unable to geocode home_address into coordinates", 400)

    # DEV DIRECT UPDATE (optional)
    if direct:
        cur.execute(
            """
            UPDATE employees
            SET
                name = COALESCE(?, name),
                mobile = COALESCE(?, mobile),
                login_time = COALESCE(?, login_time),
                logout_time = COALESCE(?, logout_time),
                home_address = COALESCE(?, home_address),
                home_lat = COALESCE(?, home_lat),
                home_lng = COALESCE(?, home_lng)
            WHERE id = ?
            """,
            (name, mobile, login_time, logout_time, home_address, resolved_home_lat, resolved_home_lng, emp_id),
        )
        conn.commit()
        conn.close()
        return ok({"message": "Profile updated (direct mode)"})

    # create change request (admin approval)
    # store payload as JSON string for simplicity
    import json
    payload = {
        "name": name,
        "mobile": mobile,
        "login_time": login_time,
        "logout_time": logout_time,
        "home_address": home_address,
        "home_lat": home_lat,
        "home_lng": home_lng,
    }
    cur.execute("PRAGMA table_info(employee_change_requests)")
    req_cols = {str(r[1]) for r in cur.fetchall()}
    if "home_lat" in req_cols and "home_lng" in req_cols:
        cur.execute(
            """
            INSERT INTO employee_change_requests
            (employee_id, name, mobile, home_address, home_lat, home_lng, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (emp_id, name, mobile, home_address, resolved_home_lat, resolved_home_lng, datetime.utcnow().isoformat()),
        )
    else:
        cur.execute(
            """
            INSERT INTO employee_change_requests (employee_id, name, mobile, home_address, status, created_at)
            VALUES (?, ?, ?, ?, 'Pending', ?)
            """,
            (emp_id, name, mobile, home_address, datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()
    return ok({"message": "Profile update request submitted (pending admin approval)"})


# =========================================================
# ABSENT REQUEST (must be >= 1 day before)
# =========================================================
@employee_bp.post("/<employee_id>/absent-request")
@employee_bp.post("/<employee_id>/absent/request")
@require_auth(roles=["employee"])
def create_absent_request(employee_id: str):
    emp_id = require_int(employee_id, "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    data = request.json or {}

    conn = get_db()
    try:
        created = create_absence_request(
            conn,
            emp_id,
            normalize_request_dates(data),
            reason=str(data.get("reason") or "").strip(),
        )
        return ok(
            {
                "message": "Absent request submitted (pending admin approval)",
                "request": created,
            }
        )
    except AbsenceFlowError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 409 if "already exists" in message.lower() else 400
        return fail(message, status)
    finally:
        conn.close()


@employee_bp.get("/<employee_id>/absence-requests")
@require_auth(roles=["employee"])
def list_my_absence_requests(employee_id: str):
    emp_id = require_int(employee_id, "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    conn = get_db()
    try:
        return ok(list_employee_requests(conn, emp_id))
    finally:
        conn.close()


@employee_bp.post("/<employee_id>/absence-cancel-request")
@require_auth(roles=["employee"])
def request_absence_cancel(employee_id: str):
    emp_id = require_int(employee_id, "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    data = request.json or {}
    conn = get_db()
    try:
        created = create_cancel_request(
            conn,
            emp_id,
            normalize_request_dates(data),
            reason=str(data.get("reason") or "").strip(),
        )
        return ok(
            {
                "message": "Absence cancellation request submitted (pending admin approval)",
                "request": created,
            }
        )
    except AbsenceFlowError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 409 if "already exists" in message.lower() else 400
        return fail(message, status)
    finally:
        conn.close()


# =========================================================
# MY TRIP (pickup/drop) + DRIVER INFO
# =========================================================
@employee_bp.get("/<employee_id>/my-trip")
@require_auth(roles=["employee"])
def get_my_trip(employee_id: str):
    """
    Returns employee's active/assigned trip for a given date and type.
    Query:
      - trip_type=pickup|drop (optional)
      - trip_date=YYYY-MM-DD (optional; default today)
    """
    emp_id = require_int(employee_id, "employee_id")

    trip_type = (request.args.get("trip_type") or "").strip().lower()
    if trip_type and trip_type not in ("pickup", "drop"):
        return fail("trip_type must be pickup or drop", 400)

    requested_trip_date = request.args.get("trip_date")
    trip_date = requested_trip_date or date.today().isoformat()
    try:
        datetime.strptime(trip_date, "%Y-%m-%d")
    except Exception:
        return fail("trip_date must be YYYY-MM-DD", 400)
    trip_day = trip_date.replace("-", "")

    conn = get_db()
    cur = conn.cursor()
    employee_admin_id = _get_employee_admin_id(cur, emp_id)
    cur.execute("PRAGMA table_info(trips)")
    trip_cols = {str(r[1]) for r in cur.fetchall()}
    cur.execute("PRAGMA table_info(trip_employees)")
    te_cols = {str(r[1]) for r in cur.fetchall()}
    no_show_sql = "tm.is_no_show" if "is_no_show" in te_cols else ("tm.no_show" if "no_show" in te_cols else "0")
    office_lat_sql = "t.office_lat AS office_lat" if "office_lat" in trip_cols else "NULL AS office_lat"
    office_lng_sql = "t.office_lng AS office_lng" if "office_lng" in trip_cols else "NULL AS office_lng"
    admin_id_sql = "t.admin_id AS admin_id" if "admin_id" in trip_cols else "NULL AS admin_id"

    # Find latest relevant trip where employee is member.
    base_sql = f"""
        SELECT
            t.id AS trip_id,
            t.route_no,
            t.trip_type,
            t.trip_day AS trip_date,
            t.schedule_time,
            t.status,
            d.vehicle_no,
            t.vehicle_type,
            t.total_km,
            d.id AS driver_id,
            d.name AS driver_name,
            d.mobile AS driver_mobile,
            {no_show_sql} AS is_no_show,
            {office_lat_sql},
            {office_lng_sql},
            {admin_id_sql}
        FROM trip_employees tm
        JOIN trips t ON t.id = tm.trip_id
        LEFT JOIN drivers d ON d.id = t.driver_id
        WHERE tm.employee_id = ?
          AND t.status IN ('assigned', 'started', 'created', 'active', 'in_progress', 'live')
    """
    base_params = [emp_id]
    if employee_admin_id and "admin_id" in trip_cols:
        base_sql += " AND CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)"
        base_params.append(employee_admin_id)

    date_filter_sql = " AND t.trip_day = ? "
    trip_type_sql = ""
    if trip_type:
        trip_type_sql = " AND t.trip_type = ? "

    sql = f"{base_sql}{date_filter_sql}{trip_type_sql} ORDER BY t.id DESC LIMIT 1"
    cur.execute(sql, tuple(base_params + [trip_day] + ([trip_type] if trip_type else [])))
    trip = cur.fetchone()

    # If dashboard did not request an explicit date and no trip exists for today,
    # surface the next upcoming assigned/pre-assigned trip so employee sees it.
    if not trip and not requested_trip_date:
        upcoming_sql = (
            f"{base_sql} AND t.trip_day >= ? {trip_type_sql} "
            "ORDER BY t.trip_day ASC, t.schedule_time ASC, t.id DESC LIMIT 1"
        )
        upcoming_params = list(base_params) + [trip_day]
        if trip_type:
            upcoming_params.append(trip_type)
        cur.execute(upcoming_sql, tuple(upcoming_params))
        trip = cur.fetchone()

    if not trip:
        conn.close()
        return ok({"has_trip": False, "message": "No active trip found for this date."})

    trip_data = dict(trip)
    is_no_show = int(trip_data.get("is_no_show") or 0) == 1
    trip_data["member_status"] = "no_show" if is_no_show else "assigned"
    if is_no_show:
        # Member no-show is employee-specific, so expose it in status for dashboard consistency.
        trip_data["status"] = "no_show"
    office_ctx = _fetch_admin_office_context(cur, trip_data.get("admin_id"))
    if office_ctx:
        trip_data["office_lat"] = office_ctx.get("office_lat")
        trip_data["office_lng"] = office_ctx.get("office_lng")
        trip_data["office_address"] = office_ctx.get("office_address")
        trip_data["office_location"] = office_ctx.get("office_location")
    trip_mode = str(trip_data.get("trip_type") or "").strip().lower()
    travel_min = _resolve_trip_duration_minutes(cur, int(trip_data.get("trip_id") or 0), trip_data.get("total_km"))
    timing_meta = derive_pickup_timing(
        trip_data.get("schedule_time"),
        travel_min,
        extra_buffer_minutes=0,
    ) if trip_mode == "pickup" else {
        "login_time": str(trip_data.get("schedule_time") or ""),
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
    trip_data["pickup_time_note"] = build_pickup_time_note(timing_meta) if trip_mode == "pickup" else ""
    gate = evaluate_trip_start_gate(
        trip_data.get("trip_date"),
        trip_data.get("schedule_time"),
        trip_type=trip_mode,
        route_duration_minutes=travel_min,
    )
    trip_data["can_start_now"] = bool(gate.get("can_start_now", True))
    trip_data["is_preassigned"] = bool(gate.get("is_preassigned", False))
    trip_data["start_allowed_after"] = gate.get("start_allowed_after")
    trip_data["seconds_until_start"] = int(gate.get("seconds_until_start", 0) or 0)
    trip_data["server_now"] = gate.get("server_now")
    trip_data = _attach_emergency_swap_context(cur, trip_data)

    # Fetch members list (so employee can see group)
    cur.execute(
        """
        SELECT
            e.id AS employee_id,
            e.name,
            e.mobile,
            e.home_address,
            tm.sequence_no as pickup_order,
            {no_show_sql} AS is_no_show
        FROM trip_employees tm
        JOIN employees e ON e.id = tm.employee_id
        WHERE tm.trip_id = ?
        ORDER BY tm.sequence_no ASC, e.name ASC
        """.format(no_show_sql=no_show_sql),
        (trip["trip_id"],),
    )
    members = [dict(r) for r in cur.fetchall()]

    conn.close()
    return ok(
        {
            "has_trip": True,
            "trip": trip_data,
            "members": members,
        }
    )


# =========================================================
# EMPLOYEE TRIP HISTORY
# =========================================================
@employee_bp.get("/<employee_id>/trip-history")
@require_auth(roles=["employee"])
def get_employee_trip_history(employee_id: str):
    emp_id = require_int(employee_id, "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    search = (request.args.get("search") or request.args.get("q") or "").strip().lower()
    from_date = (request.args.get("from") or "").strip()
    to_date = (request.args.get("to") or "").strip()
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    conn = get_db()
    cur = conn.cursor()
    employee_admin_id = _get_employee_admin_id(cur, emp_id)
    rows, _ = list_trip_history(
        conn,
        viewer_employee_id=emp_id,
        admin_id=employee_admin_id,
        search=search,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    conn.close()
    return ok(rows)


# =========================================================
# LIVE TRACKING VIEW (EMPLOYEE)
# =========================================================
@employee_bp.get("/trips/<route_no>/driver-location")
@require_auth(roles=["employee"])
def employee_view_driver_location(route_no: str):
    """
    Employee can view driver location for a trip ONLY if employee is member.
    Query:
      - employee_id=...
    """
    route_no = require_str(route_no, "route_no")
    if not validate_route_no_10(route_no):
        return fail("Invalid route_no format (must be 10 chars).", 400)

    employee_id = require_int(request.args.get("employee_id"), "employee_id")
    auth_error = _ensure_employee_identity(employee_id)
    if auth_error:
        return auth_error

    conn = get_db()
    cur = conn.cursor()

    # verify membership
    cur.execute(
        """
        SELECT t.id AS trip_id
        FROM trips t
        JOIN trip_employees tm ON tm.trip_id = t.id
        WHERE t.route_no = ? AND tm.employee_id = ?
        LIMIT 1
        """,
        (route_no, employee_id),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return fail("Not allowed: employee is not a member of this trip.", 403)

    # fetch latest location via service using current DB connection
    loc_resp = get_assigned_driver_location_by_trip(conn, int(row["trip_id"]))
    conn.close()
    if not loc_resp.get("success"):
        return ok({"has_location": False, "message": loc_resp.get("message", "Driver location not available yet.")})

    return ok({"has_location": True, "location": loc_resp.get("data")})


# =========================================================
# OTP VIEW (EMPLOYEE) - Employee sees OTP, Driver verifies OTP
# =========================================================
@employee_bp.get("/trips/<route_no>/otp")
@require_auth(roles=["employee"])
def employee_get_trip_otp(route_no: str):
    """
    Employee requests OTP for start/end.
    Query:
      - employee_id=...
      - type=start|end
    Rules:
      - OTP visible only to trip members
      - OTP valid till expiry
      - Driver will verify OTP via driver API
    """
    route_no = require_str(route_no, "route_no")
    if not validate_route_no_10(route_no):
        return fail("Invalid route_no format (must be 10 chars).", 400)

    employee_id = require_int(request.args.get("employee_id"), "employee_id")
    auth_error = _ensure_employee_identity(employee_id)
    if auth_error:
        return auth_error
    otp_type = (request.args.get("type") or "").strip().lower()
    if otp_type not in ("start", "end"):
        return fail("type must be start or end", 400)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(trip_employees)")
    te_cols = {str(r[1]) for r in cur.fetchall()}
    no_show_sql = "tm.is_no_show" if "is_no_show" in te_cols else ("tm.no_show" if "no_show" in te_cols else "0")

    # verify membership + get trip_id
    cur.execute(
        """
        SELECT t.id AS trip_id, t.status, {no_show_sql} AS is_no_show
        FROM trips t
        JOIN trip_employees tm ON tm.trip_id = t.id
        WHERE t.route_no = ? AND tm.employee_id = ?
        LIMIT 1
        """.format(no_show_sql=no_show_sql),
        (route_no, employee_id),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return fail("Not allowed: employee is not a member of this trip.", 403)

    # business rule: allow otp even if assigned/in_progress; block completed
    if row["status"] in ("completed", "cancelled"):
        conn.close()
        return fail("Trip already completed/cancelled. OTP not available.", 400)
    if int(row["is_no_show"] or 0) == 1:
        conn.close()
        return fail("You are marked as no-show for this trip.", 403)

    otp_payload = get_or_create_trip_otp_for_employee(
        conn,
        trip_id=int(row["trip_id"]),
        otp_type=otp_type,
        employee_id=str(employee_id),
    )
    conn.close()
    if not otp_payload.get("success"):
        return fail(otp_payload.get("message", "OTP not available"), 400)
    return ok(otp_payload.get("data"))


# =========================================================
# OFFICE LOCATION (from Admin profile)
# =========================================================
@employee_bp.get("/office-location")
@require_auth(roles=["employee"])
def get_office_location():
    """
    Employee dashboard needs Office Location (admin profile).
    Query:
      - admin_id=...
    """
    admin_id = require_str(request.args.get("admin_id"), "admin_id")

    conn = get_db()
    cur = conn.cursor()
    current_employee_id = require_int(getattr(g, "user_id", None), "employee_id")
    employee_admin_id = _get_employee_admin_id(cur, current_employee_id)
    if employee_admin_id and str(employee_admin_id) != str(admin_id):
        conn.close()
        return fail("Forbidden for this admin.", 403)
    cur.execute(
        """
        SELECT id, office_name, office_address, office_lat, office_lng
        FROM admins
        WHERE id = ?
        """,
        (admin_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return fail("Admin not found", 404)

    return ok(dict(row))


# =========================================================
# SOS / EMERGENCY
# =========================================================
@employee_bp.post("/sos")
@require_auth(roles=["employee"])
def trigger_sos():
    """
    Employee triggers emergency alert.
    Payload:
      - employee_id
      - trip_id (optional, if on active trip)
      - lat, lng
    """
    data = request.json or {}
    emp_id = require_int(data.get("employee_id"), "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    trip_id = data.get("trip_id")
    lat = data.get("lat")
    lng = data.get("lng")
    
    # Validation
    if trip_id is not None:
        try:
            trip_id = int(trip_id)
        except ValueError:
            return fail("trip_id must be integer", 400)
            
    if (lat is not None) and (lng is not None):
        if not validate_lat_lng(lat, lng):
             return fail("Invalid lat/lng", 400)

    conn = get_db()
    cur = conn.cursor()
    
    # Store alert
    try:
        cur.execute(
            """
            INSERT INTO sos_alerts (trip_id, employee_id, lat, lng, resolved, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (trip_id, emp_id, lat, lng, datetime.utcnow().isoformat())
        )
        alert_id = cur.lastrowid
        conn.commit()
        return ok({"alert_id": alert_id}, "SOS Alert Triggered! Admin notified.")
    except Exception as e:
        return fail(f"Failed to trigger SOS: {e}", 500)
    finally:
        conn.close()


# =========================================================
# TRIP RATING
# =========================================================
@employee_bp.post("/trip/<int:trip_id>/rate")
@require_auth(roles=["employee"])
def rate_trip(trip_id: int):
    """
    Rate a completed trip.
    Payload:
      - employee_id
      - rating (1-5)
      - feedback (text)
    """
    data = request.json or {}
    emp_id = require_int(data.get("employee_id"), "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    rating = data.get("rating")
    feedback = data.get("feedback", "")
    
    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError()
    except Exception:
         return fail("rating must be integer 1-5", 400)

    conn = get_db()
    cur = conn.cursor()
    
    # Check if already rated
    cur.execute(
        "SELECT id FROM trip_ratings WHERE trip_id=? AND employee_id=?", 
        (trip_id, emp_id)
    )
    if cur.fetchone():
        conn.close()
        return fail("You have already rated this trip.", 409)

    # Insert
    try:
        cur.execute(
            """
            INSERT INTO trip_ratings (trip_id, employee_id, rating, feedback, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (trip_id, emp_id, rating, feedback, datetime.utcnow().isoformat())
        )
        conn.commit()
        return ok({}, "Thank you for your feedback!")
    except Exception as e:
        return fail(f"Failed to submit rating: {e}", 500)
    finally:
        conn.close()


# =========================================================
# HELPDESK
# =========================================================
@employee_bp.post("/<int:employee_id>/helpdesk")
@require_auth(roles=["employee"])
def create_employee_helpdesk_ticket(employee_id: int):
    """
    Employee creates a helpdesk ticket.
    Payload: { subject, message, priority }
    """
    data = request.json or {}
    auth_error = _ensure_employee_identity(employee_id)
    if auth_error:
        return auth_error
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()
    priority = (data.get("priority") or "normal").strip().lower()

    if not subject or not message:
        return fail("Subject and message are required", 400)

    conn = get_db()
    cur = conn.cursor()

    # ensure employee exists
    cur.execute("SELECT id FROM employees WHERE id = ?", (employee_id,))
    if not cur.fetchone():
        conn.close()
        return fail("Employee not found", 404)

    try:
        cur.execute(
            """
            INSERT INTO helpdesk_tickets (user_id, user_type, subject, message, priority, status, created_at, updated_at)
            VALUES (?, 'employee', ?, ?, ?, 'open', ?, ?)
            """,
            (str(employee_id), subject, message, priority, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        conn.commit()
        ticket_id = cur.lastrowid
        return ok({"ticket_id": ticket_id}, "Helpdesk ticket created successfully.")
    except Exception as e:
        return fail(f"Failed to create ticket: {e}", 500)
    finally:
        conn.close()


@employee_bp.get("/<employee_id>/my-trips")
@require_auth(roles=["employee"])
def get_my_trips(employee_id: str):
    """
    Get ALL active assigned trips for employee.
    Used for dashboard list + polling fallback if sockets fail.
    Query:
        - date=YYYY-MM-DD (optional; if omitted returns all active trips)
    """
    emp_id = require_int(employee_id, "employee_id")
    auth_error = _ensure_employee_identity(emp_id)
    if auth_error:
        return auth_error
    trip_date = (request.args.get("date") or "").strip()
    trip_day = trip_date.replace("-", "") if trip_date else ""
    
    conn = get_db()
    cur = conn.cursor()
    employee_admin_id = _get_employee_admin_id(cur, emp_id)
    cur.execute("PRAGMA table_info(trips)")
    trip_cols = {str(r[1]) for r in cur.fetchall()}

    # Fetch all active trips, optionally filtered to one date.
    sql = """
        SELECT
            t.id AS trip_id,
            t.route_no,
            t.trip_type,
            t.trip_day AS trip_date,
            t.schedule_time,
            t.status,
            t.total_km,
            t.vehicle_type,
            d.name AS driver_name,
            d.mobile AS driver_mobile,
            d.vehicle_no AS cab_no
        FROM trip_employees te
        JOIN trips t ON t.id = te.trip_id
        LEFT JOIN drivers d ON d.id = t.driver_id
        WHERE te.employee_id = ?
          AND t.status IN ('created', 'assigned', 'started', 'active', 'in_progress', 'live')
    """

    params = [emp_id]
    if employee_admin_id and "admin_id" in trip_cols:
        sql += " AND CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)"
        params.append(employee_admin_id)
    if trip_day:
        sql += " AND t.trip_day = ?"
        params.append(trip_day)

    sql += """
        ORDER BY t.trip_day ASC, t.schedule_time ASC, t.id ASC
    """
    
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    trips = []
    
    for row in rows:
        trip = dict(row)
        trip_mode = str(trip.get("trip_type") or "").strip().lower()
        travel_min = _resolve_trip_duration_minutes(cur, int(trip.get("trip_id") or 0), trip.get("total_km"))
        timing_meta = derive_pickup_timing(
            trip.get("schedule_time"),
            travel_min,
            extra_buffer_minutes=0,
        ) if trip_mode == "pickup" else {
            "login_time": str(trip.get("schedule_time") or ""),
            "pickup_time": None,
            "route_duration_minutes": travel_min,
            "extra_buffer_minutes": 0,
            "total_lead_minutes": travel_min,
            "day_offset": 0,
        }
        trip["login_time"] = timing_meta.get("login_time")
        trip["pickup_time"] = timing_meta.get("pickup_time")
        trip["travel_time_min"] = int(timing_meta.get("route_duration_minutes", travel_min) or 0)
        trip["extra_buffer_min"] = int(timing_meta.get("extra_buffer_minutes", 0) or 0)
        trip["total_travel_with_buffer_min"] = int(timing_meta.get("total_lead_minutes", travel_min) or 0)
        trip["pickup_day_offset"] = int(timing_meta.get("day_offset", 0) or 0)
        trip["pickup_time_note"] = build_pickup_time_note(timing_meta) if trip_mode == "pickup" else ""
        gate = evaluate_trip_start_gate(
            trip.get("trip_date"),
            trip.get("schedule_time"),
            trip_type=trip_mode,
            route_duration_minutes=travel_min,
        )
        trip["can_start_now"] = bool(gate.get("can_start_now", True))
        trip["is_preassigned"] = bool(gate.get("is_preassigned", False))
        trip["start_allowed_after"] = gate.get("start_allowed_after")
        trip["seconds_until_start"] = int(gate.get("seconds_until_start", 0) or 0)
        trip["server_now"] = gate.get("server_now")
        trip = _attach_emergency_swap_context(cur, trip)

        # Get stop details for this employee
        cur.execute(
            "SELECT sequence_no FROM trip_employees WHERE trip_id = ? AND employee_id = ?",
            (trip["trip_id"], emp_id),
        )
        stop = cur.fetchone()
        
        trip["my_stop"] = {
            "sequence": stop["sequence_no"] if stop else 0,
            "eta": ""
        }
        trips.append(trip)
        
    conn.close()
    return ok({"trips": trips})

