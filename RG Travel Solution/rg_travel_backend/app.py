# backend/app.py
"""
RG Travel Solution (Lite) - Flask Backend (Single-file main app)

âœ… Path: backend/app.py

This app.py is built to match the structure you created:
- backend/db/            -> SQLite get_db(), init_db(), schema.sql, /api/db/*
- backend/utils/         -> response.py, security.py, time_utils.py, /api/utils/*, /api/security/*, /api/time/*
- backend/seeds/         -> seed_admin.py, seed_drivers.py, seed_employee.py, /api/*/seed/*
- backend/config/        -> keys.py, settings.py, /api/config/*, /api/settings/*

It registers ALL required API endpoints for your project:
- Admin: profile + login
- Driver: profile + login + hometown request
- Employee: CRUD + login
- Trips: create/group, assign, list, live tracking, OTP start/end, no-show marking

Flutter base URL (Android emulator):
  http://10.0.2.2:5000

Run:
  python app.py
or
  python -m backend.app   (if you use a package run style)

"""

from __future__ import annotations

import os
import secrets
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# âœ… Helpers to resolve path issues in some IDEs/Terminals
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from flask import Flask, request, g
from flask_cors import CORS

# ==========================
# Imports from your packages
# ==========================
# Direct imports (run from backend folder: python app.py)
from config import SETTINGS, apply_flask_config, register_config_all_routes
from db import get_db, init_db, register_db_routes
from utils import register_utils_routes
from utils.response import success_response, error_response, APIError, api_exception_handler
from utils.security import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
    require_auth,
    generate_otp,
    verify_otp,
    otp_expiry_iso,
)
from utils.time_utils import trip_day_key, iso_date_today_ist
from seeds import register_seed_routes
# âœ… Import new route blueprints
from routes.otp_routes import otp_bp
from routes.tracking_routes import tracking_bp
from routes.grouping_routes import grouping_bp
from routes.auth_routes import auth_bp
from routes.admin_requests_routes import admin_req_bp
from routes.availability_routes import availability_bp
from routes.driver_v2_routes import driver_v2_bp
from routes.health_routes import health_bp


# =========================================================
# DB helpers (small, safe)
# =========================================================
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        # fallback if row is tuple-like
        return {}


def _fetch_one(cur, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    cur.execute(sql, params)
    r = cur.fetchone()
    if not r:
        return None
    return _row_to_dict(r)


def _fetch_all(cur, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    cur.execute(sql, params)
    rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(_row_to_dict(r))
    return out


# =========================================================
# Route number generation (10 chars unique per day)
# =========================================================
def _generate_route_no() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # avoid confusing chars like I/O/1/0
    return "".join(secrets.choice(alphabet) for _ in range(10))


def _get_unique_route_no_for_today(cur) -> str:
    day = trip_day_key()
    for _ in range(50):
        rn = _generate_route_no()
        try:
            cur.execute(
                """
                INSERT INTO route_numbers (id, route_no, trip_day, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (f"rn_{secrets.token_hex(8)}", rn, day, _now_iso()),
            )
            return rn
        except Exception:
            # collision -> try again
            continue
    raise APIError("Failed to generate unique route number. Try again.", 500, "ROUTE_NO_GENERATION_FAILED")


# =========================================================
# Validation helpers
# =========================================================
def _is_mobile10(m: str) -> bool:
    return m.isdigit() and len(m) == 10


def _to_float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s.lower() == "null":
        return None
    try:
        return float(s)
    except Exception:
        return None


def _require_fields(data: Dict[str, Any], fields: List[str]) -> None:
    missing = [f for f in fields if str(data.get(f, "")).strip() == ""]
    if missing:
        raise APIError(f"Missing fields: {', '.join(missing)}", 400, "VALIDATION_ERROR")


# =========================================================
# Flask App Factory
# =========================================================
def create_app() -> Flask:
    app = Flask(__name__)
    apply_flask_config(app)

    # CORS for Flutter
    if SETTINGS.CORS_ENABLED:
        CORS(app, resources={r"/api/*": {"origins": SETTINGS.CORS_ORIGINS}})

    # Initialize DB schema (safe to run multiple times)
    try:
        init_db()
    except Exception:
        # If schema file missing/moved, app still starts
        pass

    # Register optional system endpoints
    register_db_routes(app)           # /api/db/*
    register_utils_routes(app)        # /api/utils/* + /api/security/* + /api/time/*
    register_config_all_routes(app)   # /api/config/* + /api/settings/* (guarded by env flags)
    register_seed_routes(app)         # /api/admin/seed/*, /api/drivers/seed/*, /api/employees/seed/*
    
    # âœ… Register new feature endpoints (P0 Critical Fixes)
    app.register_blueprint(otp_bp)       # /api/trip/<route_no>/otp, /api/trip/<route_no>/otp/verify
    app.register_blueprint(tracking_bp)  # /api/driver/<id>/gps, /api/admin/drivers/online, /api/tracking/route/<route_no>/latest
    app.register_blueprint(grouping_bp)  # /api/admin/groups/auto
    app.register_blueprint(availability_bp)  # /api/admin/availability/scan
    app.register_blueprint(auth_bp)      # /api/auth/admin/login, /api/auth/driver/login, ...
    app.register_blueprint(driver_v2_bp) # /api/v2/drivers/*
    app.register_blueprint(health_bp)    # /api/health/*
    
    # âœ… Notifications
    from routes.notification_routes import notification_bp
    app.register_blueprint(notification_bp)
    
    # âœ… Initialize SocketIO
    from services.socket_service import socketio
    socketio.init_app(app)

    
    # âœ… Admin Requests (Waitlist management)
    from routes.admin_requests_routes import admin_req_bp
    app.register_blueprint(admin_req_bp) # /api/admin/requests/drivers, ...

    # âœ… Admin Routes (New: Employees, Drivers, etc.)
    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    # âœ… Employee Routes (SOS, Rating, etc.)
    from routes.employee_routes import employee_bp
    app.register_blueprint(employee_bp)

    # âœ… Driver Routes  
    from routes.driver_routes import driver_bp
    app.register_blueprint(driver_bp)

    # âœ… Trip V2 Routes (Orchestration)
    from routes.trip_creation_v2_routes import trip_v2_bp, list_no_trip_requests, create_groups
    app.register_blueprint(trip_v2_bp)
    # Legacy compatibility aliases used by older Flutter builds.
    app.add_url_rule("/api/v2/employees/no-trip-requests", view_func=list_no_trip_requests, methods=["GET"])
    app.add_url_rule("/api/admin/groups/create", view_func=create_groups, methods=["POST"])

    # -----------------------------------------------------
    # Root
    # -----------------------------------------------------
    @app.get("/")
    def root():
        return success_response(
            data={
                "name": "RG Travel Solution Backend",
                "date_ist": iso_date_today_ist(),
                "api_base": "/api",
                "quick_checks": {
                    "ping": "/api/utils/ping",
                    "db_health": "/api/db/health",
                    "time_now": "/api/time/now",
                },
            },
            message="Backend is running",
        )

    # =====================================================
    # AUTH / LOGIN APIs
    # =====================================================

    # -------- Admin Login --------
    @app.post("/api/admin/login")
    @api_exception_handler("Admin login failed", include_traceback=True)
    def admin_login():
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["mobile", "password"])

        mobile = str(data["mobile"]).strip()
        password = str(data["password"]).strip()

        if not _is_mobile10(mobile):
            raise APIError("Mobile must be exactly 10 digits.", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            cur = conn.cursor()
            row = _fetch_one(
                cur,
                """
                SELECT id, name, mobile, email, office_name, office_location, office_address,
                       password_salt, password_hash
                FROM admins
                WHERE mobile = ?
                """,
                (mobile,),
            )
            if not row:
                raise APIError("Admin not found.", 404, "ADMIN_NOT_FOUND")

            if not verify_password(password, row["password_salt"], row["password_hash"]):
                raise APIError("Invalid password.", 401, "INVALID_CREDENTIALS")

            tok = create_token(user_id=row["id"], role="admin")
            profile = {
                "id": row["id"],
                "name": row["name"],
                "mobile": row["mobile"],
                "email": row.get("email"),
                "office_name": row.get("office_name"),
                "office_location": row.get("office_location"),
                "office_address": row.get("office_address"),
            }
            return success_response({"token": tok["token"], "expires_at": tok["expires_at"], "profile": profile}, "Login success")
        finally:
            conn.close()

    # -------- Admin Login (Alternative Route) --------
    # Same as /api/admin/login but at /api/auth/admin/login (for Flutter compatibility)
    # COMMENTED OUT: Handled by auth_bp now
    # @app.post("/api/auth/admin/login")
    # @api_exception_handler("Admin login failed", include_traceback=True)
    # def admin_login_auth():
    #     return admin_login()

    # -------- Driver Login --------
    # Supports BOTH:
    # 1) mobile + password
    # 2) mobile + dl_no + vehicle_no (matches your earlier Flutter UI)
    @app.post("/api/driver/login")
    @api_exception_handler("Driver login failed", include_traceback=False)
    def driver_login():
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["mobile"])

        mobile = str(data["mobile"]).strip()
        password = str(data.get("password", "")).strip()
        dl_no = str(data.get("dl_no", "")).strip()
        vehicle_no = str(data.get("vehicle_no", "")).strip()

        if not _is_mobile10(mobile):
            raise APIError("Mobile must be exactly 10 digits.", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            cur = conn.cursor()
            row = _fetch_one(
                cur,
                """
                SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved,
                       password_salt, password_hash,
                       dl_expiry, rc_expiry, insurance_expiry, fitness_expiry, permit_expiry
                FROM drivers
                WHERE mobile = ?
                """,
                (mobile,),
            )
            if not row:
                raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")

            # approval check
            if int(row.get("is_approved", 0)) != 1:
                raise APIError("Driver is not approved by admin yet.", 403, "DRIVER_NOT_APPROVED")

            ok = False
            if password:
                ok = verify_password(password, row["password_salt"], row["password_hash"])
            else:
                # fallback login mode
                if dl_no and vehicle_no and (dl_no == row["dl_no"]) and (vehicle_no == row["vehicle_no"]):
                    ok = True

            if not ok:
                raise APIError("Invalid credentials.", 401, "INVALID_CREDENTIALS")

            tok = create_token(user_id=row["id"], role="driver")
            profile = {
                "id": row["id"],
                "name": row["name"],
                "mobile": row["mobile"],
                "dl_no": row["dl_no"],
                "vehicle_no": row["vehicle_no"],
                "vehicle_type": row.get("vehicle_type"),
                "home_town": row.get("home_town"),
                "dl_expiry": row.get("dl_expiry"),
                "rc_expiry": row.get("rc_expiry"),
                "insurance_expiry": row.get("insurance_expiry"),
                "fitness_expiry": row.get("fitness_expiry"),
                "permit_expiry": row.get("permit_expiry"),
            }
            return success_response({"token": tok["token"], "expires_at": tok["expires_at"], "profile": profile}, "Login success")
        finally:
            conn.close()

    # -------- Employee Login (lite) --------
    # For your project, employee login is usually mobile-based (or future OTP).
    @app.post("/api/employee/login")
    @api_exception_handler("Employee login failed", include_traceback=False)
    def employee_login():
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["mobile"])

        mobile = str(data["mobile"]).strip()
        if not _is_mobile10(mobile):
            raise APIError("Mobile must be exactly 10 digits.", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            cur = conn.cursor()
            row = _fetch_one(
                cur,
                """
                SELECT id, name, mobile, email, login_time, logout_time, pickup_location, drop_location, drop_lat, drop_lng, is_active
                FROM employees
                WHERE mobile = ?
                """,
                (mobile,),
            )
            if not row:
                raise APIError("Employee not found.", 404, "EMPLOYEE_NOT_FOUND")
            if int(row.get("is_active", 1)) != 1:
                raise APIError("Employee is inactive.", 403, "EMPLOYEE_INACTIVE")

            tok = create_token(user_id=row["id"], role="employee")
            return success_response(
                {"token": tok["token"], "expires_at": tok["expires_at"], "profile": row},
                "Login success",
            )
        finally:
            conn.close()

    # =====================================================
    # DRIVER REGISTRATION API
    # =====================================================
    # COMMENTED OUT: Handled by auth_bp (auth_routes.py)
    # @app.post("/api/auth/driver/register")
    # @api_exception_handler("Driver registration failed", include_traceback=False)
    # def driver_register():
        """
        Register a new driver (self-registration)
        
        Flow:
        1. Insert driver profile into drivers table (is_approved=0, pending)
        2. Insert request into driver_hometown_requests (status='pending') for admin review
        3. Admin approves -> sets both is_approved=1 and driver_hometown_requests.status='approved'
        
        body: {
          "name": "John Doe",
          "mobile": "9876543210",
          "dl_no": "DL1234567",
          "vehicle_no": "KA-01-AB-1234",
          "vehicle_type": "4",
          "home_town": "Bangalore",
          "password": "secure_password"
        }
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["name", "mobile", "dl_no", "vehicle_no", "vehicle_type", "password"])

        name = str(data["name"]).strip()
        mobile = str(data["mobile"]).strip()
        dl_no = str(data["dl_no"]).strip()
        vehicle_no = str(data["vehicle_no"]).strip()
        vehicle_type = str(data["vehicle_type"]).strip()
        home_town = str(data.get("home_town", "")).strip() or None
        password = str(data["password"]).strip()

        if len(name) < 2:
            raise APIError("Name must be at least 2 characters.", 400, "VALIDATION_ERROR")
        if not _is_mobile10(mobile):
            raise APIError("Mobile must be exactly 10 digits.", 400, "VALIDATION_ERROR")
        if len(password) < 6:
            raise APIError("Password must be at least 6 characters.", 400, "VALIDATION_ERROR")
        if vehicle_type not in ("4", "6"):
            raise APIError("vehicle_type must be '4' or '6'.", 400, "VALIDATION_ERROR")

        password_salt, password_hash = hash_password(password)
        driver_id = f"drv_{secrets.token_hex(6)}"

        conn = get_db()
        try:
            cur = conn.cursor()

            # Check if mobile already exists
            cur.execute("SELECT id FROM drivers WHERE mobile = ?", (mobile,))
            if cur.fetchone():
                raise APIError("Mobile already registered.", 409, "MOBILE_EXISTS")

            # Check if DL already exists
            cur.execute("SELECT id FROM drivers WHERE dl_no = ?", (dl_no,))
            if cur.fetchone():
                raise APIError("DL number already registered.", 409, "DL_EXISTS")

            # Check if vehicle already exists
            cur.execute("SELECT id FROM drivers WHERE vehicle_no = ?", (vehicle_no,))
            if cur.fetchone():
                raise APIError("Vehicle number already registered.", 409, "VEHICLE_EXISTS")

            # ============================================================
            # STEP 1: Insert driver profile (not yet approved)
            # ============================================================
            cur.execute(
                """
                INSERT INTO drivers
                (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved,
                 password_salt, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """,
                (
                    driver_id,
                    name,
                    mobile,
                    dl_no,
                    vehicle_no,
                    vehicle_type,
                    home_town,
                    password_salt,
                    password_hash,
                    _now_iso(),
                    _now_iso(),
                ),
            )

            # ============================================================
            # STEP 2: Create request in driver_hometown_requests table
            # This is what admin dashboard reads from to show pending requests
            # ============================================================
            cur.execute(
                """
                INSERT INTO driver_hometown_requests
                (driver_id, requested_home_town, status, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?)
                """,
                (
                    driver_id,
                    home_town or "Not specified",
                    _now_iso(),
                    _now_iso(),
                ),
            )

            conn.commit()

            return success_response(
                {
                    "id": driver_id,
                    "name": name,
                    "mobile": mobile,
                    "status": "pending_approval",
                },
                "Driver registration successful. Awaiting admin approval.",
                201,
            )
        finally:
            conn.close()

    # =====================================================
    # EMPLOYEE REGISTRATION API
    # =====================================================
    # COMMENTED OUT: Handled by auth_bp
    # @app.post("/api/auth/employee/register")
    # @api_exception_handler("Employee registration failed", include_traceback=False)
    # def employee_register():
        """
        Register a new employee (self-registration)
        
        body: {
          "name": "Jane Doe",
          "mobile": "9876543211",
          "email": "jane@example.com",
          "pickup_location": "Main Gate",
          "drop_location": "Office Building A"
        }
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["name", "mobile"])

        name = str(data["name"]).strip()
        mobile = str(data["mobile"]).strip()
        email = str(data.get("email", "")).strip() or None
        pickup_location = str(data.get("pickup_location", "")).strip() or None
        drop_location = str(data.get("drop_location", "")).strip() or None
        drop_lat = data.get("drop_lat")
        drop_lng = data.get("drop_lng")

        if len(name) < 2:
            raise APIError("Name must be at least 2 characters.", 400, "VALIDATION_ERROR")
        if not _is_mobile10(mobile):
            raise APIError("Mobile must be exactly 10 digits.", 400, "VALIDATION_ERROR")

        employee_id = f"emp_{secrets.token_hex(6)}"

        conn = get_db()
        try:
            cur = conn.cursor()

            # Check if mobile already exists
            cur.execute("SELECT id FROM employees WHERE mobile = ?", (mobile,))
            if cur.fetchone():
                raise APIError("Mobile already registered.", 409, "MOBILE_EXISTS")

            # Insert employee (active by default)
            cur.execute(
                """
                INSERT INTO employees
                (id, name, mobile, email, pickup_location, drop_location, drop_lat, drop_lng, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    employee_id,
                    name,
                    mobile,
                    email,
                    pickup_location,
                    drop_location,
                    float(drop_lat) if drop_lat is not None else None,
                    float(drop_lng) if drop_lng is not None else None,
                    _now_iso(),
                    _now_iso(),
                ),
            )
            conn.commit()

            return success_response(
                {
                    "id": employee_id,
                    "name": name,
                    "mobile": mobile,
                    "status": "registered",
                },
                "Employee registration successful.",
                201,
            )
        finally:
            conn.close()

    # =====================================================
    # ADMIN PROFILE APIs
    # =====================================================
    @app.get("/api/admin/<admin_id>")
    @require_auth(roles=["admin"])
    @api_exception_handler("Failed to load admin profile", include_traceback=False)
    def get_admin_profile(admin_id: str):
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(admins)")
            cols = {str(r[1]) for r in cur.fetchall()}
            select_cols = [
                "id",
                "name",
                "mobile",
                "email",
                "office_name",
                "office_location",
                "office_address",
            ]
            if "office_lat" in cols:
                select_cols.append("office_lat")
            if "office_lng" in cols:
                select_cols.append("office_lng")
            select_cols.extend(["created_at", "updated_at"])
            row = _fetch_one(
                cur,
                """
                SELECT {select_sql}
                FROM admins WHERE id = ?
                """.format(select_sql=", ".join(select_cols)),
                (admin_id,),
            )
            if not row:
                raise APIError("Admin not found.", 404, "ADMIN_NOT_FOUND")
            return success_response(row, "Admin profile loaded")
        finally:
            conn.close()

    @app.put("/api/admin/<admin_id>")
    @require_auth(roles=["admin"])
    @api_exception_handler("Failed to update admin profile", include_traceback=False)
    def update_admin_profile(admin_id: str):
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip() or None
        mobile = str(data.get("mobile", "")).strip()
        password = str(data.get("password", "")).strip()
        office_name = str(data.get("office_name", "")).strip() or None
        office_location = str(data.get("office_location", "")).strip() or None
        office_address = str(data.get("office_address", "")).strip() or None
        office_lat = _to_float_or_none(data.get("office_lat"))
        office_lng = _to_float_or_none(data.get("office_lng"))

        if name and len(name) < 2:
            raise APIError("Name must be at least 2 characters.", 400, "VALIDATION_ERROR")
        if mobile and not _is_mobile10(mobile):
            raise APIError("Mobile must be exactly 10 digits.", 400, "VALIDATION_ERROR")
        if password and len(password) < 6:
            raise APIError("Password must be at least 6 characters.", 400, "VALIDATION_ERROR")
        if (office_lat is None) != (office_lng is None):
            raise APIError(
                "Both office_lat and office_lng are required together.",
                400,
                "VALIDATION_ERROR",
            )
        if office_lat is not None and not (-90 <= office_lat <= 90):
            raise APIError("office_lat must be between -90 and 90.", 400, "VALIDATION_ERROR")
        if office_lng is not None and not (-180 <= office_lng <= 180):
            raise APIError("office_lng must be between -180 and 180.", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(admins)")
            cols = {str(r[1]) for r in cur.fetchall()}

            existing = _fetch_one(cur, "SELECT id FROM admins WHERE id = ?", (admin_id,))
            if not existing:
                raise APIError("Admin not found.", 404, "ADMIN_NOT_FOUND")

            # keep mobile unique if updated
            if mobile:
                cur.execute("SELECT id FROM admins WHERE mobile = ? AND id <> ?", (mobile, admin_id))
                if cur.fetchone():
                    raise APIError("Mobile already exists.", 409, "MOBILE_EXISTS")

            # build update
            set_parts = [
                "name = COALESCE(?, name)",
                "email = ?",
                "mobile = COALESCE(?, mobile)",
                "office_name = ?",
                "office_location = ?",
                "office_address = ?",
            ]
            params = [
                name or None,
                email,
                mobile or None,
                office_name,
                office_location,
                office_address,
            ]
            if "office_lat" in cols:
                set_parts.append("office_lat = COALESCE(?, office_lat)")
                params.append(office_lat)
            if "office_lng" in cols:
                set_parts.append("office_lng = COALESCE(?, office_lng)")
                params.append(office_lng)
            if password:
                password_salt, password_hash = hash_password(password)
                set_parts.extend(["password_salt = ?", "password_hash = ?"])
                params.extend([password_salt, password_hash])
            set_parts.append("updated_at = ?")
            params.append(_now_iso())
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

            select_cols = [
                "id",
                "name",
                "mobile",
                "email",
                "office_name",
                "office_location",
                "office_address",
            ]
            if "office_lat" in cols:
                select_cols.append("office_lat")
            if "office_lng" in cols:
                select_cols.append("office_lng")
            select_cols.extend(["created_at", "updated_at"])
            row = _fetch_one(
                cur,
                """
                SELECT {select_sql}
                FROM admins WHERE id = ?
                """.format(select_sql=", ".join(select_cols)),
                (admin_id,),
            )
            return success_response(row, "Admin profile updated")
        finally:
            conn.close()

    # =====================================================
    # ADMIN LIST APIs: drivers, employees, requests, trips
    # =====================================================
    # COMMENTED OUT: Handled by admin_bp (admin_routes.py)
    # -----------------------------------------------------
    # @app.get("/api/admin/drivers")
    # @api_exception_handler("Failed to load drivers list", include_traceback=False)
    # def list_admin_drivers():
    #     conn = get_db()
    #     try:
    #         cur = conn.cursor()
    #         rows = _fetch_all(
    #             cur,
    #             """
    #             SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved
    #             FROM drivers
    #             WHERE is_approved = 1
    #             ORDER BY name ASC
    #             """,
    #         )
    #         return success_response(rows, "Drivers list loaded")
    #     finally:
    #         conn.close()

    # @app.get("/api/admin/driver-requests")
    # @api_exception_handler("Failed to load driver requests", include_traceback=False)
    # def list_admin_driver_requests():
    #     """
    #     List pending driver requests with driver details.
    #     Joins driver_hometown_requests with drivers table to return full info.
    #     """
    #     conn = get_db()
    #     try:
    #         cur = conn.cursor()
    #         rows = _fetch_all(
    #             cur,
    #             """
    #             SELECT 
    #                 r.id, 
    #                 r.driver_id, 
    #                 r.requested_home_town, 
    #                 r.status, 
    #                 r.created_at,
    #                 d.name,
    #                 d.mobile,
    #                 d.dl_no,
    #                 d.vehicle_no,
    #                 d.vehicle_type,
    #                 d.home_town,
    #                 d.created_at as driver_created_at
    #             FROM driver_hometown_requests r
    #             JOIN drivers d ON d.id = r.driver_id
    #             WHERE r.status = 'pending'
    #             ORDER BY r.created_at DESC
    #             """,
    #         )
    #         return success_response(rows, "Driver requests loaded")
    #     finally:
    #         conn.close()

    # @app.post("/api/admin/driver-requests/<int:request_id>/approve")
    # @api_exception_handler("Failed to approve driver", include_traceback=False)
    # def approve_driver_request(request_id: int):
    #     """
    #     Admin approves a pending driver request.
    #     
    #     Updates:
    #     1. driver_hometown_requests: status='pending' -> status='approved'
    #     2. drivers: is_approved=0 -> is_approved=1
    #     """
    #     conn = get_db()
    #     try:
    #         cur = conn.cursor()

    #         # Fetch the request
    #         req = _fetch_one(
    #             cur,
    #             """
    #             SELECT id, driver_id, requested_home_town, status
    #             FROM driver_hometown_requests
    #             WHERE id = ?
    #             """,
    #             (request_id,),
    #         )
    #         if not req:
    #             raise APIError("Driver request not found.", 404, "REQUEST_NOT_FOUND")

    #         if req["status"] != "pending":
    #             raise APIError(f"Request is already {req['status']}.", 409, "INVALID_STATUS")

    #         driver_id = req["driver_id"]

    #         # Verify driver exists
    #         driver = _fetch_one(cur, "SELECT id, name, mobile FROM drivers WHERE id = ?", (driver_id,))
    #         if not driver:
    #             raise APIError("Associated driver record not found.", 404, "DRIVER_NOT_FOUND")

    #         # Update driver_hometown_requests status
    #         cur.execute(
    #             """
    #             UPDATE driver_hometown_requests
    #             SET status = 'approved', updated_at = ?
    #             WHERE id = ?
    #             """,
    #             (_now_iso(), request_id),
    #         )

    #         # Update drivers table to mark as approved
    #         cur.execute(
    #             """
    #             UPDATE drivers
    #             SET is_approved = 1, updated_at = ?
    #             WHERE id = ?
    #             """,
    #             (_now_iso(), driver_id),
    #         )

    #         conn.commit()

    #         return success_response(
    #             {
    #                 "request_id": request_id,
    #                 "driver_id": driver_id,
    #                 "driver_name": driver["name"],
    #                 "status": "approved",
    #             },
    #             "Driver request approved.",
    #             200,
    #         )
    #     finally:
    #         conn.close()

    # @app.post("/api/admin/driver-requests/<int:request_id>/reject")
    # @api_exception_handler("Failed to reject driver", include_traceback=False)
    # def reject_driver_request(request_id: int):
    #     """
    #     Admin rejects a pending driver request.
    #     
    #     Updates:
    #     1. driver_hometown_requests: status='pending' -> status='rejected'
    #     2. drivers: is_approved remains 0 (stays pending)
    #     """
    #     conn = get_db()
    #     try:
    #         cur = conn.cursor()

    #         # Fetch the request
    #         req = _fetch_one(
    #             cur,
    #             """
    #             SELECT id, driver_id, status
    #             FROM driver_hometown_requests
    #             WHERE id = ?
    #             """,
    #             (request_id,),
    #         )
    #         if not req:
    #             raise APIError("Driver request not found.", 404, "REQUEST_NOT_FOUND")

    #         if req["status"] != "pending":
    #             raise APIError(f"Request is already {req['status']}.", 409, "INVALID_STATUS")

    #         driver_id = req["driver_id"]

    #         # Update driver_hometown_requests status
    #         cur.execute(
    #             """
    #             UPDATE driver_hometown_requests
    #             SET status = 'rejected', updated_at = ?
    #             WHERE id = ?
    #             """,
    #             (_now_iso(), request_id),
    #         )

    #         conn.commit()

    #         return success_response(
    #             {
    #                 "request_id": request_id,
    #                 "driver_id": driver_id,
    #                 "status": "rejected",
    #             },
    #             "Driver request rejected.",
    #             200,
    #         )
    #     finally:
    #         conn.close()

    # @app.get("/api/admin/employees")
    # MOVED TO routes/admin_routes.py

    @app.get("/api/admin/employee-requests")
    @api_exception_handler("Failed to load employee requests", include_traceback=False)
    def list_admin_employee_requests():
        conn = get_db()
        try:
            cur = conn.cursor()
            rows = _fetch_all(
                cur,
                """
                SELECT id, employee_id, name, mobile, email, status, created_at
                FROM employee_requests
                ORDER BY created_at DESC
                """,
            )
            return success_response(rows, "Employee requests loaded")
        finally:
            conn.close()

    # =====================================================
    # TRIP MANAGEMENT (Create, View, Update)
    # =====================================================
    @app.post("/api/admin/trips")
    @api_exception_handler("Failed to create and assign trip", include_traceback=False)
    def create_and_assign_trip():
        """
        Create a new trip and assign driver + employees in one call.
        
        body:
        {
          "route_no": "ABC123DEF456",
          "trip_type": "pickup" | "drop",
          "schedule_time": "HH:MM",
          "driver_id": <driver_id>,
          "employee_ids": [<emp_id1>, <emp_id2>, ...],
          "admin_id": <admin_id>,
          "vehicle_type": "4" | "6" (optional, auto-detected from driver)
        }
        
        Returns:
        {
          "trip_id": <trip_id>,
          "route_no": "<route_no>",
          "status": "assigned",
          "message": "Trip created and assigned"
        }
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["route_no", "trip_type", "schedule_time", "driver_id", "employee_ids", "admin_id"])

        route_no = str(data["route_no"]).strip()
        trip_type = str(data["trip_type"]).strip().lower()
        schedule_time = str(data["schedule_time"]).strip()
        driver_id = data["driver_id"]
        employee_ids = data.get("employee_ids", [])
        admin_id = data.get("admin_id")
        vehicle_type = str(data.get("vehicle_type", "")).strip()

        # Validate
        if trip_type not in ("pickup", "drop"):
            raise APIError("trip_type must be 'pickup' or 'drop'.", 400, "VALIDATION_ERROR")
        if not isinstance(employee_ids, list) or len(employee_ids) == 0:
            raise APIError("employee_ids must be a non-empty list.", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            cur = conn.cursor()

            # Verify driver exists and is approved
            driver = _fetch_one(cur, "SELECT id, is_approved, vehicle_type FROM drivers WHERE id = ?", (driver_id,))
            if not driver:
                raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")
            if int(driver.get("is_approved", 0)) != 1:
                raise APIError("Driver not approved.", 403, "DRIVER_NOT_APPROVED")

            # If vehicle_type not provided, use driver's vehicle_type
            if not vehicle_type:
                vehicle_type = driver.get("vehicle_type", "4")

            # Verify all employees exist and are active
            emp_qmarks = ",".join(["?"] * len(employee_ids))
            cur.execute(
                f"SELECT id, name FROM employees WHERE id IN ({emp_qmarks})",
                tuple(employee_ids),
            )
            found_emps = {r["id"]: r for r in cur.fetchall()}
            missing = [eid for eid in employee_ids if eid not in found_emps]
            if missing:
                raise APIError(f"Employees not found: {missing}", 404, "EMPLOYEE_NOT_FOUND")

            # Create trip
            now = _now_iso()
            cur.execute(
                """
                INSERT INTO trips
                (route_no, trip_type, schedule_time, status, admin_id, driver_id, vehicle_type, created_at, updated_at)
                VALUES (?, ?, ?, 'assigned', ?, ?, ?, ?, ?)
                """,
                (route_no, trip_type, schedule_time, admin_id, driver_id, vehicle_type, now, now),
            )
            trip_id = cur.lastrowid

            # Assign employees
            seq = 1
            for eid in employee_ids:
                cur.execute(
                    """
                    INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    (trip_id, eid, seq, now),
                )
                seq += 1

            conn.commit()
            return success_response(
                {
                    "trip_id": trip_id,
                    "route_no": route_no,
                    "status": "assigned",
                },
                "Trip created and assigned",
                201,
            )
        finally:
            conn.close()

    @app.get("/api/admin/trips")
    @api_exception_handler("Failed to load trips list", include_traceback=False)
    def list_admin_trips():
        """
        List active trips (status in: created, assigned, started).
        
        Returns array with trip details + employee list.
        """
        conn = get_db()
        try:
            cur = conn.cursor()
            
            # Get active trips
            rows = _fetch_all(
                cur,
                """
                SELECT id, route_no, trip_type, schedule_time, status, driver_id, vehicle_type, created_at
                FROM trips
                WHERE status IN ('created', 'assigned', 'started')
                ORDER BY created_at DESC
                """,
            )

            # For each trip, attach driver and employee info
            result = []
            for trip in rows:
                trip_id = trip["id"]
                driver_id = trip["driver_id"]
                
                # Get driver info
                driver = _fetch_one(cur, "SELECT id, name, mobile, vehicle_no FROM drivers WHERE id = ?", (driver_id,))
                if driver:
                    trip["driver_name"] = driver["name"]
                    trip["driver_mobile"] = driver["mobile"]
                    trip["vehicle_no"] = driver["vehicle_no"]
                else:
                    trip["driver_name"] = "â€”"
                    trip["driver_mobile"] = "â€”"
                    trip["vehicle_no"] = "â€”"

                # Get employees for this trip
                emps = _fetch_all(
                    cur,
                    """
                    SELECT e.id, e.name, e.mobile, e.drop_location
                    FROM trip_employees te
                    JOIN employees e ON e.id = te.employee_id
                    WHERE te.trip_id = ?
                    ORDER BY te.sequence_no ASC
                    """,
                    (trip_id,),
                )
                trip["employees"] = emps or []

                result.append(trip)

            return success_response(result, "Trips list loaded")
        finally:
            conn.close()

    @app.put("/api/admin/trips/<int:trip_id>")
    @api_exception_handler("Failed to update trip", include_traceback=False)
    def update_trip_status(trip_id: int):
        """
        Update trip status (complete or cancel).
        
        body:
        {
          "status": "completed" | "cancelled",
          "cancel_reason": "..." (required if status='cancelled')
        }
        
        Returns updated trip info.
        """
        data = request.get_json(silent=True) or {}
        new_status = str(data.get("status", "")).strip().lower()

        if new_status not in ("completed", "cancelled"):
            raise APIError("status must be 'completed' or 'cancelled'.", 400, "VALIDATION_ERROR")

        cancel_reason = None
        if new_status == "cancelled":
            cancel_reason = str(data.get("cancel_reason", "")).strip()
            if not cancel_reason:
                raise APIError("cancel_reason is required when cancelling a trip.", 400, "VALIDATION_ERROR")

        conn = get_db()
        try:
            cur = conn.cursor()

            # Verify trip exists
            trip = _fetch_one(cur, "SELECT id, status FROM trips WHERE id = ?", (trip_id,))
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")

            # Update trip status
            now = _now_iso()
            if new_status == "cancelled":
                cur.execute(
                    """
                    UPDATE trips
                    SET status = 'cancelled', cancel_reason = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (cancel_reason, now, trip_id),
                )
            else:  # completed
                cur.execute(
                    """
                    UPDATE trips
                    SET status = 'completed', end_time = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, trip_id),
                )

            conn.commit()

            return success_response(
                {
                    "trip_id": trip_id,
                    "status": new_status,
                    "cancel_reason": cancel_reason,
                },
                f"Trip {new_status}",
                200,
            )
        finally:
            conn.close()

    # =====================================================
    # DRIVER PROFILE + HOMETOWN REQUEST
    # =====================================================
    @app.get("/api/driver/<driver_id>")
    @require_auth(roles=["admin", "driver"])
    @api_exception_handler("Failed to load driver profile", include_traceback=False)
    def get_driver_profile(driver_id: str):
        conn = get_db()
        try:
            cur = conn.cursor()
            row = _fetch_one(
                cur,
                """
                SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved,
                       dl_expiry, rc_expiry, insurance_expiry, fitness_expiry, permit_expiry,
                       created_at, updated_at
                FROM drivers WHERE id = ?
                """,
                (driver_id,),
            )
            if not row:
                raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")
            return success_response(row, "Driver profile loaded")
        finally:
            conn.close()

    @app.put("/api/driver/<driver_id>")
    @require_auth(roles=["admin", "driver"])
    @api_exception_handler("Failed to update driver profile", include_traceback=False)
    def update_driver_profile(driver_id: str):
        data = request.get_json(silent=True) or {}

        # Only fields we allow editing here (extend if needed)
        name = str(data.get("name", "")).strip() or None
        home_town = str(data.get("home_town", "")).strip() or None
        vehicle_type = str(data.get("vehicle_type", "")).strip() or None

        conn = get_db()
        try:
            cur = conn.cursor()
            row = _fetch_one(cur, "SELECT id FROM drivers WHERE id = ?", (driver_id,))
            if not row:
                raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")

            cur.execute(
                """
                UPDATE drivers
                SET name = COALESCE(?, name),
                    home_town = COALESCE(?, home_town),
                    vehicle_type = COALESCE(?, vehicle_type),
                    updated_at = ?
                WHERE id = ?
                """,
                (name, home_town, vehicle_type, _now_iso(), driver_id),
            )
            conn.commit()
            return success_response({"updated": True}, "Driver updated")
        finally:
            conn.close()

    @app.post("/api/driver/<driver_id>/hometown_request")
    @require_auth(roles=["driver"])
    @api_exception_handler("Failed to create hometown request", include_traceback=False)
    def driver_hometown_request(driver_id: str):
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["requested_home_town"])
        requested = str(data["requested_home_town"]).strip()

        conn = get_db()
        try:
            cur = conn.cursor()
            driver = _fetch_one(cur, "SELECT id FROM drivers WHERE id = ?", (driver_id,))
            if not driver:
                raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")

            cur.execute(
                """
                INSERT INTO driver_hometown_requests (driver_id, requested_home_town, status, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?)
                """,
                (driver_id, requested, _now_iso(), _now_iso()),
            )
            conn.commit()
            return success_response({"requested_home_town": requested, "status": "pending"}, "Request submitted")
        finally:
            conn.close()

    # =====================================================
    # EMPLOYEE CRUD (Admin)
    # =====================================================
    # MOVED TO routes/admin_routes.py

    # =====================================================
    # TRIPS: create + assign + list + live tracking + OTP
    # =====================================================

    @app.post("/api/trips/create")
    @require_auth(roles=["admin"])
    @api_exception_handler("Failed to create trip", include_traceback=False)
    def create_trip():
        """
        body:
        {
          "trip_type": "pickup"|"drop",
          "schedule_time": "HH:MM",
          "vehicle_type": "4"|"6",
          "employee_ids": ["emp1","emp2", ...]
        }
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["trip_type", "schedule_time", "vehicle_type", "employee_ids"])

        trip_type = str(data["trip_type"]).strip().lower()
        schedule_time = str(data["schedule_time"]).strip()
        vehicle_type = str(data["vehicle_type"]).strip()
        employee_ids = data.get("employee_ids", [])

        if trip_type not in ("pickup", "drop"):
            raise APIError("trip_type must be pickup or drop.", 400, "VALIDATION_ERROR")
        if not isinstance(employee_ids, list) or len(employee_ids) < 1:
            raise APIError("employee_ids must be a non-empty list.", 400, "VALIDATION_ERROR")
        if vehicle_type not in ("4", "6"):
            raise APIError("vehicle_type must be '4' or '6'.", 400, "VALIDATION_ERROR")

        # Admin identity from token (stored by require_auth)
        # utils.security attaches g.user_id but we don't import g here;
        # easiest: verify token again (safe)
        admin_id = g.user_id

        conn = get_db()
        try:
            cur = conn.cursor()

            # Ensure all employees exist and active
            qmarks = ",".join(["?"] * len(employee_ids))
            cur.execute(
                f"SELECT id, is_active FROM employees WHERE id IN ({qmarks})",
                tuple(employee_ids),
            )
            found = {r["id"]: int(r["is_active"]) for r in cur.fetchall()}
            missing = [eid for eid in employee_ids if eid not in found]
            if missing:
                raise APIError(f"Employees not found: {missing}", 404, "EMPLOYEE_NOT_FOUND")
            inactive = [eid for eid in employee_ids if found.get(eid, 0) != 1]
            if inactive:
                raise APIError(f"Employees inactive: {inactive}", 403, "EMPLOYEE_INACTIVE")

            # Create unique route_no for today
            rn = _get_unique_route_no_for_today(cur)
            day = trip_day_key()

            # Create trip
            cur.execute(
                """
                INSERT INTO trips
                (route_no, trip_day, trip_type, schedule_time, status, admin_id, driver_id, vehicle_type, total_km,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, 'created', ?, NULL, ?, 0, ?, ?)
                """,
                (rn, day, trip_type, schedule_time, admin_id, vehicle_type, _now_iso(), _now_iso()),
            )
            trip_id = cur.lastrowid

            # Attach employees
            created_at = _now_iso()
            seq = 1
            for eid in employee_ids:
                cur.execute(
                    """
                    INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    (trip_id, eid, seq, created_at),
                )
                seq += 1

            conn.commit()
            return success_response(
                {"trip_id": trip_id, "route_no": rn, "trip_day": day, "status": "created"},
                "Trip created",
                201,
            )
        finally:
            conn.close()

    @app.post("/api/trips/<int:trip_id>/assign_driver")
    @require_auth(roles=["admin"])
    @api_exception_handler("Failed to assign driver", include_traceback=False)
    def assign_driver(trip_id: int):
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["driver_id"])
        driver_id = str(data["driver_id"]).strip()

        conn = get_db()
        try:
            cur = conn.cursor()

            trip = _fetch_one(cur, "SELECT id, status FROM trips WHERE id = ?", (trip_id,))
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")

            drv = _fetch_one(cur, "SELECT id, is_approved FROM drivers WHERE id = ?", (driver_id,))
            if not drv:
                raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")
            if int(drv.get("is_approved", 0)) != 1:
                raise APIError("Driver not approved.", 403, "DRIVER_NOT_APPROVED")

            cur.execute(
                """
                UPDATE trips
                SET driver_id = ?,
                    status = CASE WHEN status='created' THEN 'assigned' ELSE status END,
                    updated_at = ?
                WHERE id = ?
                """,
                (driver_id, _now_iso(), trip_id),
            )
            conn.commit()
            return success_response({"trip_id": trip_id, "driver_id": driver_id}, "Driver assigned")
        finally:
            conn.close()

    @app.get("/api/trips")
    @require_auth(roles=["admin", "driver", "employee"])
    @api_exception_handler("Failed to list trips", include_traceback=False)
    def list_trips():
        """
        Query params:
          day=YYYYMMDD (optional)
          status=created/assigned/started/completed/cancelled (optional)
          trip_type=pickup/drop (optional)
        """
        day = str(request.args.get("day", "")).strip() or trip_day_key()
        status = str(request.args.get("status", "")).strip().lower()
        trip_type = str(request.args.get("trip_type", "")).strip().lower()

        where = ["trip_day = ?"]
        params: List[Any] = [day]

        if status:
            where.append("status = ?")
            params.append(status)
        if trip_type in ("pickup", "drop"):
            where.append("trip_type = ?")
            params.append(trip_type)

        conn = get_db()
        try:
            cur = conn.cursor()
            rows = _fetch_all(
                cur,
                f"""
                SELECT id, route_no, trip_day, trip_type, schedule_time, status,
                       admin_id, driver_id, vehicle_type, total_km,
                       start_time, end_time,
                       last_lat, last_lng, last_location_at,
                       created_at, updated_at
                FROM trips
                WHERE {' AND '.join(where)}
                ORDER BY created_at DESC
                """,
                tuple(params),
            )
            return success_response(rows, "Trips loaded")
        finally:
            conn.close()

    # -------- Live tracking update (Driver) --------
    @app.post("/api/trips/<int:trip_id>/location")
    @require_auth(roles=["driver"])
    @api_exception_handler("Failed to update location", include_traceback=False)
    def update_trip_location(trip_id: int):
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["lat", "lng"])

        lat = float(data["lat"])
        lng = float(data["lng"])

        # driver identity
        token = (request.headers.get("Authorization", "").split(" ", 1)[1]).strip()
        sess = verify_token(token)
        if not sess:
            raise APIError("Invalid token.", 401, "INVALID_TOKEN")
        driver_id = sess["user_id"]

        conn = get_db()
        try:
            cur = conn.cursor()
            trip = _fetch_one(cur, "SELECT id, driver_id FROM trips WHERE id = ?", (trip_id,))
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")
            if trip.get("driver_id") != driver_id:
                raise APIError("This trip is not assigned to you.", 403, "FORBIDDEN")

            cur.execute(
                """
                UPDATE trips
                SET last_lat = ?, last_lng = ?, last_location_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (lat, lng, _now_iso(), _now_iso(), trip_id),
            )
            conn.commit()
            return success_response({"trip_id": trip_id, "lat": lat, "lng": lng}, "Location updated")
        finally:
            conn.close()

    @app.get("/api/trips/<int:trip_id>/live")
    @require_auth(roles=["admin", "driver", "employee"])
    @api_exception_handler("Failed to fetch live location", include_traceback=False)
    def get_trip_live(trip_id: int):
        conn = get_db()
        try:
            cur = conn.cursor()
            trip = _fetch_one(
                cur,
                """
                SELECT id, route_no, status, driver_id, last_lat, last_lng, last_location_at
                FROM trips WHERE id = ?
                """,
                (trip_id,),
            )
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")
            return success_response(trip, "Live status")
        finally:
            conn.close()

    # -------- OTP generate (start/end) --------
    @app.post("/api/trips/<int:trip_id>/otp/generate")
    @require_auth(roles=["admin", "driver"])
    @api_exception_handler("Failed to generate OTP", include_traceback=False)
    def trip_generate_otp(trip_id: int):
        """
        body: {"type":"start"|"end"}
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["type"])
        otp_type = str(data["type"]).strip().lower()
        if otp_type not in ("start", "end"):
            raise APIError("type must be start or end.", 400, "VALIDATION_ERROR")

        otp_plain, otp_hash = generate_otp()
        expiry = otp_expiry_iso()

        conn = get_db()
        try:
            cur = conn.cursor()
            trip = _fetch_one(cur, "SELECT id FROM trips WHERE id = ?", (trip_id,))
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")

            if otp_type == "start":
                cur.execute(
                    """
                    UPDATE trips
                    SET start_otp_hash = ?, start_otp_expiry = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (otp_hash, expiry, _now_iso(), trip_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE trips
                    SET end_otp_hash = ?, end_otp_expiry = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (otp_hash, expiry, _now_iso(), trip_id),
                )

            conn.commit()
            # NOTE: In real system you would send OTP via SMS. For demo we return it.
            return success_response({"trip_id": trip_id, "type": otp_type, "otp": otp_plain, "expires_at": expiry}, "OTP generated")
        finally:
            conn.close()

    # -------- OTP verify (start/end) by Driver --------
    @app.post("/api/trips/<int:trip_id>/otp/verify")
    @require_auth(roles=["driver"])
    @api_exception_handler("Failed to verify OTP", include_traceback=False)
    def trip_verify_otp(trip_id: int):
        """
        body: {"type":"start"|"end", "otp":"123456"}
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["type", "otp"])

        otp_type = str(data["type"]).strip().lower()
        otp_plain = str(data["otp"]).strip()

        if otp_type not in ("start", "end"):
            raise APIError("type must be start or end.", 400, "VALIDATION_ERROR")
        if not (otp_plain.isdigit() and len(otp_plain) == 6):
            raise APIError("otp must be 6 digits.", 400, "VALIDATION_ERROR")

        token = (request.headers.get("Authorization", "").split(" ", 1)[1]).strip()
        sess = verify_token(token)
        if not sess:
            raise APIError("Invalid token.", 401, "INVALID_TOKEN")
        driver_id = sess["user_id"]

        conn = get_db()
        try:
            cur = conn.cursor()
            trip = _fetch_one(
                cur,
                """
                SELECT id, driver_id, status,
                       start_otp_hash, start_otp_expiry,
                       end_otp_hash, end_otp_expiry
                FROM trips WHERE id = ?
                """,
                (trip_id,),
            )
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")
            if trip.get("driver_id") != driver_id:
                raise APIError("This trip is not assigned to you.", 403, "FORBIDDEN")

            # Check expiry + hash
            if otp_type == "start":
                otp_hash = trip.get("start_otp_hash")
                exp = trip.get("start_otp_expiry")
            else:
                otp_hash = trip.get("end_otp_hash")
                exp = trip.get("end_otp_expiry")

            if not otp_hash or not exp:
                raise APIError("OTP not generated for this trip.", 400, "OTP_NOT_GENERATED")

            # expiry check
            try:
                # Ensure exp is string
                if not isinstance(exp, str):
                     raise APIError("Invalid OTP expiry format.", 500, "OTP_EXPIRY_INVALID")
                     
                exp_dt = datetime.fromisoformat(exp)
                if exp_dt < datetime.now():
                    raise APIError("OTP expired.", 400, "OTP_EXPIRED")
            except APIError:
                raise
            except Exception:
                # if stored format invalid
                raise APIError("OTP expiry invalid.", 500, "OTP_EXPIRY_INVALID")

            if not verify_otp(otp_plain, otp_hash):
                raise APIError("Invalid OTP.", 400, "OTP_INVALID")

            # Update trip status
            if otp_type == "start":
                cur.execute(
                    """
                    UPDATE trips
                    SET status = 'started',
                        start_time = COALESCE(start_time, ?),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (_now_iso(), _now_iso(), trip_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE trips
                    SET status = 'completed',
                        end_time = COALESCE(end_time, ?),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (_now_iso(), _now_iso(), trip_id),
                )

            conn.commit()
            return success_response({"trip_id": trip_id, "type": otp_type, "verified": True}, "OTP verified")
        finally:
            conn.close()

    # -------- No-show marking (Driver) --------
    @app.post("/api/trips/<int:trip_id>/employee/no_show")
    @require_auth(roles=["driver"])
    @api_exception_handler("Failed to mark no-show", include_traceback=False)
    def mark_no_show(trip_id: int):
        """
        body: {"employee_id":"emp_rg_001", "is_no_show": 1}
        """
        data = request.get_json(silent=True) or {}
        _require_fields(data, ["employee_id"])
        employee_id = str(data["employee_id"]).strip()
        is_no_show = int(data.get("is_no_show", 1))

        token = (request.headers.get("Authorization", "").split(" ", 1)[1]).strip()
        sess = verify_token(token)
        if not sess:
            raise APIError("Invalid token.", 401, "INVALID_TOKEN")
        driver_id = sess["user_id"]

        conn = get_db()
        try:
            cur = conn.cursor()

            trip = _fetch_one(cur, "SELECT id, driver_id FROM trips WHERE id = ?", (trip_id,))
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")
            if trip.get("driver_id") != driver_id:
                raise APIError("This trip is not assigned to you.", 403, "FORBIDDEN")

            cur.execute(
                """
                UPDATE trip_employees
                SET is_no_show = ?
                WHERE trip_id = ? AND employee_id = ?
                """,
                (1 if is_no_show else 0, trip_id, employee_id),
            )
            if cur.rowcount == 0:
                raise APIError("Employee is not part of this trip.", 404, "EMPLOYEE_NOT_IN_TRIP")

            conn.commit()
            return success_response({"trip_id": trip_id, "employee_id": employee_id, "is_no_show": 1 if is_no_show else 0}, "Updated")
        finally:
            conn.close()

    @app.get("/api/trips/<int:trip_id>/employees")
    @require_auth(roles=["admin", "driver"])
    @api_exception_handler("Failed to load trip employees", include_traceback=False)
    def trip_employees(trip_id: int):
        conn = get_db()
        try:
            cur = conn.cursor()
            trip = _fetch_one(cur, "SELECT id FROM trips WHERE id = ?", (trip_id,))
            if not trip:
                raise APIError("Trip not found.", 404, "TRIP_NOT_FOUND")

            rows = _fetch_all(
                cur,
                """
                SELECT te.employee_id, te.sequence_no, te.is_no_show,
                       e.name, e.mobile, e.drop_location, e.drop_lat, e.drop_lng
                FROM trip_employees te
                JOIN employees e ON e.id = te.employee_id
                WHERE te.trip_id = ?
                ORDER BY te.sequence_no ASC
                """,
                (trip_id,),
            )
            return success_response(rows, "Trip employees loaded")
        finally:
            conn.close()

    # -----------------------------------------------------
    # Clean 404 for Flutter (instead of HTML)
    # -----------------------------------------------------
    @app.errorhandler(404)
    def not_found(_e):
        return error_response("Endpoint not found.", 404, "NOT_FOUND")

    return app


# WSGI callable
app = create_app()

if __name__ == "__main__":
    from services.socket_service import socketio
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"Server running on port {port} (WebSocket Enabled)...")
    # Use socketio.run to support WebSocket
    socketio.run(app, host="0.0.0.0", port=port, debug=True, use_reloader=False)

