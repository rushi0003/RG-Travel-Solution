# backend/routes/admin_requests_routes.py
from __future__ import annotations
from flask import Blueprint, request, g
from db import get_db
from utils.response import ok, fail
from utils.security import hash_password, require_auth
from repositories.request_repo import RequestRepo
import secrets
import datetime

admin_req_bp = Blueprint("admin_req_bp", __name__, url_prefix="/api/admin/requests")

def _now_iso():
    return datetime.datetime.utcnow().isoformat()


def _current_admin_id() -> str:
    return str(getattr(g, "user_id", "") or "").strip()

# ===========================
# DRIVERS
# ===========================
@admin_req_bp.get("/drivers")
@require_auth(roles=["admin"])
def list_driver_requests():
    conn = get_db()
    repo = RequestRepo(conn)
    rows = repo.list_pending_driver_requests(admin_id=_current_admin_id())
    conn.close()
    return ok({"success": True, "data": rows})

@admin_req_bp.post("/drivers/<int:req_id>/approve")
@require_auth(roles=["admin"])
def approve_driver(req_id):
    conn = get_db()
    repo = RequestRepo(conn)
    admin_id = _current_admin_id()
    
    req = repo.get_driver_request_by_id(req_id, admin_id=admin_id)
    if not req or str(req.get("status") or "").strip().lower() != "pending":
        conn.close()
        return fail("Request not found or not pending", 404)
    repo.claim_request_admin(table_name="driver_requests", req_id=req_id, admin_id=admin_id)

    # Move to main drivers table
    # Generate dummy password or N/A since they login with DL/CabNo
    # But schema requires password info
    salt, p_hash = hash_password("123456") # Default password, though they use DL
    
    new_id = f"drv_{secrets.token_hex(4)}"
    
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved, password_salt, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (new_id, req["name"], req["mobile"], req["dl_no"], req["cab_no"], '4', req["home_town"], salt, p_hash, _now_iso(), _now_iso())
        )
        repo.update_driver_request_status(req_id, "Approved")
        conn.commit()
    except Exception as e:
        conn.close()
        return fail(f"Error creating driver: {str(e)}", 500)

    conn.close()
    return ok({"success": True, "message": "Driver approved", "driverId": new_id})

@admin_req_bp.post("/drivers/<int:req_id>/reject")
@require_auth(roles=["admin"])
def reject_driver(req_id):
    conn = get_db()
    repo = RequestRepo(conn)
    admin_id = _current_admin_id()
    req = repo.get_driver_request_by_id(req_id, admin_id=admin_id)
    if not req:
        conn.close()
        return fail("Request not found", 404)
    repo.claim_request_admin(table_name="driver_requests", req_id=req_id, admin_id=admin_id)
    repo.update_driver_request_status(req_id, "Rejected")
    conn.close()
    return ok({"success": True, "message": "Request rejected"})


# ===========================
# EMPLOYEES
# ===========================
@admin_req_bp.get("/employees")
@require_auth(roles=["admin"])
def list_employee_requests():
    conn = get_db()
    repo = RequestRepo(conn)
    rows = repo.list_pending_employee_requests(admin_id=_current_admin_id())
    conn.close()
    return ok({"success": True, "data": rows})

@admin_req_bp.post("/employees/<int:req_id>/approve")
@require_auth(roles=["admin"])
def approve_employee(req_id):
    conn = get_db()
    repo = RequestRepo(conn)
    admin_id = _current_admin_id()
    
    req = repo.get_employee_request_by_id(req_id, admin_id=admin_id)
    if not req or str(req.get("status") or "").strip().lower() != "pending":
        conn.close()
        return fail("Request not found", 404)
    repo.claim_request_admin(table_name="employee_requests", req_id=req_id, admin_id=admin_id)

    # Generate Employee Code ? Or provided?
    # User prompt said: Employee Registration Request: name, mobile... (no emp code)
    # Employee Login: ... employeeId (which is code).
    # So ADMIN MUST GENERATE EMPLOYEE ID/CODE upon approval.
    
    emp_code = f"EMP{secrets.choice('123456789')}{secrets.token_hex(2).upper()}" # simple gen
    new_id = f"emp_{secrets.token_hex(4)}"
    
    salt, p_hash = hash_password("123456") 

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO employees (id, name, mobile, employee_code, login_time, logout_time, home_address, is_approved, pass_salt, pass_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (new_id, req["name"], req["mobile"], emp_code, req["login_time"], req["logout_time"], req["home_address"], salt, p_hash, _now_iso(), _now_iso())
        )
        repo.update_employee_request_status(req_id, "Approved")
        conn.commit()
    except Exception as e:
        conn.close()
        return fail(str(e), 500)
        
    conn.close()
    return ok({"success": True, "message": "Employee approved", "employeeId": new_id, "employeeCode": emp_code})

@admin_req_bp.post("/employees/<int:req_id>/reject")
@require_auth(roles=["admin"])
def reject_employee(req_id):
    conn = get_db()
    repo = RequestRepo(conn)
    admin_id = _current_admin_id()
    req = repo.get_employee_request_by_id(req_id, admin_id=admin_id)
    if not req:
        conn.close()
        return fail("Request not found", 404)
    repo.claim_request_admin(table_name="employee_requests", req_id=req_id, admin_id=admin_id)
    repo.update_employee_request_status(req_id, "Rejected")
    conn.close()
    return ok({"success": True, "message": "Request rejected"})
