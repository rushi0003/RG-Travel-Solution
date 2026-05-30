# backend/utils/time_utils.py
"""
RG Travel Solution - Time Utilities

✅ Path: backend/utils/time_utils.py

This module standardizes all time/date operations used across your backend:
- parsing/validating HH:MM times (employee login/logout, pickup/drop time selection)
- parsing ISO datetimes (created_at/updated_at, OTP expiry)
- calculating "next run time" for pickup/drop grouping
- converting to IST (Asia/Kolkata) consistently
- common helpers for trips: today date, compare times, window matching

✅ Optional Dev Endpoints (if you register routes):
- GET  /api/time/ping
- POST /api/time/validate_hhmm
- POST /api/time/compare
- POST /api/time/next_occurrence
- GET  /api/time/now

NOTE:
- Python 3.9+ recommended (zoneinfo)
- If your Python is 3.8, install backports.zoneinfo (not included here).
"""

from __future__ import annotations

from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, Union, Callable, List

from flask import Blueprint, request, jsonify

# Try to use zoneinfo (Python 3.9+)
try:
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


IST_TZ_NAME = "Asia/Kolkata"


# =========================================================
# Core timezone helpers
# =========================================================
def get_ist_tz():
    """
    Returns timezone for IST.
    - Prefer IANA zone: Asia/Kolkata (ZoneInfo)
    - Fallback to fixed +05:30 offset if tzdata is missing (common on Windows)
    """
    if ZoneInfo is None:
        return timezone(timedelta(hours=5, minutes=30))
    try:
        return ZoneInfo(IST_TZ_NAME)
    except Exception:
        return timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """
    Current time in IST (aware if zoneinfo available, else naive local time).
    """
    tz = get_ist_tz()
    if tz:
        return datetime.now(tz)
    return datetime.now()


def today_ist() -> date:
    return now_ist().date()


def iso_now_ist() -> str:
    """
    ISO string time in IST.
    """
    return now_ist().isoformat(timespec="seconds")


# =========================================================
# HH:MM parsing + formatting
# =========================================================
def parse_hhmm(hhmm: str) -> time:
    """
    Parse 'HH:MM' 24-hour time into datetime.time.
    Raises ValueError on invalid input.
    """
    hhmm = (hhmm or "").strip()
    try:
        return datetime.strptime(hhmm, "%H:%M").time()
    except Exception:
        raise ValueError("Time must be in HH:MM (24-hour) format.")


def is_valid_hhmm(hhmm: str) -> bool:
    try:
        parse_hhmm(hhmm)
        return True
    except Exception:
        return False


def hhmm_to_minutes(hhmm: str) -> int:
    t = parse_hhmm(hhmm)
    return t.hour * 60 + t.minute


def minutes_to_hhmm(minutes: int) -> str:
    if minutes < 0:
        minutes = 0
    minutes = minutes % (24 * 60)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


# =========================================================
# ISO datetime parsing
# =========================================================
def parse_iso(dt_str: str) -> datetime:
    """
    Parse ISO datetime string (supports 'YYYY-MM-DDTHH:MM:SS' and similar).
    """
    dt_str = (dt_str or "").strip()
    if not dt_str:
        raise ValueError("datetime string is empty")
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        # fallback common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(dt_str, fmt)
            except Exception:
                pass
    raise ValueError("Invalid ISO datetime format.")


# =========================================================
# Compare + window helpers
# =========================================================
def compare_hhmm(a: str, b: str) -> int:
    """
    Compare two HH:MM times.
    Returns:
      -1 if a < b
       0 if a == b
       1 if a > b
    """
    ma = hhmm_to_minutes(a)
    mb = hhmm_to_minutes(b)
    if ma < mb:
        return -1
    if ma > mb:
        return 1
    return 0


def is_time_in_window(target_hhmm: str, start_hhmm: str, end_hhmm: str) -> bool:
    """
    Checks if target is between start and end (inclusive).
    Assumes same-day window and start <= end.
    """
    t = hhmm_to_minutes(target_hhmm)
    s = hhmm_to_minutes(start_hhmm)
    e = hhmm_to_minutes(end_hhmm)
    return s <= t <= e


def clamp_hhmm(target_hhmm: str, min_hhmm: str, max_hhmm: str) -> str:
    """
    Clamp a HH:MM time inside [min, max]
    """
    t = hhmm_to_minutes(target_hhmm)
    mn = hhmm_to_minutes(min_hhmm)
    mx = hhmm_to_minutes(max_hhmm)
    if t < mn:
        return min_hhmm
    if t > mx:
        return max_hhmm
    return target_hhmm


# =========================================================
# Next occurrence calculation
# =========================================================
def next_occurrence_ist(hhmm: str, from_dt: Optional[datetime] = None) -> datetime:
    """
    Returns next datetime occurrence of the given HH:MM time in IST.
    - If time today has already passed -> returns tomorrow at HH:MM
    - Else returns today at HH:MM
    """
    t = parse_hhmm(hhmm)
    base = from_dt or now_ist()

    # make base timezone-aware if possible
    tz = get_ist_tz()
    if tz and base.tzinfo is None:
        base = base.replace(tzinfo=tz)

    candidate = datetime.combine(base.date(), t)
    if tz:
        candidate = candidate.replace(tzinfo=tz)

    if candidate <= base:
        candidate = candidate + timedelta(days=1)

    return candidate


def seconds_until(dt: datetime, from_dt: Optional[datetime] = None) -> int:
    base = from_dt or now_ist()
    # If dt is naive and base is aware, align
    if base.tzinfo and dt.tzinfo is None:
        dt = dt.replace(tzinfo=base.tzinfo)
    diff = dt - base
    return max(0, int(diff.total_seconds()))


# =========================================================
# Trip-day helpers (route number validity per trip/day)
# =========================================================
def trip_day_key(dt: Optional[datetime] = None) -> str:
    """
    Returns 'YYYYMMDD' for IST date. Useful for:
    - route number uniqueness per day
    - trip grouping buckets per day
    """
    d = (dt or now_ist()).date()
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


def iso_date_today_ist() -> str:
    d = today_ist()
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


# =========================================================
# Optional API endpoints for testing from Flutter/Postman
# =========================================================
time_bp = Blueprint("time_utils", __name__, url_prefix="/api/time")


def _success(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _error(message="Error", status=400, code="ERROR", data=None):
    return jsonify({"success": False, "message": message, "error": {"code": code}, "data": data}), status


@time_bp.route("/ping", methods=["GET"])
def ping():
    return _success({"pong": True}, "time_utils ok")


@time_bp.route("/now", methods=["GET"])
def api_now():
    return _success(
        {
            "now_ist": iso_now_ist(),
            "today_ist": iso_date_today_ist(),
            "trip_day_key": trip_day_key(),
            "timezone": IST_TZ_NAME,
            "zoneinfo_available": ZoneInfo is not None,
        },
        "OK",
    )


@time_bp.route("/validate_hhmm", methods=["POST"])
def api_validate_hhmm():
    body = request.get_json(silent=True) or {}
    hhmm = str(body.get("time", "")).strip()
    if not hhmm:
        return _error("time required", 400, "VALIDATION_ERROR")
    ok = is_valid_hhmm(hhmm)
    return _success({"time": hhmm, "valid": ok}, "valid" if ok else "invalid")


@time_bp.route("/compare", methods=["POST"])
def api_compare():
    body = request.get_json(silent=True) or {}
    a = str(body.get("a", "")).strip()
    b = str(body.get("b", "")).strip()
    if not (a and b):
        return _error("a and b required", 400, "VALIDATION_ERROR")
    if not (is_valid_hhmm(a) and is_valid_hhmm(b)):
        return _error("a and b must be HH:MM", 400, "VALIDATION_ERROR")
    c = compare_hhmm(a, b)
    return _success({"a": a, "b": b, "compare": c}, "OK")


@time_bp.route("/next_occurrence", methods=["POST"])
def api_next_occurrence():
    body = request.get_json(silent=True) or {}
    hhmm = str(body.get("time", "")).strip()
    if not hhmm:
        return _error("time required", 400, "VALIDATION_ERROR")
    if not is_valid_hhmm(hhmm):
        return _error("time must be HH:MM", 400, "VALIDATION_ERROR")

    dt = next_occurrence_ist(hhmm)
    return _success(
        {
            "time": hhmm,
            "next_occurrence": dt.isoformat(timespec="seconds"),
            "seconds_until": seconds_until(dt),
        },
        "OK",
    )


def register_time_routes(app: Any) -> None:
    """
    Register /api/time endpoints from app.py:

        from utils.time_utils import register_time_routes
        register_time_routes(app)
    """
    app.register_blueprint(time_bp)


__all__ = [
    "IST_TZ_NAME",
    "now_ist",
    "today_ist",
    "iso_now_ist",
    "parse_hhmm",
    "is_valid_hhmm",
    "hhmm_to_minutes",
    "minutes_to_hhmm",
    "parse_iso",
    "compare_hhmm",
    "is_time_in_window",
    "clamp_hhmm",
    "next_occurrence_ist",
    "seconds_until",
    "trip_day_key",
    "iso_date_today_ist",
    "register_time_routes",
]
