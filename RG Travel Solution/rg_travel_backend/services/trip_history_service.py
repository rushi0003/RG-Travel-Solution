from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


ACTIVE_STATUSES = ("created", "assigned", "started", "active", "in_progress", "live")
HISTORY_STATUSES = ("completed", "cancelled")


def _row_to_dict(row: Any) -> Dict[str, Any]:
    return dict(row) if row else {}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_day(value: Any) -> str:
    return _normalize_text(value).replace("-", "")


def _day_to_iso(day: str) -> str:
    if len(day) == 8 and day.isdigit():
        return f"{day[:4]}-{day[4:6]}-{day[6:]}"
    return day


def _driver_snapshot(
    driver_id: Any,
    name: Any,
    mobile: Any,
    cab_no: Any,
    role: str,
) -> Dict[str, Any]:
    return {
        "id": _normalize_text(driver_id),
        "name": _normalize_text(name),
        "mobile": _normalize_text(mobile),
        "cab_no": _normalize_text(cab_no),
        "role": role,
    }


def _history_status_filter(status: Optional[str]) -> Tuple[str, Tuple[str, ...]]:
    normalized = _normalize_text(status).lower()
    if normalized == "active":
        return (
            "LOWER(COALESCE(t.status, 'created')) IN ({})".format(",".join(["?"] * len(ACTIVE_STATUSES))),
            ACTIVE_STATUSES,
        )
    if normalized in {"completed", "cancelled"}:
        return "LOWER(COALESCE(t.status, '')) = ?", (normalized,)
    return (
        "LOWER(COALESCE(t.status, '')) IN ({})".format(",".join(["?"] * len(HISTORY_STATUSES))),
        HISTORY_STATUSES,
    )


def _attach_swap_context(cur, trip: Dict[str, Any]) -> None:
    current_driver = _driver_snapshot(
        trip.get("driver_id"),
        trip.get("driver_name"),
        trip.get("driver_mobile"),
        trip.get("cab_no"),
        "current",
    )
    trip["current_driver"] = current_driver
    trip["original_driver"] = current_driver
    trip["all_drivers"] = [current_driver]
    trip["has_emergency_swap"] = False
    trip["original_vehicle_no"] = current_driver.get("cab_no")
    trip["current_vehicle_no"] = current_driver.get("cab_no")

    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='swap_requests' LIMIT 1"
    )
    if not cur.fetchone():
        return

    cur.execute(
        """
        SELECT
            sr.id AS swap_request_id,
            sr.status AS swap_status,
            sr.old_driver_id,
            sr.new_driver_id,
            sr.new_driver_name,
            sr.new_driver_mobile,
            sr.new_cab_no,
            od.name AS old_driver_name,
            od.mobile AS old_driver_mobile,
            od.vehicle_no AS old_driver_cab_no,
            nd.name AS approved_new_driver_name,
            nd.mobile AS approved_new_driver_mobile,
            nd.vehicle_no AS approved_new_driver_cab_no
        FROM swap_requests sr
        LEFT JOIN drivers od ON CAST(od.id AS TEXT) = CAST(sr.old_driver_id AS TEXT)
        LEFT JOIN drivers nd ON CAST(nd.id AS TEXT) = CAST(sr.new_driver_id AS TEXT)
        WHERE sr.trip_id = ?
          AND LOWER(COALESCE(sr.status, '')) = 'approved'
        ORDER BY COALESCE(sr.reviewed_at, sr.updated_at, sr.created_at) DESC, sr.id DESC
        LIMIT 1
        """,
        (trip.get("id"),),
    )
    row = cur.fetchone()
    if not row:
        return

    swap = _row_to_dict(row)
    original_driver = _driver_snapshot(
        swap.get("old_driver_id"),
        swap.get("old_driver_name") or current_driver.get("name"),
        swap.get("old_driver_mobile"),
        swap.get("old_driver_cab_no") or current_driver.get("cab_no"),
        "original",
    )
    replacement_driver = _driver_snapshot(
        swap.get("new_driver_id") or current_driver.get("id"),
        swap.get("approved_new_driver_name")
        or swap.get("new_driver_name")
        or current_driver.get("name"),
        swap.get("approved_new_driver_mobile")
        or swap.get("new_driver_mobile")
        or current_driver.get("mobile"),
        swap.get("new_cab_no")
        or swap.get("approved_new_driver_cab_no")
        or current_driver.get("cab_no"),
        "replacement",
    )

    drivers = [original_driver]
    if replacement_driver != original_driver:
        drivers.append(replacement_driver)

    trip["swap_request_id"] = swap.get("swap_request_id")
    trip["swap_status"] = _normalize_text(swap.get("swap_status")).lower()
    trip["has_emergency_swap"] = len(drivers) > 1
    trip["original_driver"] = original_driver
    trip["current_driver"] = replacement_driver
    trip["all_drivers"] = drivers
    trip["original_driver_name"] = original_driver.get("name")
    trip["original_driver_mobile"] = original_driver.get("mobile")
    trip["replacement_driver_name"] = replacement_driver.get("name")
    trip["replacement_driver_mobile"] = replacement_driver.get("mobile")
    trip["original_vehicle_no"] = original_driver.get("cab_no")
    trip["current_vehicle_no"] = replacement_driver.get("cab_no")
    trip["replacement_cab_no"] = replacement_driver.get("cab_no")


def _attach_member_metrics(cur, trip: Dict[str, Any], viewer_employee_id: Optional[int]) -> None:
    cur.execute(
        """
        SELECT
            COUNT(*) AS employee_count,
            SUM(CASE WHEN COALESCE(is_no_show, 0) = 1 THEN 1 ELSE 0 END) AS no_show_count
        FROM trip_employees
        WHERE trip_id = ?
        """,
        (trip.get("id"),),
    )
    counts = _row_to_dict(cur.fetchone())
    trip["employee_count"] = int(counts.get("employee_count") or 0)
    trip["no_show_count"] = int(counts.get("no_show_count") or 0)
    trip["has_no_show"] = trip["no_show_count"] > 0
    cur.execute(
        """
        SELECT te.employee_id, e.name, e.mobile
        FROM trip_employees te
        LEFT JOIN employees e ON CAST(e.id AS TEXT) = CAST(te.employee_id AS TEXT)
        WHERE te.trip_id = ?
          AND COALESCE(te.is_no_show, 0) = 1
        ORDER BY te.sequence_no ASC, e.name ASC
        """,
        (trip.get("id"),),
    )
    trip["no_show_members"] = [
        {
            "employee_id": str(row["employee_id"]),
            "name": _normalize_text(row["name"]),
            "mobile": _normalize_text(row["mobile"]),
        }
        for row in cur.fetchall()
    ]

    if viewer_employee_id is None:
        return

    cur.execute(
        """
        SELECT COALESCE(is_no_show, 0) AS is_no_show
        FROM trip_employees
        WHERE trip_id = ? AND CAST(employee_id AS TEXT) = CAST(? AS TEXT)
        LIMIT 1
        """,
        (trip.get("id"), viewer_employee_id),
    )
    row = cur.fetchone()
    is_no_show = int((row["is_no_show"] if row else 0) or 0) == 1
    trip["member_status"] = "no_show" if is_no_show else "completed_member"


def _serialize_trip(cur, row: Any, viewer_employee_id: Optional[int]) -> Dict[str, Any]:
    src = _row_to_dict(row)
    trip_day = _normalize_day(src.get("trip_day"))
    status = _normalize_text(src.get("status")).lower()
    completed = status == "completed"
    cancelled = status == "cancelled"
    total_km = src.get("total_km")
    total_km_value = float(total_km) if total_km not in (None, "") and completed else None

    trip: Dict[str, Any] = {
        "id": src.get("id"),
        "trip_id": src.get("id"),
        "route_no": _normalize_text(src.get("route_no")),
        "trip_type": _normalize_text(src.get("trip_type")),
        "trip_day": trip_day,
        "trip_date": _day_to_iso(trip_day),
        "schedule_time": _normalize_text(src.get("schedule_time")),
        "status": status,
        "driver_id": _normalize_text(src.get("driver_id")),
        "driver_name": _normalize_text(src.get("driver_name")),
        "driver_mobile": _normalize_text(src.get("driver_mobile")),
        "vehicle_type": src.get("vehicle_type"),
        "cab_no": _normalize_text(src.get("cab_no")),
        "vehicle_no": _normalize_text(src.get("cab_no")),
        "start_time": src.get("start_time"),
        "end_time": src.get("end_time"),
        "created_at": src.get("created_at"),
        "updated_at": src.get("updated_at"),
        "cancel_reason": _normalize_text(src.get("cancel_reason")),
        "cancelled_at": src.get("cancelled_at"),
        "completed_at": src.get("end_time") if completed else None,
        "total_km": total_km_value,
        "distance_km": total_km_value,
        "show_total_km": completed,
        "distance_available": completed,
        "history_category": "history" if status in HISTORY_STATUSES else "active",
        "history_visible_at": src.get("end_time") if completed else src.get("cancelled_at") if cancelled else src.get("updated_at"),
    }

    if not cancelled:
        trip["cancel_reason"] = ""

    _attach_member_metrics(cur, trip, viewer_employee_id)
    _attach_swap_context(cur, trip)
    return trip


def _search_aliases(text: str) -> List[str]:
    base = _normalize_text(text).lower()
    if not base:
        return []
    variants = {
        base,
        base.replace("-", " "),
        base.replace("_", " "),
    }
    if base == "noshow":
        variants.update({"no show", "no-show"})
    if base in {"no show", "no-show"}:
        variants.update({"noshow"})
    if base == "swap":
        variants.update({"emergency swap", "replacement", "driver swap"})
    if base == "emergency":
        variants.update({"emergency swap"})
    return [v for v in variants if v]


def _trip_search_text(cur, trip: Dict[str, Any]) -> str:
    cur.execute(
        """
        SELECT COALESCE(e.name, ''), COALESCE(e.mobile, '')
        FROM trip_employees te
        LEFT JOIN employees e ON CAST(e.id AS TEXT) = CAST(te.employee_id AS TEXT)
        WHERE te.trip_id = ?
        ORDER BY te.sequence_no ASC, e.name ASC
        """,
        (trip.get("id"),),
    )
    employee_terms: List[str] = []
    for row in cur.fetchall():
        employee_terms.append(_normalize_text(row[0]))
        employee_terms.append(_normalize_text(row[1]))

    no_show_terms = [
        _normalize_text(item.get("name"))
        for item in (trip.get("no_show_members") or [])
        if isinstance(item, dict)
    ]
    semantic_terms: List[str] = []
    if trip.get("has_no_show"):
        semantic_terms.extend(["no show", "no-show", "noshow"])
    if trip.get("has_emergency_swap"):
        semantic_terms.extend(["swap", "emergency swap", "replacement", "driver swap"])

    return " ".join(
        [
            _normalize_text(trip.get("route_no")),
            _normalize_text(trip.get("status")),
            _normalize_text(trip.get("trip_type")),
            _normalize_text(trip.get("driver_name")),
            _normalize_text(trip.get("cab_no")),
            _normalize_text(trip.get("original_driver_name")),
            _normalize_text(trip.get("replacement_driver_name")),
            _normalize_text(trip.get("original_vehicle_no")),
            _normalize_text(trip.get("current_vehicle_no")),
            _normalize_text(trip.get("cancel_reason")),
            _normalize_text(trip.get("trip_date")),
            *employee_terms,
            *no_show_terms,
            *semantic_terms,
        ]
    ).lower()


def _order_clause(sort: Optional[str]) -> str:
    normalized = _normalize_text(sort).lower()
    if normalized == "km_desc":
        return "ORDER BY CASE WHEN LOWER(COALESCE(t.status, '')) = 'completed' THEN COALESCE(t.total_km, 0) ELSE -1 END DESC, REPLACE(COALESCE(t.trip_day, ''), '-', '') DESC, COALESCE(t.schedule_time, '') DESC, t.id DESC"
    if normalized == "km_asc":
        return "ORDER BY CASE WHEN LOWER(COALESCE(t.status, '')) = 'completed' THEN 0 ELSE 1 END ASC, COALESCE(t.total_km, 999999) ASC, REPLACE(COALESCE(t.trip_day, ''), '-', '') DESC, COALESCE(t.schedule_time, '') DESC, t.id DESC"
    return "ORDER BY REPLACE(COALESCE(t.trip_day, ''), '-', '') DESC, COALESCE(t.schedule_time, '') DESC, t.id DESC"


def list_trip_history(
    conn,
    *,
    viewer_driver_id: Optional[int] = None,
    viewer_employee_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    admin_id: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    trip_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    limit = max(1, min(int(limit), 10000))
    offset = max(0, int(offset))

    cur = conn.cursor()
    cur.execute("PRAGMA table_info(trips)")
    trip_cols = {str(r[1]) for r in cur.fetchall()}
    cab_expr = "COALESCE(d.vehicle_no, '')"
    if "vehicle_no" in trip_cols:
        cab_expr = "COALESCE(t.vehicle_no, d.vehicle_no, '')"

    where: List[str] = []
    params: List[Any] = []

    status_sql, status_params = _history_status_filter(status)
    where.append(status_sql)
    params.extend(status_params)

    if viewer_driver_id is not None:
        where.append("CAST(t.driver_id AS TEXT) = CAST(? AS TEXT)")
        params.append(viewer_driver_id)
    elif driver_id is not None:
        where.append("CAST(t.driver_id AS TEXT) = CAST(? AS TEXT)")
        params.append(driver_id)

    scoped_employee_id = viewer_employee_id if viewer_employee_id is not None else employee_id
    if scoped_employee_id is not None:
        where.append(
            """
            EXISTS (
                SELECT 1
                FROM trip_employees te_scope
                WHERE te_scope.trip_id = t.id
                  AND CAST(te_scope.employee_id AS TEXT) = CAST(? AS TEXT)
            )
            """
        )
        params.append(scoped_employee_id)

    normalized_admin_id = _normalize_text(admin_id)
    if normalized_admin_id:
        where.append("CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)")
        params.append(normalized_admin_id)

    normalized_type = _normalize_text(trip_type).lower()
    if normalized_type in {"pickup", "drop"}:
        where.append("LOWER(COALESCE(t.operation, t.trip_type, '')) = ?")
        params.append(normalized_type)

    from_day = _normalize_day(from_date)
    if from_day:
        where.append("REPLACE(COALESCE(t.trip_day, ''), '-', '') >= ?")
        params.append(from_day)

    to_day = _normalize_day(to_date)
    if to_day:
        where.append("REPLACE(COALESCE(t.trip_day, ''), '-', '') <= ?")
        params.append(to_day)

    query = f"""
        FROM trips t
        LEFT JOIN drivers d ON CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)
        WHERE {' AND '.join(where)}
    """
    order_clause = _order_clause(sort)

    search_text = _normalize_text(search).lower()
    if search_text:
        cur.execute(
            f"""
            SELECT t.id
            {query}
            {order_clause}
            """,
            tuple(params),
        )
        candidate_ids = [int(row[0]) for row in cur.fetchall()]
        filtered_ids: List[int] = []
        needles = _search_aliases(search_text)
        for trip_id in candidate_ids:
            cur.execute(
                f"""
                SELECT
                    t.id, t.route_no, LOWER(COALESCE(t.operation, t.trip_type, '')) AS trip_type,
                    REPLACE(COALESCE(t.trip_day, ''), '-', '') AS trip_day, t.schedule_time, LOWER(COALESCE(t.status, '')) AS status,
                    t.driver_id, d.name AS driver_name, d.mobile AS driver_mobile,
                    {cab_expr} AS cab_no, t.vehicle_type, t.start_time, t.end_time,
                    t.cancel_reason, t.cancelled_at, t.total_km, t.created_at, t.updated_at
                FROM trips t
                LEFT JOIN drivers d ON CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)
                WHERE t.id = ?
                """,
                (trip_id,),
            )
            trip = _serialize_trip(cur, cur.fetchone(), viewer_employee_id)
            haystack = _trip_search_text(cur, trip)
            if any(needle in haystack for needle in needles):
                filtered_ids.append(trip_id)

        total_count = len(filtered_ids)
        paged_ids = filtered_ids[offset: offset + limit]
        trips: List[Dict[str, Any]] = []
        for trip_id in paged_ids:
            cur.execute(
                f"""
                SELECT
                    t.id, t.route_no, LOWER(COALESCE(t.operation, t.trip_type, '')) AS trip_type,
                    REPLACE(COALESCE(t.trip_day, ''), '-', '') AS trip_day, t.schedule_time, LOWER(COALESCE(t.status, '')) AS status,
                    t.driver_id, d.name AS driver_name, d.mobile AS driver_mobile,
                    {cab_expr} AS cab_no, t.vehicle_type, t.start_time, t.end_time,
                    t.cancel_reason, t.cancelled_at, t.total_km, t.created_at, t.updated_at
                FROM trips t
                LEFT JOIN drivers d ON CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)
                WHERE t.id = ?
                """,
                (trip_id,),
            )
            trips.append(_serialize_trip(cur, cur.fetchone(), viewer_employee_id))
        return trips, total_count

    cur.execute(f"SELECT COUNT(*) {query}", tuple(params))
    total_count = int(cur.fetchone()[0] or 0)

    cur.execute(
        f"""
        SELECT
            t.id, t.route_no, LOWER(COALESCE(t.operation, t.trip_type, '')) AS trip_type,
            REPLACE(COALESCE(t.trip_day, ''), '-', '') AS trip_day, t.schedule_time, LOWER(COALESCE(t.status, '')) AS status,
            t.driver_id, d.name AS driver_name, d.mobile AS driver_mobile,
            {cab_expr} AS cab_no, t.vehicle_type, t.start_time, t.end_time,
            t.cancel_reason, t.cancelled_at, t.total_km, t.created_at, t.updated_at
        {query}
        {order_clause}
        LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, offset]),
    )
    trips = [_serialize_trip(cur, row, viewer_employee_id) for row in cur.fetchall()]
    return trips, total_count
