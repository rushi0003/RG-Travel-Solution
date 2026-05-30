from datetime import datetime
import unittest

from rg_travel_backend.services.trip_schedule_guard import evaluate_trip_start_gate


class TestTripScheduleGuard(unittest.TestCase):
    def test_pickup_unlocks_at_derived_pickup_time(self):
        gate = evaluate_trip_start_gate(
            "20260306",
            "09:00",
            trip_type="pickup",
            route_duration_minutes=45,
            now=datetime(2026, 3, 6, 8, 10, 0),
        )

        self.assertFalse(gate["can_start_now"])
        self.assertTrue(gate["is_preassigned"])
        self.assertEqual(gate["start_allowed_after"], "2026-03-06T08:15:00")
        self.assertEqual(gate["seconds_until_start"], 300)

    def test_pickup_previous_day_offset_is_respected(self):
        gate = evaluate_trip_start_gate(
            "20260306",
            "00:20",
            trip_type="pickup",
            route_duration_minutes=30,
            now=datetime(2026, 3, 5, 23, 45, 0),
        )

        self.assertFalse(gate["can_start_now"])
        self.assertTrue(gate["is_preassigned"])
        self.assertEqual(gate["start_allowed_after"], "2026-03-05T23:50:00")
        self.assertEqual(gate["seconds_until_start"], 300)

    def test_drop_still_uses_schedule_time(self):
        gate = evaluate_trip_start_gate(
            "20260306",
            "09:00",
            trip_type="drop",
            route_duration_minutes=45,
            now=datetime(2026, 3, 6, 8, 50, 0),
        )

        self.assertFalse(gate["can_start_now"])
        self.assertEqual(gate["start_allowed_after"], "2026-03-06T09:00:00")
        self.assertEqual(gate["seconds_until_start"], 600)


if __name__ == "__main__":
    unittest.main()
