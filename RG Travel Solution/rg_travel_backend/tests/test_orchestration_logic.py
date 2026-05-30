
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "rg_travel_backend"))

from services.capacity_optimizer import optimize_cab_capacity
from services.driver_assignment import DriverCandidate, calculate_workload_score, matches_hometown

class TestOrchestrationLogic(unittest.TestCase):

    def test_capacity_optimization_6_seater_priority(self):
        # 10 employees, 4 and 6 seaters allowed (plenty available)
        # Optimal should be 1x6 + 1x4 = 2 groups (cab count 2)
        # 3x4 = 12 seats, 3 groups (worse)
        
        # Args: num_employees, available_4, available_6, prioritize_6
        result = optimize_cab_capacity(10, 10, 10, prioritize_6_seaters=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["use_6_seaters"], 1)
        self.assertEqual(result["data"]["use_4_seaters"], 1)
        self.assertEqual(result["data"]["total_cabs"], 2)

    def test_driver_workload_score(self):
        # Selection logic picks MIN score.
        # Driver 1: More trips, less distance.
        # Driver 2: Less trips, more distance.
        
        # Driver 1: 5 trips, 100km
        score1 = calculate_workload_score(5, 100.0, 0, 0) # 500 + 1000 = 1500
        # Driver 2: 2 trips, 200km
        score2 = calculate_workload_score(2, 200.0, 0, 0) # 200 + 2000 = 2200
        
        # Driver 1 is "better" (lower score) if distance is weighted heavily (10x)
        self.assertLess(score1, score2)

    def test_go_home_priority(self):
        driver = DriverCandidate(
            id="drv1", name="John", mobile="123", vehicle_no="A1",
            vehicle_type=4, home_town="Andheri",
            go_home_requested=True, go_home_town="Andheri"
        )
        employees = [{"home_address": "Andheri East, Mumbai"}]
        
        self.assertTrue(matches_hometown(driver, employees))

if __name__ == "__main__":
    unittest.main()
