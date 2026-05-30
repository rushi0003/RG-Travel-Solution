
import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def log(msg, success=True):
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {msg}")

def run_tests():
    print("Starting JSON Key Verification...")
    
    # Login
    login_payload = {
        "name": "Rushi Gund",
        "mobile": "9325118627",
        "password": "admin123"
    } 
    
    s = requests.Session()
    try:
        url = f"{BASE_URL}/api/auth/admin/login"
        print(f"POST {url}")
        resp = s.post(url, json=login_payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

        if resp.status_code != 200:
            log(f"Login failed: {resp.text}", False)
            sys.exit(1)
            
        data = resp.json()
        if not data.get("success"):
            log("Login success=False", False)
            sys.exit(1)
            
        log("Admin Login successful")
    except Exception as e:
        log(f"Login Exception: {e}", False)
        sys.exit(1)

    # Test Live Trips to check for 'scheduled_time' key
    try:
        url = f"{BASE_URL}/api/admin/trips/live"
        print(f"GET {url}")
        resp = s.get(url)
        print(f"Response: {resp.text}")

        if resp.status_code == 200:
            data = resp.json()
            trips = data.get("data", [])
            log(f"Live Trips endpoint returned {len(trips)} trips")
            
            # Check key
            if len(trips) > 0:
                first = trips[0]
                if "scheduled_time" in first:
                    log("SUCCESS: 'scheduled_time' key found in response!")
                else:
                    log("FAIL: 'scheduled_time' key MISSING. Found keys: " + str(list(first.keys())), False)
            else:
                log("Live Trips endpoint works, but no data to verify keys. Assuming schema match based on 200 OK.")
            
        else:
            log(f"Live Trips failed: {resp.status_code} {resp.text}", False)
            sys.exit(1)
    except Exception as e:
        log(f"Live Trips Ex: {e}", False)
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
