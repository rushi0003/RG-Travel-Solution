import requests
import json
import sqlite3
import time

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = "rg_travel.db"

def reset_and_seed_db():
    print("Resetting test data in DB...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Reset Driver Requests
    cur.execute("DELETE FROM driver_requests WHERE mobile = '9998887776'")
    cur.execute("""
        INSERT INTO driver_requests (name, mobile, dl_no, cab_no, home_town, status, created_at, vehicle_type)
        VALUES ('Test Driver', '9998887776', 'MH12AAA12345678', 'MH12AB1234', 'Pune', 'Pending', datetime('now'), NULL)
    """)
    # vehicle_type is NULL to test patching
    
    # 2. Reset Employee Requests
    cur.execute("DELETE FROM employee_requests WHERE mobile = '9998887775'")
    cur.execute("DELETE FROM employees WHERE mobile = '9998887775'") # Ensure clean slate
    cur.execute("""
        INSERT INTO employee_requests (name, mobile, login_time, logout_time, home_address, status, created_at)
        VALUES ('Test Employee', '9998887775', '09:00', '18:00', 'Pune Station', 'Pending', datetime('now'))
    """)
    # Note: DB column is home_address

    conn.commit()
    conn.close()

def get_request_id(table, mobile):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {table} WHERE mobile = ? ORDER BY id DESC LIMIT 1", (mobile,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def test_approve_driver_request():
    print("\n--- Testing Driver Request Approval (Patching vehicle_type) ---")
    req_id = get_request_id('driver_requests', '9998887776')
    if not req_id:
        print("Error: Test driver request not found.")
        return

    url = f"{BASE_URL}/api/admin/driver-requests/{req_id}/approve"
    payload = {
        # "vehicle_type": "4", 
        # Intentionally omitting ALL fields to test default value "4" for vehicle_type
    }
    
    try:
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
            print("PASS: Driver approved successfully.")
        else:
            print("FAIL: Driver approval failed.")
    except Exception as e:
        print(f"Error: {e}")

def test_approve_employee_request():
    print("\n--- Testing Employee Request Approval (Address Mapping) ---")
    req_id = get_request_id('employee_requests', '9998887775')
    if not req_id:
        print("Error: Test employee request not found.")
        return

    url = f"{BASE_URL}/api/admin/employee-requests/{req_id}/approve"
    # No payload needed if logic is correct (should pick address from DB)
    
    try:
        resp = requests.post(url, json={})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
             print("PASS: Employee approved successfully.")
        else:
             print("FAIL: Employee approval failed.")
    except Exception as e:
        print(f"Error: {e}")

def test_list_change_requests():
    print("\n--- Testing List Employee Change Requests (Table Existence) ---")
    url = f"{BASE_URL}/api/admin/employee-change-requests"
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        # print(f"Response: {resp.text}")
        if resp.status_code == 200:
             print("PASS: Listed change requests successfully.")
        else:
             print(f"FAIL: Failed to list change requests. Status {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    try:
        reset_and_seed_db()
        # Ensure backend reload if needed (flask debug mode might take a moment)
        time.sleep(1) 
        
        test_approve_driver_request()
        test_approve_employee_request()
        test_list_change_requests()
    except Exception as e:
        print(f"Global Error: {e}")
