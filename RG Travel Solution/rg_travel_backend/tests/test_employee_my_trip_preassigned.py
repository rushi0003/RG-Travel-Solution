import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from flask import Flask

from rg_travel_backend.routes.employee_routes import employee_bp


class TestEmployeeMyTripPreassigned(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="employee_my_trip_", suffix=".db")
        os.close(fd)
        self._prepare_db()

        self.app = Flask(__name__)
        self.app.register_blueprint(employee_bp)
        self.client = self.app.test_client()

        self.db_patcher = patch(
            "rg_travel_backend.routes.employee_routes.get_db",
            side_effect=self._new_conn,
        )
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
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
                trip_type TEXT,
                trip_day TEXT,
                schedule_time TEXT,
                status TEXT,
                driver_id TEXT,
                vehicle_type TEXT,
                total_km REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_employees (
                trip_id INTEGER,
                employee_id INTEGER,
                sequence_no INTEGER,
                is_no_show INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE drivers (
                id INTEGER PRIMARY KEY,
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
                home_address TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE admins (
                id INTEGER PRIMARY KEY,
                office_address TEXT,
                office_lat REAL,
                office_lng REAL,
                created_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def test_returns_upcoming_preassigned_trip_when_today_has_none(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)

        conn = self._new_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO drivers (id, name, mobile, vehicle_no)
            VALUES (1, 'Driver One', '9999999999', 'MH12AB1234')
            """
        )
        cur.execute(
            """
            INSERT INTO trips (id, route_no, trip_type, trip_day, schedule_time, status, driver_id, vehicle_type, total_km)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (10, "R0010", "pickup", tomorrow.strftime("%Y%m%d"), "09:00", "assigned", "1", "cab", 12.0),
        )
        cur.execute(
            """
            INSERT INTO employees (id, name, mobile, home_address)
            VALUES (1, 'Employee One', '8888888888', 'Pune')
            """
        )
        cur.execute(
            """
            INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show)
            VALUES (10, 1, 1, 0)
            """
        )
        conn.commit()
        conn.close()

        resp = self.client.get("/api/employee/1/my-trip")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertTrue(body.get("success"))
        data = body.get("data") or {}
        self.assertTrue(data.get("has_trip"))
        trip = data.get("trip") or {}
        self.assertEqual(int(trip.get("trip_id") or 0), 10)
        self.assertEqual(str(trip.get("trip_date") or ""), tomorrow.strftime("%Y%m%d"))
        self.assertTrue(bool(trip.get("is_preassigned")))


if __name__ == "__main__":
    unittest.main()
