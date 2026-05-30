# rg_travel_backend/services/route_no_service.py
"""
RG Travel Solution — route_no_service.py
======================================

This service generates a **unique 10-character Route Number** for each trip.

✅ Your required format (exact):
- Total length: 10 characters
- First 4 characters: YEAR (YYYY)   ✅ (you said "date and year (first 4 char)" -> year fits 4)
- Next 4 characters: Random digits (0000–9999)
- Last 2 characters: First two letters of the month (JAN->JA, FEB->FE ...)

Example:
  20261234JA   (Year=2026, Rand=1234, Month=JAN => JA)

✅ Rules supported:
1) Route number is generated when a group is assigned a trip.
2) Route number remains valid only until trip is completed (this is a trip status rule; stored in trips table).
3) Once generated, the route number can **never** be reused or generated again.
4) This module ensures uniqueness by checking DB before returning.

------------------------------------------------------------
Expected DB table requirement
------------------------------------------------------------
trips table must contain:
- route_no TEXT UNIQUE
- status TEXT ("active"/"in_progress"/"completed"/"cancelled")

Uniqueness is enforced by:
- DB UNIQUE constraint + service DB check retries

------------------------------------------------------------
Public API for routes/services
------------------------------------------------------------

- generate_route_no() -> str
- generate_unique_route_no(conn) -> str
- reserve_route_no_for_trip(conn, trip_id) -> {"success":..., "data":...}
- is_route_no_exists(conn, route_no) -> bool
- format_info() -> dict   (for showing format rules in UI)

------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import random

# Safe imports for DB (package or flat)
try:
    from ..db import get_db  # type: ignore
except Exception:
    from db import get_db  # type: ignore


# ----------------------------
# Core: Route No generation
# ----------------------------

def generate_route_no(dt: Optional[datetime] = None) -> str:
    """
    Generates a 10-character route number string.

    Format:
      YYYY + 4 random digits + 2 letters month

    Example:
      20261234JA
    """
    if dt is None:
        dt = datetime.now()

    year = dt.strftime("%Y")              # 4 chars
    month2 = dt.strftime("%b").upper()[:2]  # 2 chars (JAN->JA)
    rand4 = f"{random.randint(0, 9999):04d}"  # 4 digits

    route_no = f"{year}{rand4}{month2}"

    # Safety check: exact length should be 10
    if len(route_no) != 10:
        raise ValueError(f"Invalid route no length produced: {route_no} ({len(route_no)})")

    return route_no


def is_route_no_exists(conn, route_no: str) -> bool:
    """
    Checks if route_no already exists in trips table.
    """
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
    return cur.fetchone() is not None


def generate_unique_route_no(conn, max_attempts: int = 80) -> str:
    """
    Generates a unique route number by checking DB.
    Also protected by DB UNIQUE constraint (recommended).
    """
    for _ in range(max_attempts):
        rn = generate_route_no()
        if not is_route_no_exists(conn, rn):
            return rn
    raise RuntimeError("Unable to generate unique route number (too many collisions).")


# ----------------------------
# Reserve / Assign Route No
# ----------------------------

def reserve_route_no_for_trip(conn, trip_id: int) -> Dict[str, Any]:
    """
    Assigns a unique route number to an existing trip row.

    Recommended API:
      POST /api/admin/trips/<trip_id>/reserve-route

    Returns:
      {
        "success": True,
        "data": {"trip_id":..., "route_no":...}
      }
    """
    cur = conn.cursor()

    # Ensure trip exists
    cur.execute("SELECT id, route_no FROM trips WHERE id = ? LIMIT 1", (trip_id,))
    row = cur.fetchone()
    if not row:
        return {"success": False, "message": "Trip not found."}

    existing = row[1]
    if existing:
        return {"success": True, "data": {"trip_id": trip_id, "route_no": existing}, "message": "Already assigned."}

    route_no = generate_unique_route_no(conn)

    cur.execute(
        "UPDATE trips SET route_no = ? WHERE id = ?",
        (route_no, trip_id),
    )

    conn.commit()
    return {"success": True, "data": {"trip_id": trip_id, "route_no": route_no}}


# ----------------------------
# Convenience APIs for routes
# ----------------------------

def api_generate_route_no() -> Dict[str, Any]:
    """
    Simple API response (without DB uniqueness check).
    Useful if UI needs to preview format, but NOT for final assignment.

    GET /api/admin/route-no/preview
    """
    rn = generate_route_no()
    return {"success": True, "data": {"route_no": rn, "format": format_info()}}


def api_reserve_route_no(trip_id: int) -> Dict[str, Any]:
    """
    API wrapper with DB.
    """
    conn = get_db()
    try:
        return reserve_route_no_for_trip(conn, trip_id)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def format_info() -> Dict[str, Any]:
    """
    Returns the format rules for UI display.
    """
    return {
        "length": 10,
        "format": "YYYY + 4 random digits + 2 month letters",
        "example": "20261234JA",
        "parts": [
            {"name": "year", "chars": 4, "description": "Current year (YYYY)"},
            {"name": "random_digits", "chars": 4, "description": "Random digits (0000-9999)"},
            {"name": "month_letters", "chars": 2, "description": "First 2 letters of month (JAN->JA)"},
        ],
        "rules": [
            "Unique for every trip (never reused).",
            "Generated when group is assigned to trip.",
            "Valid until trip is completed (handled by trip status).",
        ],
    }
