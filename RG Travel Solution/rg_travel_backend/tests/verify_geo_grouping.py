
import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.grouping_service import auto_group_by_sizes, EmployeePoint

class TestGeoGrouping(unittest.TestCase):
    
    def make_emp(self, id, lat, lng):
        return EmployeePoint(
            id=id, name=f"E{id}", mobile="9", address="A",
            lat=lat, lng=lng, login_time="09:00", logout_time="18:00",
            is_absent=False, trip_not_required=False
        )

    def test_geo_clustering_furthest_first(self):
        """
        Scenario:
        Office at (0,0).
        Emp 1: Near (0.1, 0.1)
        Emp 2: Near (0.2, 0.2)
        Emp 3: Far (1.0, 1.0)
        Emp 4: Far (1.1, 1.1)
        
        If we group in sizes of 2.
        Seed should be furthest first (Emp 4).
        Neighbors of Emp 4 is Emp 3.
        So Group 1: [Emp 4, Emp 3]
        Group 2: [Emp 1, Emp 2]
        """
        office_lat, office_lng = 0.0, 0.0
        
        emps = [
            self.make_emp(1, 0.1, 0.1),
            self.make_emp(2, 0.2, 0.2),
            self.make_emp(3, 1.0, 1.0),
            self.make_emp(4, 1.1, 1.1),
        ]
        
        # target_sizes = [2, 2]
        groups, unassigned = auto_group_by_sizes(emps, [2, 2], office_lat, office_lng)
        
        print("\nGeo Clusters Formed:")
        for i, g in enumerate(groups):
            print(f"Group {i+1}: ids {[e.id for e in g]}")

        self.assertEqual(len(groups), 2)
        # Group 1 should contain 3 and 4 (the far ones)
        ids1 = {e.id for e in groups[0]}
        self.assertTrue(3 in ids1 and 4 in ids1)
        
        # Group 2 should contain 1 and 2
        ids2 = {e.id for e in groups[1]}
        self.assertTrue(1 in ids2 and 2 in ids2)

if __name__ == '__main__':
    unittest.main()
