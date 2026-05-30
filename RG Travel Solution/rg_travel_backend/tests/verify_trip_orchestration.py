import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.trip_orchestration_service import (
    preview_and_organize_trip,
    create_and_assign_trip,
    TripOrchestrationError
)

class TestTripOrchestration(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.cursor.return_value = self.mock_cursor

    @patch('services.trip_validation_service.validate_trip_request')
    @patch('services.trip_validation_service.filter_eligible_employees')
    @patch('services.trip_validation_service.scan_cab_availability')
    @patch('services.trip_validation_service.validate_sufficient_resources')
    @patch('services.capacity_optimizer.optimize_cab_capacity')
    @patch('services.capacity_optimizer.rebalance_group_sizes')
    @patch('services.geo_clustering.cluster_employees_by_proximity')
    @patch('services.trip_validation_service.get_trip_validation_summary')
    def test_preview_and_organize_trip_success(
        self, mock_summary, mock_cluster, mock_rebalance, mock_optimize,
        mock_resources, mock_availability, mock_filter, mock_validate
    ):
        # Setup mocks
        mock_validate.return_value = {"success": True}
        
        # 10 employees
        employees = [{"id": i, "name": f"Emp{i}", "mobile": "123", "address": "Addr"} for i in range(10)]
        mock_filter.return_value = (employees, [])
        
        mock_availability.return_value = {
            "success": True,
            "data": {
                "available_4_count": 5,
                "available_6_count": 2,
                "available_driver_count": 7,
                "total_capacity": 32,
                "usable_cabs": 7
            }
        }
        
        mock_resources.return_value = (True, None)
        
        mock_optimize.return_value = {
            "success": True,
            "data": {
                "use_4_seaters": 1,
                "use_6_seaters": 1,
                "total_cabs": 2,
                "total_seats": 10,
                "empty_seats": 0,
                "efficiency_percent": 100,
                "strategy_used": "optimal"
            }
        }
        
        mock_rebalance.return_value = [6, 4]
        
        # 2 groups
        g1 = [MagicMock(id=i, name=f"Emp{i}", lat=12.0, lng=77.0) for i in range(6)]
        g2 = [MagicMock(id=i, name=f"Emp{i}", lat=12.1, lng=77.1) for i in range(6, 10)]
        mock_cluster.return_value = [g1, g2]
        
        mock_summary.return_value = {"warnings": []}

        # Execute
        result = preview_and_organize_trip(
            self.mock_db,
            admin_id="admin1",
            trip_type="pickup",
            selected_time="09:00",
            vehicle_type=0, # Auto
            office_lat=12.97,
            office_lng=77.59
        )

        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]["groups"]), 2)
        self.assertEqual(result["data"]["groups"][0]["members_count"], 6)
        self.assertEqual(result["data"]["groups"][1]["members_count"], 4)
        
        # Helper verification
        mock_validate.assert_called_once()
        mock_filter.assert_called_once()
        mock_optimize.assert_called_once()

    @patch('services.trip_orchestration_service._auto_assign_driver_for_group')
    @patch('services.trip_orchestration_service._get_driver_info')
    @patch('services.trip_orchestration_service._get_cab_info')
    @patch('services.route_no_service.generate_route_no')
    @patch('services.geo_clustering.calculate_group_distances')
    def test_create_and_assign_trip_success(
        self, mock_distances, mock_route_no, mock_cab, mock_driver, mock_assign
    ):
        # Mock inputs
        preview_data = {
            "trip_preview": {
                "trip_type": "pickup",
                "selected_time": "09:00",
                "vehicle_type": 4,
                "trip_day": "20231027",
                "office_lat": 12.97,
                "office_lng": 77.59
            }
        }
        
        groups_to_create = [
            {
                "group_index": 1,
                "members": [
                    {"id": 1, "name": "E1", "mobile": "111", "address": "A1", "lat": 12.0, "lng": 77.0},
                    {"id": 2, "name": "E2", "mobile": "222", "address": "A2", "lat": 12.0, "lng": 77.0}
                ]
            }
        ]
        
        # Mock standard calls
        mock_distances.return_value = {"total_route": 15.5}
        mock_assign.return_value = ("d1", "c1")
        mock_driver.return_value = {"name": "D1", "mobile": "999"}
        mock_cab.return_value = {"vehicle_no": "KA01", "vehicle_type": 4}
        mock_route_no.return_value = "RT123456"
        
        # Execute
        result = create_and_assign_trip(
            self.mock_db,
            admin_id="admin1",
            preview_data=preview_data,
            groups_to_create=groups_to_create
        )
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]["trips_created"]), 1)
        created_trip = result["data"]["trips_created"][0]
        self.assertEqual(created_trip["route_no"], "RT123456")
        self.assertEqual(created_trip["driver_id"], "d1")
        self.assertIsNotNone(created_trip["start_otp"])
        
        # Verify DB calls
        # 1 trip insert
        self.mock_cursor.execute.assert_any_call(ANY, ANY)
        # 2 employee inserts
        # Commit called
        self.mock_db.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
