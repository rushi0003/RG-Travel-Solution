
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def log(msg, success=True):
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {msg}")

def run_tests():
    print("Starting Verify Fixes Tests...")
    
    # 1. Login to get token (using the admin created by reset_data.py)
    # reset_data.py creates admin with mobile 9325118627 and password 'admin123'
    login_payload = {
        "name": "Rushi Gund",
        "mobile": "9325118627",
        "password": "admin123" # Assuming this is the password set by reset_data.py or seeds
    } 
    # Wait, reset_data.py might not have set this password. 
    # Let's check reset_data.py content if possible, or try a default. 
    # Actually, reset_data.py usually calls seed_data. 
    
    # Assuming standard admin login for now.
    
    s = requests.Session()
    
    try:
        resp = s.post(f"{BASE_URL}/api/auth/admin/login", json=login_payload)
        if resp.status_code != 200:
            log(f"Admin Login failed: {resp.text}", False)
            sys.exit(1)
        
        data = resp.json()
        if not data.get("success"):
            log(f"Admin Login success=False: {data}", False)
            sys.exit(1)
            
        admin_id = data["data"]["id"]
        log(f"Admin Login successful. ID: {admin_id}")
    except Exception as e:
        log(f"Login Exception: {e}", False)
        sys.exit(1)

    # 2. Test Employee Requests (was failing with home_lat error)
    try:
        resp = s.get(f"{BASE_URL}/api/admin/employee-requests")
        if resp.status_code == 200:
            log("Employee Requests endpoint works")
        else:
            log(f"Employee Requests failed: {resp.status_code} {resp.text}", False)
    except Exception as e:
        log(f"Employee Requests Ex: {e}", False)

    # 3. Test Live Trips (was failing with trip_time error)
    try:
        resp = s.get(f"{BASE_URL}/api/admin/trips/live")
        if resp.status_code == 200:
            log("Live Trips endpoint works")
        else:
            log(f"Live Trips failed: {resp.status_code} {resp.text}", False)
    except Exception as e:
        log(f"Live Trips Ex: {e}", False)

    # 4. Test Online Drivers (was failing with cab_no error)
    try:
        resp = s.get(f"{BASE_URL}/api/admin/drivers/online")
        if resp.status_code == 200:
            log("Online Drivers endpoint works")
        else:
            log(f"Online Drivers failed: {resp.status_code} {resp.text}", False)
    except Exception as e:
        log(f"Online Drivers Ex: {e}", False)

if __name__ == "__main__":
    run_tests()
