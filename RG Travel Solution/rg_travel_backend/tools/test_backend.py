
import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def log(msg, success=True):
    status = "[OK]" if success else "[FAIL]"
    line = f"{status} {msg}"
    print(line)
    with open("test_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_tests():
    with open("test_log.txt", "w", encoding="utf-8") as f:
        f.write("Starting Backend Tests...\n")
    print("Starting Backend Tests...")
    
    # 1. Login
    login_payload = {
        "name": "Rushi Gund",
        "mobile": "9325118627",
        "password": "Rushi123", # Default from seed
        "role": "admin"
    }
    
    try:
        res = requests.post(f"{BASE_URL}/api/auth/admin/login", json=login_payload)
        if res.status_code != 200:
            log(f"Login failed: {res.text}", False)
            return
        
        data = res.json()
        token = data.get("token") or data.get("access_token") # Adapt to actual response
        if not token:
             # Check if response structure is different
             if 'data' in data and 'token' in data['data']:
                 token = data['data']['token']
             else:
                 log(f"No token in login response: {data}", False)
                 return

        log("Admin Login successful")
        headers = {"Authorization": f"Bearer {token}"}
        
    except Exception as e:
        log(f"Login connection failed: {e}", False)
        return

    # 2. Create Employee
    import random
    rand_mobile = f"9{random.randint(100000000, 999999999)}"
    
    emp_payload = {
        "name": "Test Employee",
        "mobile": rand_mobile, # Unique
        "login_time": "09:00",
        "logout_time": "18:00",
        "address": "Test Address",
        "lat": 18.5204,
        "lng": 73.8567
    }
    
    emp_id = None
    try:
        # Note: admin_routes.py uses /api/admin/employees for POST
        res = requests.post(f"{BASE_URL}/api/admin/employees", json=emp_payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            # admin_routes.py wraps in {success: true, data: ...} or direct?
            # _ok helper returns {success: true, message: ..., data: ...} usually (see code)
            # or data merged.
            # admin_routes.py: return _ok({"employee_id": emp_id, "employee_code": code}, "Employee created successfully.")
            # _ok -> {success: true, message: ..., data: ...}
            
            emb_data = data.get("data", {})
            emp_id = emb_data.get("employee_id")
            emp_code = emb_data.get("employee_code")
            
            if emp_id and emp_code:
                log(f"Created Employee: ID={emp_id}, Code={emp_code}")
            else:
                log(f"Created but missing ID/Code: {data}", False)
        else:
            log(f"Create Employee failed: {res.status_code} {res.text}", False)
    except Exception as e:
        log(f"Create Employee error: {e}", False)

    # 3. List Employees (Search)
    if emp_id:
        try:
            # Search by name
            res = requests.get(f"{BASE_URL}/api/admin/employees?search=Test", headers=headers)
            if res.status_code == 200:
                data = res.json() # expect list inside 'data' or direct list?
                # admin_routes.py: return _ok([list]) -> {success: true, data: [list]}
                
                rows = data.get("data", [])
                log(f"Search Rows found: {[r.get('id') for r in rows]}")
                found = any(str(r.get("id")) == str(emp_id) for r in rows)
                if found:
                    log("Search by Name found the employee")
                else:
                    log(f"Search by Name failed to find employee. Rows: {len(rows)}", False)
            else:
                log(f"Search failed: {res.status_code}", False)

            # Search by code
            # We don't have code in variable unless we parsed it. Assuming we did.
        except Exception as e:
            log(f"Search error: {e}", False)
            
    # 4. Delete Employee
    if emp_id:
        try:
            res = requests.delete(f"{BASE_URL}/api/admin/employees/{emp_id}", headers=headers)
            if res.status_code == 200:
                log("Delete Employee successful")
            else:
                 log(f"Delete Employee failed: {res.status_code} {res.text}", False)
        except Exception as e:
            log(f"Delete error: {e}", False)

if __name__ == "__main__":
    run_tests()
