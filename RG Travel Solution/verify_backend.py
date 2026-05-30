import requests
import json

BASE_URL = "http://localhost:5000"

def test_login():
    try:
        # Try with admin123 (from fix_admin_login.py)
        pwd = "admin123"
        print(f"Testing login with password: {pwd}")
        
        resp = requests.post(f"{BASE_URL}/api/auth/admin/login", json={
            "name": "Rushi Gund", 
            "mobile": "9325118627",
            "password": pwd
        })
        
        print(f"Status: {resp.status_code}")
        try:
            data = resp.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
            
            if data.get("success") == True:
                print("\n✅ Login SUCCESS")
                if "admin" in data and "id" in data["admin"]:
                    print("✅ CONFIRMED: Response contains nested 'admin' object with 'id'")
                elif "adminId" in data:
                    print("⚠️ FOUND: 'adminId' at root level")
                elif "admin_id" in data:
                    print("⚠️ FOUND: 'admin_id' at root level")
                else:
                    print("❌ UNKNOWN FORMAT: ID not found in expected keys")
            else:
                print("\n❌ Login FAILED (Backend returned success=false)")
                
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(resp.text)
            
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Backend might not be running.")

if __name__ == "__main__":
    test_login()
