# backend/seeds/seed_admin.py
"""
RG Travel Solution - Admin Seeder + Seed APIs

✅ What this file does
1) Creates required DB tables (admins) if not exist
2) Seeds a default admin (id + login fields + office profile fields)
3) Exposes seed APIs/endpoints you can call from Flutter/Postman

✅ Endpoints (after you register routes in app.py)
- GET  /api/admin/seed/status
- POST /api/admin/seed            (creates default admin if missing; upserts if you pass body)
- POST /api/admin/seed/reset      (DANGER: deletes all admins then creates default)

This file assumes you already have:
- backend/db.py with get_db() that returns sqlite3 connection (row_factory optional)
"""

from __future__ import annotations

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, request, jsonify


# ---------------------------------------------------------
# Safe import of get_db (supports multiple project layouts)
# ---------------------------------------------------------
def _import_get_db():
    """
    Tries common import styles based on different app.py run modes.
    You should keep your project structure consistent, but this makes it robust.
    """
    try:
        # Most common when running from backend/ as package
        from ..db import get_db  # type: ignore
        return get_db
    except Exception:
        pass

    try:
        # If app.py is run from backend folder directly
        from db import get_db  # type: ignore
        return get_db
    except Exception as e:
        raise ImportError(
            "Could not import get_db(). Ensure backend/db.py has get_db() "
            "and that app.py is run from the correct folder."
        ) from e


get_db = _import_get_db()


# ==========================
# Password hashing utilities
# ==========================
def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Returns (salt, password_hash).
    Uses sha256(salt + password). For production, use bcrypt/argon2.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, h


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ==========================
# Table creation
# ==========================
def ensure_admin_tables() -> None:
    """
    Create admins table if not exists.
    Keeps fields aligned with your Admin profile requirements:
    - name, mobile(10), email (optional)
    - office_name, office_location, office_address
    - password_salt, password_hash
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                mobile TEXT NOT NULL UNIQUE,
                email TEXT,
                office_name TEXT,
                office_location TEXT,
                office_address TEXT,

                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ==========================
# Seeding logic
# ==========================
def default_admin_payload() -> Dict[str, Any]:
    """
    Default seed admin (you can change these values).
    NOTE: mobile must be exactly 10 digits.
    """
    return {
        "id": "admin_rg_001",
        "name": "Rushi Gund",
        "mobile": "9325118627",
        "email": "admin@rgtravelsolution.com",
        "office_name": "RG Travel Solution",
        "office_location": "Pune",
        "office_address": "RG Office Address, Pune, Maharashtra",
        "password": "Rushi123",
    }


def validate_admin_payload(data: Dict[str, Any]) -> Tuple[bool, str]:
    name = str(data.get("name", "")).strip()
    mobile = str(data.get("mobile", "")).strip()
    password = str(data.get("password", "")).strip()

    if len(name) < 2:
        return False, "Admin name must be at least 2 characters."
    if not (mobile.isdigit() and len(mobile) == 10):
        return False, "Mobile must be exactly 10 digits."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    # Optional fields
    email = str(data.get("email", "")).strip()
    if email and "@" not in email:
        return False, "Invalid email format."

    return True, "ok"


def upsert_admin(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates admin if not exists by mobile, else updates it.
    Returns the saved admin public fields (no password hash).
    """
    ensure_admin_tables()

    ok, msg = validate_admin_payload(data)
    if not ok:
        raise ValueError(msg)

    admin_id = str(data.get("id") or "").strip() or f"admin_{secrets.token_hex(6)}"
    name = str(data.get("name")).strip()
    mobile = str(data.get("mobile")).strip()
    email = str(data.get("email") or "").strip() or None
    office_name = str(data.get("office_name") or "").strip() or None
    office_location = str(data.get("office_location") or "").strip() or None
    office_address = str(data.get("office_address") or "").strip() or None
    password = str(data.get("password")).strip()

    salt, pwd_hash = _hash_password(password)

    conn = get_db()
    try:
        cur = conn.cursor()

        # Check by mobile (unique)
        cur.execute("SELECT id FROM admins WHERE mobile = ?", (mobile,))
        row = cur.fetchone()

        if row:
            existing_id = row[0] if isinstance(row, (tuple, list)) else row["id"]
            cur.execute(
                """
                UPDATE admins
                SET
                    name = ?,
                    email = ?,
                    office_name = ?,
                    office_location = ?,
                    office_address = ?,
                    password_salt = ?,
                    password_hash = ?,
                    updated_at = ?
                WHERE mobile = ?
                """,
                (
                    name,
                    email,
                    office_name,
                    office_location,
                    office_address,
                    salt,
                    pwd_hash,
                    _now_iso(),
                    mobile,
                ),
            )
            saved_id = existing_id
            action = "updated"
        else:
            cur.execute(
                """
                INSERT INTO admins (
                    id, name, mobile, email,
                    office_name, office_location, office_address,
                    password_salt, password_hash,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    admin_id,
                    name,
                    mobile,
                    email,
                    office_name,
                    office_location,
                    office_address,
                    salt,
                    pwd_hash,
                    _now_iso(),
                    _now_iso(),
                ),
            )
            saved_id = admin_id
            action = "created"

        conn.commit()

        return {
            "action": action,
            "admin": {
                "id": saved_id,
                "name": name,
                "mobile": mobile,
                "email": email,
                "office_name": office_name,
                "office_location": office_location,
                "office_address": office_address,
            },
        }
    finally:
        conn.close()


def get_seed_status() -> Dict[str, Any]:
    ensure_admin_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admins")
        total = cur.fetchone()[0]
        return {"admins_count": int(total)}
    finally:
        conn.close()


def reset_admins_and_seed_default() -> Dict[str, Any]:
    """
    Deletes ALL admins then seeds the default admin.
    Use only for development.
    """
    ensure_admin_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM admins")
        conn.commit()
    finally:
        conn.close()

    return upsert_admin(default_admin_payload())


# ==========================
# Seed API / Endpoints
# ==========================
seed_bp = Blueprint("seed_admin", __name__, url_prefix="/api/admin/seed")


@seed_bp.route("/status", methods=["GET"])
def seed_status():
    try:
        return jsonify(success=True, data=get_seed_status())
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("", methods=["POST"])
def seed_create_or_update():
    """
    If request body is empty -> seed default admin.
    If body present -> upsert admin using provided values.
    """
    try:
        body = request.get_json(silent=True) or {}
        payload = default_admin_payload() if not body else {**default_admin_payload(), **body}

        result = upsert_admin(payload)
        return jsonify(success=True, message=f"Admin seed {result['action']}.", data=result)
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except sqlite3.IntegrityError as se:
        # mobile unique conflict etc.
        return jsonify(success=False, message=f"DB integrity error: {se}"), 409
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@seed_bp.route("/reset", methods=["POST"])
def seed_reset():
    """
    DANGER: deletes all admins then seeds the default.
    """
    try:
        result = reset_admins_and_seed_default()
        return jsonify(success=True, message="Admins reset and default admin seeded.", data=result)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


def register_seed_admin_routes(app):
    """
    Call this from app.py:
        from seeds.seed_admin import register_seed_admin_routes
        register_seed_admin_routes(app)
    """
    app.register_blueprint(seed_bp)


# Optional: allow running as a script (dev use)
if __name__ == "__main__":
    # Minimal CLI seed (won't start flask)
    print("Seeding default admin into DB...")
    print(upsert_admin(default_admin_payload()))
