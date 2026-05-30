import contextlib
import io
import sqlite3
import unittest

from rg_travel_backend.db.migrate import create_new_tables, table_exists
from rg_travel_backend.services.absence_flow_service import (
    admin_remove_approved_absence,
    create_absence_request,
    create_cancel_request,
    list_approved_absence_ranges,
    list_admin_requests,
    list_employee_requests,
    review_request,
)
from rg_travel_backend.services.trip_validation_service import (
    filter_eligible_employees,
)


class TestAbsenceFlowUpgrade(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._prepare_base_schema()

    def tearDown(self):
        self.conn.close()

    def _prepare_base_schema(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
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

            CREATE TABLE admins (
                id TEXT PRIMARY KEY,
                name TEXT
            );

            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                operation TEXT,
                trip_type TEXT,
                status TEXT,
                trip_day TEXT,
                time_slot TEXT,
                schedule_time TEXT
            );

            CREATE TABLE trip_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                employee_id TEXT
            );
            """
        )
        cur.execute(
            """
            INSERT INTO employees (
                id, name, mobile, email, login_time, logout_time, is_active, is_approved,
                pickup_lat, pickup_lng, pickup_address, home_lat, home_lng, home_address,
                drop_lat, drop_lng, drop_location
            )
            VALUES
                (1, 'Emp One', '9000000001', 'e1@test.com', '09:00', '18:00', 1, 1, 18.1, 73.1, 'P1', 18.1, 73.1, 'H1', 18.1, 73.1, 'D1'),
                (2, 'Emp Two', '9000000002', 'e2@test.com', '09:00', '18:00', 1, 1, 18.2, 73.2, 'P2', 18.2, 73.2, 'H2', 18.2, 73.2, 'D2')
            """
        )
        cur.execute("INSERT INTO admins(id, name) VALUES ('ADM1', 'Admin')")
        self.conn.commit()

    def _run_create_new_tables(self):
        with contextlib.redirect_stdout(io.StringIO()):
            create_new_tables(self.conn)

    def test_migration_creates_absence_flow_tables(self):
        self._run_create_new_tables()

        self.assertTrue(table_exists(self.conn, "employee_absences"))
        self.assertTrue(table_exists(self.conn, "employee_absence_requests"))
        self.assertTrue(table_exists(self.conn, "absence_request_batches"))
        self.assertTrue(table_exists(self.conn, "absence_request_batch_dates"))

    def test_multi_day_approval_and_cancel_request_flow(self):
        self._run_create_new_tables()

        absence = create_absence_request(
            self.conn,
            1,
            ["2026-03-10", "2026-03-11", "2026-03-12"],
            reason="Festival leave",
        )
        self.assertEqual(absence["total_days"], 3)
        self.assertEqual(absence["request_kind"], "absence")

        admin_queue = list_admin_requests(self.conn)
        self.assertEqual(len(admin_queue), 1)
        self.assertEqual(admin_queue[0]["dates"], ["2026-03-10", "2026-03-11", "2026-03-12"])

        review = review_request(
            self.conn,
            absence["id"],
            decision="approve",
            reviewed_by="ADM1",
        )
        self.assertEqual(review.status, "approved")

        approved_rows = self.conn.execute(
            """
            SELECT absence_date, status
            FROM employee_absences
            WHERE employee_id = '1'
            ORDER BY absence_date
            """
        ).fetchall()
        self.assertEqual(
            [tuple(row) for row in approved_rows],
            [
                ("2026-03-10", "approved"),
                ("2026-03-11", "approved"),
                ("2026-03-12", "approved"),
            ],
        )

        cancel = create_cancel_request(
            self.conn,
            1,
            ["2026-03-10", "2026-03-11"],
            reason="Need transport again",
        )
        self.assertEqual(cancel["request_kind"], "cancel")
        review_request(self.conn, cancel["id"], decision="approve", reviewed_by="ADM1")

        remaining_rows = self.conn.execute(
            """
            SELECT absence_date, status
            FROM employee_absences
            WHERE employee_id = '1'
            ORDER BY absence_date
            """
        ).fetchall()
        self.assertEqual([tuple(row) for row in remaining_rows], [("2026-03-12", "approved")])

        employee_history = list_employee_requests(self.conn, 1)
        self.assertEqual(employee_history[0]["request_kind"], "cancel")
        self.assertEqual(employee_history[1]["request_kind"], "absence")

    def test_filter_eligible_employees_excludes_approved_absence_date(self):
        self._run_create_new_tables()
        absence = create_absence_request(
            self.conn,
            1,
            ["2026-03-10", "2026-03-11"],
            reason="Vacation",
        )
        review_request(self.conn, absence["id"], decision="approve", reviewed_by="ADM1")

        eligible, exclusions = filter_eligible_employees(
            self.conn,
            trip_type="pickup",
            selected_time="09:00",
            trip_day="20260311",
        )

        eligible_ids = {item["id"] for item in eligible}
        self.assertEqual(eligible_ids, {2})
        self.assertTrue(any("EMP#1: Approved absence on 20260311" == item for item in exclusions))

    def test_list_approved_absence_ranges_groups_contiguous_dates(self):
        self._run_create_new_tables()
        absence = create_absence_request(
            self.conn,
            1,
            ["2026-03-10", "2026-03-11", "2026-03-13"],
            reason="Vacation",
        )
        review_request(self.conn, absence["id"], decision="approve", reviewed_by="ADM1")

        ranges = list_approved_absence_ranges(self.conn, on_or_after="2026-03-10")

        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0]["employee_id"], 1)
        self.assertEqual(ranges[0]["from_date"], "2026-03-10")
        self.assertEqual(ranges[0]["to_date"], "2026-03-11")
        self.assertEqual(ranges[0]["total_days"], 2)
        self.assertEqual(ranges[0]["dates"], ["2026-03-10", "2026-03-11"])
        self.assertEqual(ranges[1]["from_date"], "2026-03-13")
        self.assertEqual(ranges[1]["to_date"], "2026-03-13")

    def test_admin_remove_approved_absence_creates_audit_and_unblocks_dates(self):
        self._run_create_new_tables()
        absence = create_absence_request(
            self.conn,
            1,
            ["2026-03-10", "2026-03-11", "2026-03-12"],
            reason="Medical leave",
        )
        review_request(self.conn, absence["id"], decision="approve", reviewed_by="ADM1")

        result = admin_remove_approved_absence(
            self.conn,
            1,
            ["2026-03-10", "2026-03-11"],
            reviewed_by="ADM1",
            reason="Admin correction",
        )

        self.assertEqual(result["request_kind"], "cancel")
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["dates"], ["2026-03-10", "2026-03-11"])

        remaining_rows = self.conn.execute(
            """
            SELECT absence_date
            FROM employee_absences
            WHERE employee_id = '1'
            ORDER BY absence_date
            """
        ).fetchall()
        self.assertEqual([row["absence_date"] for row in remaining_rows], ["2026-03-12"])

        audit_row = self.conn.execute(
            """
            SELECT request_kind, status, reason, admin_reason
            FROM absence_request_batches
            WHERE id = ?
            """,
            (result["request_id"],),
        ).fetchone()
        self.assertIsNotNone(audit_row)
        self.assertEqual(audit_row["request_kind"], "cancel")
        self.assertEqual(audit_row["status"], "approved")
        self.assertEqual(audit_row["reason"], "Admin correction")
        self.assertEqual(audit_row["admin_reason"], "Removed by admin")


if __name__ == "__main__":
    unittest.main()
