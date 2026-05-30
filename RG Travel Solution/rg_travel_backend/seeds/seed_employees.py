# backend/seeds/seed_employee.py
"""
RG Travel Solution - Employee Seeder + Seed APIs

✅ Folder: backend/seeds/
✅ File:   seed_employee.py

This file provides:
1) Creates required DB table (employees) if not exists
2) Seeds default employees ONLY when you call the seed endpoint
3) Seed APIs/endpoints for:
   - seed status
   - seed (insert/upsert employees)
   - reset (delete all employees then seed)
   - (optional helper) list employees for quick UI testing

✅ Endpoints (after you register routes in app.py):
- GET  /api/employees/seed/status
- POST /api/employees/seed
- POST /api/employees/seed/reset
- GET  /api/employees/seed/list   (dev helper)

Matches your project requirements:
- employees have login_time / logout_time
- pickup/drop grouping uses time fields
- permanent drop location stored
- employee edit support via upsert

Assumes:
- backend/db.py has get_db() returning sqlite3 connection
"""

from __future__ import annotations

import sqlite3
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, request, jsonify


# ---------------------------------------------------------
# Safe import of get_db (supports multiple run layouts)
# ---------------------------------------------------------
def _import_get_db():
    try:
        from ..db import get_db  # type: ignore
        return get_db
    except Exception:
        pass

    try:
        from db import get_db  # type: ignore
        return get_db
    except Exception as e:
        raise ImportError(
            "Could not import get_db(). Ensure backend/db.py has get_db() "
            "and run app.py from correct folder."
        ) from e


get_db = _import_get_db()


# ==========================
# Utilities
# ==========================
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _is_valid_mobile(m: str) -> bool:
    return m.isdigit() and len(m) == 10


def _is_valid_time_hhmm(t: str) -> bool:
    """
    Validates time format 'HH:MM' in 24-hour.
    """
    try:
        datetime.strptime(t, "%H:%M")
        return True
    except Exception:
        return False


# ==========================
# Table creation
# ==========================
def ensure_employee_tables() -> None:
    """
    Creates employees table if not exists.
    Fields support:
    - employee login
    - pickup/drop times for grouping
    - permanent drop location storage
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id TEXT PRIMARY KEY,

                name TEXT NOT NULL,
                mobile TEXT NOT NULL UNIQUE,
                email TEXT,

                -- Work timing (used for pickup/drop grouping)
                login_time TEXT,        -- HH:MM (employee login time)
                logout_time TEXT,       -- HH:MM (employee logout time)

                -- Locations
                pickup_location TEXT,   -- optional fixed pickup (if you use)
                drop_location TEXT,     -- permanent drop location (your requirement)
                drop_lat REAL,
                drop_lng REAL,

                is_active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ==========================
# Seed data
# ==========================
def default_employee_seed_list() -> List[Dict[str, Any]]:
    """
    Default employees to seed.
    ✅ Seeds only when /api/employees/seed is called.
    """
    return [
        {
            "id": "emp_rg_001",
            "name": "Rohit Kulkarni",
            "mobile": "8000000001",
            "email": "rohit@rg.com",
            "login_time": "09:30",
            "logout_time": "18:30",
            "pickup_location": "RG Office Gate, Pune",
            "drop_location": "Kothrud, Pune",
            "drop_lat": 18.5074,
            "drop_lng": 73.8077,
            "is_active": 1,
        },
        {
            "id": "emp_rg_002",
            "name": "Sneha Deshmukh",
            "mobile": "8000000002",
            "email": "sneha@rg.com",
            "login_time": "10:00",
            "logout_time": "19:00",
            "pickup_location": "RG Office Gate, Pune",
            "drop_location": "Hinjewadi Phase 1, Pune",
            "drop_lat": 18.5865,
            "drop_lng": 73.7360,
            "is_active": 1,
        },
        {
            "id": "emp_rg_003",
            "name": "Vishal Pawar",
            "mobile": "8000000003",
            "email": "vishal@rg.com",
            "login_time": "09:30",
            "logout_time": "18:30",
            "pickup_location": "RG Office Gate, Pune",
            "drop_location": "Wakad, Pune",
            "drop_lat": 18.5993,
            "drop_lng": 73.7707,
            "is_active": 1,
        },
    ]


def validate_employee_payload(e: Dict[str, Any]) -> Tuple[bool, str]:
    name = str(e.get("name", "")).strip()
    mobile = str(e.get("mobile", "")).strip()

    if len(name) < 2:
        return False, "Employee name must be at least 2 characters."
    if not _is_valid_mobile(mobile):
        return False, "Employee mobile must be exactly 10 digits."

    email = str(e.get("email") or "").strip()
    if email and "@" not in email:
        return False, "Invalid email format."

    login_time = str(e.get("login_time") or "").strip()
    logout_time = str(e.get("logout_time") or "").strip()
    if login_time and not _is_valid_time_hhmm(login_time):
        return False, "login_time must be in HH:MM format."
    if logout_time and not _is_valid_time_hhmm(logout_time):
        return False, "logout_time must be in HH:MM format."

    # drop_lat/lng if present must be numeric
    for k in ["drop_lat", "drop_lng"]:
        if e.get(k) is not None:
            try:
                float(e.get(k))
            except Exception:
                return False, f"{k} must be numeric."

    if e.get("is_active") is not None:
        try:
            ia = int(e.get("is_active"))
            if ia not in (0, 1):
                return False, "is_active must be 0 or 1."
        except Exception:
            return False, "is_active must be 0 or 1."

    return True, "ok"


def upsert_employee(e: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert by mobile (unique).
    If exists -> update
    If not -> insert
    """
    ensure_employee_tables()

    ok, msg = validate_employee_payload(e)
    if not ok:
        raise ValueError(msg)

    emp_id = str(e.get("id") or "").strip() or f"emp_{secrets.token_hex(6)}"
    name = str(e.get("name")).strip()
    mobile = str(e.get("mobile")).strip()
    email = str(e.get("email") or "").strip() or None

    login_time = str(e.get("login_time") or "").strip() or None
    logout_time = str(e.get("logout_time") or "").strip() or None

    pickup_location = str(e.get("pickup_location") or "").strip() or None
    drop_location = str(e.get("drop_location") or "").strip() or None

    drop_lat = e.get("drop_lat")
    drop_lng = e.get("drop_lng")
    drop_lat = float(drop_lat) if drop_lat is not None else None
    drop_lng = float(drop_lng) if drop_lng is not None else None

    is_active = int(e.get("is_active", 1))

    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM employees WHERE mobile = ?", (mobile,))
        row = cur.fetchone()

        if row:
            existing_id = row[0] if isinstance(row, (tuple, list)) else row["id"]
            cur.execute(
                """
                UPDATE employees
                SET
                    name = ?,
                    email = ?,
                    login_time = ?,
                    logout_time = ?,
                    pickup_location = ?,
                    drop_location = ?,
                    drop_lat = ?,
                    drop_lng = ?,
                    is_active = ?,
                    updated_at = ?
                WHERE mobile = ?
                """,
                (
                    name,
                    email,
                    login_time,
                    logout_time,
                    pickup_location,
                    drop_location,
                    drop_lat,
                    drop_lng,
                    is_active,
                    _now_iso(),
                    mobile,
                ),
            )
            saved_id = existing_id
            action = "updated"
        else:
            cur.execute(
                """
                INSERT INTO employees (
                    id, name, mobile, email,
                    login_time, logout_time,
                    pickup_location, drop_location, drop_lat, drop_lng,
                    is_active,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    emp_id,
                    name,
                    mobile,
                    email,
                    login_time,
                    logout_time,
                    pickup_location,
                    drop_location,
                    drop_lat,
                    drop_lng,
                    is_active,
                    _now_iso(),
                    _now_iso(),
                ),
            )
            saved_id = emp_id
            action = "created"

        conn.commit()

        return {
            "action": action,
            "employee": {
                "id": saved_id,
                "name": name,
                "mobile": mobile,
                "email": email,
                "login_time": login_time,
                "logout_time": logout_time,
                "pickup_location": pickup_location,
                "drop_location": drop_location,
                "drop_lat": drop_lat,
                "drop_lng": drop_lng,
                "is_active": is_active,
            },
        }
    finally:
        conn.close()


def seed_many(employees: List[Dict[str, Any]]) -> Dict[str, Any]:
    created = 0
    updated = 0
    results: List[Dict[str, Any]] = []

    for e in employees:
        r = upsert_employee(e)
        results.append(r)
        if r["action"] == "created":
            created += 1
        else:
            updated += 1

    return {"created": created, "updated": updated, "results": results}


def get_seed_status() -> Dict[str, Any]:
    ensure_employee_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM employees")
        total = cur.fetchone()[0]
        return {"employees_count": int(total)}
    finally:
        conn.close()


def reset_employees_and_seed_default() -> Dict[str, Any]:
    ensure_employee_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM employees")
        conn.commit()
    finally:
        conn.close()

    return seed_many(default_employee_seed_list())


def list_employees(limit: int = 200) -> List[Dict[str, Any]]:
    """
    Dev helper for quick UI testing.
    """
    ensure_employee_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, email, login_time, logout_time,
                   pickup_location, drop_location, drop_lat, drop_lng, is_active,
                   created_at, updated_at
            FROM employees
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            if isinstance(r, (tuple, list)):
                # If row_factory not dict-like, map by index
                out.append(
                    {
                        "id": r[0],
                        "name": r[1],
                        "mobile": r[2],
                        "email": r[3],
                        "login_time": r[4],
                        "logout_time": r[5],
                        "pickup_location": r[6],
                        "drop_location": r[7],
                        "drop_lat": r[8],
                        "drop_lng": r[9],
                        "is_active": r[10],
                        "created_at": r[11],
                        "updated_at": r[12],
                    }
                )
            else:
                out.append(dict(r))
        return out
    finally:
        conn.close()


# ==========================
# Seed API / Endpoints
# ==========================
seed_bp = Blueprint("seed_employee", __name__, url_prefix="/api/employees/seed")


@seed_bp.route("/status", methods=["GET"])
def seed_status():
    try:
        return jsonify(success=True, data=get_seed_status())
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("", methods=["POST"])
def seed_create_or_update():
    """
    If request body empty -> seed default employees list
    If body contains:
      - {"employees": [ ... ]} -> seeds those employees
      - or a single employee object -> seeds that one
    """
    try:
        body = request.get_json(silent=True) or {}

        if not body:
            employees = default_employee_seed_list()
        elif isinstance(body.get("employees"), list):
            employees = body["employees"]
        else:
            employees = [body]

        result = seed_many(employees)
        return jsonify(
            success=True,
            message=f"Employees seed done. created={result['created']}, updated={result['updated']}",
            data=result,
        )
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except sqlite3.IntegrityError as se:
        return jsonify(success=False, message=f"DB integrity error: {se}"), 409
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("/reset", methods=["POST"])
def seed_reset():
    """
    DANGER: deletes all employees then seeds default list.
    """
    try:
        result = reset_employees_and_seed_default()
        return jsonify(success=True, message="Employees reset and seeded.", data=result)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("/list", methods=["GET"])
def seed_list_employees():
    """
    Dev helper endpoint.
    """
    try:
        limit = int(request.args.get("limit", "200"))
        if limit < 1:
            limit = 1
        if limit > 1000:
            limit = 1000
        data = list_employees(limit=limit)
        return jsonify(success=True, data=data)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


def register_seed_employee_routes(app):
    """
    Register these endpoints from app.py:

        from seeds.seed_employee import register_seed_employee_routes
        register_seed_employee_routes(app)
    """
    app.register_blueprint(seed_bp)


if __name__ == "__main__":
    print("Seeding default employees into DB...")
    print(seed_many(default_employee_seed_list()))
