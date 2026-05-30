# backend/seeds/seed_drivers.py
"""
RG Travel Solution - Driver Seeder + Seed APIs

✅ Folder: backend/seeds/
✅ File:   seed_drivers.py

What this file provides:
1) Creates required DB tables (drivers) if not exist
2) Seeds demo drivers ONLY when you call the seed endpoint (no auto seed)
3) Provides APIs/endpoints for:
   - seed status
   - seed (insert/upsert drivers)
   - reset (delete all drivers then seed)

✅ Endpoints (after you register routes in app.py):
- GET  /api/drivers/seed/status
- POST /api/drivers/seed
- POST /api/drivers/seed/reset

NOTES (matches your project needs):
- driver license no. stored in db (dl_no)
- vehicle no. stored in db (vehicle_no)
- driver hometown stored (home_town)
- admin approval field (is_approved) default 0 (pending)
- documents expiry dates stored; expired docs flagged by API response

This file assumes you already have:
- backend/db.py with get_db() returning sqlite3 connection
"""

from __future__ import annotations

import sqlite3
import hashlib
import secrets
from datetime import datetime, date
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


def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Returns (salt, password_hash) using sha256(salt + password).
    For production, use bcrypt/argon2.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, h


def _is_valid_mobile(m: str) -> bool:
    return m.isdigit() and len(m) == 10


def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        # expecting YYYY-MM-DD
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None


def _is_expired(d: Optional[str]) -> bool:
    dt = _parse_date(d)
    if not dt:
        return False
    return dt < date.today()


# ==========================
# Table creation
# ==========================
def ensure_driver_tables() -> None:
    """
    Creates drivers table if not exists.
    Fields are designed to support:
    - driver login
    - admin approval workflow
    - hometown-based assignment
    - document expiry highlighting
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS drivers (
                id TEXT PRIMARY KEY,

                name TEXT NOT NULL,
                mobile TEXT NOT NULL UNIQUE,

                dl_no TEXT NOT NULL UNIQUE,
                vehicle_no TEXT NOT NULL UNIQUE,
                vehicle_type TEXT,                  -- cab type: 4/6 seater, etc.

                home_town TEXT,                     -- for hometown assignment logic
                is_approved INTEGER NOT NULL DEFAULT 0,  -- 0=pending,1=approved,2=rejected

                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,

                -- Document info (expiry highlighting)
                dl_expiry TEXT,                     -- YYYY-MM-DD
                rc_expiry TEXT,                     -- YYYY-MM-DD
                insurance_expiry TEXT,              -- YYYY-MM-DD
                fitness_expiry TEXT,                -- YYYY-MM-DD
                permit_expiry TEXT,                 -- YYYY-MM-DD

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
def default_driver_seed_list() -> List[Dict[str, Any]]:
    """
    Default drivers to seed.
    ✅ These are only inserted when you call seed endpoint.
    You can modify these values anytime.
    """
    return [
        {
            "id": "drv_rg_001",
            "name": "Rahul Patil",
            "mobile": "9000000001",
            "password": "driver123",
            "dl_no": "MH12DL1111111",
            "vehicle_no": "MH12AB1234",
            "vehicle_type": "4",
            "home_town": "Pune",
            "is_approved": 1,
            "dl_expiry": "2030-12-31",
            "rc_expiry": "2030-12-31",
            "insurance_expiry": "2028-12-31",
            "fitness_expiry": "2027-12-31",
            "permit_expiry": "2029-12-31",
        },
        {
            "id": "drv_rg_002",
            "name": "Amit Shinde",
            "mobile": "9000000002",
            "password": "driver123",
            "dl_no": "MH14DL2222222",
            "vehicle_no": "MH14CD5678",
            "vehicle_type": "6",
            "home_town": "Nashik",
            "is_approved": 0,  # pending
            "dl_expiry": "2029-10-10",
            "rc_expiry": "2029-10-10",
            "insurance_expiry": "2027-10-10",
            "fitness_expiry": "2026-05-20",
            "permit_expiry": "2028-03-15",
        },
    ]


def validate_driver_payload(d: Dict[str, Any]) -> Tuple[bool, str]:
    name = str(d.get("name", "")).strip()
    mobile = str(d.get("mobile", "")).strip()
    password = str(d.get("password", "")).strip()
    dl_no = str(d.get("dl_no", "")).strip()
    vehicle_no = str(d.get("vehicle_no", "")).strip()

    if len(name) < 2:
        return False, "Driver name must be at least 2 characters."
    if not _is_valid_mobile(mobile):
        return False, "Driver mobile must be exactly 10 digits."
    if len(password) < 4:
        return False, "Driver password must be at least 4 characters."
    if len(dl_no) < 6:
        return False, "Invalid dl_no."
    if len(vehicle_no) < 5:
        return False, "Invalid vehicle_no."

    # Optional: expiry format check (YYYY-MM-DD)
    for k in ["dl_expiry", "rc_expiry", "insurance_expiry", "fitness_expiry", "permit_expiry"]:
        if d.get(k):
            if _parse_date(str(d.get(k))) is None:
                return False, f"Invalid date format for {k}. Use YYYY-MM-DD."

    is_approved = d.get("is_approved")
    if is_approved is not None:
        try:
            ia = int(is_approved)
            if ia not in (0, 1, 2):
                return False, "is_approved must be 0(pending), 1(approved), or 2(rejected)."
        except Exception:
            return False, "is_approved must be integer 0/1/2."

    return True, "ok"


def upsert_driver(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert by mobile (unique).
    If exists -> update record and rotate password hash if provided.
    If not -> insert.
    """
    ensure_driver_tables()

    ok, msg = validate_driver_payload(d)
    if not ok:
        raise ValueError(msg)

    driver_id = str(d.get("id") or "").strip() or f"drv_{secrets.token_hex(6)}"
    name = str(d.get("name")).strip()
    mobile = str(d.get("mobile")).strip()
    password = str(d.get("password")).strip()

    dl_no = str(d.get("dl_no")).strip()
    vehicle_no = str(d.get("vehicle_no")).strip()
    vehicle_type = str(d.get("vehicle_type") or "").strip() or None
    home_town = str(d.get("home_town") or "").strip() or None
    is_approved = int(d.get("is_approved", 0))

    dl_expiry = str(d.get("dl_expiry") or "").strip() or None
    rc_expiry = str(d.get("rc_expiry") or "").strip() or None
    insurance_expiry = str(d.get("insurance_expiry") or "").strip() or None
    fitness_expiry = str(d.get("fitness_expiry") or "").strip() or None
    permit_expiry = str(d.get("permit_expiry") or "").strip() or None

    salt, pwd_hash = _hash_password(password)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM drivers WHERE mobile = ?", (mobile,))
        row = cur.fetchone()

        if row:
            existing_id = row[0] if isinstance(row, (tuple, list)) else row["id"]
            cur.execute(
                """
                UPDATE drivers
                SET
                    name = ?,
                    dl_no = ?,
                    vehicle_no = ?,
                    vehicle_type = ?,
                    home_town = ?,
                    is_approved = ?,

                    password_salt = ?,
                    password_hash = ?,

                    dl_expiry = ?,
                    rc_expiry = ?,
                    insurance_expiry = ?,
                    fitness_expiry = ?,
                    permit_expiry = ?,

                    updated_at = ?
                WHERE mobile = ?
                """,
                (
                    name,
                    dl_no,
                    vehicle_no,
                    vehicle_type,
                    home_town,
                    is_approved,
                    salt,
                    pwd_hash,
                    dl_expiry,
                    rc_expiry,
                    insurance_expiry,
                    fitness_expiry,
                    permit_expiry,
                    _now_iso(),
                    mobile,
                ),
            )
            saved_id = existing_id
            action = "updated"
        else:
            cur.execute(
                """
                INSERT INTO drivers (
                    id, name, mobile,
                    dl_no, vehicle_no, vehicle_type,
                    home_town, is_approved,
                    password_salt, password_hash,
                    dl_expiry, rc_expiry, insurance_expiry, fitness_expiry, permit_expiry,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    driver_id,
                    name,
                    mobile,
                    dl_no,
                    vehicle_no,
                    vehicle_type,
                    home_town,
                    is_approved,
                    salt,
                    pwd_hash,
                    dl_expiry,
                    rc_expiry,
                    insurance_expiry,
                    fitness_expiry,
                    permit_expiry,
                    _now_iso(),
                    _now_iso(),
                ),
            )
            saved_id = driver_id
            action = "created"

        conn.commit()

        # flag expired docs for UI highlight
        expired = {
            "dl_expired": _is_expired(dl_expiry),
            "rc_expired": _is_expired(rc_expiry),
            "insurance_expired": _is_expired(insurance_expiry),
            "fitness_expired": _is_expired(fitness_expiry),
            "permit_expired": _is_expired(permit_expiry),
        }

        return {
            "action": action,
            "driver": {
                "id": saved_id,
                "name": name,
                "mobile": mobile,
                "dl_no": dl_no,
                "vehicle_no": vehicle_no,
                "vehicle_type": vehicle_type,
                "home_town": home_town,
                "is_approved": is_approved,
                "dl_expiry": dl_expiry,
                "rc_expiry": rc_expiry,
                "insurance_expiry": insurance_expiry,
                "fitness_expiry": fitness_expiry,
                "permit_expiry": permit_expiry,
                "expired_flags": expired,
            },
        }
    finally:
        conn.close()


def seed_many(drivers: List[Dict[str, Any]]) -> Dict[str, Any]:
    created = 0
    updated = 0
    results: List[Dict[str, Any]] = []
    for d in drivers:
        r = upsert_driver(d)
        results.append(r)
        if r["action"] == "created":
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "results": results}


def get_seed_status() -> Dict[str, Any]:
    ensure_driver_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM drivers")
        total = cur.fetchone()[0]
        return {"drivers_count": int(total)}
    finally:
        conn.close()


def reset_drivers_and_seed_default() -> Dict[str, Any]:
    ensure_driver_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM drivers")
        conn.commit()
    finally:
        conn.close()

    return seed_many(default_driver_seed_list())


# ==========================
# Seed API / Endpoints
# ==========================
seed_bp = Blueprint("seed_drivers", __name__, url_prefix="/api/drivers/seed")


@seed_bp.route("/status", methods=["GET"])
def seed_status():
    try:
        return jsonify(success=True, data=get_seed_status())
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("", methods=["POST"])
def seed_create_or_update():
    """
    If request body is empty -> seed default drivers list
    If body contains:
      - {"drivers": [ ... ]} -> seeds those drivers
      - or a single driver object -> seeds that one
    """
    try:
        body = request.get_json(silent=True) or {}

        if not body:
            drivers = default_driver_seed_list()
        elif isinstance(body.get("drivers"), list):
            drivers = body["drivers"]
        else:
            drivers = [body]

        result = seed_many(drivers)
        return jsonify(
            success=True,
            message=f"Drivers seed done. created={result['created']}, updated={result['updated']}",
            data=result,
        )
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except sqlite3.IntegrityError as se:
        # unique conflicts: mobile/dl_no/vehicle_no
        return jsonify(success=False, message=f"DB integrity error: {se}"), 409
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("/reset", methods=["POST"])
def seed_reset():
    """
    DANGER: deletes all drivers then seeds default list.
    """
    try:
        result = reset_drivers_and_seed_default()
        return jsonify(success=True, message="Drivers reset and seeded.", data=result)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


def register_seed_driver_routes(app):
    """
    Call this from app.py:
        from seeds.seed_drivers import register_seed_driver_routes
        register_seed_driver_routes(app)
    """
    app.register_blueprint(seed_bp)


if __name__ == "__main__":
    # Minimal CLI seed (dev use)
    print("Seeding default drivers into DB...")
    print(seed_many(default_driver_seed_list()))
