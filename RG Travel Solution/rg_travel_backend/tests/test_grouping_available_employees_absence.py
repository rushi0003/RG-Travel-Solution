import sqlite3
import unittest
from unittest.mock import patch

from flask import Flask

from rg_travel_backend.routes.grouping_routes import grouping_bp
from rg_travel_backend.services.absence_flow_service import (
    create_absence_request,
    review_request,
)
from rg_travel_backend.db.migrate import create_new_tables


class TestGroupingAvailableEmployeesAbsence(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._prepare_db()

        self.app = Flask(__name__)
        self.app.register_blueprint(grouping_bp)
        self.client = self.app.test_client()

        self.db_patcher = patch(
            "rg_travel_backend.routes.grouping_routes.get_db",
            side_effect=self._get_db,
        )
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
        self.conn.close()

    def _get_db(self):
        return self.conn

    def _prepare_db(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                employee_id TEXT,
                name TEXT,
                mobile TEXT,
                email TEXT,
                login_time TEXT,
                logout_time TEXT,
                is_active INTEGER DEFAULT 1,
                is_approved INTEGER DEFAULT 1,
                pickup_lat REAL,
                pickup_lng REAL,
                pickup_address TEXT,
                home_lat REAL,
                home_lng REAL,
                home_address TEXT,
                drop_lat REAL,
                drop_lng REAL,
                drop_location TEXT
            );

            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                trip_day TEXT,
                operation TEXT,
                trip_type TEXT,
                time_slot TEXT,
                schedule_time TEXT,
                status TEXT
            );

            CREATE TABLE trip_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                employee_id TEXT
            );

            CREATE TABLE admins (
                id TEXT PRIMARY KEY,
                name TEXT
            );
            """
        )
        cur.execute("INSERT INTO admins(id, name) VALUES ('ADM1', 'Admin')")
        cur.executemany(
            """
            INSERT INTO employees (
                id, employee_id, name, mobile, email, login_time, logout_time, is_active, is_approved,
                pickup_lat, pickup_lng, pickup_address, home_lat, home_lng, home_address,
                drop_lat, drop_lng, drop_location
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "1", "Emp One", "9000000001", "e1@test.com", "09:00", "18:00", 1, 1, 18.1, 73.1, "P1", 18.1, 73.1, "H1", 18.1, 73.1, "D1"),
                (2, "2", "Emp Two", "9000000002", "e2@test.com", "09:00", "18:00", 1, 1, 18.2, 73.2, "P2", 18.2, 73.2, "H2", 18.2, 73.2, "D2"),
            ],
        )
        self.conn.commit()
        create_new_tables(self.conn)

    def test_available_employees_excludes_approved_absence(self):
        absence = create_absence_request(
            self.conn,
            1,
            ["2026-03-16"],
            reason="Approved leave",
        )
        review_request(self.conn, absence["id"], decision="approve", reviewed_by="ADM1")

        response = self.client.get(
            "/api/admin/available-employees",
            query_string={
                "trip_type": "pickup",
                "time_slot": "09:00",
                "trip_day": "20260316",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        employees = body["data"]["employees"]
        employee_ids = {str(item["id"]) for item in employees}
        self.assertEqual(employee_ids, {"2"})


if __name__ == "__main__":
    unittest.main()
