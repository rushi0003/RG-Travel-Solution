import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_endpoints():
    print("Testing REST API Fallback Endpoints...")

    # 1. Test Employee My Trips
    # Assuming an employee exists. I'll pick ID 1 or search for one.
    # actually, strict ID checking might be in place. 
    # Let's try to get a profile first to ensure valid ID, or just try ID 1.
    employee_id = 1
    print(f"\n[Employee] Fetching trips for Employee ID {employee_id}...")
    try:
        resp = requests.get(f"{BASE_URL}/api/employee/{employee_id}/my-trips")
        if resp.status_code == 200:
            print("SUCCESS: /api/employee/<id>/my-trips")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"FAILED: Status {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"ERROR: {e}")

    # 2. Test Driver My Trips
    driver_id = 1
    print(f"\n[Driver] Fetching trips for Driver ID {driver_id}...")
    try:
        resp = requests.get(f"{BASE_URL}/api/driver/{driver_id}/my-trips")
        if resp.status_code == 200:
            print("SUCCESS: /api/driver/<id>/my-trips")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"FAILED: Status {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_endpoints()
