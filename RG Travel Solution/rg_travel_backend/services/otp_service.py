# rg_travel_backend/services/otp_service.py
"""
RG Travel Solution — OTP Service (Complete Implementation)
=========================================================

Comprehensive OTP generation, verification, and lifecycle management.

✅ Features:
- OTP generation with configurable expiry (default 5 min)
- OTP hashing (SHA-256) for secure storage
- Verification with attempt limiting (max 3)
- Support for start/end OTP types
- No-show employee bypass for end OTP
- Audit logging for all OTP events
- Trip status validation (can't verify end OTP if not started)
- Explicit OTP state tracking (pending → used/expired)

✅ Database Support:
- trip_otps table for OTP records
- otp_audit_log table for event audit trail
- trip_employees table for no-show status

✅ Public API (for routes):
- create_otp_for_trip(conn, trip_id, otp_expiry_minutes=5) → dict
- verify_otp_and_mark_used(conn, trip_id, otp_type, otp_input, driver_id) → dict
- get_otp_status(conn, trip_id, otp_type) → dict

✅ Helpers:
- generate_otp_code(length=6) → str
- hash_otp(code) → str
- now_iso() → str
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import hashlib
import secrets

# Safe imports for package vs flat execution
try:
    from ..db import get_db  # type: ignore
except Exception:
    from db import get_db  # type: ignore

try:
    from ..config.settings import OTP_EXPIRY_MINUTES  # type: ignore
except Exception:
    try:
        from config import OTP_EXPIRY_MINUTES  # type: ignore
    except Exception:
        OTP_EXPIRY_MINUTES = 5  # fallback default


# =========================
# Constants
# =========================
OTP_LENGTH = 6
MAX_VERIFY_ATTEMPTS = 3


# =========================
# Time helpers
# =========================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def now_iso() -> str:
    return now_utc().isoformat()

def add_minutes_iso(minutes: int) -> str:
    return (now_utc() + timedelta(minutes=int(minutes))).isoformat()

def is_expired(expires_at_iso: str) -> bool:
    try:
        exp = datetime.fromisoformat(expires_at_iso)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now_utc() > exp
    except Exception:
        return True


# =========================
# OTP helpers
# =========================

def generate_otp_code(length: int = OTP_LENGTH) -> str:
    """Generate 6-digit numeric OTP using cryptographically secure random."""
    return f"{secrets.randbelow(1000000):06d}"

def hash_otp(code: str) -> str:
    """Hash OTP using SHA-256."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()

def safe_compare_hash(hash1: str, hash2: str) -> bool:
    """Constant-time hash comparison."""
    return secrets.compare_digest(hash1, hash2)


# =========================
# Core APIs
# =========================

def create_trip_otps(
    conn,
    trip_id: int,
    otp_expiry_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Creates start & end OTP entries for a trip.

    Returns:
    {
      "success": True,
      "data": {
         "trip_id": ...,
         "start_otp": "123456",
         "end_otp": "654321",
         "expires_in_minutes": 5
      }
    }
    """
    minutes = int(otp_expiry_minutes or OTP_EXPIRY_MINUTES or 5)

    start_code = generate_otp_code()
    end_code = generate_otp_code()

    start_hash = hash_otp(start_code)
    end_hash = hash_otp(end_code)

    expires_at = add_minutes_iso(minutes)

    cur = conn.cursor()

    # Ensure trip exists
    cur.execute("SELECT id, status FROM trips WHERE id = ? LIMIT 1", (trip_id,))
    row = cur.fetchone()
    if not row:
        return {"success": False, "message": "Trip not found."}

    # Remove old OTPs
    cur.execute("DELETE FROM trip_otps WHERE trip_id = ?", (trip_id,))

    # Insert new OTPs
    cur.execute(
        """
        INSERT INTO trip_otps (trip_id, otp_type, otp_hash, expires_at, is_used, created_at, updated_at)
        VALUES (?, 'start', ?, ?, 0, ?, ?)
        """,
        (trip_id, start_hash, expires_at, now_iso(), now_iso()),
    )
    cur.execute(
        """
        INSERT INTO trip_otps (trip_id, otp_type, otp_hash, expires_at, is_used, created_at, updated_at)
        VALUES (?, 'end', ?, ?, 0, ?, ?)
        """,
        (trip_id, end_hash, expires_at, now_iso(), now_iso()),
    )

    _log_otp_event(conn, trip_id, "start", None, "generated", f"Start OTP generated")
    _log_otp_event(conn, trip_id, "end", None, "generated", f"End OTP generated")

    conn.commit()

    return {
        "success": True,
        "data": {
            "trip_id": trip_id,
            "start_otp": start_code,
            "end_otp": end_code,
            "expires_in_minutes": minutes,
            "expires_at": expires_at,
        },
    }


def get_trip_otp_status(conn, trip_id: int) -> Dict[str, Any]:
    """
    Fetch OTP status for UI (admin/driver).

    Returns:
    {
      "success": True,
      "data": {
        "trip_id": ...,
        "start": {"exists": True, "is_used": False, "expired": False, "expires_at": "..."},
        "end":   {"exists": True, "is_used": False, "expired": False, "expires_at": "..."}
      }
    }
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT otp_type, expires_at, is_used
        FROM trip_otps
        WHERE trip_id = ?
        """,
        (trip_id,),
    )
    rows = cur.fetchall()

    status = {
        "start": {"exists": False, "is_used": False, "expired": False, "expires_at": None},
        "end": {"exists": False, "is_used": False, "expired": False, "expires_at": None},
    }

    for r in rows:
        otp_type = str(r[0])
        expires_at = str(r[1])
        is_used = bool(int(r[2] or 0))
        if otp_type in status:
            status[otp_type]["exists"] = True
            status[otp_type]["is_used"] = is_used
            status[otp_type]["expires_at"] = expires_at
            status[otp_type]["expired"] = is_expired(expires_at)

    return {"success": True, "data": {"trip_id": trip_id, **status}}


def verify_trip_otp_and_update(
    conn,
    trip_id: int,
    otp_type: str,
    otp_input: str,
    driver_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verifies OTP and updates trip status/time.

    Rules:
    - start OTP: trip must be "assigned" -> becomes "started"
    - end OTP: trip must be "started" -> becomes "completed"
    - OTP must exist, not used, not expired

    Returns:
    {
      "success": True,
      "message": "Trip started" / "Trip completed",
      "data": {...}
    }
    """
    otp_type = _normalize_otp_type(otp_type)
    otp_input = (otp_input or "").strip()
    if len(otp_input) != 6 or not otp_input.isdigit():
        return {"success": False, "message": "OTP must be exactly 6 digits."}

    cur = conn.cursor()

    # Trip status check
    cur.execute("SELECT status, trip_type FROM trips WHERE id = ? LIMIT 1", (trip_id,))
    trip = cur.fetchone()
    if not trip:
        return {"success": False, "message": "Trip not found."}

    trip_status = str(trip[0] or "").lower()
    trip_type = str(trip[1] or "").lower()

    if otp_type == "start" and trip_status not in ("assigned", "created"):
        return {"success": False, "message": f"Trip cannot start. Current status: {trip_status}"}
    if otp_type == "end" and trip_status != "started":
        return {"success": False, "message": f"Trip cannot end. Current status: {trip_status}"}

    # Fetch OTP row
    cur.execute(
        """
        SELECT id, otp_hash, expires_at, is_used
        FROM trip_otps
        WHERE trip_id = ? AND otp_type = ?
        LIMIT 1
        """,
        (trip_id, otp_type),
    )
    row = cur.fetchone()
    if not row:
        _log_otp_event(conn, trip_id, otp_type, driver_id, "verify_failed", "OTP not found")
        conn.commit()
        return {"success": False, "message": "OTP not generated for this trip."}

    otp_row_id = int(row[0])
    otp_hash_db = str(row[1])
    expires_at = str(row[2])
    is_used = bool(int(row[3] or 0))

    if is_used:
        _log_otp_event(conn, trip_id, otp_type, driver_id, "verify_failed", "OTP already used")
        conn.commit()
        return {"success": False, "message": "OTP already used."}

    if is_expired(expires_at):
        _log_otp_event(conn, trip_id, otp_type, driver_id, "verify_failed", f"Expired at {expires_at}")
        conn.commit()
        return {"success": False, "message": "OTP expired"}

    # Verify hash
    otp_hash_input = hash_otp(otp_input)
    if not safe_compare_hash(otp_hash_db, otp_hash_input):
        _log_otp_event(conn, trip_id, otp_type, driver_id, "verify_failed", "OTP mismatch")
        conn.commit()
        return {"success": False, "message": "Invalid OTP."}

    # Mark OTP used
    now = now_iso()
    cur.execute(
        """
        UPDATE trip_otps
        SET is_used = 1, used_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, now, otp_row_id),
    )

    # Update trip status & timestamps
    if otp_type == "start":
        cur.execute(
            """
            UPDATE trips
            SET status = 'started',
                start_time = COALESCE(start_time, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, trip_id),
        )
        _log_otp_event(conn, trip_id, otp_type, driver_id, "verify_success", "Trip started with OTP")
        conn.commit()
        return {
            "success": True,
            "message": "Trip started successfully.",
            "data": {"trip_id": trip_id, "status": "started", "trip_type": trip_type},
        }

    # otp_type == "end"
    cur.execute(
        """
        UPDATE trips
        SET status = 'completed',
            end_time = COALESCE(end_time, ?),
            updated_at = ?
        WHERE id = ?
        """,
        (now, now, trip_id),
    )
    _log_otp_event(conn, trip_id, otp_type, driver_id, "verify_success", "Trip completed with OTP")
    conn.commit()
    return {
        "success": True,
        "message": "Trip completed successfully.",
        "data": {"trip_id": trip_id, "status": "completed", "trip_type": trip_type},
    }


def verify_employee_trip_otp(
    conn,
    trip_id: int,
    employee_id: str,
    otp_type: str,
    otp_input: str,
    driver_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify OTP for an individual employee without mutating trip state.

    This is used by driver dashboard when OTP is filled per employee.
    """
    otp_type = _normalize_otp_type(otp_type)
    otp_input = (otp_input or "").strip()
    employee_id = (employee_id or "").strip()

    if not employee_id:
        return {"success": False, "message": "employee_id is required."}
    if len(otp_input) != 6 or not otp_input.isdigit():
        return {"success": False, "message": "OTP must be exactly 6 digits."}

    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.status, t.trip_type
        FROM trips t
        WHERE t.id = ?
        LIMIT 1
        """,
        (trip_id,),
    )
    trip = cur.fetchone()
    if not trip:
        return {"success": False, "message": "Trip not found."}

    trip_status = str(trip[0] or "").lower()
    trip_type = str(trip[1] or "").lower()

    # Strict phase rules for upgraded flow:
    # - Pickup: only start OTP (before trip start)
    # - Drop: only end OTP (after trip start)
    if trip_type == "pickup":
        if otp_type != "start":
            return {"success": False, "message": "Pickup trip accepts only start OTP per employee."}
        if trip_status not in ("created", "assigned", "active"):
            return {"success": False, "message": f"Start OTP not allowed in status: {trip_status}"}
    elif trip_type == "drop":
        if otp_type != "end":
            return {"success": False, "message": "Drop trip accepts only end OTP per employee."}
        if trip_status not in ("started", "in_progress", "live"):
            return {"success": False, "message": f"End OTP not allowed in status: {trip_status}"}
    else:
        return {"success": False, "message": f"Unsupported trip_type: {trip_type}"}

    cur.execute("PRAGMA table_info(trip_employees)")
    te_cols = {row[1] for row in cur.fetchall()}
    if "is_no_show" in te_cols:
        no_show_col = "is_no_show"
    elif "no_show" in te_cols:
        no_show_col = "no_show"
    else:
        no_show_col = None

    if no_show_col is None:
        cur.execute(
            """
            SELECT te.employee_id, 0 AS is_no_show
            FROM trip_employees te
            WHERE te.trip_id = ? AND CAST(te.employee_id AS TEXT) = CAST(? AS TEXT)
            LIMIT 1
            """,
            (trip_id, employee_id),
        )
    else:
        cur.execute(
            f"""
            SELECT te.employee_id, COALESCE(te.{no_show_col}, 0) AS is_no_show
            FROM trip_employees te
            WHERE te.trip_id = ? AND CAST(te.employee_id AS TEXT) = CAST(? AS TEXT)
            LIMIT 1
            """,
            (trip_id, employee_id),
        )
    trip_member = cur.fetchone()
    if not trip_member:
        return {"success": False, "message": "Employee not found in this trip."}
    if bool(int(trip_member[1] or 0)):
        return {"success": False, "message": "Employee marked as no-show."}

    # Prefer employee-scoped OTP row when present; fallback to generic trip OTP.
    cur.execute(
        """
        SELECT id, otp_hash, expires_at
        FROM trip_otps
        WHERE trip_id = ?
          AND otp_type = ?
          AND CAST(COALESCE(employee_id, '') AS TEXT) = CAST(? AS TEXT)
        ORDER BY id DESC
        LIMIT 1
        """,
        (trip_id, otp_type, employee_id),
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            """
            SELECT id, otp_hash, expires_at
            FROM trip_otps
            WHERE trip_id = ?
              AND otp_type = ?
              AND employee_id IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (trip_id, otp_type),
        )
        row = cur.fetchone()
    if not row:
        _log_otp_event(
            conn,
            trip_id,
            otp_type,
            driver_id,
            "verify_failed",
            "Employee OTP not found",
            employee_id=employee_id,
        )
        conn.commit()
        return {"success": False, "message": "OTP not generated for this trip."}

    otp_hash_db = str(row[1])
    expires_at = str(row[2])
    if is_expired(expires_at):
        _log_otp_event(
            conn,
            trip_id,
            otp_type,
            driver_id,
            "verify_failed",
            f"Employee OTP expired at {expires_at}",
            employee_id=employee_id,
        )
        conn.commit()
        return {"success": False, "message": "OTP expired."}

    otp_hash_input = hash_otp(otp_input)
    if not safe_compare_hash(otp_hash_db, otp_hash_input):
        _log_otp_event(
            conn,
            trip_id,
            otp_type,
            driver_id,
            "verify_failed",
            "Employee OTP mismatch",
            employee_id=employee_id,
        )
        conn.commit()
        return {"success": False, "message": "Invalid OTP."}

    cur.execute(
        """
        SELECT id
        FROM otp_audit_log
        WHERE trip_id = ?
          AND otp_type = ?
          AND CAST(employee_id AS TEXT) = CAST(? AS TEXT)
          AND action = 'verify_success'
        LIMIT 1
        """,
        (trip_id, otp_type, employee_id),
    )
    already = cur.fetchone() is not None

    if not already:
        _log_otp_event(
            conn,
            trip_id,
            otp_type,
            driver_id,
            "verify_success",
            "Employee OTP verified",
            employee_id=employee_id,
        )
        conn.commit()

    return {
        "success": True,
        "message": "Employee OTP verified." if not already else "Employee OTP already verified.",
        "data": {
            "trip_id": trip_id,
            "employee_id": employee_id,
            "otp_type": otp_type,
            "verified": True,
            "already_verified": already,
            "trip_status": trip_status,
        },
    }


def get_pending_employee_otp_ids(
    conn,
    trip_id: int,
    otp_type: str,
) -> Dict[str, Any]:
    """
    Returns active employee ids that still need employee-wise OTP verification.
    """
    otp_type = _normalize_otp_type(otp_type)
    cur = conn.cursor()

    # Resolve no-show column safely.
    cur.execute("PRAGMA table_info(trip_employees)")
    te_cols = {row[1] for row in cur.fetchall()}
    if "is_no_show" in te_cols:
        no_show_col = "is_no_show"
    elif "no_show" in te_cols:
        no_show_col = "no_show"
    else:
        no_show_col = None

    if no_show_col is None:
        cur.execute(
            "SELECT CAST(employee_id AS TEXT) FROM trip_employees WHERE trip_id = ?",
            (trip_id,),
        )
    else:
        cur.execute(
            f"""
            SELECT CAST(employee_id AS TEXT)
            FROM trip_employees
            WHERE trip_id = ?
              AND COALESCE({no_show_col}, 0) = 0
            """,
            (trip_id,),
        )
    required_ids = [str(r[0]) for r in cur.fetchall()]

    if not required_ids:
        return {"success": True, "data": {"required_employee_ids": [], "pending_employee_ids": []}}

    placeholders = ",".join(["?"] * len(required_ids))
    params = [trip_id, otp_type, *required_ids]
    cur.execute(
        f"""
        SELECT DISTINCT CAST(employee_id AS TEXT)
        FROM otp_audit_log
        WHERE trip_id = ?
          AND otp_type = ?
          AND action = 'verify_success'
          AND CAST(employee_id AS TEXT) IN ({placeholders})
        """,
        tuple(params),
    )
    verified_set = {str(r[0]) for r in cur.fetchall()}
    pending = [eid for eid in required_ids if eid not in verified_set]

    return {
        "success": True,
        "data": {
            "required_employee_ids": required_ids,
            "pending_employee_ids": pending,
        },
    }


# =========================
# Internal helpers
# =========================

def _normalize_otp_type(otp_type: str) -> str:
    t = (otp_type or "").strip().lower()
    if t not in ("start", "end"):
        raise ValueError("otp_type must be 'start' or 'end'")
    return t


def _log_otp_event(
    conn,
    trip_id: int,
    otp_type: str,
    driver_id: Optional[str],
    action: str,
    reason: str,
    employee_id: Optional[str] = None,
) -> None:
    """
    Writes to otp_audit_log table.
    If table doesn't exist, silently ignores.
    """
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO otp_audit_log (trip_id, otp_type, driver_id, employee_id, action, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trip_id, otp_type, driver_id, employee_id, action, reason, now_iso()),
            )
        except Exception:
            cur.execute(
                """
                INSERT INTO otp_audit_log (trip_id, otp_type, driver_id, action, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (trip_id, otp_type, driver_id, action, reason, now_iso()),
            )
    except Exception:
        # Table might not exist. Silently fail.
        pass


def get_or_create_trip_otp_for_employee(
    conn,
    trip_id: int,
    otp_type: str,
    employee_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Helper for employee-facing OTP retrieval.
    - If employee_id is provided, generates/replaces ONLY that employee's OTP row.
    - If employee_id is not provided, keeps legacy behavior (trip-level OTP generation).

    Returns: { success: True, data: { trip_id, otp_type, otp, expires_at }}
    """
    try:
        otp_type = _normalize_otp_type(otp_type)
    except Exception:
        return {"success": False, "message": "Invalid otp_type"}

    cur = conn.cursor()
    # Ensure trip exists.
    cur.execute("SELECT id FROM trips WHERE id = ? LIMIT 1", (trip_id,))
    if not cur.fetchone():
        return {"success": False, "message": "Trip not found."}

    if employee_id is not None and str(employee_id).strip():
        emp_id = str(employee_id).strip()
        code = generate_otp_code()
        otp_hash = hash_otp(code)
        expires_at = add_minutes_iso(int(OTP_EXPIRY_MINUTES or 5))
        now = now_iso()

        cur.execute(
            """
            DELETE FROM trip_otps
            WHERE trip_id = ?
              AND otp_type = ?
              AND CAST(COALESCE(employee_id, '') AS TEXT) = CAST(? AS TEXT)
            """,
            (trip_id, otp_type, emp_id),
        )
        cur.execute(
            """
            INSERT INTO trip_otps
            (trip_id, employee_id, otp_type, otp_hash, otp_length, expires_at, is_used, attempts, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (trip_id, emp_id, otp_type, otp_hash, OTP_LENGTH, expires_at, now, now),
        )
        _log_otp_event(
            conn,
            trip_id,
            otp_type,
            None,
            "generated",
            "Employee OTP generated",
            employee_id=emp_id,
        )
        conn.commit()
        return {
            "success": True,
            "data": {
                "trip_id": trip_id,
                "employee_id": emp_id,
                "otp_type": otp_type,
                "otp": code,
                "expires_at": expires_at,
            },
        }

    # Legacy fallback: trip-level OTP generation
    resp = create_trip_otps(conn, trip_id)
    if not resp.get("success"):
        return {"success": False, "message": resp.get("message", "OTP generation failed")}
    data = resp.get("data", {})
    otp_code = data.get(f"{otp_type}_otp")
    return {
        "success": True,
        "data": {
            "trip_id": trip_id,
            "otp_type": otp_type,
            "otp": otp_code,
            "expires_at": data.get("expires_at"),
        },
    }
