"""
Assignment Service - Step 6 vehicle/driver assignment rules.

Rules implemented:
1. Use only approved and active drivers.
2. Use only available vehicles (vehicles.is_available = 1 when table is present).
3. Rotation: avoid repeatedly assigning the same vehicle for same day/time slot.
4. Go-home preference: if approved request exists, prefer groups near driver home.
5. Admin pre-selected vehicles: restrict candidates to selected vehicles only.
6. Return mapping group -> {vehicle_id, driver_id, vehicle_no, vehicle_type}.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def _table_exists(cursor: Any, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _group_centroid(group: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    members = group.get("members") or []
    lat_vals: List[float] = []
    lng_vals: List[float] = []

    for m in members:
        lat = m.get("lat")
        lng = m.get("lng")
        if lat is None or lng is None:
            continue
        try:
            lat_vals.append(float(lat))
            lng_vals.append(float(lng))
        except Exception:
            continue

    if not lat_vals or not lng_vals:
        return None, None
    return (sum(lat_vals) / len(lat_vals), sum(lng_vals) / len(lng_vals))


def _normalize_trip_day(trip_day: str) -> Tuple[str, str]:
    raw = str(trip_day or "").strip()
    raw_compact = raw.replace("-", "")
    if len(raw_compact) == 8 and raw_compact.isdigit():
        return raw_compact, f"{raw_compact[:4]}-{raw_compact[4:6]}-{raw_compact[6:]}"
    today = datetime.now().strftime("%Y%m%d")
    return today, f"{today[:4]}-{today[4:6]}-{today[6:]}"


def _go_home_request_info(cursor: Any, driver_id: str, trip_day: str) -> Dict[str, Any]:
    """Check if driver has an approved go-home request (any date or for trip_day if travel_date exists)."""
    try:
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(driver_hometown_requests)").fetchall()]
        has_travel_date = "travel_date" in cols
        if has_travel_date:
            compact_day, dashed_day = _normalize_trip_day(trip_day)
            cursor.execute(
                """
                SELECT r.requested_home_town,
                       REPLACE(COALESCE(travel_date, ''), '-', '') AS req_day
                FROM driver_hometown_requests r
                WHERE r.driver_id = ? AND r.status = 'approved'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM trips t
                    WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                      AND LOWER(COALESCE(t.status, 'created')) IN
                          ('created','assigned','started','active','in_progress','live','completed')
                      AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                          datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                  )
                ORDER BY
                  CASE
                    WHEN REPLACE(COALESCE(travel_date, ''), '-', '') = ? THEN 0
                    WHEN COALESCE(travel_date, '') = ? THEN 0
                    WHEN COALESCE(travel_date, '') = '' THEN 1
                    ELSE 2
                  END ASC, id DESC
                LIMIT 1
                """,
                (driver_id, compact_day, dashed_day),
            )
        else:
            cursor.execute(
                """
                SELECT r.requested_home_town
                FROM driver_hometown_requests r
                WHERE r.driver_id = ? AND r.status = 'approved'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM trips t
                    WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                      AND LOWER(COALESCE(t.status, 'created')) IN
                          ('created','assigned','started','active','in_progress','live','completed')
                      AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                          datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                  )
                ORDER BY r.id DESC
                LIMIT 1
                """,
                (driver_id,),
            )
        row = cursor.fetchone()
        if not row:
            return {"approved": False, "priority_tier": 2, "requested_home_town": None}
        requested_town = row[0]
        if has_travel_date and len(row) > 1:
            req_day = str(row[1] or "").strip()
            compact_day, _ = _normalize_trip_day(trip_day)
            tier = 0 if req_day == compact_day else 1
        else:
            tier = 0
        return {
            "approved": True,
            "priority_tier": tier,
            "requested_home_town": requested_town,
        }
    except Exception:
        return {"approved": False, "priority_tier": 2, "requested_home_town": None}


def _fetch_candidates(
    conn: Any,
    required_capacity: int,
    selected_vehicle_ids: Optional[List[int]],
    scheduled_time: str,
    trip_day: str,
) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    has_vehicles = _table_exists(cursor, "vehicles")

    candidates: List[Dict[str, Any]] = []

    if has_vehicles:
        where: List[str] = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "v.is_available = 1",
            "(CAST(v.vehicle_type AS TEXT) = ? OR v.vehicle_type = ?)",
        ]
        params: List[Any] = [str(required_capacity), required_capacity]

        if selected_vehicle_ids:
            placeholders = ",".join(["?"] * len(selected_vehicle_ids))
            where.append(f"v.vehicle_id IN ({placeholders})")
            params.extend(selected_vehicle_ids)

        # Exclude drivers already busy at same day/time.
        where.append(
            """
            d.id NOT IN (
                SELECT driver_id
                FROM trips
                WHERE trip_day = ?
                  AND COALESCE(time_slot, schedule_time, '') = ?
                  AND status IN ('created', 'assigned', 'started')
                  AND driver_id IS NOT NULL
            )
            """
        )
        params.extend([trip_day, scheduled_time])

        cursor.execute(
            f"""
            SELECT
                d.id AS driver_id,
                d.name AS driver_name,
                d.mobile AS driver_phone,
                d.home_town,
                d.hometown_lat,
                d.hometown_lng,
                v.vehicle_id,
                v.vehicle_no,
                v.vehicle_type
            FROM drivers d
            JOIN vehicles v
              ON (d.vehicle_id = v.vehicle_id OR d.vehicle_no = v.vehicle_no)
            WHERE {" AND ".join(where)}
            ORDER BY v.vehicle_type DESC, d.id ASC
            """
        , tuple(params))

        rows = cursor.fetchall()
        for r in rows:
            candidates.append(
                {
                    "driver_id": str(r[0]),
                    "driver_name": r[1],
                    "driver_phone": r[2],
                    "home_town": r[3],
                    "hometown_lat": r[4],
                    "hometown_lng": r[5],
                    "vehicle_id": r[6],
                    "vehicle_no": r[7],
                    "vehicle_type": int(r[8]) if r[8] is not None else required_capacity,
                }
            )
            go_home = _go_home_request_info(cursor, str(r[0]), trip_day)
            candidates[-1]["go_home_approved"] = bool(go_home.get("approved"))
            candidates[-1]["go_home_priority_tier"] = int(go_home.get("priority_tier", 2))
            candidates[-1]["go_home_town"] = go_home.get("requested_home_town")

    # Backward-compatible fallback when vehicles table is empty/not present.
    if not candidates:
        compact_day, _ = _normalize_trip_day(trip_day)
        params: List[Any] = [str(required_capacity)]
        where = [
            "d.is_approved = 1",
            "COALESCE(d.is_active, 1) = 1",
            "CAST(d.vehicle_type AS TEXT) = ?",
            """
            d.id NOT IN (
                SELECT driver_id
                FROM trips
                WHERE REPLACE(COALESCE(trip_day, ''), '-', '') = ?
                  AND COALESCE(time_slot, schedule_time, '') = ?
                  AND LOWER(COALESCE(status, 'created')) IN ('created', 'assigned', 'started', 'active', 'in_progress')
                  AND driver_id IS NOT NULL
            )
            """,
        ]
        if selected_vehicle_ids:
            placeholders = ",".join(["?"] * len(selected_vehicle_ids))
            where.append(f"d.id IN ({placeholders})")
            params.extend([str(v) for v in selected_vehicle_ids])
        params.extend([compact_day, scheduled_time])

        cursor.execute(
            f"""
            SELECT d.id, d.name, d.mobile, d.home_town, d.hometown_lat, d.hometown_lng, d.vehicle_no, d.vehicle_type
            FROM drivers d
            WHERE {" AND ".join(where)}
            ORDER BY d.id ASC
            """,
            tuple(params),
        )
        for r in cursor.fetchall():
            candidates.append(
                {
                    "driver_id": str(r[0]),
                    "driver_name": r[1],
                    "driver_phone": r[2],
                    "home_town": r[3],
                    "hometown_lat": r[4],
                    "hometown_lng": r[5],
                    "vehicle_id": None,
                    "vehicle_no": r[6],
                    "vehicle_type": int(r[7]) if str(r[7]).isdigit() else required_capacity,
                }
            )
            go_home = _go_home_request_info(cursor, str(r[0]), trip_day)
            candidates[-1]["go_home_approved"] = bool(go_home.get("approved"))
            candidates[-1]["go_home_priority_tier"] = int(go_home.get("priority_tier", 2))
            candidates[-1]["go_home_town"] = go_home.get("requested_home_town")

    return candidates


def _rotation_penalty(
    conn: Any,
    candidate: Dict[str, Any],
    scheduled_time: str,
    trip_day: str,
) -> float:
    cursor = conn.cursor()
    penalty = 0.0

    # Same-slot repetition on same day.
    vehicle_no = candidate.get("vehicle_no")
    if vehicle_no:
        cursor.execute(
            """
            SELECT COUNT(1)
            FROM trips
            WHERE trip_day = ?
              AND COALESCE(time_slot, schedule_time, '') = ?
              AND vehicle_no = ?
              AND status IN ('created','assigned','started','completed')
            """,
            (trip_day, scheduled_time, vehicle_no),
        )
        same_slot_count = int((cursor.fetchone() or [0])[0])
        penalty += same_slot_count * 20.0

        cursor.execute(
            """
            SELECT COUNT(1)
            FROM trips
            WHERE trip_day = ?
              AND vehicle_no = ?
              AND status IN ('created','assigned','started','completed')
            """,
            (trip_day, vehicle_no),
        )
        day_count = int((cursor.fetchone() or [0])[0])
        penalty += day_count * 5.0

    return penalty


def _go_home_bonus(
    candidate: Dict[str, Any],
    group: Dict[str, Any],
) -> float:
    if not bool(candidate.get("go_home_approved")):
        return 0.0

    # Prefer proximity to hometown coordinates when available.
    lat = candidate.get("hometown_lat")
    lng = candidate.get("hometown_lng")
    group_lat, group_lng = _group_centroid(group)
    if lat is not None and lng is not None and group_lat is not None and group_lng is not None:
        try:
            km = _haversine_km(float(lat), float(lng), float(group_lat), float(group_lng))
            return max(0.0, 40.0 - min(40.0, km))
        except Exception:
            pass

    # Fallback: hometown string found in member addresses.
    town = str(candidate.get("go_home_town") or candidate.get("home_town") or "").strip().lower()
    if town:
        for m in group.get("members") or []:
            addr = str(m.get("address") or m.get("home_address") or "").lower()
            if town in addr:
                return 30.0

    return 10.0


def assign_group_resources(
    conn: Any,
    groups: List[Dict[str, Any]],
    scheduled_time: str,
    trip_day: str,
    selected_vehicle_ids: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Any]]:
    """
    Assign a driver + vehicle to each group.

    Returns:
      {group_index: {"vehicle_id","vehicle_no","vehicle_type","driver_id","driver_name","driver_phone"}}
    """
    assignments: Dict[int, Dict[str, Any]] = {}
    used_drivers: Set[str] = set()
    used_vehicles: Set[str] = set()

    for idx, group in enumerate(groups):
        members = group.get("members") or []
        required_capacity = int(group.get("vehicle_type") or (6 if len(members) > 4 else 4))

        candidates = _fetch_candidates(
            conn=conn,
            required_capacity=required_capacity,
            selected_vehicle_ids=selected_vehicle_ids,
            scheduled_time=scheduled_time,
            trip_day=trip_day,
        )

        # In-request dedupe so the same resource is not reused in a single batch.
        filtered = []
        for c in candidates:
            if c["driver_id"] in used_drivers:
                continue
            if c.get("vehicle_no") and c["vehicle_no"] in used_vehicles:
                continue
            filtered.append(c)

        best: Optional[Dict[str, Any]] = None
        best_key: Optional[Tuple[int, float, float]] = None
        for c in filtered:
            score = _rotation_penalty(conn, c, scheduled_time, trip_day)
            score -= _go_home_bonus(c, group)
            go_home_tier = int(c.get("go_home_priority_tier", 2))
            if not bool(c.get("go_home_approved")):
                go_home_tier = 2
            # Stable tie-break by driver_id/vehicle_no.
            tie = (hash(str(c["driver_id"])) % 1000) / 100000.0
            key = (go_home_tier, score, tie)

            if best_key is None or key < best_key:
                best_key = key
                best = c

        if not best:
            continue

        assignments[idx] = {
            "driver_id": best["driver_id"],
            "driver_name": best.get("driver_name"),
            "driver_phone": best.get("driver_phone"),
            "vehicle_id": best.get("vehicle_id"),
            "vehicle_no": best.get("vehicle_no"),
            "vehicle_type": best.get("vehicle_type", required_capacity),
        }

        used_drivers.add(str(best["driver_id"]))
        if best.get("vehicle_no"):
            used_vehicles.add(str(best["vehicle_no"]))

    return assignments


def assign_drivers_to_trips(
    conn: Any,
    groups: List[Any],
    scheduled_time: str,
    trip_day: str,
    office_lat: float,
    office_lng: float,
) -> Dict[int, Dict[str, Any]]:
    """
    Backward-compatible wrapper used by existing grouping flow.
    """
    normalized: List[Dict[str, Any]] = []
    for g in groups:
        if isinstance(g, dict):
            members = g.get("members") or g.get("ordered_stops") or []
            normalized.append(
                {
                    "members": members,
                    "vehicle_type": int(g.get("vehicle_type") or (6 if len(members) > 4 else 4)),
                }
            )
        else:
            members = getattr(g, "members", [])
            normalized.append(
                {
                    "members": members,
                    "vehicle_type": int(getattr(g, "vehicle_type", 6 if len(members) > 4 else 4)),
                }
            )

    mapped = assign_group_resources(
        conn=conn,
        groups=normalized,
        scheduled_time=scheduled_time,
        trip_day=trip_day,
        selected_vehicle_ids=None,
    )

    # Preserve old keys for current callers.
    result: Dict[int, Dict[str, Any]] = {}
    for k, v in mapped.items():
        result[k] = {
            "driver_id": v.get("driver_id"),
            "vehicle_no": v.get("vehicle_no"),
            "vehicle_id": v.get("vehicle_id"),
            "vehicle_type": v.get("vehicle_type"),
        }
    return result
