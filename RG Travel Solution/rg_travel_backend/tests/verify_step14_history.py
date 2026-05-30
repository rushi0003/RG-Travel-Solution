import requests  # pyre-ignore[21]
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_trip_completion_and_history():
    print("--- Testing Step 14: Trip Completion & History ---")
    
    # 1. Get an active trip or create one
    print("Fetching active trips...")
    active_resp = requests.get(f"{BASE_URL}/api/v2/trips/active")
    trips = active_resp.json().get("data", {}).get("trips", [])
    
    if not trips:
        print("No active trips found. Please run verify_step13_visibility.py first to create a trip.")
        return
        
    trip = trips[0]
    trip_id = trip["trip_id"]
    print(f"Found Trip ID: {trip_id}, Current Status: {trip['status']}")
    
    # 2. Force Complete Trip via Admin Endpoint
    print(f"Force completing trip {trip_id}...")
    complete_resp = requests.post(
        f"{BASE_URL}/api/v2/trips/{trip_id}/complete",
        json={"admin_id": "test_admin"}
    )
    
    if complete_resp.status_code == 200:
        print("Trip completed successfully!")
    else:
        print(f"Failed to complete trip: {complete_resp.json()}")
        return
        
    # 3. Verify Trip in History
    print("Verifying trip in history...")
    history_resp = requests.get(f"{BASE_URL}/api/v2/trips/history?status=completed")
    history_data = history_resp.json().get("data", {}).get("trips", [])
    
    found = False
    for t in history_data:
        if t["id"] == trip_id:
            found = True
            print(f"Verified: Trip {trip_id} found in history with status 'completed'.")
            print(f"Details: KM: {t['total_km']}, Driver: {t['driver_name']}")
            break
            
    if not found:
        print(f"Error: Trip {trip_id} not found in history.")
        
    print("--- Step 14 Verification Finished ---")

if __name__ == "__main__":
    test_trip_completion_and_history()
