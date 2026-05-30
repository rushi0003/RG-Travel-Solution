import requests  # pyre-ignore[21]

BASE_URL = "http://127.0.0.1:5000"


def _pick_slot_with_employees(trip_type: str = "pickup") -> str:
    slots_resp = requests.get(
        f"{BASE_URL}/api/admin/time-slots",
        params={"trip_type": trip_type},
        timeout=20,
    )
    if slots_resp.status_code != 200:
        raise RuntimeError(f"time-slots failed: {slots_resp.text}")

    slots = (slots_resp.json().get("data") or {}).get("slots") or []
    if not slots:
        raise RuntimeError("No time slots available.")

    for slot in slots:
        emp_resp = requests.get(
            f"{BASE_URL}/api/admin/available-employees",
            params={"trip_type": trip_type, "time_slot": slot},
            timeout=20,
        )
        if emp_resp.status_code != 200:
            continue
        employees = (emp_resp.json().get("data") or {}).get("employees") or []
        if employees:
            return str(slot)

    raise RuntimeError(f"No slot has eligible employees for trip_type={trip_type}.")


def test_visibility_data():
    print("Testing Step 13: Live Visibility Data...")
    selected_trip_type = None
    selected_time = None
    for trip_type in ("pickup", "drop"):
        try:
            selected_time = _pick_slot_with_employees(trip_type)
            selected_trip_type = trip_type
            break
        except Exception:
            continue
    if not selected_trip_type or not selected_time:
        raise RuntimeError("No slot has eligible employees.")
    trip_type = str(selected_trip_type)
    print(f"Using slot: {selected_time}")
    print(f"Using trip_type: {trip_type}")

    # 1. Setup data using a slot that has eligible employees
    preview_payload = {
        "admin_id": "admin_main",
        "trip_type": trip_type,
        "selected_time": selected_time,
        "vehicle_types": [4, 6],
        "office_lat": 19.0760,
        "office_lng": 72.8777
    }
    
    resp = requests.post(f"{BASE_URL}/api/v2/trips/preview", json=preview_payload, timeout=30)
    if resp.status_code != 200:
        print(f"Preview failed: {resp.text}")
        return
    
    preview_data = resp.json()["data"]
    groups = preview_data["groups"]
    if not groups:
        print("No groups generated for testing.")
        return
    
    # 2. Create Trip
    create_payload = {
        "admin_id": "admin_main",
        "preview_data": preview_data,
        "groups_to_create": [groups[0]]
    }
    
    resp = requests.post(f"{BASE_URL}/api/v2/trips/create", json=create_payload, timeout=30)
    if resp.status_code != 201:
        print(f"Create failed (might already exist): {resp.text}")
        # Try to find an existing trip
        active_resp = requests.get(f"{BASE_URL}/api/v2/trips/active", timeout=20)
        trips = active_resp.json().get("data", {}).get("trips", [])
        if not trips:
             print("No active trips found to verify.")
             return
        trip_id = trips[0]["trip_id"]
        print(f"Using existing Trip ID: {trip_id}")
    else:
        trip_id = resp.json()["data"]["trips_created"][0]["trip_id"]
        print(f"Created new Trip ID: {trip_id}")

    # 3. Verify Trip Details (Enhanced Step 13)
    resp = requests.get(f"{BASE_URL}/api/v2/trips/{trip_id}", timeout=20)
    if resp.status_code != 200:
        print(f"Fetch trip failed: {resp.text}")
        return
    
    data = resp.json()["data"]
    
    # Check Office Coordinates
    office = data.get("office_location")
    if office and office.get("lat") == 19.076:
        print("Office coordinates present and correct.")
    else:
        print(f"Office coordinates missing or incorrect: {office}")

    # Check Employee Coordinates
    employees = data.get("employees", [])
    if employees and "pickup_lat" in employees[0]:
        print(f"Employee stop coordinates present (First: {employees[0]['pickup_lat']},{employees[0]['pickup_lng']}).")
    else:
        print("Employee stop coordinates missing.")

    print("\nStep 13 Visibility Verification Complete.")

if __name__ == "__main__":
    # Ensure server is running before running this test
    try:
        test_visibility_data()
    except Exception as e:
        print(f"Error during test: {e}")
