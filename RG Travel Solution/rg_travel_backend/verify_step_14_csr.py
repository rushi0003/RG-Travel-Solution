import sys
import os
import json
import sqlite3
from datetime import datetime

# Add project root to path
# CWD is c:/Users/HP/Desktop/RG Travel Solution/RG Travel Solution/rg_travel_backend
sys.path.append(os.getcwd())

from app import app
from db import get_db

if __name__ == "__main__":
    ctx = app.app_context()
    ctx.push()
    client = app.test_client()
    
    print("\n" + "="*50)
    print("STEP 14: CSR BACKEND VERIFICATION")
    print("="*50)

    print("\n>>> 1. PREVIEW GROUPS (clustering)")
    headers = {"Authorization": "Bearer demo-admin-token-12345"}
    
    # Use V2 Preview Endpoint
    resp = client.post("/api/v2/trips/preview", json={
        "admin_id": "admin_001",
        "trip_type": "pickup",
        "selected_time": "09:00",
        "vehicle_type": 4,
        "office_lat": 19.1136, 
        "office_lng": 72.8697
    }, headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        # V2 response structure: data -> trip_preview, validated_employees, groups
        # Actually checking the response structure from trip_creation_v2_routes.py/preview_and_organize_trip
        # It returns {"success": True, "data": result} where result has "groups"
        
        # Let's inspect the keys to be safe
        data = resp.json["data"]
        groups = data.get("groups", [])
        print(f"Success: Found {len(groups)} groups.")
        
    else:
        print(f"Error: {resp.json}")
        sys.exit(1)

    print("\n>>> 2. ASSIGN TRIP (Auto-assignment with rotation)")
    if not groups:
        print("No groups generated, cannot proceed with assignment.")
        sys.exit(1)

    # We assign the first group
    first_group = groups[0]
    
    # V2 Create Payload
    assign_payload = {
        "admin_id": "admin_001",
        "preview_data": data, # Pass full preview data context
        "groups_to_create": [first_group], # Create specific group(s)
        "driver_assignments": {} # Let system auto-assign
    }
    
    # Use V2 Create Endpoint
    resp = client.post("/api/v2/trips/create", json=assign_payload, headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code in (200, 201):
        # V2 response: data -> trips_created (list)
        trips_created = resp.json["data"].get("trips_created", [])
        if trips_created:
            trip_data = trips_created[0]
            trip_id = trip_data["trip_id"]
            driver_id = trip_data.get("driver_id", "unknown")
            print(f"Success: Trip {trip_id} created and assigned to Driver {driver_id}")
        else:
            print("Success, but no trips returned in response?")
            print(resp.text)
            sys.exit(1)
    else:
        print(f"Error: {resp.text}")
        sys.exit(1)

    print("\n>>> 3. SWAP CAB (CSR flow)")
    # Get another driver for swap
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, vehicle_no FROM drivers WHERE id != ? AND is_approved=1 LIMIT 1", (driver_id,))
    row = cur.fetchone()
    if not row:
         print("No other approved driver found for swap.")
         new_cab = "TEST-CAB"
    else:
         new_cab = row[1]
    
    print(f"Swapping to Cab: {new_cab}")
    
    resp = client.post(f"/api/admin/trips/{trip_id}/swap-cab", json={
        "cab_no": new_cab,
        "admin_id": "admin_001"
    }, headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success: Cab swapped successfully.")
    else:
        print(f"Error: {resp.json}")

    print("\n>>> 4. HELPDESK RESOLUTION")
    # Simulate a ticket
    cur.execute("INSERT INTO helpdesk_tickets (user_id, user_type, subject, message, priority, status, created_at, updated_at) VALUES (?, 'employee', 'General Issue', 'Test Ticket Description', 'normal', 'open', ?, ?)", (1, datetime.now().isoformat(), datetime.now().isoformat()))
    ticket_id = cur.lastrowid
    conn.commit()
    
    resp = client.post(f"/api/admin/helpdesk/{ticket_id}/resolve", json={
        "note": "Resolved during verification",
        "admin_id": "admin_001"
    }, headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success: Helpdesk ticket resolved.")
    else:
        print(f"Error: {resp.json}")

    print("\n>>> 5. SOS ALERTS FETCH")
    # Simulate SOS
    cur.execute("INSERT INTO sos_alerts (employee_id, trip_id, lat, lng, resolved, created_at) VALUES (?, ?, 19.1, 72.8, 0, ?)", (1, trip_id, datetime.now().isoformat()))
    conn.commit()
    
    resp = client.get("/api/admin/sos-alerts", headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        alerts = resp.json["data"]
        print(f"Success: Fetched {len(alerts)} SOS alerts.")
    else:
        print(f"Error: {resp.json}")

    print("\n>>> 6. ABSENCE REQUEST LISTING & APPROVAL")
    # Simulate absence
    cur.execute("INSERT INTO employee_absences (employee_id, absence_date, reason, status, requested_at, created_at, updated_at) VALUES (?, '2026-02-20', 'Vacation', 'pending', ?, ?, ?)", (1, datetime.now().isoformat(), datetime.now().isoformat(), datetime.now().isoformat()))
    abs_id = cur.lastrowid
    conn.commit()
    
    resp = client.get("/api/admin/absence-requests", headers=headers)
    print(f"List Status: {resp.status_code}")
    
    resp = client.post(f"/api/admin/absence-requests/{abs_id}/approve", headers=headers)
    print(f"Approve Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success: Absence request approved.")
    else:
        print(f"Error: {resp.json}")

    print("\n" + "="*50)
    print("VERIFICATION COMPLETE")
    print("="*50)
