
import sqlite3
import datetime
from typing import List, Dict, Any

def get_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn

def setup_schema(conn):
    cur = conn.cursor()
    # Drivers table
    cur.execute("""
    CREATE TABLE drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        vehicle_no TEXT,
        vehicle_type TEXT,
        is_approved INTEGER,
        is_online INTEGER DEFAULT 0
    );
    """)
    # Trips table
    cur.execute("""
    CREATE TABLE trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_no TEXT,
        trip_day TEXT,
        schedule_time TEXT,
        status TEXT,
        driver_id INTEGER
    );
    """)
    conn.commit()

def seed_data(conn):
    cur = conn.cursor()
    # 1. Driver A: Approved, Free, 4-Seater
    cur.execute("INSERT INTO drivers (name, mobile, vehicle_no, vehicle_type, is_approved) VALUES ('Driver A', '100', 'CAB1', '4', 1)")
    # 2. Driver B: Approved, Busy (Active Trip), 6-Seater
    cur.execute("INSERT INTO drivers (name, mobile, vehicle_no, vehicle_type, is_approved) VALUES ('Driver B', '200', 'CAB2', '6', 1)")
    # 3. Driver C: Pending, Free
    cur.execute("INSERT INTO drivers (name, mobile, vehicle_no, vehicle_type, is_approved) VALUES ('Driver C', '300', 'CAB3', '4', 0)")
    # 4. Driver D: Approved, Trip Cancelled (Should be free), 4-Seater
    cur.execute("INSERT INTO drivers (name, mobile, vehicle_no, vehicle_type, is_approved) VALUES ('Driver D', '400', 'CAB4', '4', 1)")
    
    # Trips
    today = datetime.datetime.now().strftime("%Y%m%d")
    time_slot = "09:00"
    
    # Trip for Driver B (Busy)
    cur.execute("INSERT INTO trips (trip_day, schedule_time, status, driver_id) VALUES (?, ?, 'assigned', 2)", (today, time_slot))
    # Trip for Driver D (Cancelled)
    cur.execute("INSERT INTO trips (trip_day, schedule_time, status, driver_id) VALUES (?, ?, 'cancelled', 4)", (today, time_slot))
    
    conn.commit()
    return today, time_slot

def fetch_available_drivers(conn, trip_day, time_slot):
    cur = conn.cursor()
    busy_query = """
        SELECT driver_id 
        FROM trips 
        WHERE trip_day = ? 
          AND schedule_time = ? 
          AND status IN ('created', 'assigned', 'started', 'active')
    """
    
    query = f"""
        SELECT id, name, vehicle_type 
        FROM drivers
        WHERE is_approved = 1
          AND id NOT IN ({busy_query})
    """
    
    cur.execute(query, (trip_day, time_slot))
    return [dict(x) for x in cur.fetchall()]

def run_test():
    conn = get_db()
    setup_schema(conn)
    today, time_slot = seed_data(conn)
    
    print(f"Testing for Trip Day: {today}, Time: {time_slot}")
    
    available = fetch_available_drivers(conn, today, time_slot)
    
    print(f"Found {len(available)} available drivers:")
    for d in available:
        print(f" - {d['name']} (Type: {d['vehicle_type']})")
        
    # inventory
    cnt4 = sum(1 for d in available if str(d['vehicle_type']) == "4")
    cnt6 = sum(1 for d in available if str(d['vehicle_type']) == "6")
    
    print(f"Inventory: 4-Seater={cnt4}, 6-Seater={cnt6}")
    
    # Assertions
    # Driver A should be there
    names = [d['name'] for d in available]
    assert "Driver A" in names, "Driver A should be available (Free)"
    assert "Driver B" not in names, "Driver B should be busy (Assigned)"
    assert "Driver C" not in names, "Driver C should be hidden (Pending)"
    assert "Driver D" in names, "Driver D should be available (Cancelled trip)"
    
    # Inventory Check
    assert cnt4 == 2, "Should have 2 available 4-seaters (A and D)"
    assert cnt6 == 0, "Should have 0 available 6-seaters (B is busy)"
    
    print("\nVerification Successful!")

if __name__ == "__main__":
    run_test()
