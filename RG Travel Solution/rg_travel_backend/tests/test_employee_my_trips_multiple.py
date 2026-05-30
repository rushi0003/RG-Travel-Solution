import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

from rg_travel_backend.routes.employee_routes import employee_bp


class TestEmployeeMyTripsMultiple(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="employee_my_trips_", suffix=".db")
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
                driver_id INTEGER,
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
        conn.commit()
        conn.close()

    def test_returns_all_active_trips_when_date_not_specified(self):
        conn = self._new_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO drivers (id, name, mobile, vehicle_no) VALUES (1, 'Driver One', '9999999999', 'MH12AA1111')"
        )
        cur.execute(
            """
            INSERT INTO trips (id, route_no, trip_type, trip_day, schedule_time, status, driver_id, vehicle_type, total_km)
            VALUES
            (1, 'R0001', 'pickup', '20260306', '09:00', 'assigned', 1, 'cab', 10.0),
            (2, 'R0002', 'drop', '20260307', '18:00', 'created', 1, 'cab', 12.0)
            """
        )
        cur.execute(
            """
            INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show)
            VALUES
            (1, 7, 1, 0),
            (2, 7, 1, 0)
            """
        )
        conn.commit()
        conn.close()

        resp = self.client.get("/api/employee/7/my-trips")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertTrue(body.get("success"))
        trips = ((body.get("data") or {}).get("trips") or [])
        self.assertEqual(len(trips), 2)
        self.assertEqual([str(t.get("route_no")) for t in trips], ["R0001", "R0002"])


if __name__ == "__main__":
    unittest.main()
