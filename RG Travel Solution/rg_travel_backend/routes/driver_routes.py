# backend/routes/driver_routes.py
# RG Travel Solution - Driver APIs (request/response only)
#
# Endpoints:
#   GET  /api/driver/profile/<driver_id>
#   PUT  /api/driver/profile/<driver_id>
#   POST /api/driver/profile/<driver_id>/change-request
#
#   GET  /api/driver/<driver_id>/assigned-trip
#   GET  /api/driver/<driver_id>/trip-history
#
#   POST /api/driver/<driver_id>/gps
#   GET  /api/driver/<driver_id>/gps/latest
#
#   POST /api/driver/<driver_id>/trip/<trip_id>/otp/verify   (start/end)
#   POST /api/driver/<driver_id>/trip/<trip_id>/no-show
#
#   POST /api/driver/<driver_id>/trip/<trip_id>/swap-request
#
# Notes:
# - This file only handles HTTP layer. Business logic is in services.
# - All responses return: { success: bool, message: str, data: any }

from flask import Blueprint, request, jsonify, g
from datetime import datetime

from db import get_db

from services.validation_service import (
    validate_mobile_10,
    validate_dl_number,
    validate_vehicle_no,
    validate_lat_lng,
    validate_route_no_optional,
)

from services.tracking_service import (
    api_update_location,
    api_get_driver_latest,
)

from services.otp_service import (
    verify_trip_otp_and_update,
    verify_employee_trip_otp,
    get_pending_employee_otp_ids,
)
from services.trip_lifecycle_service import mark_trip_completed, mark_member_no_show
from services.trip_schedule_guard import evaluate_trip_start_gate, derive_pickup_timing, build_pickup_time_note
from services.trip_history_service import list_trip_history
from utils.logger import log_trip_event
from utils.security import require_auth

driver_bp = Blueprint("driver_bp", __name__, url_prefix="/api/driver")


# -----------------------------
# Small response helpers
# -----------------------------
def ok(message="OK", data=None):
    return jsonify({"success": True, "message": message, "data": data})


def fail(message="Error", status=400, data=None):
    return jsonify({"success": False, "message": message, "data": data}), status


def _ensure_driver_identity(driver_id: str):
    current_user_id = str(getattr(g, "user_id", "") or "").strip()
    if current_user_id != str(driver_id):
        return fail("Forbidden for this driver.", 403)
    return None


def _resolve_driver_pk(cur, driver_ref: str):
    cur.execute("PRAGMA table_info(drivers)")
    cols = {str(r[1]) for r in cur.fetchall()}
    alias_predicate = ""
    params = [str(driver_ref)]
    if "driver_id" in cols:
        alias_predicate = " OR (driver_id IS NOT NULL AND CAST(driver_id AS TEXT) = ?)"
        params.append(str(driver_ref))
    cur.execute(
        f"""
        SELECT id
        FROM drivers
        WHERE CAST(id AS TEXT) = ?
           {alias_predicate}
        LIMIT 1
        """,
        tuple(params),
    )
    row = cur.fetchone()
    return row["id"] if row else None


def _driver_has_admin_access(cur, driver_id: str, admin_id: str) -> bool:
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


def _get_driver_selected_admin(cur, driver_id: str, requested_admin_id: str | None = None):
    req = str(requested_admin_id or "").strip()
    if req and _driver_has_admin_access(cur, driver_id, req):
        return req

    cur.execute("PRAGMA table_info(drivers)")
    cols = {str(r[1]) for r in cur.fetchall()}
    current_expr = "current_admin_id" if "current_admin_id" in cols else "NULL"
    primary_expr = "primary_admin_id" if "primary_admin_id" in cols else "NULL"
    cur.execute(
        f"""
        SELECT {current_expr} AS current_admin_id, {primary_expr} AS primary_admin_id
        FROM drivers
        WHERE CAST(id AS TEXT) = CAST(? AS TEXT)
        LIMIT 1
        """,
        (str(driver_id),),
    )
    row = cur.fetchone()
    if row:
        current_admin_id = str(row["current_admin_id"] or "").strip()
        if current_admin_id and _driver_has_admin_access(cur, driver_id, current_admin_id):
            return current_admin_id
        primary_admin_id = str(row["primary_admin_id"] or "").strip()
        if primary_admin_id and _driver_has_admin_access(cur, driver_id, primary_admin_id):
            return primary_admin_id

    cur.execute(
        """
        SELECT admin_id
        FROM driver_admin_assignments
        WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
          AND is_active = 1
        ORDER BY id ASC
        LIMIT 1
        """,
        (str(driver_id),),
    )
    row = cur.fetchone()
    return str(row["admin_id"]).strip() if row and row["admin_id"] is not None else None


def _set_driver_selected_admin(cur, driver_id: str, admin_id: str) -> None:
    cur.execute("PRAGMA table_info(drivers)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "current_admin_id" not in cols:
        return
    cur.execute(
        """
        UPDATE drivers
        SET current_admin_id = ?
        WHERE CAST(id AS TEXT) = CAST(? AS TEXT)
        """,
        (str(admin_id), str(driver_id)),
    )


def _driver_trip_join_sql(cur) -> str:
    cur.execute("PRAGMA table_info(drivers)")
    driver_cols = {str(r[1]) for r in cur.fetchall()}
    join_sql = "CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)"
    if "driver_id" in driver_cols:
        join_sql += " OR (d.driver_id IS NOT NULL AND CAST(d.driver_id AS TEXT) = CAST(t.driver_id AS TEXT))"
    return join_sql


def _resolve_driver_selected_admin(
    cur,
    driver_id: str,
    requested_admin_id: str | None = None,
    *,
    persist: bool = False,
):
    selected_admin_id = _get_driver_selected_admin(cur, driver_id, requested_admin_id)
    if persist and selected_admin_id:
        _set_driver_selected_admin(cur, driver_id, selected_admin_id)
    return selected_admin_id


def _get_driver_trip_row(
    cur,
    *,
    driver_id: str,
    trip_id: int,
    requested_admin_id: str | None = None,
    select_fields: str = "t.id",
):
    selected_admin_id = _resolve_driver_selected_admin(cur, driver_id, requested_admin_id)
    if not selected_admin_id:
        return None, None

    driver_join_sql = _driver_trip_join_sql(cur)
    cur.execute(
        f"""
        SELECT {select_fields}
        FROM trips t
        JOIN drivers d
          ON {driver_join_sql}
        WHERE t.id = ?
          AND d.id = ?
          AND CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)
        LIMIT 1
        """,
        (trip_id, driver_id, selected_admin_id),
    )
    return cur.fetchone(), selected_admin_id


def _list_driver_admin_companies(cur, driver_id: str):
    cur.execute(
        """
        SELECT
            daa.admin_id,
            a.name AS admin_name,
            a.office_name,
            a.office_address
        FROM driver_admin_assignments daa
        LEFT JOIN admins a
          ON CAST(a.id AS TEXT) = CAST(daa.admin_id AS TEXT)
        WHERE CAST(daa.driver_id AS TEXT) = CAST(? AS TEXT)
          AND daa.is_active = 1
        ORDER BY daa.id ASC
        """,
        (str(driver_id),),
    )
    return [
        {
            "admin_id": str(row["admin_id"]),
            "admin_name": str(row["admin_name"] or ""),
            "office_name": str(row["office_name"] or ""),
            "office_address": str(row["office_address"] or ""),
            "company_name": str(row["office_name"] or row["admin_name"] or ""),
        }
        for row in (cur.fetchall() or [])
        if row["admin_id"] is not None
    ]


def _has_trip_after_go_home_approval(cur, driver_id: str, approved_at: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM trips
        WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
          AND LOWER(COALESCE(status, 'created')) IN
              ('created','assigned','started','active','in_progress','live','completed')
          AND datetime(COALESCE(created_at, updated_at, '1970-01-01')) >= datetime(?)
        LIMIT 1
        """,
        (str(driver_id), str(approved_at or "1970-01-01")),
    )
    return cur.fetchone() is not None


def _expire_consumed_go_home_request(cur, driver_id: str) -> None:
    """Auto-expire approved go-home request after first trip assignment/use."""
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='driver_hometown_requests' LIMIT 1"
    )
    if not cur.fetchone():
        return

    cur.execute(
        """
        SELECT id, COALESCE(updated_at, created_at, '1970-01-01') AS approved_at
        FROM driver_hometown_requests
        WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
          AND status = 'approved'
        ORDER BY id DESC
        LIMIT 1
        """,
        (str(driver_id),),
    )
    req = cur.fetchone()
    if not req:
        return

    req_id = req["id"]
    approved_at = str(req["approved_at"] or "1970-01-01")
    if _has_trip_after_go_home_approval(cur, str(driver_id), approved_at):
        cur.execute(
            """
            UPDATE driver_hometown_requests
            SET status = 'rejected', updated_at = datetime('now')
            WHERE id = ?
            """,
            (req_id,),
        )


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
    lat_raw = row_map.get("office_lat")
    lng_raw = row_map.get("office_lng")

    try:
        if lat_raw is not None and lng_raw is not None:
            lat_val = float(lat_raw)
            lng_val = float(lng_raw)
            if abs(lat_val) > 0.000001 and abs(lng_val) > 0.000001:
                return {"lat": lat_val, "lng": lng_val, "address": office_address}
    except Exception:
        pass

    parsed_lat, parsed_lng = _parse_office_location_text(row_map.get("office_location"))
    if parsed_lat is not None and parsed_lng is not None:
        return {"lat": float(parsed_lat), "lng": float(parsed_lng), "address": office_address}
    return {"lat": None, "lng": None, "address": office_address}


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


def _ensure_temporary_driver_column(cur) -> bool:
    cur.execute("PRAGMA table_info(drivers)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "is_temporary" in cols:
        return True
    try:
        cur.execute("ALTER TABLE drivers ADD COLUMN is_temporary INTEGER DEFAULT 0")
        return True
    except Exception:
        return False


def _cleanup_temp_swap_driver(conn, trip_id: int) -> None:
    cur = conn.cursor()
    cur.execute("SELECT driver_id FROM trips WHERE id = ? LIMIT 1", (trip_id,))
    row = cur.fetchone()
    if not row:
        return
    driver_id = str((row["driver_id"] if "driver_id" in row.keys() else row[0]) or "").strip()
    if not driver_id:
        return

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
    d = cur.fetchone()
    if not d:
        return
    is_temp = int((d["is_temporary"] if "is_temporary" in d.keys() else d[0]) or 0) == 1
    dl_no = str((d["dl_no"] if "dl_no" in d.keys() else d[1]) or "").upper()
    if not is_temp and dl_no != "ADHOC_SWAP":
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
    active = cur.fetchone()
    active_count = int((active["c"] if "c" in active.keys() else active[0]) or 0)
    if active_count == 0:
        cur.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))


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


# =========================================================
# DRIVER PROFILE
# =========================================================
@driver_bp.route("/<driver_id>/companies", methods=["GET"])
@require_auth(roles=["driver"])
def get_driver_companies(driver_id: str):
    conn = get_db()
    cur = conn.cursor()
    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error

    companies = _list_driver_admin_companies(cur, str(resolved_id))
    selected_admin_id = _get_driver_selected_admin(
        cur,
        str(resolved_id),
        request.args.get("admin_id"),
    )
    if selected_admin_id:
        _set_driver_selected_admin(cur, str(resolved_id), selected_admin_id)
        conn.commit()
    conn.close()
    return ok(
        "Driver companies",
        {
            "companies": companies,
            "selected_admin_id": selected_admin_id,
        },
    )


@driver_bp.route("/<driver_id>/switch-company", methods=["POST"])
@require_auth(roles=["driver"])
def switch_driver_company(driver_id: str):
    data = request.get_json(silent=True) or {}
    target_admin_id = str(data.get("admin_id") or data.get("company_id") or "").strip()
    if not target_admin_id:
        return fail("admin_id is required", 400)

    conn = get_db()
    cur = conn.cursor()
    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error
    if not _driver_has_admin_access(cur, str(resolved_id), target_admin_id):
        conn.close()
        return fail("Driver is not linked to this company", 403)

    _set_driver_selected_admin(cur, str(resolved_id), target_admin_id)
    conn.commit()
    companies = _list_driver_admin_companies(cur, str(resolved_id))
    conn.close()
    return ok(
        "Company switched",
        {
            "selected_admin_id": target_admin_id,
            "companies": companies,
        },
    )


@driver_bp.route("/profile/<driver_id>", methods=["GET"])
@require_auth(roles=["driver"])
def get_driver_profile(driver_id: str):
    """
    Returns driver profile.
    """
    conn = get_db()
    cur = conn.cursor()

    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error
    cur.execute("PRAGMA table_info(drivers)")
    driver_cols = {str(r[1]) for r in cur.fetchall()}

    cab_col = "cab_no" if "cab_no" in driver_cols else ("vehicle_no" if "vehicle_no" in driver_cols else "NULL")
    hometown_col = "hometown" if "hometown" in driver_cols else ("home_town" if "home_town" in driver_cols else "NULL")
    home_address_col = "home_address" if "home_address" in driver_cols else hometown_col
    home_lat_col = "home_lat" if "home_lat" in driver_cols else ("hometown_lat" if "hometown_lat" in driver_cols else "NULL")
    home_lng_col = "home_lng" if "home_lng" in driver_cols else ("hometown_lng" if "hometown_lng" in driver_cols else "NULL")
    status_col = "status" if "status" in driver_cols else ("CASE WHEN is_approved = 1 THEN 'approved' ELSE 'pending' END")

    cur.execute(
        f"""
        SELECT id,
               name,
               mobile,
               dl_no,
               {cab_col} AS cab_no,
               vehicle_type,
               {hometown_col} AS hometown,
               {home_address_col} AS home_address,
               {home_lat_col} AS home_lat,
               {home_lng_col} AS home_lng,
               {status_col} AS status,
               created_at
        FROM drivers
        WHERE id = ?
        """,
        (resolved_id,),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return fail("Driver not found", 404)

    payload = dict(row)
    companies = _list_driver_admin_companies(cur, str(resolved_id))
    selected_admin_id = _get_driver_selected_admin(
        cur,
        str(resolved_id),
        request.args.get("admin_id"),
    )
    if selected_admin_id:
        _set_driver_selected_admin(cur, str(resolved_id), selected_admin_id)
        conn.commit()
    payload["companies"] = companies
    payload["selected_admin_id"] = selected_admin_id
    conn.close()

    return ok("Driver profile", payload)


@driver_bp.route("/profile/<driver_id>", methods=["PUT"])
@require_auth(roles=["driver"])
def update_driver_profile(driver_id: str):
    """
    Direct update (ONLY if your system allows).
    If you want strict admin approval, use change-request endpoint instead.
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    mobile = (data.get("mobile") or "").strip()
    dl_no = (data.get("dl_no") or "").strip().upper()
    cab_no = (data.get("cab_no") or "").strip().upper()
    vehicle_type = (data.get("vehicle_type") or "").strip().lower()  # "4" / "6" / "4seater" / "6seater"
    hometown = (data.get("hometown") or "").strip()
    home_lat = data.get("home_lat")
    home_lng = data.get("home_lng")

    if not name:
        return fail("Name is required")
    if not validate_mobile_10(mobile):
        return fail("Mobile must be exactly 10 digits")
    if dl_no and not validate_dl_number(dl_no):
        return fail("DL number format invalid (expected 2 letters + 13 digits)")
    if cab_no and not validate_vehicle_no(cab_no):
        return fail("Cab/Vehicle number format invalid (ex: MH12AB1234)")

    if vehicle_type not in ("", "4", "6", "4seater", "6seater"):
        return fail("vehicle_type must be 4 or 6")

    conn = get_db()
    cur = conn.cursor()

    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error

    cur.execute("PRAGMA table_info(drivers)")
    driver_cols = {str(r[1]) for r in cur.fetchall()}
    cab_col = "cab_no" if "cab_no" in driver_cols else "vehicle_no"
    hometown_col = "hometown" if "hometown" in driver_cols else "home_town"

    cur.execute(
        f"""
        UPDATE drivers
        SET name=?,
            mobile=?,
            dl_no=?,
            {cab_col}=?,
            vehicle_type=?,
            {hometown_col}=?
        WHERE id=?
        """,
        (name, mobile, dl_no, cab_no, vehicle_type, hometown, resolved_id),
    )

    conn.commit()
    conn.close()
    return ok("Driver profile updated")


@driver_bp.route("/profile/<driver_id>/change-request", methods=["POST"])
@require_auth(roles=["driver"])
def create_driver_change_request(driver_id: str):
    """
    Driver requests profile changes.
    Admin can approve/reject from admin_routes.
    """
    data = request.get_json(silent=True) or {}

    # optional fields
    name = (data.get("name") or "").strip()
    mobile = (data.get("mobile") or "").strip()
    dl_no = (data.get("dl_no") or "").strip().upper()
    cab_no = (data.get("cab_no") or "").strip().upper()
    hometown = (data.get("hometown") or "").strip()
    home_lat = data.get("home_lat")
    home_lng = data.get("home_lng")

    if mobile and not validate_mobile_10(mobile):
        return fail("Mobile must be exactly 10 digits")
    if dl_no and not validate_dl_number(dl_no):
        return fail("DL number format invalid")
    if cab_no and not validate_vehicle_no(cab_no):
        return fail("Vehicle number format invalid")
    if (home_lat is not None) or (home_lng is not None):
        if not validate_lat_lng(home_lat, home_lng):
            return fail("home_lat/home_lng invalid")

    conn = get_db()
    cur = conn.cursor()

    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error

    cur.execute("PRAGMA table_info(driver_change_requests)")
    req_cols = {str(r[1]) for r in cur.fetchall()}
    if (home_lat is not None or home_lng is not None) and not (("home_lat" in req_cols) and ("home_lng" in req_cols)):
        try:
            if "home_lat" not in req_cols:
                cur.execute("ALTER TABLE driver_change_requests ADD COLUMN home_lat REAL")
            if "home_lng" not in req_cols:
                cur.execute("ALTER TABLE driver_change_requests ADD COLUMN home_lng REAL")
            conn.commit()
            cur.execute("PRAGMA table_info(driver_change_requests)")
            req_cols = {str(r[1]) for r in cur.fetchall()}
        except Exception:
            pass
    if "home_lat" in req_cols and "home_lng" in req_cols:
        cur.execute(
            """
            INSERT INTO driver_change_requests (driver_id, name, mobile, dl_no, vehicle_no, home_town, home_lat, home_lng, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
            """,
            (
                resolved_id,
                name or None,
                mobile or None,
                dl_no or None,
                cab_no or None,
                hometown or None,
                home_lat,
                home_lng,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO driver_change_requests (driver_id, name, mobile, dl_no, vehicle_no, home_town, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
            """,
            (resolved_id, name or None, mobile or None, dl_no or None, cab_no or None, hometown or None),
        )
    conn.commit()
    req_id = cur.lastrowid
    conn.close()

    return ok("Change request submitted", {"request_id": req_id})


@driver_bp.route("/<driver_id>/hometown-request", methods=["POST"])
@driver_bp.route("/<driver_id>/hometown_request", methods=["POST"])
@require_auth(roles=["driver"])
def create_driver_hometown_request(driver_id: str):
    """
    Driver sends go-home/hometown priority request.
    Accepts both payload keys for backward compatibility:
    - requested_home_town
    - home_town
    - hometown
    """
    data = request.get_json(silent=True) or {}
    requested_home_town = (
        data.get("requested_home_town")
        or data.get("home_town")
        or data.get("home_address")
        or data.get("hometown")
        or ""
    ).strip()

    conn = get_db()
    cur = conn.cursor()
    try:
        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error

        cur.execute("PRAGMA table_info(drivers)")
        driver_cols = {str(r[1]) for r in cur.fetchall()}
        profile_home_col = (
            "home_address"
            if "home_address" in driver_cols
            else (
                "hometown"
                if "hometown" in driver_cols
                else ("home_town" if "home_town" in driver_cols else None)
            )
        )
        if not requested_home_town and profile_home_col:
            cur.execute(
                f"SELECT {profile_home_col} AS profile_home_address FROM drivers WHERE id = ?",
                (resolved_id,),
            )
            driver_row = cur.fetchone()
            requested_home_town = str(
                (driver_row["profile_home_address"] if driver_row else "") or ""
            ).strip()

        if not requested_home_town:
            return fail("Driver home address is required", 400)

        _expire_consumed_go_home_request(cur, str(resolved_id))
        cur.execute(
            """
            SELECT id, status
            FROM driver_hometown_requests
            WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
              AND status IN ('pending', 'approved')
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(resolved_id),),
        )
        open_req = cur.fetchone()
        if open_req:
            current = str(open_req["status"] or "").strip().lower()
            if current == "pending":
                return fail(
                    "Go-home request already pending. Wait for admin decision.",
                    409,
                )
            if current == "approved":
                return fail(
                    "Go-home request already approved and valid for one trip.",
                    409,
                )

        cur.execute("PRAGMA table_info(driver_hometown_requests)")
        cols = {str(r[1]) for r in cur.fetchall()}
        now = datetime.now().isoformat(timespec="seconds")

        if "travel_date" in cols:
            cur.execute(
                """
                INSERT INTO driver_hometown_requests
                (driver_id, requested_home_town, home_town, status, travel_date, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', date('now'), ?, ?)
                """,
                (str(resolved_id), requested_home_town, requested_home_town, now, now),
            )
        elif "home_town" in cols:
            cur.execute(
                """
                INSERT INTO driver_hometown_requests
                (driver_id, requested_home_town, home_town, status, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (str(resolved_id), requested_home_town, requested_home_town, now, now),
            )
        else:
            cur.execute(
                """
                INSERT INTO driver_hometown_requests
                (driver_id, requested_home_town, status, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?)
                """,
                (str(resolved_id), requested_home_town, now, now),
            )

        conn.commit()
        return ok(
            "Hometown request submitted",
            {
                "request_id": cur.lastrowid,
                "driver_id": resolved_id,
                "requested_home_town": requested_home_town,
                "home_address": requested_home_town,
                "status": "pending",
            },
        )
    finally:
        conn.close()


@driver_bp.route("/<driver_id>/hometown-request-status", methods=["GET"])
@driver_bp.route("/<driver_id>/hometown_request_status", methods=["GET"])
@require_auth(roles=["driver"])
def get_driver_hometown_request_status(driver_id: str):
    """
    Return latest hometown/go-home request status for this driver.
    Includes pending/approved/rejected so driver dashboard can auto-refresh status.
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error

        _expire_consumed_go_home_request(cur, str(resolved_id))
        conn.commit()

        cur.execute("PRAGMA table_info(driver_hometown_requests)")
        cols = {str(r[1]) for r in cur.fetchall()}
        requested_col = "requested_home_town" if "requested_home_town" in cols else "home_town"
        home_col = "home_town" if "home_town" in cols else requested_col
        travel_col = ", travel_date" if "travel_date" in cols else ""

        cur.execute(
            f"""
            SELECT id, driver_id, {requested_col} AS requested_home_town, {home_col} AS home_town,
                   status, created_at, updated_at{travel_col}
            FROM driver_hometown_requests
            WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(resolved_id),),
        )
        row = cur.fetchone()
        if not row:
            return ok("No hometown request found", None)
        payload = dict(row)
        payload["home_address"] = (
            payload.get("requested_home_town") or payload.get("home_town") or ""
        )
        return ok("Hometown request status", payload)
    finally:
        conn.close()


# =========================================================
# ASSIGNED TRIP (current active/in_progress)
# =========================================================
@driver_bp.route("/<driver_id>/assigned-trip", methods=["GET"])
@require_auth(roles=["driver"])
def get_assigned_trip(driver_id: str):
    """
    Returns driver's latest active trip:
    status in ('assigned', 'active', 'in_progress', 'started', 'live')
    """
    conn = get_db()
    cur = conn.cursor()
    requested_admin_id = request.args.get("admin_id")

    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return ok("No assigned trip", None)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error
    _expire_consumed_go_home_request(cur, str(resolved_id))
    selected_admin_id = _get_driver_selected_admin(cur, str(resolved_id), requested_admin_id)
    if selected_admin_id:
        _set_driver_selected_admin(cur, str(resolved_id), selected_admin_id)
    conn.commit()

    cur.execute("PRAGMA table_info(trips)")
    trip_cols = {str(r[1]) for r in cur.fetchall()}
    cur.execute("PRAGMA table_info(drivers)")
    driver_cols = {str(r[1]) for r in cur.fetchall()}
    office_lat_sql = "t.office_lat AS office_lat" if "office_lat" in trip_cols else "NULL AS office_lat"
    office_lng_sql = "t.office_lng AS office_lng" if "office_lng" in trip_cols else "NULL AS office_lng"
    admin_id_sql = "t.admin_id AS admin_id" if "admin_id" in trip_cols else "NULL AS admin_id"
    cab_sql = "COALESCE(t.vehicle_no, d.vehicle_no) AS cab_no" if "vehicle_no" in trip_cols else "d.vehicle_no AS cab_no"
    driver_join_sql = "CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)"
    if "driver_id" in driver_cols:
        driver_join_sql += " OR (d.driver_id IS NOT NULL AND CAST(d.driver_id AS TEXT) = CAST(t.driver_id AS TEXT))"

    # Keep trip visible to original driver even after emergency swap approval,
    # until trip is completed/cancelled.
    swap_visibility_sql = ""
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='swap_requests' LIMIT 1"
    )
    if cur.fetchone():
        swap_visibility_sql = """
          OR EXISTS (
              SELECT 1
              FROM swap_requests sr
              WHERE sr.trip_id = t.id
                AND CAST(sr.old_driver_id AS TEXT) = CAST(? AS TEXT)
                AND LOWER(COALESCE(sr.status, '')) = 'approved'
          )
        """

    cur.execute(
        f"""
        SELECT t.id, t.route_no, t.trip_type, t.operation, t.status, t.schedule_time, t.trip_day,
               t.total_km, t.polyline AS route_polyline,
               d.name AS driver_name, d.mobile AS driver_mobile, {cab_sql},
               {office_lat_sql}, {office_lng_sql}, {admin_id_sql}
        FROM trips t
        JOIN drivers d
          ON {driver_join_sql}
        WHERE (
              d.id = ?
              {swap_visibility_sql}
        )
          AND (? IS NULL OR CAST(COALESCE(t.admin_id, '') AS TEXT) = ?)
          AND t.status IN ('assigned','active','in_progress','started','live')
        ORDER BY t.id DESC
        LIMIT 1
        """,
        (resolved_id, resolved_id, selected_admin_id, selected_admin_id)
        if swap_visibility_sql
        else (resolved_id, selected_admin_id, selected_admin_id),
    )
    trip = cur.fetchone()
    if not trip:
        conn.close()
        return ok("No assigned trip", None)

    trip = dict(trip)
    trip_mode = str(trip.get("trip_type") or trip.get("operation") or "").strip().lower()
    travel_min = _resolve_trip_duration_minutes(cur, int(trip.get("id") or 0), trip.get("total_km"))
    gate = evaluate_trip_start_gate(
        trip.get("trip_day"),
        trip.get("schedule_time"),
        trip_type=trip_mode,
        route_duration_minutes=travel_min,
    )
    trip["can_start_now"] = bool(gate.get("can_start_now", True))
    trip["is_preassigned"] = bool(gate.get("is_preassigned", False))
    trip["start_allowed_after"] = gate.get("start_allowed_after")
    trip["seconds_until_start"] = int(gate.get("seconds_until_start", 0) or 0)
    trip["server_now"] = gate.get("server_now")
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
    resolved_office = _fetch_admin_office_context(cur, trip.get("admin_id"))
    if resolved_office:
        trip["office_address"] = resolved_office.get("address")
        if resolved_office.get("lat") is not None and resolved_office.get("lng") is not None:
            trip["office_lat"] = float(resolved_office["lat"])
            trip["office_lng"] = float(resolved_office["lng"])
        else:
            trip["office_lat"] = None
            trip["office_lng"] = None

    # employees in this trip
    cur.execute(
        """
        SELECT e.id, e.name, e.mobile, e.home_address AS address, te.is_no_show
        FROM trip_employees te
        JOIN employees e ON e.id = te.employee_id
        WHERE te.trip_id = ?
        ORDER BY te.sequence_no ASC
        """,
        (trip["id"],),
    )
    trip["employees"] = [dict(r) for r in cur.fetchall()]

    # OTP phase metadata for driver UI.
    trip_type = str(trip.get("trip_type") or trip.get("operation") or "").strip().lower()
    status = str(trip.get("status") or "").strip().lower()
    otp_required_type = ""
    if trip_type == "pickup" and status in ("assigned", "created", "active"):
        otp_required_type = "start"
    elif trip_type == "drop" and status in ("started", "in_progress", "live"):
        otp_required_type = "end"

    pending_ids = []
    verified_ids = set()
    if otp_required_type:
        gate = get_pending_employee_otp_ids(conn, trip_id=int(trip["id"]), otp_type=otp_required_type)
        pending_ids = ((gate.get("data") or {}).get("pending_employee_ids") or [])

        # Fetch verified employee ids for this OTP phase (employee-level tracking).
        cur.execute(
            """
            SELECT DISTINCT CAST(employee_id AS TEXT)
            FROM otp_audit_log
            WHERE trip_id = ?
              AND otp_type = ?
              AND action = 'verify_success'
              AND employee_id IS NOT NULL
            """,
            (int(trip["id"]), otp_required_type),
        )
        verified_ids = {str(r[0]) for r in cur.fetchall()}

    # Attach employee-level OTP status for strict frontend rendering.
    for emp in trip["employees"]:
        emp_id = str(emp.get("id") or emp.get("employee_id") or "").strip()
        no_show = bool(int(emp.get("is_no_show") or emp.get("no_show") or 0))
        otp_required = bool(otp_required_type) and not no_show
        otp_verified = otp_required and emp_id in verified_ids
        emp["otp_required"] = otp_required
        emp["otp_verified"] = otp_verified
        emp["otp_type_required"] = otp_required_type if otp_required else ""

    trip["otp_required_type"] = otp_required_type
    trip["otp_pending_employee_ids"] = pending_ids
    trip["otp_pending_count"] = len(pending_ids)
    try:
        _ensure_trip_cancel_requests_table(cur)
        cur.execute(
            """
            SELECT id, status, reason, admin_note, created_at, updated_at
            FROM trip_cancel_requests
            WHERE trip_id = ?
              AND CAST(driver_id AS TEXT) = CAST(? AS TEXT)
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(trip["id"]), str(resolved_id)),
        )
        latest_cancel_req = cur.fetchone()
        if latest_cancel_req:
            cancel_req = dict(latest_cancel_req)
            trip["cancel_request"] = cancel_req
            trip["cancel_request_status"] = str(cancel_req.get("status") or "").lower()
        else:
            trip["cancel_request"] = None
            trip["cancel_request_status"] = ""
    except Exception:
        trip["cancel_request"] = None
        trip["cancel_request_status"] = ""

    # Attach latest go-home request status so dashboards polling assigned-trip
    # can reflect pending/approved/rejected without relying on a second API call.
    try:
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='driver_hometown_requests' LIMIT 1"
        )
        if cur.fetchone():
            cur.execute("PRAGMA table_info(driver_hometown_requests)")
            req_cols = {str(r[1]) for r in cur.fetchall()}
            requested_col = "requested_home_town" if "requested_home_town" in req_cols else (
                "home_town" if "home_town" in req_cols else "NULL"
            )
            home_col = "home_town" if "home_town" in req_cols else requested_col
            travel_col = ", travel_date" if "travel_date" in req_cols else ""
            cur.execute(
                f"""
                SELECT id, status, {requested_col} AS requested_home_town, {home_col} AS home_town,
                       created_at, updated_at{travel_col}
                FROM driver_hometown_requests
                WHERE CAST(driver_id AS TEXT) = CAST(? AS TEXT)
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(resolved_id),),
            )
            req = cur.fetchone()
            if req:
                req_map = dict(req)
                trip["go_home_request"] = req_map
                trip["go_home_request_id"] = req_map.get("id")
                trip["go_home_request_status"] = req_map.get("status")
                trip["go_home_requested_home_town"] = req_map.get("requested_home_town") or req_map.get("home_town")
                trip["go_home_request_updated_at"] = req_map.get("updated_at") or req_map.get("created_at")
    except Exception:
        pass

    conn.close()
    return ok("Assigned trip", trip)


# =========================================================
# DRIVER TRIP HISTORY
# =========================================================
@driver_bp.route("/<driver_id>/trip-history", methods=["GET"])
@require_auth(roles=["driver"])
def driver_trip_history(driver_id: str):
    """
    List completed/cancelled trips for this driver.
    Supports query:
      ?search=... (route_no/cab_no/status/type)
      ?limit=50
    """
    search = (request.args.get("search") or request.args.get("q") or "").strip().lower()
    from_date = (request.args.get("from") or "").strip()
    to_date = (request.args.get("to") or "").strip()
    limit = request.args.get("limit") or "50"
    try:
        limit = max(1, min(200, int(limit)))
    except Exception:
        limit = 50

    conn = get_db()
    cur = conn.cursor()
    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return ok("Driver trip history", [])
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error
    selected_admin_id = _resolve_driver_selected_admin(
        cur,
        resolved_id,
        request.args.get("admin_id"),
    )
    if not selected_admin_id:
        conn.close()
        return ok("Driver trip history", [])
    rows, _ = list_trip_history(
        conn,
        viewer_driver_id=resolved_id,
        admin_id=selected_admin_id,
        search=search,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=0,
    )
    conn.close()

    return ok("Driver trip history", rows)


# =========================================================
# GPS UPDATE (LIVE TRACKING)
# =========================================================
@driver_bp.route("/<driver_id>/gps", methods=["POST"])
@require_auth(roles=["driver"])
def driver_gps_update(driver_id: str):
    """
    Driver sends GPS update every X seconds.
    Body: { "lat": 18.52, "lng": 73.85, "route_no": "...."(optional) }
    """
    data = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")
    route_no = (data.get("route_no") or "").strip()

    if not validate_lat_lng(lat, lng):
        return fail("Invalid lat/lng")

    if route_no and not validate_route_no_optional(route_no):
        return fail("Invalid route_no format")
    auth_error = _ensure_driver_identity(str(driver_id))
    if auth_error:
        return auth_error

    # store location in DB via tracking_service wrapper
    # lat and lng are guaranteed to be valid numbers after validate_lat_lng check
    try:
        lat_float = float(lat) if lat is not None else 0.0
        lng_float = float(lng) if lng is not None else 0.0
    except (ValueError, TypeError):
        return fail("Invalid lat/lng values")
    
    payload = {"driver_id": str(driver_id), "lat": lat_float, "lng": lng_float, "route_no": route_no or None}
    resp = api_update_location(payload)
    if not resp.get("success"):
        return fail(resp.get("message", "Failed to save location"), 500)
    return ok("Location updated", resp.get("data"))


@driver_bp.route("/<driver_id>/gps/latest", methods=["GET"])
@require_auth(roles=["driver"])
def driver_gps_latest(driver_id: str):
    """
    Returns driver's latest location.
    Used by driver app or debug.
    """
    auth_error = _ensure_driver_identity(str(driver_id))
    if auth_error:
        return auth_error
    resp = api_get_driver_latest(driver_id)
    if not resp.get("success"):
        return fail(resp.get("message", "No location found"), 404)
    return ok("Latest location", resp.get("data"))


# =========================================================
# OTP VERIFY (START / END)
# =========================================================
@driver_bp.route("/<driver_id>/trip/<int:trip_id>/otp/verify", methods=["POST"])
@require_auth(roles=["driver"])
def driver_verify_trip_otp(driver_id: str, trip_id: int):
    """
    Driver verifies OTP for:
      - start trip (otp_type="start")
      - end trip   (otp_type="end")
    Body:
      { "otp_type": "start"|"end", "otp": "123456", "employee_id": "12"(optional) }

    If employee_id is provided, performs employee-level verification for dashboard flow.
    """
    data = request.get_json(silent=True) or {}
    otp_type = (data.get("otp_type") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    employee_id = data.get("employee_id")

    if otp_type not in ("start", "end"):
        return fail("otp_type must be 'start' or 'end'")
    if not otp.isdigit() or len(otp) != 6:
        return fail("OTP must be exactly 6 digits")
    if employee_id is None or str(employee_id).strip() == "":
        return fail("employee_id is required for employee-wise OTP verification")

    conn = get_db()
    try:
        cur = conn.cursor()
        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error
        trip_row, _ = _get_driver_trip_row(
            cur,
            driver_id=resolved_id,
            trip_id=trip_id,
            requested_admin_id=request.args.get("admin_id"),
        )
        if not trip_row:
            return fail("Trip not found", 404)
        result = verify_employee_trip_otp(
            conn,
            trip_id=trip_id,
            employee_id=str(employee_id).strip(),
            otp_type=otp_type,
            otp_input=otp,
            driver_id=driver_id,
        )
    except Exception as e:
        return fail(str(e), 400)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if not result.get("success"):
        return fail(result.get("message", "OTP verify failed"), 400)
    return ok("OTP verified", result.get("data"))


@driver_bp.route("/<driver_id>/trip/<int:trip_id>/start", methods=["POST"])
@require_auth(roles=["driver"])
def driver_start_trip_no_otp(driver_id: str, trip_id: int):
    """
    Start trip WITHOUT OTP (e.g. Drop trips).
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error
        row, _ = _get_driver_trip_row(
            cur,
            driver_id=resolved_id,
            trip_id=trip_id,
            requested_admin_id=request.args.get("admin_id"),
            select_fields=(
                "t.id, t.status, t.trip_type, "
                "COALESCE(t.time_slot, t.schedule_time) AS scheduled_time, "
                "t.trip_day, t.total_km"
            ),
        )
        if not row:
            return fail("Trip not found", 404)
        
        status = str(row["status"] or "").lower()
        trip_type = str(row["trip_type"] or "").lower()
        if status not in ("assigned", "created", "active"):
            return fail(f"Trip is {row['status']}, cannot start.", 400)

        gate = evaluate_trip_start_gate(
            row["trip_day"],
            row["scheduled_time"],
            trip_type=trip_type,
            route_duration_minutes=_resolve_trip_duration_minutes(cur, trip_id, row["total_km"]),
        )
        if not bool(gate.get("can_start_now", True)):
            log_trip_event(
                "trip_start_blocked_preassigned",
                trip_id=trip_id,
                driver_id=resolved_id,
                start_allowed_after=gate.get("start_allowed_after"),
            )
            return fail(
                "Trip is pre-assigned. Start allowed only at scheduled date/time.",
                400,
                {
                    "error_code": "TRIP_NOT_STARTED_YET",
                    "start_allowed_after": gate.get("start_allowed_after"),
                    "seconds_until_start": int(gate.get("seconds_until_start", 0) or 0),
                    "server_now": gate.get("server_now"),
                },
            )

        # Upgraded flow:
        # - pickup: all employee start OTPs must be verified before start
        # - drop: start allowed without OTP
        if trip_type == "pickup":
            otp_gate = get_pending_employee_otp_ids(conn, trip_id=trip_id, otp_type="start")
            pending = ((otp_gate.get("data") or {}).get("pending_employee_ids") or [])
            if pending:
                return fail(
                    "Cannot start pickup trip. Employee start OTP pending.",
                    400,
                    {"pending_employee_ids": pending},
                )

        # Update status
        # Keep DB-schema compatibility: many deployments allow 'started' but not 'in_progress'.
        cur.execute("UPDATE trips SET status='started', start_time=CURRENT_TIMESTAMP WHERE id=?", (trip_id,))
        conn.commit()
        log_trip_event("trip_started", trip_id=trip_id, driver_id=resolved_id)
        return ok("Trip started")
    except Exception as e:
        return fail(f"Failed to start trip: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@driver_bp.route("/<driver_id>/trip/<int:trip_id>/complete", methods=["POST"])
@require_auth(roles=["driver"])
def driver_complete_trip_no_otp(driver_id: str, trip_id: int):
    """
    Complete trip WITHOUT OTP (e.g. Pickup trips ending at office).
    """
    conn = get_db()
    try:
        data = request.get_json(silent=True) or {}
        cur = conn.cursor()
        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error
        row, _ = _get_driver_trip_row(
            cur,
            driver_id=resolved_id,
            trip_id=trip_id,
            requested_admin_id=request.args.get("admin_id"),
            select_fields="t.id, t.status, t.trip_type",
        )
        if not row:
            return fail("Trip not found", 404)
        
        status = str(row["status"] or "").lower()
        trip_type = str(row["trip_type"] or "").lower()
        if status not in ("started", "in_progress", "live"):
            return fail(f"Trip is {row['status']}, cannot complete.", 400)

        # Upgraded flow:
        # - pickup: no end OTP required
        # - drop: all employee end OTPs must be verified before complete
        if trip_type == "drop":
            otp_gate = get_pending_employee_otp_ids(conn, trip_id=trip_id, otp_type="end")
            pending = ((otp_gate.get("data") or {}).get("pending_employee_ids") or [])
            if pending:
                return fail(
                    "Cannot end drop trip. Employee end OTP pending.",
                    400,
                    {"pending_employee_ids": pending},
                )

        total_km_raw = data.get("total_km")
        total_km = None
        if total_km_raw not in (None, ""):
            try:
                total_km = float(total_km_raw)
            except (TypeError, ValueError):
                return fail("total_km must be numeric", 400)

        outcome = mark_trip_completed(
            conn,
            trip_id,
            actor_role="driver",
            actor_id=str(resolved_id),
            total_km=total_km,
            polyline=data.get("polyline"),
            route_json=data.get("route_json"),
        )
        _cleanup_temp_swap_driver(conn, trip_id)
        conn.commit()
        log_trip_event("trip_completed", trip_id=trip_id, driver_id=resolved_id, total_km=total_km)
        return ok("Trip completed", outcome)
    except Exception as e:
        return fail(f"Failed to complete trip: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# NO-SHOW (driver marks employee absent at pickup/drop)
# =========================================================
@driver_bp.route("/<driver_id>/trip/<int:trip_id>/no-show", methods=["POST"])
@require_auth(roles=["driver"])
def mark_employee_no_show(driver_id: str, trip_id: int):
    """
    Body: { "employee_id": 5 }
    Sets trip_employees.no_show = 1
    """
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    reason = str(data.get("reason") or "").strip()

    if employee_id is None:
        return fail("employee_id is required")
    
    try:
        employee_id = int(employee_id)
    except (ValueError, TypeError):
        return fail("employee_id must be a valid integer")

    conn = get_db()
    cur = conn.cursor()
    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error

    trip_row, _ = _get_driver_trip_row(
        cur,
        driver_id=resolved_id,
        trip_id=trip_id,
        requested_admin_id=request.args.get("admin_id"),
    )
    if not trip_row:
        conn.close()
        return fail("Trip not found for this driver", 404)

    cur.execute(
        "SELECT id FROM trip_employees WHERE trip_id=? AND employee_id=?",
        (trip_id, employee_id),
    )
    if not cur.fetchone():
        conn.close()
        return fail("Employee not found in this trip", 404)

    payload = mark_member_no_show(
        conn,
        trip_id,
        employee_id,
        marked_by_driver_id=str(resolved_id),
        reason=reason,
    )
    conn.commit()
    conn.close()

    log_trip_event(
        "no_show_marked",
        trip_id=trip_id,
        driver_id=resolved_id,
        employee_id=employee_id,
        reason=reason,
    )
    return ok("Employee marked as no-show", payload)


# =========================================================
# EMERGENCY SWAP REQUEST (vehicle failure / driver swap)
# =========================================================
@driver_bp.route("/<driver_id>/trip/<int:trip_id>/swap-request", methods=["POST"])
@require_auth(roles=["driver"])
def create_swap_request(driver_id: str, trip_id: int):
    """
    Driver requests swap during live trip.
    Body:
      {
        "new_driver_name": "...",
        "new_driver_mobile": "10digits",
        "new_cab_no": "MH12AB1234",
        "reason": "vehicle failure",
        "photo_base64": "..." (optional)
      }
    Admin must approve in admin_routes.
    """
    data = request.get_json(silent=True) or {}

    new_driver_name = (data.get("new_driver_name") or "").strip()
    new_driver_mobile = (data.get("new_driver_mobile") or "").strip()
    new_cab_no = (data.get("new_cab_no") or "").strip().upper()
    reason = (data.get("reason") or "").strip()
    photo_base64 = (data.get("photo_base64") or "").strip()

    if not new_driver_name:
        return fail("new_driver_name is required")
    if not validate_mobile_10(new_driver_mobile):
        return fail("new_driver_mobile must be exactly 10 digits")
    if not validate_vehicle_no(new_cab_no):
        return fail("new_cab_no format invalid (ex: MH12AB1234)")
    if not reason:
        return fail("reason is required")

    # Handle file upload for proof image
    proof_image_path = None
    if 'proof_image' in request.files:
        file = request.files['proof_image']
        if file and file.filename:
            import os
            import uuid
            from werkzeug.utils import secure_filename
            
            # Validate file extension
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename.lower())[1]
            
            if ext not in allowed_extensions:
                return fail("Only image files (jpg, png, gif) are allowed.", 400)
            
            # Create upload directory if not exists
            upload_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'swap')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            proof_image_path = f"uploads/swap/{unique_filename}"

    conn = get_db()
    try:
        cur = conn.cursor()

        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error

        trip_row, _ = _get_driver_trip_row(
            cur,
            driver_id=resolved_id,
            trip_id=trip_id,
            requested_admin_id=request.args.get("admin_id"),
        )
        if not trip_row:
            return fail("Trip not found for this driver", 404)

        cur.execute(
            """
            INSERT INTO swap_requests (
                trip_id, old_driver_id, new_driver_name, new_driver_mobile,
                new_cab_no, note, proof_image_path, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
            """,
            (trip_id, resolved_id, new_driver_name, new_driver_mobile, new_cab_no, reason, proof_image_path),
        )
        conn.commit()
        req_id = cur.lastrowid
        return ok("Swap request submitted (pending admin approval)", {"request_id": req_id, "proof_uploaded": proof_image_path is not None})
    except Exception as e:
        return fail(f"Failed to submit swap request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# PREASSIGN CANCEL REQUEST (Driver -> Admin)
# =========================================================
@driver_bp.route("/<driver_id>/trip/<int:trip_id>/cancel-request", methods=["POST"])
@require_auth(roles=["driver"])
def create_trip_cancel_request(driver_id: str, trip_id: int):
    payload = request.get_json(silent=True) or {}
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        return fail("reason is required (min 3 chars)")

    conn = get_db()
    try:
        cur = conn.cursor()
        resolved_id = _resolve_driver_pk(cur, driver_id)
        if resolved_id is None:
            return fail("Driver not found", 404)
        auth_error = _ensure_driver_identity(str(resolved_id))
        if auth_error:
            return auth_error

        trip_row, _ = _get_driver_trip_row(
            cur,
            driver_id=resolved_id,
            trip_id=trip_id,
            requested_admin_id=request.args.get("admin_id"),
            select_fields="t.id, t.trip_day, t.schedule_time, t.trip_type, t.total_km",
        )
        if not trip_row:
            return fail("Trip not found for this driver", 404)
        gate = evaluate_trip_start_gate(
            trip_row["trip_day"] if "trip_day" in trip_row.keys() else None,
            trip_row["schedule_time"] if "schedule_time" in trip_row.keys() else None,
            trip_type=trip_row["trip_type"] if "trip_type" in trip_row.keys() else None,
            route_duration_minutes=_resolve_trip_duration_minutes(
                cur,
                trip_id,
                trip_row["total_km"] if "total_km" in trip_row.keys() else None,
            ),
        )
        if not bool(gate.get("is_preassigned", False)):
            return fail("Cancel request is allowed only for pre-assigned trips", 400)

        _ensure_trip_cancel_requests_table(cur)
        cur.execute(
            """
            SELECT id
            FROM trip_cancel_requests
            WHERE trip_id = ?
              AND CAST(driver_id AS TEXT) = CAST(? AS TEXT)
              AND LOWER(COALESCE(status, '')) = 'pending'
            LIMIT 1
            """,
            (trip_id, str(resolved_id)),
        )
        existing = cur.fetchone()
        if existing:
            return fail("Cancel request already pending for this trip", 409)

        cur.execute(
            """
            INSERT INTO trip_cancel_requests (
                trip_id, driver_id, reason, status, created_at, updated_at
            )
            VALUES (?, ?, ?, 'pending', datetime('now'), datetime('now'))
            """,
            (trip_id, str(resolved_id), reason),
        )
        conn.commit()
        return ok(
            "Trip cancel request sent to admin",
            {
                "request_id": cur.lastrowid,
                "trip_id": trip_id,
                "driver_id": str(resolved_id),
                "status": "pending",
            },
        )
    except Exception as e:
        return fail(f"Failed to send cancel request: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================================================
# HELPDESK
# =========================================================
@driver_bp.post("/<driver_id>/helpdesk")
@require_auth(roles=["driver"])
def create_driver_helpdesk_ticket(driver_id: str):
    """
    Driver creates a helpdesk ticket.
    Payload: { subject, message, priority }
    """
    data = request.json or {}
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()
    priority = (data.get("priority") or "normal").strip().lower()

    if not subject or not message:
        return fail("Subject and message are required", 400)

    conn = get_db()
    cur = conn.cursor()

    # ensure driver exists
    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return fail("Driver not found", 404)
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error

    try:
        cur.execute(
            """
            INSERT INTO helpdesk_tickets (user_id, user_type, subject, message, priority, status, created_at, updated_at)
            VALUES (?, 'driver', ?, ?, ?, 'open', ?, ?)
            """,
            (str(resolved_id), subject, message, priority, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        conn.commit()
        ticket_id = cur.lastrowid
        return ok({"ticket_id": ticket_id}, "Helpdesk ticket created successfully.")
    except Exception as e:
        return fail(f"Failed to create ticket: {e}", 500)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@driver_bp.route("/<driver_id>/my-trips", methods=["GET"])
@require_auth(roles=["driver"])
def get_driver_trips(driver_id: str):
    """
    Get ALL active assigned trips for driver.
    Used for dashboard list + polling fallback.
    Query:
        - date=YYYY-MM-DD (optional; if omitted returns all active trips)
    """
    trip_date = (request.args.get("date") or "").strip()
    trip_day = trip_date.replace("-", "") if trip_date else ""
    
    conn = get_db()
    cur = conn.cursor()
    requested_admin_id = request.args.get("admin_id")
    resolved_id = _resolve_driver_pk(cur, driver_id)
    if resolved_id is None:
        conn.close()
        return ok("Driver trips", {"trips": []})
    auth_error = _ensure_driver_identity(str(resolved_id))
    if auth_error:
        conn.close()
        return auth_error
    selected_admin_id = _get_driver_selected_admin(cur, str(resolved_id), requested_admin_id)
    if selected_admin_id:
        _set_driver_selected_admin(cur, str(resolved_id), selected_admin_id)
        conn.commit()
    
    cur.execute("PRAGMA table_info(trips)")
    trip_cols = {row[1] for row in cur.fetchall()}
    cur.execute("PRAGMA table_info(trip_employees)")
    te_cols = {row[1] for row in cur.fetchall()}
    cur.execute("PRAGMA table_info(drivers)")
    driver_cols = {row[1] for row in cur.fetchall()}

    if trip_day and "trip_day" in trip_cols:
        day_predicate = "REPLACE(COALESCE(t.trip_day, ''), '-', '') = ?"
        day_param = trip_day
    elif trip_day and "trip_date" in trip_cols:
        day_predicate = "REPLACE(COALESCE(t.trip_date, ''), '-', '') = ?"
        day_param = trip_day
    else:
        day_predicate = "1=1"
        day_param = None

    no_show_expr = "te.is_no_show" if "is_no_show" in te_cols else ("te.no_show" if "no_show" in te_cols else "0")
    eta_expr = "te.estimated_arrival_time" if "estimated_arrival_time" in te_cols else "''"
    driver_join_sql = "CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)"
    if "driver_id" in driver_cols:
        driver_join_sql += " OR (d.driver_id IS NOT NULL AND CAST(d.driver_id AS TEXT) = CAST(t.driver_id AS TEXT))"

    sql = f"""
        SELECT t.id, t.route_no, t.trip_type, t.status, t.schedule_time, t.trip_day,
               t.total_km, t.polyline AS route_polyline,
               d.name AS driver_name, d.mobile AS driver_mobile, d.vehicle_no AS cab_no
        FROM trips t
        JOIN drivers d
          ON {driver_join_sql}
        WHERE d.id = ?
          AND (? IS NULL OR CAST(COALESCE(t.admin_id, '') AS TEXT) = ?)
          AND {day_predicate}
          AND t.status IN ('created', 'assigned', 'started', 'active', 'in_progress', 'live')
        ORDER BY t.trip_day ASC, t.schedule_time ASC, t.id ASC
    """
    
    params = [resolved_id, selected_admin_id, selected_admin_id]
    if day_param is not None:
        params.append(day_param)
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    trips = []
    
    for row in rows:
        trip = dict(row)
        trip_mode = str(trip.get("trip_type") or "").strip().lower()
        travel_min = _resolve_trip_duration_minutes(cur, int(trip.get("id") or 0), trip.get("total_km"))
        gate = evaluate_trip_start_gate(
            trip.get("trip_day"),
            trip.get("schedule_time"),
            trip_type=trip_mode,
            route_duration_minutes=travel_min,
        )
        trip["can_start_now"] = bool(gate.get("can_start_now", True))
        trip["is_preassigned"] = bool(gate.get("is_preassigned", False))
        trip["start_allowed_after"] = gate.get("start_allowed_after")
        trip["seconds_until_start"] = int(gate.get("seconds_until_start", 0) or 0)
        trip["server_now"] = gate.get("server_now")
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
        
        # Get passengers
        cur.execute(
            f"""
            SELECT e.id, e.name, e.mobile, e.home_address AS address, 
                   te.sequence_no, {eta_expr} AS estimated_arrival_time, {no_show_expr} AS no_show
            FROM trip_employees te
            JOIN employees e ON e.id = te.employee_id
            WHERE te.trip_id = ?
            ORDER BY te.sequence_no ASC
            """,
            (trip["id"],)
        )
        trip["passengers"] = [dict(r) for r in cur.fetchall()]
        
        trips.append(trip)
        
    conn.close()
    return ok("Driver trips", {"trips": trips})
