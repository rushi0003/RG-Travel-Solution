import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

try:
    from rg_travel_backend.routes.driver_routes import driver_bp
    from rg_travel_backend.routes.employee_routes import employee_bp
    from rg_travel_backend.routes.trip_creation_v2_routes import trip_v2_bp
    DRIVER_DB_PATCH = "rg_travel_backend.routes.driver_routes.get_db"
    EMPLOYEE_DB_PATCH = "rg_travel_backend.routes.employee_routes.get_db"
    TRIP_DB_PATCH = "rg_travel_backend.routes.trip_creation_v2_routes.get_db"
except ModuleNotFoundError:
    from routes.driver_routes import driver_bp
    from routes.employee_routes import employee_bp
    from routes.trip_creation_v2_routes import trip_v2_bp
    DRIVER_DB_PATCH = "routes.driver_routes.get_db"
    EMPLOYEE_DB_PATCH = "routes.employee_routes.get_db"
    TRIP_DB_PATCH = "routes.trip_creation_v2_routes.get_db"


class TestTripHistoryStep1(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="trip_history_step1_", suffix=".db")
        os.close(fd)
        self._prepare_db()
        self._seed_data()

        self.app = Flask(__name__)
        self.app.register_blueprint(driver_bp)
        self.app.register_blueprint(employee_bp)
        self.app.register_blueprint(trip_v2_bp)
        self.client = self.app.test_client()

        self.patches = [
            patch(DRIVER_DB_PATCH, side_effect=self._new_conn),
            patch(EMPLOYEE_DB_PATCH, side_effect=self._new_conn),
            patch(TRIP_DB_PATCH, side_effect=self._new_conn),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _new_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _prepare_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                route_no TEXT,
                trip_day TEXT,
                operation TEXT,
                trip_type TEXT,
                schedule_time TEXT,
                status TEXT,
                driver_id TEXT,
                vehicle_no TEXT,
                vehicle_type TEXT,
                total_km REAL,
                start_time TEXT,
                end_time TEXT,
                cancel_reason TEXT,
                cancelled_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                office_lat REAL,
                office_lng REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_employees (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER,
                employee_id TEXT,
                sequence_no INTEGER,
                is_no_show INTEGER DEFAULT 0,
                no_show_reason TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE drivers (
                id INTEGER PRIMARY KEY,
                driver_id TEXT,
                name TEXT,
                mobile TEXT,
                vehicle_no TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                mobile TEXT,
                home_address TEXT,
                pickup_address TEXT,
                pickup_lat REAL,
                pickup_lng REAL,
                drop_lat REAL,
                drop_lng REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_otps (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER,
                otp_type TEXT,
                is_used INTEGER,
                expires_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE swap_requests (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER,
                old_driver_id TEXT,
                new_driver_id TEXT,
                new_driver_name TEXT,
                new_driver_mobile TEXT,
                new_cab_no TEXT,
                status TEXT,
                reviewed_at TEXT,
                updated_at TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _seed_data(self):
        conn = self._new_conn()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO drivers (id, driver_id, name, mobile, vehicle_no)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "1", "Original Driver", "9000000001", "MH12AA1111"),
                (2, "2", "Replacement Driver", "9000000002", "MH12BB2222"),
                (3, "3", "Cancelled Driver", "9000000003", "MH12CC3333"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO employees (id, name, mobile)
            VALUES (?, ?, ?)
            """,
            [
                (11, "Employee One", "8000000001"),
                (12, "Employee Two", "8000000002"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO trips (
                id, route_no, trip_day, operation, trip_type, schedule_time, status,
                driver_id, vehicle_no, vehicle_type, total_km, start_time, end_time, cancel_reason,
                cancelled_at, created_at, updated_at, office_lat, office_lng
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    101, "R101", "20260306", "pickup", "pickup", "09:00", "completed",
                    "2", "MH12BB2222", "6", 24.5, "2026-03-06T09:05:00", "2026-03-06T10:00:00", None,
                    None, "2026-03-06T08:00:00", "2026-03-06T10:00:00", 18.52, 73.85,
                ),
                (
                    102, "R102", "20260305", "drop", "drop", "18:00", "cancelled",
                    "3", "MH12CC3333", "4", 19.0, None, None, "vehicle breakdown",
                    "2026-03-05T17:40:00", "2026-03-05T16:00:00", "2026-03-05T17:40:00", 18.53, 73.86,
                ),
            ],
        )
        cur.executemany(
            """
            INSERT INTO trip_employees (id, trip_id, employee_id, sequence_no, is_no_show, no_show_reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 101, "11", 1, 0, ""),
                (2, 101, "12", 2, 1, "Employee absent at pickup"),
                (3, 102, "11", 1, 0, ""),
            ],
        )
        cur.execute(
            """
            INSERT INTO swap_requests (
                id, trip_id, old_driver_id, new_driver_id, new_driver_name, new_driver_mobile,
                new_cab_no, status, reviewed_at, updated_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                501, 101, "1", "2", "Replacement Driver", "9000000002",
                "MH12BB2222", "approved", "2026-03-06T08:55:00", "2026-03-06T08:55:00", "2026-03-06T08:50:00",
            ),
        )
        conn.commit()
        conn.close()

    def test_admin_history_returns_enriched_lifecycle_fields(self):
        resp = self.client.get("/api/v2/trips/history")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertTrue(body.get("success"))
        trips = (body.get("data") or {}).get("trips") or []
        self.assertEqual(len(trips), 2)

        completed = next(t for t in trips if int(t["id"]) == 101)
        cancelled = next(t for t in trips if int(t["id"]) == 102)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["total_km"], 24.5)
        self.assertTrue(completed["show_total_km"])
        self.assertEqual(completed["no_show_count"], 1)
        self.assertTrue(completed["has_emergency_swap"])
        self.assertEqual(completed["original_driver"]["name"], "Original Driver")
        self.assertEqual(completed["current_driver"]["name"], "Replacement Driver")
        self.assertEqual(completed["original_vehicle_no"], "MH12AA1111")
        self.assertEqual(completed["current_vehicle_no"], "MH12BB2222")

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertIsNone(cancelled["total_km"])
        self.assertFalse(cancelled["show_total_km"])
        self.assertEqual(cancelled["cancel_reason"], "vehicle breakdown")

    def test_admin_history_supports_driver_and_employee_filters(self):
        resp = self.client.get("/api/v2/trips/history?driver_id=2")
        trips = ((resp.get_json() or {}).get("data") or {}).get("trips") or []
        self.assertEqual(len(trips), 1)
        self.assertEqual(int(trips[0]["id"]), 101)

        resp = self.client.get("/api/v2/trips/history?employee_id=12")
        trips = ((resp.get_json() or {}).get("data") or {}).get("trips") or []
        self.assertEqual(len(trips), 1)
        self.assertEqual(int(trips[0]["id"]), 101)

    def test_driver_history_uses_shared_contract(self):
        resp = self.client.get("/api/driver/2/trip-history")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertTrue(body.get("success"))
        trips = body.get("data") or []
        self.assertEqual(len(trips), 1)
        self.assertEqual(int(trips[0]["id"]), 101)
        self.assertEqual(trips[0]["current_driver"]["name"], "Replacement Driver")

    def test_employee_history_includes_member_status(self):
        resp = self.client.get("/api/employee/12/trip-history")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertTrue(body.get("success"))
        trips = body.get("data") or []
        self.assertEqual(len(trips), 1)
        self.assertEqual(int(trips[0]["id"]), 101)
        self.assertEqual(trips[0]["member_status"], "no_show")

    def test_admin_history_search_supports_employee_no_show_and_swap_terms(self):
        checks = {
            "Employee Two": 101,
            "no-show": 101,
            "swap": 101,
            "MH12AA1111": 101,
            "vehicle breakdown": 102,
        }
        for query, trip_id in checks.items():
            resp = self.client.get(f"/api/v2/trips/history?search={query}")
            self.assertEqual(resp.status_code, 200)
            trips = ((resp.get_json() or {}).get("data") or {}).get("trips") or []
            self.assertTrue(any(int(t["id"]) == trip_id for t in trips), query)

    def test_admin_history_sort_by_km_desc_prioritizes_completed_distance(self):
        resp = self.client.get("/api/v2/trips/history?sort=km_desc")
        self.assertEqual(resp.status_code, 200)
        trips = ((resp.get_json() or {}).get("data") or {}).get("trips") or []
        self.assertEqual(int(trips[0]["id"]), 101)

    def test_admin_history_pagination_metadata(self):
        resp = self.client.get("/api/v2/trips/history?limit=1&offset=1")
        self.assertEqual(resp.status_code, 200)
        data = (resp.get_json() or {}).get("data") or {}
        self.assertEqual(data.get("total_count"), 2)
        self.assertEqual(data.get("limit"), 1)
        self.assertEqual(data.get("offset"), 1)
        trips = data.get("trips") or []
        self.assertEqual(len(trips), 1)
        self.assertEqual(int(trips[0]["id"]), 102)

    def test_trip_detail_payload_includes_swap_and_no_show_context(self):
        resp = self.client.get("/api/v2/trips/101")
        self.assertEqual(resp.status_code, 200)
        data = (resp.get_json() or {}).get("data") or {}
        self.assertEqual(data.get("trip_id"), 101)
        self.assertTrue(data.get("has_emergency_swap"))
        self.assertEqual((data.get("original_driver") or {}).get("name"), "Original Driver")
        self.assertEqual((data.get("current_driver") or {}).get("name"), "Replacement Driver")
        self.assertEqual(data.get("no_show_count"), 1)
        self.assertEqual(len(data.get("no_show_members") or []), 1)
        self.assertEqual(data.get("status"), "completed")
        self.assertTrue(data.get("show_total_km"))
        self.assertEqual(data.get("total_km"), 24.5)
        employees = data.get("employees") or []
        no_show_emp = next(emp for emp in employees if emp.get("no_show") is True)
        self.assertEqual(no_show_emp.get("no_show_reason"), "Employee absent at pickup")

    def test_trip_history_export_returns_csv(self):
        resp = self.client.get("/api/v2/trips/history/export?search=swap")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "text/csv")
        body = resp.get_data(as_text=True)
        self.assertIn("route_no", body)
        self.assertIn("R101", body)
        self.assertIn("Original Driver", body)
        self.assertIn("Replacement Driver", body)


if __name__ == "__main__":
    unittest.main()
