"""
Trip schedule guard utilities for pre-assigned trips.

Purpose:
- Allow pre-assignment (trip visible to admin/driver).
- Prevent driver-side "start" before scheduled date/time.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple


def _normalize_trip_day(raw: Any) -> Optional[str]:
    s = str(raw or "").strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return s
    return None


def _parse_time(raw: Any) -> Optional[Tuple[int, int]]:
    text = str(raw or "").strip()
    if not text:
        return None

    # HH:MM
    try:
        hh, mm = text.split(":", 1)
        h = int(hh)
        m = int(mm[:2])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except Exception:
        pass

    # HH:MM AM/PM
    try:
        dt = datetime.strptime(text, "%I:%M %p")
        return dt.hour, dt.minute
    except Exception:
        return None


def evaluate_trip_start_gate(
    trip_day: Any,
    schedule_time: Any,
    *,
    trip_type: Any = None,
    route_duration_minutes: Any = None,
    extra_buffer_minutes: int = 0,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Returns schedule lock decision for starting a trip.
    """
    now_dt = now or datetime.now()
    day = _normalize_trip_day(trip_day)
    tm = _parse_time(schedule_time)

    if not day or tm is None:
        # If schedule metadata missing, do not hard-block start.
        return {
            "has_schedule": False,
            "can_start_now": True,
            "is_preassigned": False,
            "start_allowed_after": None,
            "seconds_until_start": 0,
            "server_now": now_dt.isoformat(timespec="seconds"),
            "reason": "SCHEDULE_METADATA_MISSING",
        }

    year = int(day[0:4])
    month = int(day[4:6])
    dd = int(day[6:8])
    effective_tm = tm
    day_shift = 0
    trip_mode = str(trip_type or "").strip().lower()
    if trip_mode == "pickup":
        timing_meta = derive_pickup_timing(
            schedule_time,
            route_duration_minutes,
            extra_buffer_minutes=extra_buffer_minutes,
        )
        pickup_tm = _parse_time(timing_meta.get("pickup_time"))
        if pickup_tm is not None:
            effective_tm = pickup_tm
            day_shift = int(timing_meta.get("day_offset") or 0)

    hh, mm = effective_tm
    allowed_after = datetime(year, month, dd, hh, mm, 0)
    if day_shift:
        allowed_after = allowed_after + timedelta(days=day_shift)
    can_start = now_dt >= allowed_after
    seconds_until_start = max(0, int((allowed_after - now_dt).total_seconds()))

    return {
        "has_schedule": True,
        "can_start_now": can_start,
        "is_preassigned": not can_start,
        "start_allowed_after": allowed_after.isoformat(timespec="seconds"),
        "seconds_until_start": seconds_until_start,
        "server_now": now_dt.isoformat(timespec="seconds"),
        "reason": None if can_start else "TRIP_NOT_STARTED_YET",
    }


def derive_pickup_timing(
    login_time: Any,
    route_duration_minutes: Any,
    *,
    extra_buffer_minutes: int = 0,
) -> Dict[str, Any]:
    """
    Derive pickup reporting time from login time and route duration.
    pickup_time = login_time - (route_duration_minutes + extra_buffer_minutes)
    """
    tm = _parse_time(login_time)
    try:
        route_min = max(0, int(route_duration_minutes or 0))
    except Exception:
        route_min = 0
    extra_min = max(0, int(extra_buffer_minutes or 0))
    total_lead_min = route_min + extra_min

    if tm is None:
        return {
            "has_timing": False,
            "login_time": str(login_time or ""),
            "pickup_time": None,
            "route_duration_minutes": route_min,
            "extra_buffer_minutes": extra_min,
            "total_lead_minutes": total_lead_min,
            "day_offset": 0,
            "reason": "LOGIN_TIME_INVALID",
        }

    login_total = (tm[0] * 60) + tm[1]
    pickup_total = login_total - total_lead_min
    day_offset = 0
    while pickup_total < 0:
        pickup_total += 24 * 60
        day_offset -= 1

    pickup_h = pickup_total // 60
    pickup_m = pickup_total % 60

    return {
        "has_timing": True,
        "login_time": f"{tm[0]:02d}:{tm[1]:02d}",
        "pickup_time": f"{pickup_h:02d}:{pickup_m:02d}",
        "route_duration_minutes": route_min,
        "extra_buffer_minutes": extra_min,
        "total_lead_minutes": total_lead_min,
        "day_offset": day_offset,
        "reason": None,
    }


def build_pickup_time_note(timing_meta: Dict[str, Any]) -> str:
    """
    Build UI-friendly pickup timing note for pickup trips.
    """
    if not timing_meta or not bool(timing_meta.get("has_timing")):
        return ""
    login_time = str(timing_meta.get("login_time") or "").strip()
    pickup_time = str(timing_meta.get("pickup_time") or "").strip()
    if not login_time or not pickup_time:
        return ""

    travel_min = int(timing_meta.get("route_duration_minutes") or 0)
    buffer_min = int(timing_meta.get("extra_buffer_minutes") or 0)
    day_offset = int(timing_meta.get("day_offset") or 0)
    day_suffix = " (previous day)" if day_offset < 0 else ""
    return (
        f"Start at {pickup_time}{day_suffix} for {login_time} login "
        f"(travel {travel_min} min + buffer {buffer_min} min)"
    )
