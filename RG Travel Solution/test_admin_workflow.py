
import requests  # pyre-ignore[21]  # type: ignore[import]
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def get_admin_headers():
    # Assuming no auth or simple mock auth for now, or we can login if needed.
    # In this dev env, we might be able to skip auth or use a test token.
    # Let's try to grab a token first, or just proceed if endpoints are open/mocked.
    # Based on previous steps, we might need a token.
    # Let's try to login as admin first.
    try:
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "id": "admin", # Simple login if enabled, or mobile/password
            "mobile": "9999999999", # Seeded admin
            "password": "admin"     # Seeded password
        })
        if res.status_code == 200:
            token = res.json().get("token")
            return {"Authorization": f"Bearer {token}"}
    except:
        pass
    return {} # Fallback

def run_test():
    print("🚀 Starting Admin Workflow Verification...")
    
    headers = get_admin_headers()
    print(f"🔑 Auth Headers: {headers}")

    # 1. Verify Absence Requests
    print("\n--- 1. Testing Absence Requests ---")
    res = requests.get(f"{BASE_URL}/api/admin/absence-requests", headers=headers)
    if res.status_code == 200:
        requests_list = res.json().get("data", [])
        print(f"✅ Fetched {len(requests_list)} absence requests.")
        
        if requests_list:
            target_id = requests_list[0]["id"]
            print(f"👉 Attempting to APPROVE absence request #{target_id}...")
            res_app = requests.post(f"{BASE_URL}/api/admin/absence-requests/{target_id}/approve", headers=headers)
            if res_app.status_code == 200:
                print(f"✅ Approved absence request #{target_id}.")
            else:
                print(f"❌ Failed to approve: {res_app.text}")
        else:
            print("⚠️ No absence requests to test approval.")
    else:
        print(f"❌ Failed to fetch absence requests: {res.text}")

    # 2. Verify Driver/Hometown Requests
    # Note: Endpoint assumption based on AdminService.dart analysis
    # getDriverChangeRequests -> /api/admin/driver-change-requests or similar?
    # Actually AdminService.dart uses: /api/admin/driver-requests (approvals?)
    # Let's check AdminService.dart again or just try probable paths.
    # AdminService.dart line 333: _getJson("/api/admin/driver-requests")
    # AdminService.dart line 44 (getDriverChangeRequests) -> ??? 
    # I'll stick to what I saw in AdminRequestsScreen: AdminService.getDriverChangeRequests()
    # Let's assume the path is /api/admin/driver-requests for now as per dashboard.
    
    print("\n--- 2. Testing Driver Requests ---")
    res = requests.get(f"{BASE_URL}/api/admin/driver-requests", headers=headers)
    if res.status_code == 200:
        requests_list = res.json().get("data", [])
        print(f"✅ Fetched {len(requests_list)} driver requests.")
        
        if requests_list:
            target_id = requests_list[0]["id"]
            print(f"👉 Attempting to REJECT driver request #{target_id}...")
            res_rej = requests.post(f"{BASE_URL}/api/admin/driver-requests/{target_id}/reject", headers=headers)
            if res_rej.status_code == 200:
                print(f"✅ Rejected driver request #{target_id}.")
            else:
                print(f"❌ Failed to reject: {res_rej.text}")
        else:
            print("⚠️ No driver requests to test rejection.")
    else:
        print(f"❌ Failed to fetch driver requests: {res.text}")

    # 3. Verify SOS Alerts
    print("\n--- 3. Testing SOS Alerts ---")
    res = requests.get(f"{BASE_URL}/api/admin/sos-alerts", headers=headers)
    if res.status_code == 200:
        sos_list = res.json().get("data", [])
        print(f"✅ Fetched {len(sos_list)} active SOS alerts.")
        
        if sos_list:
            target_id = sos_list[0]["id"]
            print(f"👉 Attempting to RESOLVE SOS alert #{target_id}...")
            res_sol = requests.post(f"{BASE_URL}/api/admin/sos-alerts/{target_id}/resolve", 
                                    json={"note": "Verified via script"}, headers=headers)
            if res_sol.status_code == 200:
                print(f"✅ Resolved SOS alert #{target_id}.")
            else:
                print(f"❌ Failed to resolve: {res_sol.text}")
        else:
             print("⚠️ No active SOS alerts to resolve.")
    else:
        print(f"❌ Failed to fetch SOS alerts: {res.text}")

    print("\n🎉 Admin Workflow Verification Complete.")

if __name__ == "__main__":
    run_test()
