# backend/routes/auth_routes.py
from __future__ import annotations

from flask import Blueprint, request
from datetime import datetime
import re
import secrets

from db import get_db
from utils.response import ok, fail, success_response, error_response
from utils.security import hash_password, verify_password, create_token
from repositories.request_repo import RequestRepo

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

# STRICT REGEX PATTERNS
REGEX_MOBILE = r"^\d{10}$"
REGEX_DL = r"^[A-Za-z]{2}\d{13}$"
REGEX_CAB = r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$"

def validate_regex(value: str, pattern: str) -> bool:
    return bool(re.match(pattern, value))

def _row_dict(row):
    return dict(row) if row else None

# =========================================================
# 1. ADMIN LOGIN
# =========================================================
@auth_bp.post("/admin/login")
def admin_login():
    """
    POST /api/auth/admin/login
    Body: {name, mobile, password}
    
    Requires ALL 3 fields:
    - name: Admin name (case-insensitive match)
    - mobile: 10-digit mobile number
    - password: Admin password
    """
    data = request.json or {}
    name = str(data.get("name", "")).strip()
    mobile = str(data.get("mobile", "")).strip()
    password = str(data.get("password", "")).strip()

    # Validate all 3 fields
    if not name:
        return fail("Admin name is required.", 400)
    if not validate_regex(mobile, REGEX_MOBILE):
        return fail("Mobile must be exactly 10 digits.", 400)
    if not password:
        return fail("Password is required.", 400)
    if len(password) < 4:
        return fail("Password too short.", 400)

    conn = get_db()
    cur = conn.cursor()
    
    # Find admin using BOTH name (case-insensitive) AND mobile
    cur.execute("""
        SELECT * FROM admins 
        WHERE LOWER(name) = LOWER(?) AND mobile = ?
    """, (name, mobile))
    row = _row_dict(cur.fetchone())
    conn.close()

    if not row:
        return fail("Admin not found.", 404)
    
    # Verify password
    if not verify_password(password, row["password_salt"], row["password_hash"]):
        return fail("Invalid credentials.", 401)

    # Success - return admin data including name
    token_data = create_token(row["id"], "admin")
    # Success - return admin data including name
    token_data = create_token(row["id"], "admin")
    return ok(
        data={
            "id": row["id"],
            "adminId": row["id"],
            "name": row["name"],
            "mobile": row["mobile"],
            "token": token_data["token"]
        },
        message="Login successful"
    )

# =========================================================
# 2. DRIVER LOGIN
# =========================================================
@auth_bp.post("/driver/login")
def driver_login():
    """
    POST /api/auth/driver/login
    Body: {mobile, dl_no, cab_no} 
    (Note: Frontend sends this. Backend earlier used mobile+password. We adapter here.)
    """
    data = request.json or {}
    mobile = str(data.get("mobile", "")).strip()
    dl_no = str(data.get("dl_no", "")).strip()
    cab_no = str(data.get("cab_no", "")).strip().upper().replace(" ", "")

    if not validate_regex(mobile, REGEX_MOBILE):
        return fail("Mobile must be exactly 10 digits.", 400)
    
    # Note: Frontend sends DL/Cab for login validation in some flows, or maybe just mobile+password depending on implementation.
    # The prompt user request says: "Driver Login: name, mobile, cabNo". 
    # But standard auth usually needs a secret (password). 
    # IF the frontend is sending name/mobile/cabNo as 'credentials', that's insecure but we must match requirements.
    # HOWEVER, existing backend expected password.
    # User's frontend walkthrough: "Driver Login: Mobile, DL No, Cab No". NO PASSWORD in prompt details for Driver Login!
    # So we must authenticate using these 3 fields matching.

    if not validate_regex(dl_no, REGEX_DL):
        return fail("Invalid DL format.", 400)
    if not validate_regex(cab_no, REGEX_CAB):
        return fail("Invalid Cab format.", 400)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM drivers WHERE mobile = ?", (mobile,))
    row = _row_dict(cur.fetchone())
    conn.close()

    if not row:
        return fail("Driver not found.", 404)

    # Verify matching details (DL + Cab) as 'password' replacement
    if row["dl_no"] != dl_no:
        return fail("DL Number does not match records.", 401)
    
    # Check vehicle_no (cab_no in prompt) - might need normalization check
    db_veh = row["vehicle_no"].upper().replace(" ", "")
    if db_veh != cab_no:
        return fail("Cab Number does not match records.", 401)

    # Check approval
    if int(row.get("is_approved", 0)) != 1:
        return fail("Account pending approval.", 403)

    token_data = create_token(row["id"], "driver")
    token_data = create_token(row["id"], "driver")
    return ok(
        data={
            "id": row["id"],
            "driverId": row["id"],
            "name": row["name"],
            "mobile": row["mobile"],
            "cabNo": row["vehicle_no"],
            "approved": True,
            "token": token_data["token"]
        },
        message="Login successful"
    )

# =========================================================
# 3. EMPLOYEE LOGIN
# =========================================================
@auth_bp.post("/employee/login")
def employee_login():
    """
    POST /api/auth/employee/login
    Body: {mobile, employeeId} or {mobile, employee_code}
    """
    data = request.json or {}
    mobile = str(data.get("mobile", "")).strip()
    emp_code = str(
        data.get("employeeId", data.get("employee_code", data.get("employeeCode", "")))
    ).strip()

    if not validate_regex(mobile, REGEX_MOBILE):
        return fail("Mobile must be exactly 10 digits.", 400)
    if len(emp_code) < 3:
        return fail("Invalid Employee ID.", 400)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE mobile = ?", (mobile,))
    row = _row_dict(cur.fetchone())
    conn.close()

    if not row:
        return fail("Employee not found.", 404)

    # Verify employee identity: allow DB id OR employee_code from frontend.
    row_id = str(row.get("id", ""))
    row_emp_code = str(row.get("employee_code", ""))
    if emp_code not in (row_id, row_emp_code):
        return fail("Employee ID does not match records.", 401)
    
    # Check approval
    if int(row.get("is_approved", 0)) != 1:
        return fail("Account pending approval.", 403)

    token_data = create_token(row["id"], "employee")
    return ok(
        data={
            "id": row["id"],
            "employeeId": row["id"],
            "name": row["name"],
            "mobile": row["mobile"],
            "approved": True,
            "token": token_data["token"]
        },
        message="Login successful"
    )


# =========================================================
# 4. PUBLIC ADMIN DIRECTORY
# =========================================================
@auth_bp.get("/companies")
@auth_bp.get("/admins")
def list_companies():
    """
    Public company/admin directory for signup flows.
    Returns only minimal non-sensitive fields required for company selection.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(admins)")
        cols = {str(r[1]) for r in cur.fetchall()}

        office_name_expr = "office_name" if "office_name" in cols else "NULL"
        office_address_expr = "office_address" if "office_address" in cols else (
            "office_location" if "office_location" in cols else "NULL"
        )

        cur.execute(
            f"""
            SELECT
                id,
                name,
                COALESCE(NULLIF({office_name_expr}, ''), name) AS company_name,
                COALESCE(NULLIF({office_address_expr}, ''), '') AS office_address
            FROM admins
            ORDER BY company_name ASC, name ASC
            """
        )
        rows = [_row_dict(r) for r in cur.fetchall() or []]
        return ok(data=rows, message="Companies loaded")
    finally:
        conn.close()


# =========================================================
# 5. DRIVER REGISTRATION REQUEST
# =========================================================
@auth_bp.post("/driver/signup-request")
@auth_bp.post("/driver/request") # Alias
def driver_request():
    """
    Body: {name, mobile, dlNo, cabNo, homeTown, (vehicle_type optional?)}
    """
    data = request.json or {}
    name = str(data.get("name", "")).strip()
    mobile = str(data.get("mobile", "")).strip()
    dl_no = str(data.get("dlNo", data.get("dl_no", ""))).strip()
    cab_no = str(data.get("cabNo", data.get("cab_no", ""))).strip().upper().replace(" ", "")
    home_town = str(data.get("homeTown", data.get("home_town", ""))).strip()
    raw_lat = data.get("home_lat", data.get("lat"))
    raw_lng = data.get("home_lng", data.get("lng"))
    admin_id = str(data.get("admin_id", data.get("adminId", ""))).strip() or None

    driver_vehicle_type = str(data.get("vehicleType", data.get("vehicle_type", "4"))).strip()

    # Validations
    if len(name) < 2: return fail("Name too short", 400)
    if not validate_regex(mobile, REGEX_MOBILE): return fail("Invalid Mobile (10 digits)", 400)
    if not validate_regex(dl_no, REGEX_DL): return fail("Invalid DL Format (AA1234567890123)", 400)
    if not validate_regex(cab_no, REGEX_CAB): return fail("Invalid Cab No (MH12AB1234)", 400)
    if len(home_town) < 3: return fail("Home town required", 400)
    if driver_vehicle_type not in ["4", "6"]: return fail("Vehicle Type must be 4 or 6", 400)
    if not admin_id: return fail("Company selection is required", 400)
    home_lat = None
    home_lng = None
    if (raw_lat is not None) or (raw_lng is not None):
        try:
            home_lat = float(raw_lat)
            home_lng = float(raw_lng)
        except Exception:
            return fail("home_lat/home_lng invalid", 400)
        if not (-90.0 <= home_lat <= 90.0 and -180.0 <= home_lng <= 180.0):
            return fail("home_lat/home_lng out of range", 400)

    conn = get_db()
    # Check if exists in main table already
    cur = conn.cursor()
    cur.execute("SELECT id FROM admins WHERE id = ? LIMIT 1", (admin_id,))
    if not cur.fetchone():
        conn.close()
        return fail("Selected company not found", 404)

    cur.execute("SELECT id FROM drivers WHERE mobile = ?", (mobile,))
    if cur.fetchone():
        conn.close()
        return fail("Driver already registered.", 409)

    # Create Request
    repo = RequestRepo(conn)
    req_id = repo.create_driver_request(
        name,
        mobile,
        dl_no,
        cab_no,
        home_town,
        vehicle_type=driver_vehicle_type,
        lat=home_lat,
        lng=home_lng,
        admin_id=admin_id,
    )
    conn.close()

    return ok(
        data={"requestId": req_id, "status": "Pending"},
        message="Request sent successfully"
    )

# =========================================================
# 6. EMPLOYEE REGISTRATION REQUEST
# =========================================================
@auth_bp.post("/employee/signup-request")
@auth_bp.post("/employee/request") # Alias
def employee_request():
    """
    Body: {name, mobile, loginTime, logoutTime, homeAddress}
    """
    data = request.json or {}
    name = str(data.get("name", "")).strip()
    mobile = str(data.get("mobile", "")).strip()
    login_time = str(data.get("loginTime", data.get("login_time", ""))).strip()
    logout_time = str(data.get("logoutTime", data.get("logout_time", ""))).strip()
    home = str(data.get("homeAddress", data.get("home_address", ""))).strip()
    raw_lat = data.get("home_lat", data.get("lat"))
    raw_lng = data.get("home_lng", data.get("lng"))
    admin_id = str(data.get("admin_id", data.get("adminId", ""))).strip() or None

    if len(name) < 2: return fail("Name too short", 400)
    if not validate_regex(mobile, REGEX_MOBILE): return fail("Invalid Mobile", 400)
    if not login_time or not logout_time: return fail("Times required", 400)
    if len(home) < 5: return fail("Valid home address required", 400)
    if not admin_id: return fail("Company selection is required", 400)

    home_lat = None
    home_lng = None
    if (raw_lat is not None) or (raw_lng is not None):
        try:
            home_lat = float(raw_lat)
            home_lng = float(raw_lng)
        except Exception:
            return fail("home_lat/home_lng invalid", 400)
        if not (-90.0 <= home_lat <= 90.0 and -180.0 <= home_lng <= 180.0):
            return fail("home_lat/home_lng out of range", 400)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM admins WHERE id = ? LIMIT 1", (admin_id,))
    if not cur.fetchone():
        conn.close()
        return fail("Selected company not found", 404)

    cur.execute("SELECT id FROM employees WHERE mobile = ?", (mobile,))
    if cur.fetchone():
        conn.close()
        return fail("Employee already registered", 409)

    repo = RequestRepo(conn)
    req_id = repo.create_employee_request(
        name,
        mobile,
        login_time,
        logout_time,
        home,
        lat=home_lat,
        lng=home_lng,
        admin_id=admin_id,
    )
    conn.close()

    return ok(
        data={"requestId": req_id, "status": "Pending"},
        message="Request sent successfully"
    )
