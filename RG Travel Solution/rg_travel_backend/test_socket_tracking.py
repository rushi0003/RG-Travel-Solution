
import socketio
import requests
import time
import json
import uuid

# Configuration
BASE_URL = "http://127.0.0.1:5000"
SOCKET_URL = "http://127.0.0.1:5000"

# Test Data
driver_id = f"drv_{uuid.uuid4().hex[:6]}"
try:
    # Use an existing route from DB if possible, or a dummy one
    # Note: Authentication is required for the API, we need a token.
    # For this test, we might mock it or need a valid driver login.
    # Let's try to login as a driver first to get a token.
    # If no driver exists, we might need to register one or use a known one.
    # For simplicity, let's assume we can hit the endpoint if we have a token.
    pass
except Exception:
    pass

# 2. Initialize SocketIO Client
# Enable logger to see transport details
sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("✅ [SocketIO] Connected!")

@sio.event
def connect_error(data):
    print(f"❌ [SocketIO] Connection failed: {data}")

@sio.event
def disconnect():
    print("⚠️ [SocketIO] Disconnected")

@sio.on('driver_location_update')
def on_location_update(data):
    print(f"📍 [SocketIO] Recieved Location Update: {data}")

def test_live_tracking():
    print("--- Starting Live Tracking Test ---")
    
    connected = False
    
    # Define an event handler for broadcast location
    location_received = {"received": False, "data": None}
    
    @sio.on('driver_location_update')
    def on_location_update(data):
        print(f"📡 WebSocket Received Location Update: {data}")
        location_received["received"] = True
        location_received["data"] = data

    @sio.on('tracking_error')
    def on_error(data):
        print(f"❌ WebSocket Error: {data}")

    # 1. Connect to SocketIO
    try:
        # Use auth header for handshake if supported, or just connect and rely on join_route payload
        sio.connect(BASE_URL, headers={"Authorization": f"Bearer {token}"})
        connected = True
        print("✅ Socket Connected")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Failed to connect to server (SocketIO): {e}")
        print("⚠️ Proceeding to API test without SocketIO connection...")

    # ... (Register Driver & Create Trip happened above) ...
    # Wait! Route No is dynamic now. We need to create the trip FIRST before joining the room.
    # Moving Socket Join to AFTER trip creation logic.

    # 3. Register and Login a Test Driver
    print("👉 Setting up Test Driver and Active Trip...")
    import time
    timestamp_suffix = str(int(time.time() * 1000))[-6:] # Last 6 digits of timestamp
    
    import random
    random_suffix_digits = str(random.randint(1000, 9999))
    driver_mobile = f"900000{random_suffix_digits}" # 10 digits
    driver_pass = "password123"
    driver_name = f"Test Driver {timestamp_suffix}"
    
    test_driver_id = f"drv_{timestamp_suffix}"
    route_no = f"TEST_ROUTE_{timestamp_suffix}"
    
    # 3a. Register via API (using the password-based endpoint in app.py if available, or auth_bp)
    # create_app registers auth_bp at /api/auth
    # app.py has /api/driver/login
    # But registration? app.py commented out registration.
    # auth_routes.py has /api/auth/driver/signup-request
    
    # Let's insert directly into DB to avoid approval workflow complexity in test
    import sqlite3
    import os
    from utils.security import hash_password 
    # Use direct DB insertion for test setup
    try:
        conn = sqlite3.connect("rg_travel.db")
        cur = conn.cursor()
        
        # Create Driver
        salt, p_hash = hash_password(driver_pass)
        test_driver_id = f"drv_{timestamp_suffix}"
        cur.execute(
            """
            INSERT INTO drivers (id, name, mobile, vehicle_no, dl_no, is_approved, password_salt, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (test_driver_id, driver_name, driver_mobile, f"KA01{timestamp_suffix}", f"DL{timestamp_suffix}", salt, p_hash, "2024-01-01", "2024-01-01")
        )
        
        # Create Active Trip for this driver (Required for Step 3 API Validation)
        # Schema requires: route_no, trip_day, operation, trip_type, schedule_time, created_at, updated_at
        cur.execute(
            """
            INSERT INTO trips (route_no, driver_id, status, trip_day, operation, trip_type, schedule_time, created_at, updated_at)
            VALUES (?, ?, 'started', '20240218', 'pickup', 'pickup', '09:00', ?, ?)
            """,
            (route_no, test_driver_id, "2024-02-18T09:00:00Z", "2024-02-18T09:00:00Z")
        )
        
        conn.commit()
        conn.close()
        print(f"✅ Test Driver Account & Active Trip Created: {driver_mobile} / {route_no}")
    except Exception as e:
        print(f"❌ DB Setup Failed: {e}")
        import traceback
        traceback.print_exc()
        sio.disconnect()
        return

    # 3b. Login
    print("👉 Logging in...")
    login_resp = requests.post(f"{BASE_URL}/api/driver/login", json={"mobile": driver_mobile, "password": driver_pass})

    if login_resp.status_code == 200:
        token = login_resp.json()['data']['token']
        driver_id = login_resp.json()['data']['profile']['id']
        print(f"✅ Login successful. Token obtained.")
        
        # NOW Join the socket room with the valid token and dynamic route_no
        if connected:
            print(f"👉 Joining room: route:{route_no}")
            # Step 4: Validate Auth & Room Join
            # Admin can join any, but we are logged in as Driver. 
            # Our updated socket_service allows assigned driver to join.
            # Real Admin would use Admin Token.
            sio.emit("join_route", {"routeNo": route_no, "token": token})
            time.sleep(1)
            
    else:
        print(f"❌ Login failed: {login_resp.text}")
        if connected: sio.disconnect()
        return

    # 4. Send Location Update
    print(f"👉 Sending location update for driver {driver_id} on route {route_no}...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "routeNo": route_no,
        "lat": 12.9716,
        "lng": 77.5946,
        "speed": 40.5,
        "heading": 90.0,
        "deviceTime": "2024-02-18T10:00:00Z"
        # driverId is NOT sent in payload anymore (extracted from token)
        # But wait, did I remove it from payload in logic?
        # My secure API logic EXTRACTS it from token. Payload can have it but it's ignored or checked.
        # Let's NOT send it to prove we don't need it.
    }
    
    resp = requests.post(f"{BASE_URL}/api/driver/location", json=payload, headers=headers)
    print(f"API Response: {resp.status_code} - {resp.text}")

    if resp.status_code == 200:
        print("✅ Location Update API Success!")
        # Validate Response Format
        data = resp.json()
        if data.get("success") and "serverTime" in data:
             print("✅ Response Format Verified.")
             
             # Step 4 Verification: Did we receive the socket event?
             time.sleep(2) # Wait a bit for async broadcast
             if location_received["received"]:
                 print(f"✅ Broadcast Verified: Received {location_received['data']['lat']},{location_received['data']['lng']} on channel")
             else:
                 print("❌ Broadcast NOT Received (Socket logic failed or client not in room)")
             
        else:
             print("❌ Unexpected Response Format.")
    else:
        print(f"❌ API Failed: {resp.text}")

    # 5. Verify Database State
    import sqlite3
    conn = sqlite3.connect("rg_travel.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM driver_live_locations WHERE driver_id = ? AND route_no = ?", (driver_id, route_no))
    row = cur.fetchone()
    if row:
        print(f"✅ DB Update Verified: {row}")
    else:
        print("❌ DB Update Failed: Row not found")
    conn.close()

    sio.disconnect()
    print("--- Test Finished ---")

if __name__ == "__main__":
    test_live_tracking()
