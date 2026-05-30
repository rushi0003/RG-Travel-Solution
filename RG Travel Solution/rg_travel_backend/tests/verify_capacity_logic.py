
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.capacity_optimizer import optimize_cab_capacity
from services.grouping_service import auto_group_mixed, EmployeePoint


# Create a mock EmployeePoint class for testing if needed, or use the real one
# EmployeePoint is a dataclass, so we can instantiate it easily.

class TestCapacityOptimization(unittest.TestCase):

    def make_employees(self, n):
        emps = []
        for i in range(n):
            emps.append(EmployeePoint(
                id=i+1,
                name=f"Emp{i+1}",
                mobile=f"90000000{i:02d}",
                address="Test Addr",
                lat=12.9 + (i*0.01), # slightly different locations
                lng=77.6 + (i*0.01),
                login_time="09:00",
                logout_time="18:00",
                is_absent=False,
                trip_not_required=False
            ))
        return emps

    def test_optimize_cab_capacity_13_employees(self):
        """
        13 Employees. 
        Avail: 10 of 4-seater, 10 of 6-seater.
        Expect: 1x6 (6) + 2x4 (8) = 14 seats. 3 cabs.
        Checking score vs alternatives:
        - 3x4 (12 seats) -> Not enough
        - 4x4 (16 seats) -> 3 empty. Score: 400 + 30 = 430
        - 3x6 (18 seats) -> 5 empty. Score: 300 + 50 = 350
        - 1x6, 2x4 (14 seats) -> 1 empty. Score: 300 + 10 = 310 (WINNER)
        """
        avail_4 = 10
        avail_6 = 10
        res = optimize_cab_capacity(13, avail_4, avail_6)
        
        self.assertTrue(res['success'])
        data = res['data']
        self.assertEqual(data['use_6_seaters'], 1)
        self.assertEqual(data['use_4_seaters'], 2)
        self.assertEqual(data['total_cabs'], 3)
        self.assertEqual(data['empty_seats'], 1)
        print("\nTest 1 (13 Emp): Success. Mix:", data['use_6_seaters'], "x 6-seater,", data['use_4_seaters'], "x 4-seater")

    def test_optimize_cab_capacity_17_employees(self):
        """
        17 Employees.
        Expect: 3x6 (18 seats). 1 empty. Score: 300 + 10 = 310.
        vs
        1x6 + 3x4 (18 seats). 1 empty. Score: 400 + 10 = 410. (More cabs)
        """
        res = optimize_cab_capacity(17, 10, 10)
        self.assertTrue(res['success'])
        data = res['data']
        # Should prefer fewer cabs
        self.assertEqual(data['use_6_seaters'], 3)
        self.assertEqual(data['use_4_seaters'], 0)
        print("Test 2 (17 Emp): Success. Mix:", data['use_6_seaters'], "x 6-seater,", data['use_4_seaters'], "x 4-seater")

    def test_grouping_mix_execution(self):
        """
        Verify auto_group_mixed respects the counts.
        """
        emps = self.make_employees(13)
        # Mix: 1x6, 2x4
        groups, unassigned = auto_group_mixed(emps, num_4=2, num_6=1)
        
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(unassigned), 0)
        
        # First group should be 6-seater (size 6 or 5 depending on distribution but we have 13)
        # 1x6 -> fills 6. Remaining 7.
        # 1x4 -> fills 4. Remaining 3.
        # 1x4 -> fills 3.
        # Sizes should be [6, 4, 3] or similar.
        
        sizes = [len(g) for g in groups]
        print("Test 3 (Grouping): Group sizes:", sizes)
        self.assertIn(6, sizes)
        self.assertTrue(any(s <= 4 for s in sizes[1:]))

if __name__ == '__main__':
    # Mock search_employee_repo just in case, though we don't call it directly in valid tests
    unittest.main()
