from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional, Set


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _table_columns(cur, table_name: str) -> Set[str]:
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(row[1]) for row in cur.fetchall()}


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _emit_trip_event(
    cur,
    trip_id: int,
    route_no: str,
    event_type: str,
    actor_role: str,
    actor_id: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    if not _table_exists(cur, "trip_events"):
        return
    cur.execute(
        """
        INSERT INTO trip_events (
            trip_id, route_no, event_type, actor_role, actor_id, payload_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(trip_id),
            str(route_no or ""),
            str(event_type or ""),
            str(actor_role or ""),
            None if actor_id is None else str(actor_id),
            json.dumps(payload or {}, ensure_ascii=True),
            _now_iso(),
        ),
    )


def _trip_snapshot(cur, trip_id: int) -> Dict[str, Any]:
    trip_cols = _table_columns(cur, "trips")
    cab_expr = "'' AS cab_no"
    if "vehicle_no" in trip_cols:
        cab_expr = "COALESCE(t.vehicle_no, d.vehicle_no, '') AS cab_no"
    else:
        cab_expr = "COALESCE(d.vehicle_no, '') AS cab_no"
    cur.execute(
        f"""
        SELECT
            t.id,
            t.route_no,
            t.status,
            t.driver_id,
            {cab_expr},
            t.trip_day,
            t.total_km
        FROM trips t
        LEFT JOIN drivers d ON CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)
        WHERE t.id = ?
        LIMIT 1
        """,
        (int(trip_id),),
    )
    row = cur.fetchone()
    return dict(row) if row else {}


def mark_trip_completed(
    conn,
    trip_id: int,
    *,
    actor_role: str,
    actor_id: Optional[str],
    total_km: Optional[float] = None,
    polyline: Optional[str] = None,
    route_json: Optional[str] = None,
) -> Dict[str, Any]:
    cur = conn.cursor()
    trip = _trip_snapshot(cur, trip_id)
    if not trip:
        raise ValueError("Trip not found")

    trip_cols = _table_columns(cur, "trips")
    completed_at = _now_iso()
    fields = ["status = 'completed'", "updated_at = ?"]
    params: list[Any] = [completed_at]

    if "end_time" in trip_cols:
        fields.insert(1, "end_time = ?")
        params.insert(1, completed_at)
    if total_km is not None and "total_km" in trip_cols:
        fields.append("total_km = ?")
        params.append(float(total_km))
    if polyline is not None and "polyline" in trip_cols:
        fields.append("polyline = ?")
        params.append(str(polyline))
    if route_json is not None and "route_json" in trip_cols:
        fields.append("route_json = ?")
        params.append(str(route_json))
    if "cancelled_at" in trip_cols:
        fields.append("cancelled_at = NULL")
    if "cancelled_by" in trip_cols:
        fields.append("cancelled_by = NULL")
    if "cancel_reason" in trip_cols:
        fields.append("cancel_reason = NULL")

    params.append(int(trip_id))
    cur.execute(f"UPDATE trips SET {', '.join(fields)} WHERE id = ?", tuple(params))

    if _table_exists(cur, "trip_cab_history"):
        cur.execute(
            """
            INSERT INTO trip_cab_history (
                trip_id, cab_no, driver_id, trip_day, total_km, operation, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(trip_id),
                str(trip.get("cab_no") or ""),
                trip.get("driver_id"),
                str(trip.get("trip_day") or ""),
                float(total_km) if total_km is not None else trip.get("total_km"),
                "completed",
                completed_at,
            ),
        )

    _emit_trip_event(
        cur,
        trip_id=int(trip_id),
        route_no=str(trip.get("route_no") or ""),
        event_type="trip_completed",
        actor_role=actor_role,
        actor_id=actor_id,
        payload={
            "completed_at": completed_at,
            "total_km": float(total_km) if total_km is not None else trip.get("total_km"),
        },
    )
    return {"trip_id": int(trip_id), "completed_at": completed_at}


def mark_trip_cancelled(
    conn,
    trip_id: int,
    *,
    reason: str,
    actor_role: str,
    actor_id: Optional[str],
) -> Dict[str, Any]:
    cur = conn.cursor()
    trip = _trip_snapshot(cur, trip_id)
    if not trip:
        raise ValueError("Trip not found")

    trip_cols = _table_columns(cur, "trips")
    cancelled_at = _now_iso()
    fields = ["status = 'cancelled'", "cancel_reason = ?", "updated_at = ?"]
    params: list[Any] = [str(reason or "").strip(), cancelled_at]
    if "cancelled_at" in trip_cols:
        fields.append("cancelled_at = ?")
        params.append(cancelled_at)
    if "cancelled_by" in trip_cols:
        fields.append("cancelled_by = ?")
        params.append(None if actor_id is None else str(actor_id))
    if "total_km" in trip_cols:
        fields.append("total_km = NULL")
    if "end_time" in trip_cols:
        fields.append("end_time = NULL")

    params.append(int(trip_id))
    cur.execute(f"UPDATE trips SET {', '.join(fields)} WHERE id = ?", tuple(params))

    _emit_trip_event(
        cur,
        trip_id=int(trip_id),
        route_no=str(trip.get("route_no") or ""),
        event_type="trip_cancelled",
        actor_role=actor_role,
        actor_id=actor_id,
        payload={"cancelled_at": cancelled_at, "reason": str(reason or "").strip()},
    )
    return {"trip_id": int(trip_id), "cancelled_at": cancelled_at}


def mark_member_no_show(
    conn,
    trip_id: int,
    employee_id: int,
    *,
    marked_by_driver_id: Optional[str],
    reason: str = "",
) -> Dict[str, Any]:
    cur = conn.cursor()
    te_cols = _table_columns(cur, "trip_employees")
    if "is_no_show" in te_cols:
        no_show_col = "is_no_show"
    elif "no_show" in te_cols:
        no_show_col = "no_show"
    else:
        raise ValueError("No no-show column found in trip_employees")

    marked_at = _now_iso()
    fields = [f"{no_show_col} = 1"]
    params: list[Any] = []
    if "no_show_marked_at" in te_cols:
        fields.append("no_show_marked_at = ?")
        params.append(marked_at)
    if "no_show_marked_by" in te_cols:
        fields.append("no_show_marked_by = ?")
        params.append(None if marked_by_driver_id is None else str(marked_by_driver_id))
    if "no_show_reason" in te_cols:
        fields.append("no_show_reason = ?")
        params.append(str(reason or "").strip())

    params.extend([int(trip_id), str(employee_id)])
    cur.execute(
        f"""
        UPDATE trip_employees
        SET {', '.join(fields)}
        WHERE trip_id = ? AND CAST(employee_id AS TEXT) = CAST(? AS TEXT)
        """,
        tuple(params),
    )

    trip = _trip_snapshot(cur, trip_id)
    _emit_trip_event(
        cur,
        trip_id=int(trip_id),
        route_no=str(trip.get("route_no") or ""),
        event_type="no_show_marked",
        actor_role="driver",
        actor_id=marked_by_driver_id,
        payload={
            "employee_id": int(employee_id),
            "reason": str(reason or "").strip(),
            "marked_at": marked_at,
        },
    )
    return {"trip_id": int(trip_id), "employee_id": int(employee_id), "marked_at": marked_at}


def apply_swap_approval(
    conn,
    trip_id: int,
    *,
    request_id: int,
    old_driver_id: Optional[str],
    new_driver_id: str,
    new_cab_no: Optional[str],
    reviewed_by: Optional[str],
) -> Dict[str, Any]:
    cur = conn.cursor()
    trip = _trip_snapshot(cur, trip_id)
    if not trip:
        raise ValueError("Trip not found")

    trip_cols = _table_columns(cur, "trips")
    fields = ["driver_id = ?", "updated_at = ?"]
    params: list[Any] = [str(new_driver_id), _now_iso()]
    if "vehicle_no" in trip_cols and new_cab_no is not None:
        fields.append("vehicle_no = ?")
        params.append(str(new_cab_no))
    params.append(int(trip_id))
    cur.execute(f"UPDATE trips SET {', '.join(fields)} WHERE id = ?", tuple(params))

    if _table_exists(cur, "swap_requests"):
        swap_cols = _table_columns(cur, "swap_requests")
        update_parts = ["status = 'approved'", "new_driver_id = ?", "updated_at = ?"]
        update_params: list[Any] = [str(new_driver_id), _now_iso()]
        if "reviewed_by" in swap_cols:
            update_parts.append("reviewed_by = ?")
            update_params.append(None if reviewed_by is None else str(reviewed_by))
        if "reviewed_at" in swap_cols:
            update_parts.append("reviewed_at = ?")
            update_params.append(_now_iso())
        update_params.append(int(request_id))
        cur.execute(
            f"UPDATE swap_requests SET {', '.join(update_parts)} WHERE id = ?",
            tuple(update_params),
        )

    _emit_trip_event(
        cur,
        trip_id=int(trip_id),
        route_no=str(trip.get("route_no") or ""),
        event_type="swap_approved",
        actor_role="admin",
        actor_id=reviewed_by,
        payload={
            "request_id": int(request_id),
            "old_driver_id": None if old_driver_id is None else str(old_driver_id),
            "new_driver_id": str(new_driver_id),
            "new_cab_no": str(new_cab_no or ""),
        },
    )
    return {"trip_id": int(trip_id), "request_id": int(request_id)}
