import sys
import os
import json
import sqlite3
from datetime import datetime

# Add project root to path
# We are in tests/, keys is ..
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from rg_travel_backend.app import app
    from rg_travel_backend.db import get_db
except ImportError:
    # Try appending one level up if run from root?
    # If run as python tests/verify..., cwd is root, but __file__ is tests/verify...
    # dirname is tests. .. is root. So it should work.
    # Maybe explicit append of current dir?
    sys.path.append(os.getcwd())
    from rg_travel_backend.app import app
    from rg_travel_backend.db import get_db

if __name__ == "__main__":
    # Manual Test Setup
    # 1. Setup Context
    ctx = app.app_context()
    ctx.push()
    
    client = app.test_client()
    
    print(">>> 1. Preview Groups (Grouping Service)")
    # Need some dummy employees. Assuming seed data exists from Step 14.
    resp = client.post("/api/groups/preview", json={
        "admin_id": "admin_test",
        "trip_type": "pickup",
        "scheduled_time": "09:00", # Matches seed data? Seed was 09:00
        "vehicle_type": 4,
        "office_lat": 19.1136, 
        "office_lng": 72.8697
    })
    print(f"Preview Status: {resp.status_code}")
    if resp.status_code != 200:
        print(resp.json)
        sys.exit(1)
        
    preview_data = resp.json["data"]
    groups = preview_data.get("groups", [])
    if not groups:
        print("No groups found! Ensure seed data is present (Step 14).")
        # Ensure seed data is present matches logic.
        # If no groups, we can't test trip creation.
        # Check seed data time.
    else:
        print(f"Found {len(groups)} groups.")
        group_to_assign = groups[0]
        
        print("\n>>> 2. Assign Trip (TripService)")
        # We need a valid driver ID.
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM drivers WHERE is_online=1 AND vehicle_type=4 LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("No online 4-seater driver found. Cannot assign.")
            # Try to find ANY driver and force online?
            cur.execute("SELECT id FROM drivers WHERE vehicle_type=4 LIMIT 1")
            row = cur.fetchone()
            if row:
                print("Found offline driver, using them (might fail if service checks online status strict).")
                # Service checks `driver_repo.find_available_driver` which checks is_online=1?
                # Let's check DriverRepo implementation. 
                # It does check is_online=1.
                # Update driver to online.
                cur.execute("UPDATE drivers SET is_online=1 WHERE id=?", (row[0],))
                conn.commit()
                driver_id = row[0]
            else:
                 print("No drivers available at all.")
                 sys.exit(1)
        else:
            driver_id = row[0]
            
        print(f"Assigning to Driver ID: {driver_id}")
        
        # Payload for matching assignTrip
        assign_payload = {
            "group_id": group_to_assign["group_index"], # Logic in FE might differ, usually we send full group members
            "driver_id": driver_id,
            "admin_id": "admin_test",
            "operation": "pickup",
            "vehicle_type": 4,
            "schedule_time": "09:00",
             # The new assign_group_trip expects 'group' dict with 'ordered_stops' or 'members'
            "group": group_to_assign # Pass the whole group object as 'group'
        }
        
        resp = client.post("/api/admin/trips/assign-group", json=assign_payload) # Check correct route path
        # Actually route is @grouping_bp.route("/trips/assign-group") -> /api/trips/assign-group or similar?
        # In grouping_routes.py: @grouping_bp.route("/trips/assign-group")
        # In app.py: app.register_blueprint(grouping_bp, url_prefix="/api") (Assumption)
        # Result: /api/trips/assign-group
        
        print(f"Assign Status: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.json)
            # Try /api/admin/trips/assign-group if prefix differs
        else:
            trip_data = resp.json["data"]
            trip_id = trip_data["trip_id"]
            print(f"Trip Created: ID {trip_id}, Route {trip_data['route_no']}")
            
            print("\n>>> 3. Get Trip Details (TripService)")
            resp = client.get(f"/api/admin/trips/{trip_id}")
            print(f"Get Details Status: {resp.status_code}")
            if resp.status_code == 200:
                print("Trip Details Fetched.")
            else:
                print(resp.json)

            print("\n>>> 4. Swap Driver (TripService)")
            # Find another driver
            cur.execute("SELECT id, vehicle_no FROM drivers WHERE id != ? AND vehicle_type=4 LIMIT 1", (driver_id,))
            row2 = cur.fetchone()
            if row2:
                new_driver_id, new_cab_no = row2
                # Ensure online
                cur.execute("UPDATE drivers SET is_online=1 WHERE id=?", (new_driver_id,))
                conn.commit()
                
                print(f"Swapping to Cab: {new_cab_no}")
                resp = client.post(f"/api/admin/trips/{trip_id}/swap-cab", json={
                    "cab_no": new_cab_no,
                    "admin_id": "admin_test"
                })
                print(f"Swap Status: {resp.status_code}")
                print(resp.json)
            else:
                print("No second driver for swap test.")
                
            print("\n>>> 5. Add/Remove Employee (TripService)")
            members = trip_data.get("employees", [])
            if members:
                emp_to_remove = members[0]["employee_id"]
                print(f"Removing Employee: {emp_to_remove}")
                resp = client.post(f"/api/admin/trips/{trip_id}/remove-employee", json={
                    "employee_id": emp_to_remove,
                    "admin_id": "admin_test"
                })
                print(f"Remove Status: {resp.status_code}")
                
                print(f"Adding Employee Back: {emp_to_remove}")
                resp = client.post(f"/api/admin/trips/{trip_id}/add-employee", json={
                    "employee_id": emp_to_remove,
                    "admin_id": "admin_test"
                })
                print(f"Add Status: {resp.status_code}")
            
    print("\n>>> Test Complete")
