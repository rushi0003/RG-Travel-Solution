import requests
import sqlite3
import time
import os

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = os.path.join(os.path.dirname(__file__), "rg_travel.db")

def verify_driver_signup_vehicle_type():
    print("--- Verifying Driver Signup Vehicle Type ---")
    
    # 1. Prepare Request Payload with vehicleType = '6'
    payload = {
        "name": "Verify Driver",
        "mobile": "9998887779", # Unique mobile for test
        "dlNo": "MH1234567890123", # 2 letters + 13 digits
        "cabNo": "MH12AB9999",
        "homeTown": "Mumbai",
        "vehicleType": "6" 
    }
    
    # 2. Clean up existing test data if any
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM driver_requests WHERE mobile = ?", (payload["mobile"],))
    conn.commit()
    conn.close()
    
    # 3. Send Request
    url = f"{BASE_URL}/api/auth/driver/signup-request"
    try:
        print(f"Sending POST to {url} with vehicleType='6'...")
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code != 200:
            print("❌ API Request Failed")
            return

        # 4. Verify in Database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT vehicle_type FROM driver_requests WHERE mobile = ?", (payload["mobile"],))
        row = cur.fetchone()
        conn.close()
        
        if row:
            stored_type = row[0]
            print(f"Stored Vehicle Type in DB: '{stored_type}'")
            if str(stored_type) == "6":
                print("✅ PASS: Vehicle Type '6' stored successfully.")
            else:
                print(f"❌ FAIL: Expected '6', got '{stored_type}'")
        else:
            print("❌ FAIL: Driver request record not found in DB.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_driver_signup_vehicle_type()
