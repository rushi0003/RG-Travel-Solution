import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.driver_assignment import (
    calculate_workload_score,
    DriverCandidate,
    get_available_drivers,
    assign_drivers_to_groups
)

class TestDriverAssignment(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()

    def test_calculate_workload_score(self):
        # Scenario 1: High workload
        score1 = calculate_workload_score(
            weekly_trips=12,
            total_distance_km=250,
            consecutive_same_route=2,
            days_since_last_trip=1
        )
        # (12*100) + (250*10) + (2*50) + (1*-20) = 1200 + 2500 + 100 - 20 = 3780
        self.assertEqual(score1, 3780.0)

        # Scenario 2: Low workload (Driver B from docstring)
        score2 = calculate_workload_score(
            weekly_trips=8,
            total_distance_km=180,
            consecutive_same_route=0,
            days_since_last_trip=3
        )
        # (8*100) + (180*10) + (0*50) + (3*-20) = 800 + 1800 + 0 - 60 = 2540
        self.assertEqual(score2, 2540.0)

    @patch('db.database.query')
    def test_get_available_drivers(self, mock_query):
        # Mock DB response
        mock_query.return_value = [
            {
                "id": "d1", "name": "Driver 1", "mobile": "123",
                "vehicle_no": "KA01", "vehicle_type": 4, "home_town": "Bangalore"
            }
        ]

        drivers = get_available_drivers(self.mock_db, vehicle_type=4)
        
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0].id, "d1")
        self.assertEqual(drivers[0].vehicle_type, 4)
        
        # Verify query was called with correct params
        args, _ = mock_query.call_args
        self.assertIn("SELECT d.id", args[1])
        self.assertEqual(args[2], ['4'])

    @patch('services.driver_assignment.get_available_drivers')
    @patch('services.driver_assignment.get_driver_trip_history')
    @patch('services.driver_assignment.calculate_days_since_last_trip')
    def test_assign_drivers_to_groups(self, mock_days, mock_history, mock_get_drivers):
        # Setup drivers
        d1 = DriverCandidate("d1", "Low Workload", "111", "V1", 4, "Pune")
        d2 = DriverCandidate("d2", "High Workload", "222", "V2", 4, "Mumbai")
        
        mock_get_drivers.return_value = [d1, d2]
        
        # Setup history returns (mocking emptiness for simplicity)
        mock_history.return_value = []
        mock_days.return_value = 1
        
        # Test assignment for 1 group
        groups = [[{"id": 1, "address": "Pune"}]] # Group needs 1 driver
        
        # We need to mock workload calculation indirectly or trust the function
        # The function assigns inside loop.
        # Let's manually set properties that would be set by the loop if we didn't mock internal calls?
        # Actually assign_drivers_to_groups calls get_driver_trip_history effectively.
        
        # Let's just run it. The service calculates score based on history.
        # D1: 0 trips -> score (0*100) + ... + (1*-20) = -20
        # D2: 0 trips -> score -20 (tie?)
        
        # Let's force d2 to have history
        def side_effect_history(conn, driver_id, days):
            if driver_id == "d2":
                return [{"total_km": 100}] # 1 trip
            return []
        
        mock_history.side_effect = side_effect_history
        
        assignments = assign_drivers_to_groups(
            self.mock_db,
            groups,
            vehicle_type=4,
            operation="pickup",
            trip_day="20231027"
        )
        
        self.assertEqual(len(assignments), 1)
        # D1 should be picked (0 trips vs D2's 1 trip)
        self.assertEqual(assignments[0]["driver_id"], "d1")
        self.assertEqual(assignments[0]["assignment_reason"], "hometown_match") # -30 bonus for Pune match?
        # Wait, d1 is Pune. Group has address Pune. Match!
        
        # Helper check
        self.assertEqual(assignments[0]["driver_name"], "Low Workload")

if __name__ == '__main__':
    unittest.main()
