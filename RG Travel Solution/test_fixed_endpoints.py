#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5000"
admin_id = "admin_rg_001"

# Test the three endpoints
endpoints = [
    f"/api/admin/driver-requests",
    f"/api/admin/employee-requests",
    f"/api/admin/trips"
]

print("=" * 80)
print("TESTING FIXED ENDPOINTS")
print("=" * 80)

for endpoint in endpoints:
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url)
        print(f"\n{endpoint}")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"\n{endpoint}")
        print(f"  ERROR: {e}")
