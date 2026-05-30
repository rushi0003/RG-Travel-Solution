import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.admin_override_service import AdminOverrideService

class TestAdminOverride(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.service = AdminOverrideService()
        
    @patch('services.admin_override_service.get_db')
    @patch('services.admin_override_service.TripRepo')
    @patch('services.admin_override_service.routing_service')
    def test_move_employee_success(self, mock_routing, mock_repo_cls, mock_get_db):
        # Setup Mocks
        mock_get_db.return_value = self.mock_db
        mock_repo = mock_repo_cls.return_value
        
        # Mock Trips
        trip1 = {"id": 1, "trip_type": "pickup", "vehicle_type": 4, "route_no": "R1", "office_lat": 12.0, "office_lng": 77.0}
        trip2 = {"id": 2, "trip_type": "pickup", "vehicle_type": 4, "route_no": "R2", "office_lat": 12.0, "office_lng": 77.0}
        
        def get_trip_side_effect(tid):
            return trip1 if tid == 1 else trip2
        mock_repo.get_trip_by_id.side_effect = get_trip_side_effect
        
        # Mock Capacity
        mock_repo.get_trip_capacity_info.return_value = {"member_count": 2} # Trip 2 has space (cap 4)
        
        # Mock Members
        # Trip 1 has Emp1 (id=101)
        # Trip 2 has Emp2 (id=102)
        mock_repo.list_trip_members.side_effect = lambda tid: (
            [{"employee_id": 101, "home_lat": 12.1, "home_lng": 77.1}] if tid == 1 else 
            [{"employee_id": 102, "home_lat": 12.2, "home_lng": 77.2}]
        )
        
        # Mock Routing
        mock_routing.build_multi_stop_route.return_value = {
            "success": True, 
            "polyline": "poly_new", 
            "total_km": 10.5,
            "ordered_points": []
        }

        # Execute Move Emp 101 from Trip 1 to Trip 2
        result = self.service.move_employee("admin1", "101", 1, 2)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Employee moved successfully.")
        
        # Updates
        # Trip 1 members updated (removed 101) -> []
        mock_repo.add_trip_members.assert_any_call(1, [])
        # Trip 2 members updated (added 101) -> [102, 101] (IDs)
        # Note: The service logic calls list_trip_members for Trip 2 which returns [102] in our mock, 
        # then appends 101. So arg should be [102, '101'] (str/int handling might vary)
        # The service uses: [m["employee_id"] for m in to_members] which are ints in our mock.
        # But `move_employee` arg `employee_id` is str.
        # Let's check assert with flexibility or exact expectation.
        # The service code: new_to_members_ids.append(employee_id) -> append("101")
        mock_repo.add_trip_members.assert_any_call(2, [102, "101"])
        
        # Route Recalculation called for Trip 2 only (Trip 1 is empty, handled by early return)
        self.assertEqual(mock_routing.build_multi_stop_route.call_count, 1)
        
        # Check update_route_data called for both
        # Trip 1 (Empty)
        mock_repo.update_route_data.assert_any_call(1, route_polyline="", stops_json="[]", total_km=0)
        # Trip 2 (Calculated)
        mock_repo.update_route_data.assert_any_call(
            trip_id=2, 
            route_polyline="poly_new", 
            stops_json="[]", # Mock returned empty ordered_points
            total_km=10.5
        )
        
        # Audit Log
        self.assertEqual(mock_repo.log_trip_event.call_count, 2)
        
        # Commit
        self.mock_db.commit.assert_called_once()

    @patch('services.admin_override_service.get_db')
    @patch('services.admin_override_service.TripRepo')
    def test_swap_vehicle_success(self, mock_repo_cls, mock_get_db):
        mock_get_db.return_value = self.mock_db
        mock_repo = mock_repo_cls.return_value
        
        mock_repo.get_trip_by_id.return_value = {
            "id": 1, "route_no": "R1", "vehicle_no": "OldV", "driver_id": "OldD"
        }
        
        result = self.service.swap_vehicle("admin1", 1, "NewV", "NewD")
        
        self.assertTrue(result["success"])
        
        mock_repo.update_trip_assignment.assert_called_with(
            trip_id=1, vehicle_no="NewV", driver_id="NewD"
        )
        
        mock_repo.log_trip_event.assert_called_once()
        self.mock_db.commit.assert_called_once()

    @patch('services.admin_override_service.get_db')
    @patch('services.admin_override_service.TripRepo')
    def test_move_employee_full_capacity(self, mock_repo_cls, mock_get_db):
        mock_get_db.return_value = self.mock_db
        mock_repo = mock_repo_cls.return_value
        
        trip1 = {"id": 1, "trip_type": "pickup", "vehicle_type": 4}
        trip2 = {"id": 2, "trip_type": "pickup", "vehicle_type": 4}
        mock_repo.get_trip_by_id.side_effect = lambda tid: trip1 if tid == 1 else trip2
        
        # Mock Full Capacity
        mock_repo.get_trip_capacity_info.return_value = {"member_count": 4}
        
        result = self.service.move_employee("admin1", "101", 1, 2)
        
        self.assertFalse(result["success"])
        self.assertIn("Destination trip is full", result["message"])
        
        self.mock_db.commit.assert_not_called()

if __name__ == '__main__':
    unittest.main()
