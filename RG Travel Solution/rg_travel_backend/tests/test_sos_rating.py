
import pytest
import sys
import os
import json
from datetime import datetime

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from db import get_db, init_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DATABASE"] = "test_sos_rating.db"
    
    # Init DB
    with app.app_context():
        init_db()
        
        # Seed Data
        conn = get_db()
        # Create Admin
        conn.execute("INSERT INTO admins (id, name, mobile, password_salt, password_hash, created_at, updated_at) VALUES ('adm1', 'Admin', '9999999999', 'salt', 'hash', ?, ?)", (datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        # Create Employee
        conn.execute("INSERT INTO employees (name, mobile, is_approved) VALUES ('Emp1', '8888888888', 1)")
        emp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Create Driver
        conn.execute("INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, is_approved, password_salt, password_hash, created_at, updated_at) VALUES ('drv1', 'Driver1', '7777777777', 'DL123', 'MH12AB1234', 1, 'salt', 'hash', ?, ?)", (datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        # Create Trip
        conn.execute("INSERT INTO trips (route_no, trip_day, operation, trip_type, schedule_time, status, driver_id, created_at, updated_at) VALUES ('R100', '20260204', 'pickup', 'pickup', '09:00', 'completed', 'drv1', ?, ?)", (datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        trip_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        conn.commit()
        conn.close()
        
    global EMPLOYEE_ID, TRIP_ID
    EMPLOYEE_ID = emp_id
    TRIP_ID = trip_id

    with app.test_client() as client:
        yield client
        
    # Cleanup
    if os.path.exists("test_sos_rating.db"):
        os.remove("test_sos_rating.db")

def test_sos_trigger(client):
    res = client.post("/api/employee/sos", json={
        "employee_id": EMPLOYEE_ID,
        "trip_id": TRIP_ID,
        "lat": 18.5204,
        "lng": 73.8567
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] == True
    assert "alert_id" in data["data"]
    print("SOS Triggered Successfully")

def test_rate_trip(client):
    res = client.post(f"/api/employee/trip/{TRIP_ID}/rate", json={
        "employee_id": EMPLOYEE_ID,
        "rating": 5,
        "feedback": "Great ride!"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] == True
    print("Rating Submitted Successfully")
    
    # Test Duplicate Rating
    res = client.post(f"/api/employee/trip/{TRIP_ID}/rate", json={
        "employee_id": EMPLOYEE_ID,
        "rating": 4
    })
    assert res.status_code == 409
    print("Duplicate Rating Blocked Correctly")
