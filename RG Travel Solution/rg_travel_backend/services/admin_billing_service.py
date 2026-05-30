from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def _normalize_text(value: Any) -> str:
    return str(value or '').strip()


def _normalize_day(value: Any) -> str:
    return _normalize_text(value).replace('-', '')


def _day_to_iso(day: str) -> str:
    if len(day) == 8 and day.isdigit():
        return f'{day[:4]}-{day[4:6]}-{day[6:]}'
    return day


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


def _table_columns(cur, table_name: str) -> set[str]:
    cur.execute(f'PRAGMA table_info({table_name})')
    return {str(row[1]) for row in (cur.fetchall() or [])}


def _safe_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value or '{}')
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _trip_vehicle_expr(cur) -> str:
    cur.execute('PRAGMA table_info(trips)')
    trip_cols = {str(row[1]) for row in cur.fetchall()}
    if 'vehicle_no' in trip_cols:
        return "COALESCE(t.vehicle_no, d.vehicle_no, '')"
    return "COALESCE(d.vehicle_no, '')"


def _billing_filters(
    *,
    vehicle_expr: str,
    driver_id: Optional[str] = None,
    vehicle_no: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    trip_id: Optional[int] = None,
    search: Optional[str] = None,
    include_cancelled: bool = False,
) -> tuple[list[str], list[Any]]:
    where: List[str] = []
    params: List[Any] = []

    if include_cancelled:
        where.append("LOWER(COALESCE(t.status, '')) = 'cancelled'")
    else:
        where.append("LOWER(COALESCE(t.status, '')) = 'completed'")

    normalized_driver_id = _normalize_text(driver_id)
    if normalized_driver_id:
        where.append("CAST(t.driver_id AS TEXT) = CAST(? AS TEXT)")
        params.append(normalized_driver_id)

    normalized_vehicle = _normalize_text(vehicle_no).lower()
    if normalized_vehicle:
        where.append(f"LOWER({vehicle_expr}) = ?")
        params.append(normalized_vehicle)

    normalized_from = _normalize_day(from_date)
    if normalized_from:
        where.append("REPLACE(COALESCE(t.trip_day, ''), '-', '') >= ?")
        params.append(normalized_from)

    normalized_to = _normalize_day(to_date)
    if normalized_to:
        where.append("REPLACE(COALESCE(t.trip_day, ''), '-', '') <= ?")
        params.append(normalized_to)

    if trip_id is not None:
        where.append('t.id = ?')
        params.append(int(trip_id))

    normalized_search = _normalize_text(search).lower()
    if normalized_search:
        where.append(
            """
            (
                LOWER(COALESCE(t.route_no, '')) LIKE ?
                OR LOWER(COALESCE(d.name, '')) LIKE ?
                OR LOWER({vehicle_expr}) LIKE ?
                OR LOWER(COALESCE(t.trip_day, '')) LIKE ?
            )
            """
        )
        like_value = f'%{normalized_search}%'
        params.extend([like_value, like_value, like_value, like_value])

    return where, params


def list_billable_vehicle_assignments(
    conn,
    *,
    admin_id: str,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    normalized_search = f"%{_normalize_text(search).lower()}%"

    if _table_exists(cur, 'driver_admin_assignments'):
        cur.execute(
            """
            SELECT
                d.id AS driver_id,
                d.name AS driver_name,
                d.mobile AS driver_mobile,
                d.vehicle_no,
                d.vehicle_type,
                COUNT(DISTINCT CASE
                    WHEN LOWER(COALESCE(t.status, '')) = 'completed' THEN t.id
                    ELSE NULL
                END) AS completed_trip_count,
                MAX(REPLACE(COALESCE(t.trip_day, ''), '-', '')) AS latest_trip_day
            FROM drivers d
            INNER JOIN driver_admin_assignments daa
              ON daa.driver_id = d.id
             AND daa.admin_id = ?
             AND daa.is_active = 1
            LEFT JOIN trips t
              ON CAST(t.driver_id AS TEXT) = CAST(d.id AS TEXT)
             AND CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)
            WHERE (
                ? = '%%'
                OR LOWER(COALESCE(d.name, '')) LIKE ?
                OR LOWER(COALESCE(d.vehicle_no, '')) LIKE ?
                OR LOWER(COALESCE(d.mobile, '')) LIKE ?
            )
            GROUP BY d.id, d.name, d.mobile, d.vehicle_no, d.vehicle_type
            ORDER BY LOWER(COALESCE(d.vehicle_no, '')) ASC, LOWER(COALESCE(d.name, '')) ASC
            """,
            (
                admin_id,
                admin_id,
                normalized_search,
                normalized_search,
                normalized_search,
                normalized_search,
            ),
        )
    else:
        cur.execute(
            """
            SELECT
                d.id AS driver_id,
                d.name AS driver_name,
                d.mobile AS driver_mobile,
                d.vehicle_no,
                d.vehicle_type,
                COUNT(DISTINCT CASE
                    WHEN LOWER(COALESCE(t.status, '')) = 'completed' THEN t.id
                    ELSE NULL
                END) AS completed_trip_count,
                MAX(REPLACE(COALESCE(t.trip_day, ''), '-', '')) AS latest_trip_day
            FROM drivers d
            LEFT JOIN trips t
              ON CAST(t.driver_id AS TEXT) = CAST(d.id AS TEXT)
             AND CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)
            WHERE (
                ? = '%%'
                OR LOWER(COALESCE(d.name, '')) LIKE ?
                OR LOWER(COALESCE(d.vehicle_no, '')) LIKE ?
                OR LOWER(COALESCE(d.mobile, '')) LIKE ?
            )
            GROUP BY d.id, d.name, d.mobile, d.vehicle_no, d.vehicle_type
            HAVING COUNT(DISTINCT t.id) > 0
            ORDER BY LOWER(COALESCE(d.vehicle_no, '')) ASC, LOWER(COALESCE(d.name, '')) ASC
            """,
            (
                admin_id,
                normalized_search,
                normalized_search,
                normalized_search,
                normalized_search,
            ),
        )

    rows = cur.fetchall() or []
    results: List[Dict[str, Any]] = []
    for row in rows:
        latest_trip_day = _normalize_text(row['latest_trip_day']) if 'latest_trip_day' in row.keys() else ''
        results.append(
            {
                'driver_id': _normalize_text(row['driver_id']),
                'driver_name': _normalize_text(row['driver_name']),
                'driver_mobile': _normalize_text(row['driver_mobile']),
                'vehicle_no': _normalize_text(row['vehicle_no']),
                'vehicle_type': _normalize_text(row['vehicle_type']),
                'completed_trip_count': int(row['completed_trip_count'] or 0),
                'latest_trip_date': _day_to_iso(latest_trip_day) if latest_trip_day else '',
            }
        )
    return results


def list_billable_trips(
    conn,
    *,
    admin_id: str,
    driver_id: Optional[str] = None,
    vehicle_no: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    trip_id: Optional[int] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    cur = conn.cursor()
    vehicle_expr = _trip_vehicle_expr(cur)
    where, params = _billing_filters(
        vehicle_expr=vehicle_expr,
        driver_id=driver_id,
        vehicle_no=vehicle_no,
        from_date=from_date,
        to_date=to_date,
        trip_id=trip_id,
        search=search,
        include_cancelled=False,
    )
    where.insert(0, "CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)")
    params.insert(0, admin_id)

    query = f"""
        FROM trips t
        LEFT JOIN drivers d
          ON CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)
        WHERE {' AND '.join(where)}
    """

    cur.execute(
        f"""
        SELECT
            t.id AS trip_id,
            t.route_no,
            REPLACE(COALESCE(t.trip_day, ''), '-', '') AS trip_day,
            t.schedule_time,
            LOWER(COALESCE(t.status, '')) AS status,
            t.driver_id,
            d.name AS driver_name,
            d.mobile AS driver_mobile,
            {vehicle_expr} AS vehicle_no,
            t.vehicle_type,
            COALESCE(t.total_km, 0) AS total_km,
            t.start_time,
            t.end_time,
            t.created_at,
            (
                SELECT COUNT(*)
                FROM trip_employees te
                WHERE te.trip_id = t.id
            ) AS employee_count,
            (
                SELECT COUNT(*)
                FROM trip_employees te
                WHERE te.trip_id = t.id
                  AND COALESCE(te.is_no_show, 0) = 1
            ) AS no_show_count
        {query}
        ORDER BY REPLACE(COALESCE(t.trip_day, ''), '-', '') DESC,
                 COALESCE(t.schedule_time, '') DESC,
                 t.id DESC
        """,
        tuple(params),
    )
    rows = cur.fetchall() or []

    trips: List[Dict[str, Any]] = []
    total_km = 0.0
    for row in rows:
        trip_day = _normalize_text(row['trip_day']) if 'trip_day' in row.keys() else ''
        trip_km = float(row['total_km'] or 0)
        total_km += trip_km
        trips.append(
            {
                'trip_id': int(row['trip_id'] or 0),
                'route_no': _normalize_text(row['route_no']),
                'trip_date': _day_to_iso(trip_day) if trip_day else '',
                'trip_day': trip_day,
                'schedule_time': _normalize_text(row['schedule_time']),
                'status': _normalize_text(row['status']).lower(),
                'driver_id': _normalize_text(row['driver_id']),
                'driver_name': _normalize_text(row['driver_name']),
                'driver_mobile': _normalize_text(row['driver_mobile']),
                'vehicle_no': _normalize_text(row['vehicle_no']),
                'vehicle_type': _normalize_text(row['vehicle_type']),
                'total_km': round(trip_km, 2),
                'employee_count': int(row['employee_count'] or 0),
                'no_show_count': int(row['no_show_count'] or 0),
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'created_at': row['created_at'],
            }
        )

    cancelled_where, cancelled_params = _billing_filters(
        vehicle_expr=vehicle_expr,
        driver_id=driver_id,
        vehicle_no=vehicle_no,
        from_date=from_date,
        to_date=to_date,
        trip_id=trip_id,
        search=search,
        include_cancelled=True,
    )
    cancelled_where.insert(0, "CAST(COALESCE(t.admin_id, '') AS TEXT) = CAST(? AS TEXT)")
    cancelled_params.insert(0, admin_id)
    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM trips t
        LEFT JOIN drivers d
          ON CAST(d.id AS TEXT) = CAST(t.driver_id AS TEXT)
        WHERE {' AND '.join(cancelled_where)}
        """,
        tuple(cancelled_params),
    )
    excluded_cancelled_count = int((cur.fetchone() or [0])[0] or 0)

    return {
        'trips': trips,
        'summary': {
            'total_trips': len(trips),
            'total_km': round(total_km, 2),
            'excluded_cancelled_trips': excluded_cancelled_count,
            'driver_id': _normalize_text(driver_id),
            'vehicle_no': _normalize_text(vehicle_no),
            'from_date': _day_to_iso(_normalize_day(from_date)) if _normalize_day(from_date) else '',
            'to_date': _day_to_iso(_normalize_day(to_date)) if _normalize_day(to_date) else '',
            'selected_trip_id': int(trip_id) if trip_id is not None else None,
        },
    }


def create_billing_record(
    conn,
    *,
    admin_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    assignment = payload.get('assignment') if isinstance(payload.get('assignment'), dict) else {}
    calculation = payload.get('calculation') if isinstance(payload.get('calculation'), dict) else {}
    pdf_meta = payload.get('pdf') if isinstance(payload.get('pdf'), dict) else {}
    invoice_meta = payload.get('invoice_meta') if isinstance(payload.get('invoice_meta'), dict) else {}
    trips_raw = payload.get('trips') if isinstance(payload.get('trips'), list) else []

    driver_id = _normalize_text(assignment.get('driver_id'))
    vehicle_no = _normalize_text(assignment.get('vehicle_no'))
    if not driver_id:
        raise ValueError('driver_id is required.')
    if not vehicle_no:
        raise ValueError('vehicle_no is required.')

    trip_ids: List[int] = []
    for item in trips_raw:
        if not isinstance(item, dict):
            continue
        try:
            trip_ids.append(int(item.get('trip_id') or item.get('id')))
        except Exception:
            continue

    now_iso = datetime.utcnow().isoformat()
    cur = conn.cursor()
    record_cols = _table_columns(cur, 'billing_records')
    has_invoice_meta = 'invoice_meta_json' in record_cols
    insert_cols = [
        'admin_id',
        'driver_id',
        'driver_name',
        'vehicle_no',
        'vehicle_type',
        'billing_mode',
        'from_date',
        'to_date',
        'selected_trip_id',
        'trip_ids_json',
        'total_trips',
        'excluded_cancelled_trips',
        'total_km',
        'per_km_amount',
        'advance_paid',
        'gst_percent',
        'subtotal',
        'gst_amount',
        'grand_total',
        'payable_amount',
        'pdf_file_name',
        'pdf_saved_path',
        'created_at',
        'updated_at',
    ]
    insert_values: List[Any] = [
        admin_id,
        driver_id,
        _normalize_text(assignment.get('driver_name')),
        vehicle_no,
        _normalize_text(assignment.get('vehicle_type')),
        _normalize_text(payload.get('billing_mode')) or 'dateRange',
        _normalize_text(payload.get('from_date')),
        _normalize_text(payload.get('to_date')),
        payload.get('selected_trip_id'),
        json.dumps(trip_ids),
        int(payload.get('total_trips') or 0),
        int(payload.get('excluded_cancelled_trips') or 0),
        float(payload.get('total_km') or 0),
        float(payload.get('per_km_amount') or 0),
        float(payload.get('advance_paid') or 0),
        float(payload.get('gst_percent') or 0),
        float(calculation.get('subtotal') or 0),
        float(calculation.get('gst_amount') or 0),
        float(calculation.get('grand_total') or 0),
        float(calculation.get('payable_amount') or 0),
        _normalize_text(pdf_meta.get('file_name')),
        _normalize_text(pdf_meta.get('saved_path')),
        now_iso,
        now_iso,
    ]
    if has_invoice_meta:
        insert_cols.append('invoice_meta_json')
        insert_values.append(json.dumps(invoice_meta))

    cur.execute(
        f"""
        INSERT INTO billing_records ({', '.join(insert_cols)})
        VALUES ({', '.join(['?'] * len(insert_cols))})
        """,
        tuple(insert_values),
    )
    conn.commit()
    return get_billing_record(
        conn,
        admin_id=admin_id,
        record_id=int(cur.lastrowid or 0),
    ) or {}


def get_billing_record(
    conn,
    *,
    admin_id: str,
    record_id: int,
) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM billing_records
        WHERE id = ?
          AND CAST(admin_id AS TEXT) = CAST(? AS TEXT)
        LIMIT 1
        """,
        (int(record_id), admin_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    return _serialize_billing_record(row)


def list_billing_records(
    conn,
    *,
    admin_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    safe_limit = max(1, min(int(limit), 200))
    cur.execute(
        """
        SELECT *
        FROM billing_records
        WHERE CAST(admin_id AS TEXT) = CAST(? AS TEXT)
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
        """,
        (admin_id, safe_limit),
    )
    return [_serialize_billing_record(row) for row in (cur.fetchall() or [])]


def save_billing_settings(
    conn,
    *,
    admin_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    now_iso = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO billing_settings (
            admin_id,
            service_type,
            rg_gst_no,
            bank_name,
            account_number,
            ifsc_code,
            upi_id,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(admin_id) DO UPDATE SET
            service_type = excluded.service_type,
            rg_gst_no = excluded.rg_gst_no,
            bank_name = excluded.bank_name,
            account_number = excluded.account_number,
            ifsc_code = excluded.ifsc_code,
            upi_id = excluded.upi_id,
            updated_at = excluded.updated_at
        """,
        (
            admin_id,
            _normalize_text(payload.get('service_type')),
            _normalize_text(payload.get('rg_gst_no')),
            _normalize_text(payload.get('bank_name')),
            _normalize_text(payload.get('account_number')),
            _normalize_text(payload.get('ifsc_code')),
            _normalize_text(payload.get('upi_id')),
            now_iso,
        ),
    )
    conn.commit()
    return get_billing_prefill(conn, admin_id=admin_id)


def get_billing_prefill(
    conn,
    *,
    admin_id: str,
) -> Dict[str, Any]:
    cur = conn.cursor()
    profile: Dict[str, Any] = {}
    settings: Dict[str, Any] = {}
    last_invoice_meta: Dict[str, Any] = {}

    if _table_exists(cur, 'admins'):
        admin_cols = _table_columns(cur, 'admins')
        select_cols = [
            'id',
            'name',
            'email',
            'mobile',
            'office_name',
            'office_location',
            'office_address',
        ]
        safe_cols = [col for col in select_cols if col in admin_cols]
        if safe_cols:
            cur.execute(
                f"SELECT {', '.join(safe_cols)} FROM admins WHERE CAST(id AS TEXT) = CAST(? AS TEXT) LIMIT 1",
                (admin_id,),
            )
            row = cur.fetchone()
            if row:
                profile = {col: _normalize_text(row[col]) for col in safe_cols}

    if _table_exists(cur, 'billing_settings'):
        cur.execute(
            """
            SELECT *
            FROM billing_settings
            WHERE CAST(admin_id AS TEXT) = CAST(? AS TEXT)
            LIMIT 1
            """,
            (admin_id,),
        )
        row = cur.fetchone()
        if row:
            settings = {
                'service_type': _normalize_text(row['service_type']),
                'rg_gst_no': _normalize_text(row['rg_gst_no']),
                'bank_name': _normalize_text(row['bank_name']),
                'account_number': _normalize_text(row['account_number']),
                'ifsc_code': _normalize_text(row['ifsc_code']),
                'upi_id': _normalize_text(row['upi_id']),
            }

    if _table_exists(cur, 'billing_records'):
        record_cols = _table_columns(cur, 'billing_records')
        if 'invoice_meta_json' in record_cols:
            cur.execute(
                """
                SELECT invoice_meta_json
                FROM billing_records
                WHERE CAST(admin_id AS TEXT) = CAST(? AS TEXT)
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1
                """,
                (admin_id,),
            )
            row = cur.fetchone()
            if row:
                last_invoice_meta = _safe_json_dict(row['invoice_meta_json'])

    merged = dict(last_invoice_meta)
    for key, value in settings.items():
        if _normalize_text(value):
            merged[key] = value

    return {
        'admin_profile': profile,
        'billing_settings': settings,
        'last_invoice_meta': last_invoice_meta,
        'prefill': {
            'company_name': _normalize_text(
                merged.get('company_name')
                or profile.get('office_name')
                or profile.get('name')
            ),
            'company_address': _normalize_text(
                merged.get('company_address')
                or profile.get('office_address')
                or profile.get('office_location')
            ),
            'company_email': _normalize_text(
                merged.get('company_email')
                or profile.get('email')
            ),
            'contact_person': _normalize_text(merged.get('contact_person')),
            'client_gst_no': _normalize_text(merged.get('client_gst_no')),
            'service_type': _normalize_text(
                merged.get('service_type') or settings.get('service_type')
            ),
            'office_address': _normalize_text(
                merged.get('office_address')
                or profile.get('office_address')
                or profile.get('office_location')
            ),
            'rg_gst_no': _normalize_text(
                merged.get('rg_gst_no') or settings.get('rg_gst_no')
            ),
            'total_employees': _normalize_text(merged.get('total_employees')),
            'notes': _normalize_text(merged.get('notes')),
            'bank_name': _normalize_text(
                merged.get('bank_name') or settings.get('bank_name')
            ),
            'account_number': _normalize_text(
                merged.get('account_number') or settings.get('account_number')
            ),
            'ifsc_code': _normalize_text(
                merged.get('ifsc_code') or settings.get('ifsc_code')
            ),
            'upi_id': _normalize_text(
                merged.get('upi_id') or settings.get('upi_id')
            ),
        },
    }


def _serialize_billing_record(row: Any) -> Dict[str, Any]:
    trip_ids_raw = row['trip_ids_json'] if 'trip_ids_json' in row.keys() else '[]'
    try:
        trip_ids = json.loads(trip_ids_raw or '[]')
    except Exception:
        trip_ids = []
    invoice_meta = _safe_json_dict(row['invoice_meta_json']) if 'invoice_meta_json' in row.keys() else {}

    return {
        'id': int(row['id'] or 0),
        'admin_id': _normalize_text(row['admin_id']),
        'driver_id': _normalize_text(row['driver_id']),
        'driver_name': _normalize_text(row['driver_name']),
        'vehicle_no': _normalize_text(row['vehicle_no']),
        'vehicle_type': _normalize_text(row['vehicle_type']),
        'billing_mode': _normalize_text(row['billing_mode']),
        'from_date': _normalize_text(row['from_date']),
        'to_date': _normalize_text(row['to_date']),
        'selected_trip_id': row['selected_trip_id'],
        'trip_ids': trip_ids if isinstance(trip_ids, list) else [],
        'total_trips': int(row['total_trips'] or 0),
        'excluded_cancelled_trips': int(row['excluded_cancelled_trips'] or 0),
        'total_km': float(row['total_km'] or 0),
        'per_km_amount': float(row['per_km_amount'] or 0),
        'advance_paid': float(row['advance_paid'] or 0),
        'gst_percent': float(row['gst_percent'] or 0),
        'subtotal': float(row['subtotal'] or 0),
        'gst_amount': float(row['gst_amount'] or 0),
        'grand_total': float(row['grand_total'] or 0),
        'payable_amount': float(row['payable_amount'] or 0),
        'pdf_file_name': _normalize_text(row['pdf_file_name']),
        'pdf_saved_path': _normalize_text(row['pdf_saved_path']),
        'invoice_meta': invoice_meta,
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }
