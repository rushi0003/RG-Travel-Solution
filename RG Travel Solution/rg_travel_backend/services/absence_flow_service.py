from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence


ABSENCE_KIND = "absence"
CANCEL_KIND = "cancel"
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"


class AbsenceFlowError(Exception):
    pass


@dataclass(frozen=True)
class ReviewResult:
    request_id: int
    request_kind: str
    status: str
    employee_id: int
    dates: List[str]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: Any) -> Dict[str, Any]:
    return dict(row) if row else {}


def ensure_absence_flow_tables(conn: Any) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS absence_request_batches (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id       TEXT NOT NULL,
            request_kind      TEXT NOT NULL
                              CHECK(request_kind IN ('absence', 'cancel')),
            original_request_id INTEGER,
            from_date         TEXT NOT NULL,
            to_date           TEXT NOT NULL,
            total_days        INTEGER NOT NULL DEFAULT 1,
            reason            TEXT,
            status            TEXT NOT NULL DEFAULT 'pending'
                              CHECK(status IN ('pending', 'approved', 'rejected')),
            admin_reason      TEXT,
            reviewed_by       TEXT,
            reviewed_at       TEXT,
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY(original_request_id) REFERENCES absence_request_batches(id) ON DELETE SET NULL,
            FOREIGN KEY(reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS absence_request_batch_dates (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id        INTEGER NOT NULL,
            absence_date      TEXT NOT NULL,
            created_at        TEXT NOT NULL,
            UNIQUE(request_id, absence_date),
            FOREIGN KEY(request_id) REFERENCES absence_request_batches(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_absence_batch_employee_status
        ON absence_request_batches(employee_id, status, request_kind)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_absence_batch_dates_date
        ON absence_request_batch_dates(absence_date)
        """
    )
    conn.commit()


def _parse_iso_date(raw: Any, field_name: str = "date") -> date:
    try:
        return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
    except Exception as exc:
        raise AbsenceFlowError(f"{field_name} must be YYYY-MM-DD") from exc


def normalize_request_dates(payload: Dict[str, Any]) -> List[str]:
    date_values: List[str] = []

    if isinstance(payload.get("dates"), list):
        for item in payload.get("dates") or []:
            value = str(item or "").strip()
            if value:
                date_values.append(value)

    for key in ("absent_date", "date"):
        value = str(payload.get(key) or "").strip()
        if value:
            date_values.append(value)

    from_date = str(payload.get("from_date") or "").strip()
    to_date = str(payload.get("to_date") or "").strip()
    if from_date or to_date:
        if not from_date or not to_date:
            raise AbsenceFlowError("from_date and to_date are both required for range requests")
        start_dt = _parse_iso_date(from_date, "from_date")
        end_dt = _parse_iso_date(to_date, "to_date")
        if end_dt < start_dt:
            raise AbsenceFlowError("to_date must be on or after from_date")
        current = start_dt
        while current <= end_dt:
            date_values.append(current.isoformat())
            current = current + timedelta(days=1)

    unique_dates = sorted({_parse_iso_date(item).isoformat() for item in date_values})
    if not unique_dates:
        raise AbsenceFlowError("At least one valid date is required")
    return unique_dates


def validate_future_dates(date_strings: Sequence[str], *, allow_today: bool = False) -> None:
    today = date.today()
    for raw in date_strings:
        target = _parse_iso_date(raw)
        if allow_today:
            if target < today:
                raise AbsenceFlowError("Dates must be today or future")
        elif target <= today:
            raise AbsenceFlowError("Requests must be submitted at least one day before the absence date")


def _load_employee(conn: Any, employee_id: int) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, COALESCE(is_approved, 0) AS is_approved FROM employees WHERE id = ? LIMIT 1",
        (employee_id,),
    )
    row = cur.fetchone()
    if not row:
        raise AbsenceFlowError("Employee not found")
    return _row_to_dict(row)


def _existing_batch_conflicts(
    conn: Any,
    employee_id: int,
    dates: Sequence[str],
    *,
    request_kind: str,
) -> List[str]:
    ensure_absence_flow_tables(conn)
    placeholders = ",".join(["?"] * len(dates))
    params: List[Any] = [str(employee_id), request_kind, PENDING, APPROVED, *dates]
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT DISTINCT d.absence_date
        FROM absence_request_batches b
        JOIN absence_request_batch_dates d
          ON d.request_id = b.id
        WHERE CAST(b.employee_id AS TEXT) = CAST(? AS TEXT)
          AND b.request_kind = ?
          AND b.status IN (?, ?)
          AND d.absence_date IN ({placeholders})
        ORDER BY d.absence_date
        """,
        params,
    )
    return [str(row[0]) for row in cur.fetchall()]


def _legacy_absence_conflicts(conn: Any, employee_id: int, dates: Sequence[str]) -> List[str]:
    placeholders = ",".join(["?"] * len(dates))
    cur = conn.cursor()
    conflicts: set[str] = set()
    for table_name, date_col in (
        ("employee_absences", "absence_date"),
        ("employee_absence_requests", "absent_date"),
    ):
        try:
            cur.execute(
                f"""
                SELECT DISTINCT {date_col}
                FROM {table_name}
                WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
                  AND status IN ('pending', 'approved')
                  AND {date_col} IN ({placeholders})
                """,
                [str(employee_id), *dates],
            )
            conflicts.update(str(row[0]) for row in cur.fetchall())
        except Exception:
            continue
    return sorted(conflicts)


def create_absence_request(
    conn: Any,
    employee_id: int,
    dates: Sequence[str],
    *,
    reason: str = "",
) -> Dict[str, Any]:
    ensure_absence_flow_tables(conn)
    _load_employee(conn, employee_id)
    normalized_dates = sorted({_parse_iso_date(item).isoformat() for item in dates})
    validate_future_dates(normalized_dates)

    conflicts = sorted(
        set(_existing_batch_conflicts(conn, employee_id, normalized_dates, request_kind=ABSENCE_KIND))
        | set(_legacy_absence_conflicts(conn, employee_id, normalized_dates))
    )
    if conflicts:
        raise AbsenceFlowError(
            f"Absence request already exists for: {', '.join(conflicts)}"
        )

    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO absence_request_batches (
            employee_id, request_kind, from_date, to_date, total_days,
            reason, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(employee_id),
            ABSENCE_KIND,
            normalized_dates[0],
            normalized_dates[-1],
            len(normalized_dates),
            (reason or "").strip(),
            PENDING,
            now,
            now,
        ),
    )
    request_id = int(cur.lastrowid)
    cur.executemany(
        """
        INSERT INTO absence_request_batch_dates (request_id, absence_date, created_at)
        VALUES (?, ?, ?)
        """,
        [(request_id, item, now) for item in normalized_dates],
    )
    conn.commit()
    return get_request_details(conn, request_id)


def create_cancel_request(
    conn: Any,
    employee_id: int,
    dates: Sequence[str],
    *,
    reason: str = "",
) -> Dict[str, Any]:
    ensure_absence_flow_tables(conn)
    _load_employee(conn, employee_id)
    normalized_dates = sorted({_parse_iso_date(item).isoformat() for item in dates})
    validate_future_dates(normalized_dates)

    cur = conn.cursor()
    approved_dates: List[str] = []
    for item in normalized_dates:
        cur.execute(
            """
            SELECT 1
            FROM employee_absences
            WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
              AND absence_date = ?
              AND status = 'approved'
            LIMIT 1
            """,
            (str(employee_id), item),
        )
        if cur.fetchone():
            approved_dates.append(item)
    if len(approved_dates) != len(normalized_dates):
        missing = sorted(set(normalized_dates) - set(approved_dates))
        raise AbsenceFlowError(
            f"Only approved absence dates can be cancelled. Missing approved dates: {', '.join(missing)}"
        )

    conflicts = _existing_batch_conflicts(conn, employee_id, normalized_dates, request_kind=CANCEL_KIND)
    if conflicts:
        raise AbsenceFlowError(
            f"Cancellation request already exists for: {', '.join(conflicts)}"
        )

    cur.execute(
        """
        SELECT b.id, COUNT(*) AS matched_days
        FROM absence_request_batches b
        JOIN absence_request_batch_dates d
          ON d.request_id = b.id
        WHERE CAST(b.employee_id AS TEXT) = CAST(? AS TEXT)
          AND b.request_kind = 'absence'
          AND b.status = 'approved'
          AND d.absence_date IN ({placeholders})
        GROUP BY b.id
        ORDER BY matched_days DESC, b.id DESC
        LIMIT 1
        """.replace("{placeholders}", ",".join(["?"] * len(normalized_dates))),
        [str(employee_id), *normalized_dates],
    )
    source_row = cur.fetchone()
    original_request_id = int(source_row[0]) if source_row else None

    now = _now()
    cur.execute(
        """
        INSERT INTO absence_request_batches (
            employee_id, request_kind, original_request_id, from_date, to_date, total_days,
            reason, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(employee_id),
            CANCEL_KIND,
            original_request_id,
            normalized_dates[0],
            normalized_dates[-1],
            len(normalized_dates),
            (reason or "").strip(),
            PENDING,
            now,
            now,
        ),
    )
    request_id = int(cur.lastrowid)
    cur.executemany(
        """
        INSERT INTO absence_request_batch_dates (request_id, absence_date, created_at)
        VALUES (?, ?, ?)
        """,
        [(request_id, item, now) for item in normalized_dates],
    )
    conn.commit()
    return get_request_details(conn, request_id)


def _legacy_rows_for_employee(conn: Any, employee_id: int) -> List[Dict[str, Any]]:
    batch_dates = {
        item["absence_date"]
        for item in list_request_dates_for_employee(conn, employee_id)
    }
    cur = conn.cursor()
    rows: List[Dict[str, Any]] = []
    for table_name, date_col in (
        ("employee_absences", "absence_date"),
        ("employee_absence_requests", "absent_date"),
    ):
        try:
            cur.execute(
                f"""
                SELECT id, {date_col} AS absence_date, reason, status, created_at, updated_at
                FROM {table_name}
                WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
                ORDER BY {date_col} DESC, id DESC
                """,
                (str(employee_id),),
            )
            for row in cur.fetchall():
                item = _row_to_dict(row)
                absence_date = str(item.get("absence_date") or "")
                if absence_date and absence_date in batch_dates:
                    continue
                rows.append(
                    {
                        "id": f"legacy-{table_name}-{item.get('id')}",
                        "request_kind": ABSENCE_KIND,
                        "source": table_name,
                        "status": item.get("status") or PENDING,
                        "from_date": absence_date,
                        "to_date": absence_date,
                        "absent_date": absence_date,
                        "dates": [absence_date] if absence_date else [],
                        "total_days": 1,
                        "reason": item.get("reason") or "",
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at"),
                        "can_request_cancel": (item.get("status") == APPROVED),
                    }
                )
        except Exception:
            continue
    return rows


def list_request_dates_for_employee(conn: Any, employee_id: int) -> List[Dict[str, Any]]:
    ensure_absence_flow_tables(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT d.absence_date
        FROM absence_request_batches b
        JOIN absence_request_batch_dates d
          ON d.request_id = b.id
        WHERE CAST(b.employee_id AS TEXT) = CAST(? AS TEXT)
        """,
        (str(employee_id),),
    )
    return [{"absence_date": str(row[0])} for row in cur.fetchall()]


def _batch_to_payload(conn: Any, batch_row: Dict[str, Any], *, employee_name: str = "", employee_mobile: str = "") -> Dict[str, Any]:
    cur = conn.cursor()
    request_id = int(batch_row["id"])
    cur.execute(
        """
        SELECT absence_date
        FROM absence_request_batch_dates
        WHERE request_id = ?
        ORDER BY absence_date ASC
        """,
        (request_id,),
    )
    dates = [str(row[0]) for row in cur.fetchall()]
    payload = {
        "id": request_id,
        "employee_id": int(batch_row["employee_id"]),
        "employee_name": employee_name or batch_row.get("employee_name") or "",
        "employee_mobile": employee_mobile or batch_row.get("employee_mobile") or "",
        "request_kind": batch_row.get("request_kind") or ABSENCE_KIND,
        "status": batch_row.get("status") or PENDING,
        "reason": batch_row.get("reason") or "",
        "admin_reason": batch_row.get("admin_reason") or "",
        "from_date": batch_row.get("from_date"),
        "to_date": batch_row.get("to_date"),
        "absent_date": batch_row.get("from_date"),
        "dates": dates,
        "total_days": int(batch_row.get("total_days") or len(dates) or 1),
        "created_at": batch_row.get("created_at"),
        "updated_at": batch_row.get("updated_at"),
        "reviewed_at": batch_row.get("reviewed_at"),
        "reviewed_by": batch_row.get("reviewed_by"),
        "original_request_id": batch_row.get("original_request_id"),
    }
    payload["can_request_cancel"] = (
        payload["request_kind"] == ABSENCE_KIND
        and payload["status"] == APPROVED
        and any(_parse_iso_date(item) > date.today() for item in dates)
    )
    return payload


def list_employee_requests(conn: Any, employee_id: int) -> List[Dict[str, Any]]:
    ensure_absence_flow_tables(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM absence_request_batches
        WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
        ORDER BY created_at DESC, id DESC
        """,
        (str(employee_id),),
    )
    batches = [_batch_to_payload(conn, _row_to_dict(row)) for row in cur.fetchall()]
    legacy = _legacy_rows_for_employee(conn, employee_id)
    merged = batches + legacy
    merged.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id"))), reverse=True)
    return merged


def list_approved_absence_ranges(conn: Any, *, on_or_after: Optional[str] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    date_filter = ""
    params: List[Any] = []
    if on_or_after:
        normalized = _parse_iso_date(on_or_after, "on_or_after").isoformat()
        date_filter = " AND a.absence_date >= ?"
        params.append(normalized)

    cur.execute(
        f"""
        SELECT
            CAST(a.employee_id AS TEXT) AS employee_id,
            e.name AS employee_name,
            e.mobile AS employee_mobile,
            a.absence_date,
            a.reason,
            a.reviewed_at,
            a.reviewed_by
        FROM employee_absences a
        JOIN employees e
          ON CAST(e.id AS TEXT) = CAST(a.employee_id AS TEXT)
        WHERE a.status = 'approved'
        {date_filter}
        ORDER BY CAST(a.employee_id AS TEXT) ASC, a.absence_date ASC, a.id ASC
        """,
        params,
    )
    rows = [_row_to_dict(row) for row in cur.fetchall()]
    if not rows:
        return []

    grouped: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for row in rows:
        absence_date = _parse_iso_date(row["absence_date"]).isoformat()
        reason = str(row.get("reason") or "").strip()
        if current is None:
            current = {
                "employee_id": int(row["employee_id"]),
                "employee_name": row.get("employee_name") or "",
                "employee_mobile": row.get("employee_mobile") or "",
                "from_date": absence_date,
                "to_date": absence_date,
                "dates": [absence_date],
                "total_days": 1,
                "reason": reason,
                "reviewed_at": row.get("reviewed_at"),
                "reviewed_by": row.get("reviewed_by"),
            }
            continue

        previous_date = _parse_iso_date(current["to_date"])
        is_same_employee = int(row["employee_id"]) == int(current["employee_id"])
        is_contiguous = _parse_iso_date(absence_date) == previous_date + timedelta(days=1)
        same_reason = reason == str(current.get("reason") or "").strip()
        if is_same_employee and is_contiguous and same_reason:
            current["to_date"] = absence_date
            current["dates"].append(absence_date)
            current["total_days"] = int(current["total_days"]) + 1
        else:
            grouped.append(current)
            current = {
                "employee_id": int(row["employee_id"]),
                "employee_name": row.get("employee_name") or "",
                "employee_mobile": row.get("employee_mobile") or "",
                "from_date": absence_date,
                "to_date": absence_date,
                "dates": [absence_date],
                "total_days": 1,
                "reason": reason,
                "reviewed_at": row.get("reviewed_at"),
                "reviewed_by": row.get("reviewed_by"),
            }

    if current is not None:
        grouped.append(current)

    return grouped


def admin_remove_approved_absence(
    conn: Any,
    employee_id: int,
    dates: Sequence[str],
    *,
    reviewed_by: Optional[str] = None,
    reason: str = "",
) -> Dict[str, Any]:
    ensure_absence_flow_tables(conn)
    _load_employee(conn, employee_id)
    normalized_dates = sorted({_parse_iso_date(item).isoformat() for item in dates})
    if not normalized_dates:
        raise AbsenceFlowError("At least one valid date is required")

    cur = conn.cursor()
    approved_dates: List[str] = []
    for item in normalized_dates:
        cur.execute(
            """
            SELECT 1
            FROM employee_absences
            WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
              AND absence_date = ?
              AND status = 'approved'
            LIMIT 1
            """,
            (str(employee_id), item),
        )
        if cur.fetchone():
            approved_dates.append(item)

    if len(approved_dates) != len(normalized_dates):
        missing = sorted(set(normalized_dates) - set(approved_dates))
        raise AbsenceFlowError(
            f"Only approved absence dates can be removed. Missing approved dates: {', '.join(missing)}"
        )

    now = _now()
    cur.execute(
        """
        INSERT INTO absence_request_batches (
            employee_id, request_kind, from_date, to_date, total_days,
            reason, status, admin_reason, reviewed_by, reviewed_at, created_at, updated_at
        )
        VALUES (?, 'cancel', ?, ?, ?, ?, 'approved', ?, ?, ?, ?, ?)
        """,
        (
            str(employee_id),
            approved_dates[0],
            approved_dates[-1],
            len(approved_dates),
            (reason or "").strip() or "Removed by admin",
            "Removed by admin",
            reviewed_by,
            now,
            now,
            now,
        ),
    )
    request_id = int(cur.lastrowid)
    cur.executemany(
        """
        INSERT INTO absence_request_batch_dates (request_id, absence_date, created_at)
        VALUES (?, ?, ?)
        """,
        [(request_id, item, now) for item in approved_dates],
    )
    cur.executemany(
        """
        DELETE FROM employee_absences
        WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
          AND absence_date = ?
          AND status = 'approved'
        """,
        [(str(employee_id), item) for item in approved_dates],
    )
    conn.commit()
    return {
        "request_id": request_id,
        "employee_id": employee_id,
        "request_kind": CANCEL_KIND,
        "status": APPROVED,
        "dates": approved_dates,
    }


def list_admin_requests(conn: Any) -> List[Dict[str, Any]]:
    ensure_absence_flow_tables(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            b.*,
            e.name AS employee_name,
            e.mobile AS employee_mobile
        FROM absence_request_batches b
        JOIN employees e
          ON CAST(e.id AS TEXT) = CAST(b.employee_id AS TEXT)
        ORDER BY
            CASE WHEN b.status = 'pending' THEN 0 ELSE 1 END,
            b.created_at DESC,
            b.id DESC
        """
    )
    items = [
        _batch_to_payload(
            conn,
            _row_to_dict(row),
            employee_name=_row_to_dict(row).get("employee_name") or "",
            employee_mobile=_row_to_dict(row).get("employee_mobile") or "",
        )
        for row in cur.fetchall()
    ]

    items.sort(
        key=lambda item: (
            0 if str(item.get("status") or "").lower() == PENDING else 1,
            str(item.get("created_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=False,
    )
    return items


def get_request_details(conn: Any, request_id: int) -> Dict[str, Any]:
    ensure_absence_flow_tables(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM absence_request_batches
        WHERE id = ?
        LIMIT 1
        """,
        (request_id,),
    )
    row = cur.fetchone()
    if not row:
        raise AbsenceFlowError("Absence request not found")
    return _batch_to_payload(conn, _row_to_dict(row))


def review_request(
    conn: Any,
    request_id: int,
    *,
    decision: str,
    admin_reason: str = "",
    reviewed_by: Optional[str] = None,
) -> ReviewResult:
    ensure_absence_flow_tables(conn)
    decision_value = str(decision or "").strip().lower()
    if decision_value not in ("approve", "reject", APPROVED, REJECTED):
        raise AbsenceFlowError("decision must be approve or reject")
    target_status = APPROVED if decision_value in ("approve", APPROVED) else REJECTED

    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM absence_request_batches
        WHERE id = ?
        LIMIT 1
        """,
        (request_id,),
    )
    batch = cur.fetchone()
    if batch:
        batch_dict = _row_to_dict(batch)
        if str(batch_dict.get("status") or "").lower() != PENDING:
            raise AbsenceFlowError("Only pending requests can be reviewed")

        cur.execute(
            """
            SELECT absence_date
            FROM absence_request_batch_dates
            WHERE request_id = ?
            ORDER BY absence_date ASC
            """,
            (request_id,),
        )
        dates = [str(row[0]) for row in cur.fetchall()]
        now = _now()

        if target_status == APPROVED:
            if batch_dict.get("request_kind") == ABSENCE_KIND:
                for absence_date in dates:
                    cur.execute(
                        """
                        SELECT id
                        FROM employee_absences
                        WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
                          AND absence_date = ?
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (str(batch_dict["employee_id"]), absence_date),
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            """
                            UPDATE employee_absences
                            SET reason = ?, status = 'approved', reviewed_at = ?, reviewed_by = ?,
                                updated_at = ?, requested_at = COALESCE(requested_at, ?)
                            WHERE id = ?
                            """,
                            (
                                batch_dict.get("reason") or "",
                                now,
                                reviewed_by,
                                now,
                                batch_dict.get("created_at") or now,
                                int(existing[0]),
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO employee_absences (
                                employee_id, absence_date, reason, status,
                                requested_at, reviewed_at, reviewed_by, created_at, updated_at
                            )
                            VALUES (?, ?, ?, 'approved', ?, ?, ?, ?, ?)
                            """,
                            (
                                str(batch_dict["employee_id"]),
                                absence_date,
                                batch_dict.get("reason") or "",
                                batch_dict.get("created_at") or now,
                                now,
                                reviewed_by,
                                batch_dict.get("created_at") or now,
                                now,
                            ),
                        )
            else:
                for absence_date in dates:
                    cur.execute(
                        """
                        DELETE FROM employee_absences
                        WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
                          AND absence_date = ?
                          AND status = 'approved'
                        """,
                        (str(batch_dict["employee_id"]), absence_date),
                    )

        cur.execute(
            """
            UPDATE absence_request_batches
            SET status = ?, admin_reason = ?, reviewed_by = ?, reviewed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (target_status, admin_reason.strip(), reviewed_by, now, now, request_id),
        )
        conn.commit()
        return ReviewResult(
            request_id=request_id,
            request_kind=str(batch_dict.get("request_kind") or ABSENCE_KIND),
            status=target_status,
            employee_id=int(batch_dict["employee_id"]),
            dates=dates,
        )

    # Legacy fallback.
    for table_name, date_col in (
        ("employee_absences", "absence_date"),
        ("employee_absence_requests", "absent_date"),
    ):
        try:
            cur.execute(
                f"SELECT employee_id, {date_col} AS absence_date FROM {table_name} WHERE id = ? LIMIT 1",
                (request_id,),
            )
            legacy = cur.fetchone()
            if not legacy:
                continue
            now = _now()
            try:
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET status = ?, reviewed_at = ?, reviewed_by = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (target_status, now, reviewed_by, now, request_id),
                )
            except Exception:
                cur.execute(
                    f"UPDATE {table_name} SET status = ? WHERE id = ?",
                    (target_status, request_id),
                )
            if table_name == "employee_absence_requests" and target_status == APPROVED:
                legacy_dict = _row_to_dict(legacy)
                absence_date = str(legacy_dict["absence_date"])
                cur.execute(
                    """
                    SELECT id
                    FROM employee_absences
                    WHERE CAST(employee_id AS TEXT) = CAST(? AS TEXT)
                      AND absence_date = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (str(legacy_dict["employee_id"]), absence_date),
                )
                existing_absence = cur.fetchone()
                if existing_absence:
                    cur.execute(
                        """
                        UPDATE employee_absences
                        SET reason = ?, status = 'approved', reviewed_at = COALESCE(reviewed_at, ?),
                            reviewed_by = COALESCE(reviewed_by, ?), updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            legacy_dict.get("reason") or "",
                            now,
                            reviewed_by,
                            now,
                            int(existing_absence[0]),
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO employee_absences (
                            employee_id, absence_date, reason, status,
                            requested_at, reviewed_at, reviewed_by, created_at, updated_at
                        )
                        VALUES (?, ?, ?, 'approved', ?, ?, ?, ?, ?)
                        """,
                        (
                            str(legacy_dict["employee_id"]),
                            absence_date,
                            legacy_dict.get("reason") or "",
                            legacy_dict.get("created_at") or now,
                            now,
                            reviewed_by,
                            legacy_dict.get("created_at") or now,
                            now,
                        ),
                    )
            conn.commit()
            legacy_dict = _row_to_dict(legacy)
            return ReviewResult(
                request_id=request_id,
                request_kind=ABSENCE_KIND,
                status=target_status,
                employee_id=int(legacy_dict["employee_id"]),
                dates=[str(legacy_dict["absence_date"])],
            )
        except Exception:
            continue

    raise AbsenceFlowError("Absence request not found")
