import requests
import sqlite3
import time
import os

BASE_URL = "http://127.0.0.1:5001"
DB_PATH = os.path.join(os.path.dirname(__file__), "rg_travel.db")

def verify_driver_rejection():
    print("--- Verifying Driver Rejection Flow ---")
    
    # 1. Prepare Request Payload
    payload = {
        "name": "Reject Driver",
        "mobile": "9998887780", 
        "dlNo": "MH1288888888888",

        "cabNo": "MH12RJ9999",
        "homeTown": "Mumbai",
        "vehicleType": "4" 
    }
    
    # 2. Clean up existing test driver
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM driver_requests WHERE mobile = ?", (payload["mobile"],))
    conn.commit()
    conn.close()
    
    # 3. Send Signup Request
    url = f"{BASE_URL}/api/auth/driver/signup-request"
    try:
        print(f"1. Sending Signup Request to {url}...")
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            print(f"❌ Signup Failed: {resp.text}")
            return
            
        data = resp.json()
        print(f"DEBUG: Signup data: {data}")
        req_id = data.get("requestId")
        # Try finding it in data['data'] if nested
        if not req_id and "data" in data:
             req_id = data["data"].get("requestId") or data["data"].get("row_id") or data["data"].get("id")
        
        print(f"   Signup successful. Request ID: {req_id}")
        
        # 4. Reject Request with Reason
        reject_url = f"{BASE_URL}/api/admin/driver-requests/{req_id}/reject"
        reject_reason = "Documents unclear"
        print(f"2. Rejecting Request at {reject_url} with reason: '{reject_reason}'...")
        
        resp = requests.post(reject_url, json={"reason": reject_reason})
        print(f"   Status: {resp.status_code}")


        
        if resp.status_code != 200:
            print("❌ Rejection API Failed")
            return

        # 5. Verify in Database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT status, review_note, reviewed_at FROM driver_requests WHERE id = ?", (req_id,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            status, note, reviewed_at = row
            print(f"3. DB Verification:")
            print(f"   Status: {status}")
            print(f"   Note: {note}")
            print(f"   Time: {reviewed_at}")
            
            if status == "Rejected" and note == reject_reason and reviewed_at is not None:
                print("✅ PASS: Driver rejected correctly with reason.")
            else:
                print(f"❌ FAIL: DB data mismatch. Expected 'Rejected' with reason '{reject_reason}'.")
        else:
            print("❌ FAIL: Request record not found in DB.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_driver_rejection()
