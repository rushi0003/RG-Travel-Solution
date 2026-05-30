
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from services import grouping_service as gs
from services.grouping_service import GroupResult, _prepare_group_result, EmployeePoint

class TestRoutePlanning(unittest.TestCase):
    def setUp(self):
        self.office_lat = 18.5204
        self.office_lng = 73.8567
        self.employees = [
            EmployeePoint(id=1, name="E1", mobile="1", address="A1", lat=18.5300, lng=73.8600, login_time="09:00", logout_time="18:00", is_absent=False, trip_not_required=False),
            EmployeePoint(id=2, name="E2", mobile="2", address="A2", lat=18.5400, lng=73.8700, login_time="09:00", logout_time="18:00", is_absent=False, trip_not_required=False),
        ]

    @patch("services.grouping_service.routing_service")
    def test_prepare_group_result_with_routing(self, mock_rs):
        # Mock successful Google Maps response
        mock_rs.build_multi_stop_route.return_value = {
            "success": True,
            "polyline": "mock_polyline_123",
            "total_km": 15.5,
            "total_duration_min": 35,
            "ordered_points": [(18.5204, 73.8567), (18.5300, 73.8600), (18.5400, 73.8700), (18.5204, 73.8567)]
        }

        # Call with optimize_waypoints=True
        res = _prepare_group_result(
            group_index=1,
            group_members=self.employees,
            vehicle_type=4,
            operation="drop",
            scheduled_time="18:00",
            office_lat=self.office_lat,
            office_lng=self.office_lng,
            optimize_waypoints=True
        )

        self.assertEqual(res.polyline, "mock_polyline_123")
        self.assertEqual(res.distance_km_estimate, 15.5)
        self.assertEqual(res.duration_min_estimate, 35)
        self.assertEqual(len(res.warnings), 0)
        
        # Verify routing service was called
        mock_rs.build_multi_stop_route.assert_called_once()
        args, kwargs = mock_rs.build_multi_stop_route.call_args
        self.assertEqual(kwargs['origin'], (self.office_lat, self.office_lng))
        self.assertTrue(kwargs['optimize'])

    @patch("services.grouping_service.routing_service")
    def test_prepare_group_result_fallback(self, mock_rs):
        # Mock failed Google Maps response
        mock_rs.build_multi_stop_route.return_value = {
            "success": False,
            "error": "API Key Expired"
        }

        # Call with optimize_waypoints=True
        res = _prepare_group_result(
            group_index=1,
            group_members=self.employees,
            vehicle_type=4,
            operation="drop",
            scheduled_time="18:00",
            office_lat=self.office_lat,
            office_lng=self.office_lng,
            optimize_waypoints=True
        )

        # Should have polyline empty but distance estimated via haversine
        self.assertEqual(res.polyline, "")
        self.assertGreater(res.distance_km_estimate, 0)
        self.assertGreater(res.duration_min_estimate, 0)
        self.assertTrue(any("Google Routing failed" in w for w in res.warnings))

if __name__ == "__main__":
    unittest.main()
