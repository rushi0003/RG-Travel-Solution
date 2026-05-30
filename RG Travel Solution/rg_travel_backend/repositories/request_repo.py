# backend/repositories/request_repo.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

# Type alias for row dictionary
RowDict = Dict[str, Any]

def _now() -> str:
    return datetime.utcnow().isoformat()

class RequestRepo:
    def __init__(self, conn: Any):
        self.conn = conn

    def _column_names(self, table_name: str) -> set[str]:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        return {str(r[1]) for r in cur.fetchall()}

    def _should_include_legacy_unscoped_rows(self, admin_id: Optional[str]) -> bool:
        normalized_admin_id = str(admin_id or "").strip()
        if not normalized_admin_id:
            return True

        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admins")
        row = cur.fetchone()
        try:
            admin_count = int(row[0]) if row else 0
        except Exception:
            admin_count = 0
        return admin_count <= 1

    def _list_pending_requests(
        self,
        *,
        table_name: str,
        admin_id: Optional[str] = None,
        selected_columns: str = "*",
    ) -> List[RowDict]:
        cur = self.conn.cursor()
        cols = self._column_names(table_name)
        params: List[Any] = []
        where = ["LOWER(COALESCE(status, 'pending')) = 'pending'"]

        if "admin_id" in cols:
            normalized_admin_id = str(admin_id or "").strip()
            if normalized_admin_id:
                if self._should_include_legacy_unscoped_rows(normalized_admin_id):
                    where.append(
                        "(CAST(COALESCE(admin_id, '') AS TEXT) = CAST(? AS TEXT) OR COALESCE(TRIM(admin_id), '') = '')"
                    )
                else:
                    where.append("CAST(COALESCE(admin_id, '') AS TEXT) = CAST(? AS TEXT)")
                params.append(normalized_admin_id)
            elif not self._should_include_legacy_unscoped_rows(None):
                where.append("COALESCE(TRIM(admin_id), '') = ''")

        cur.execute(
            f"""
            SELECT {selected_columns}
            FROM {table_name}
            WHERE {' AND '.join(where)}
            ORDER BY datetime(COALESCE(created_at, '1970-01-01T00:00:00')) DESC, id DESC
            """,
            tuple(params),
        )
        return [dict(r) for r in cur.fetchall()]

    def _get_request_by_id(
        self,
        *,
        table_name: str,
        req_id: int,
        admin_id: Optional[str] = None,
    ) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cols = self._column_names(table_name)
        params: List[Any] = [req_id]
        where = ["id = ?"]

        if "admin_id" in cols:
            normalized_admin_id = str(admin_id or "").strip()
            if normalized_admin_id:
                if self._should_include_legacy_unscoped_rows(normalized_admin_id):
                    where.append(
                        "(CAST(COALESCE(admin_id, '') AS TEXT) = CAST(? AS TEXT) OR COALESCE(TRIM(admin_id), '') = '')"
                    )
                else:
                    where.append("CAST(COALESCE(admin_id, '') AS TEXT) = CAST(? AS TEXT)")
                params.append(normalized_admin_id)

        cur.execute(
            f"SELECT * FROM {table_name} WHERE {' AND '.join(where)} LIMIT 1",
            tuple(params),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def claim_request_admin(
        self,
        *,
        table_name: str,
        req_id: int,
        admin_id: str,
    ) -> bool:
        cur = self.conn.cursor()
        cols = self._column_names(table_name)
        if "admin_id" not in cols:
            return True

        normalized_admin_id = str(admin_id or "").strip()
        if not normalized_admin_id:
            return False

        if self._should_include_legacy_unscoped_rows(normalized_admin_id):
            cur.execute(
                f"""
                UPDATE {table_name}
                SET admin_id = ?
                WHERE id = ?
                  AND COALESCE(TRIM(admin_id), '') = ''
                """,
                (normalized_admin_id, req_id),
            )
            self.conn.commit()
        return True

    # =========================================================
    # DRIVER REQUESTS
    # =========================================================
    def create_driver_request(
        self,
        name: str,
        mobile: str,
        dl_no: str,
        cab_no: str,
        home_town: str,
        vehicle_type: str = "4",
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        admin_id: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(driver_requests)")
        cols = {str(r[1]) for r in cur.fetchall()}
        if (lat is not None or lng is not None) and not (("lat" in cols) and ("lng" in cols)):
            try:
                if "lat" not in cols:
                    cur.execute("ALTER TABLE driver_requests ADD COLUMN lat REAL")
                if "lng" not in cols:
                    cur.execute("ALTER TABLE driver_requests ADD COLUMN lng REAL")
                self.conn.commit()
                cur.execute("PRAGMA table_info(driver_requests)")
                cols = {str(r[1]) for r in cur.fetchall()}
            except Exception:
                pass
        has_lat_lng = ("lat" in cols) and ("lng" in cols)
        has_admin_id = "admin_id" in cols

        if has_lat_lng:
            if has_admin_id:
                cur.execute(
                    """
                    INSERT INTO driver_requests (name, mobile, dl_no, cab_no, home_town, vehicle_type, lat, lng, admin_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, dl_no, cab_no, home_town, vehicle_type, lat, lng, admin_id, _now())
                )
            else:
                cur.execute(
                    """
                    INSERT INTO driver_requests (name, mobile, dl_no, cab_no, home_town, vehicle_type, lat, lng, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, dl_no, cab_no, home_town, vehicle_type, lat, lng, _now())
                )
        else:
            if has_admin_id:
                cur.execute(
                    """
                    INSERT INTO driver_requests (name, mobile, dl_no, cab_no, home_town, vehicle_type, admin_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, dl_no, cab_no, home_town, vehicle_type, admin_id, _now())
                )
            else:
                cur.execute(
                    """
                    INSERT INTO driver_requests (name, mobile, dl_no, cab_no, home_town, vehicle_type, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, dl_no, cab_no, home_town, vehicle_type, _now())
                )
        self.conn.commit()
        return cur.lastrowid

    def get_driver_request_by_id(self, req_id: int, admin_id: Optional[str] = None) -> Optional[RowDict]:
        return self._get_request_by_id(
            table_name="driver_requests",
            req_id=req_id,
            admin_id=admin_id,
        )

    def list_pending_driver_requests(
        self,
        admin_id: Optional[str] = None,
        selected_columns: str = "*",
    ) -> List[RowDict]:
        return self._list_pending_requests(
            table_name="driver_requests",
            admin_id=admin_id,
            selected_columns=selected_columns,
        )

    def update_driver_request_status(self, req_id: int, status: str, note: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE driver_requests
            SET status = ?, review_note = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (status, note, _now(), req_id)
        )
        self.conn.commit()

    # =========================================================
    # EMPLOYEE REQUESTS
    # =========================================================
    def create_employee_request(
        self,
        name: str,
        mobile: str,
        login_time: str,
        logout_time: str,
        home_address: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        admin_id: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(employee_requests)")
        cols = {str(r[1]) for r in cur.fetchall()}
        has_lat_lng = ("lat" in cols) and ("lng" in cols)
        has_admin_id = "admin_id" in cols

        if has_lat_lng:
            if has_admin_id:
                cur.execute(
                    """
                    INSERT INTO employee_requests (name, mobile, login_time, logout_time, home_address, lat, lng, admin_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, login_time, logout_time, home_address, lat, lng, admin_id, _now())
                )
            else:
                cur.execute(
                    """
                    INSERT INTO employee_requests (name, mobile, login_time, logout_time, home_address, lat, lng, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, login_time, logout_time, home_address, lat, lng, _now())
                )
        else:
            if has_admin_id:
                cur.execute(
                    """
                    INSERT INTO employee_requests (name, mobile, login_time, logout_time, home_address, admin_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, login_time, logout_time, home_address, admin_id, _now())
                )
            else:
                cur.execute(
                    """
                    INSERT INTO employee_requests (name, mobile, login_time, logout_time, home_address, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (name, mobile, login_time, logout_time, home_address, _now())
                )
        self.conn.commit()
        return cur.lastrowid

    def get_employee_request_by_id(self, req_id: int, admin_id: Optional[str] = None) -> Optional[RowDict]:
        return self._get_request_by_id(
            table_name="employee_requests",
            req_id=req_id,
            admin_id=admin_id,
        )

    def list_pending_employee_requests(
        self,
        admin_id: Optional[str] = None,
        selected_columns: str = "*",
    ) -> List[RowDict]:
        return self._list_pending_requests(
            table_name="employee_requests",
            admin_id=admin_id,
            selected_columns=selected_columns,
        )

    def update_employee_request_status(self, req_id: int, status: str, note: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE employee_requests
            SET status = ?, review_note = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (status, note, _now(), req_id)
        )
        self.conn.commit()
