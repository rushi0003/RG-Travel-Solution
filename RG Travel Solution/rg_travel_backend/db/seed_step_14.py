import sqlite3
import random
import uuid
from datetime import datetime

DB_PATH = "rg_travel.db"

def get_db():
    return sqlite3.connect(DB_PATH)

def clear_data(conn):
    print("Clearing old test data...")
    cur = conn.cursor()
    tables = [
        "trip_group_members", "trip_groups", "trip_routes", "trips", 
        "cabs", "drivers", "employees", "otp_store"
    ]
    for t in tables:
        try:
            cur.execute(f"DELETE FROM {t}")
            cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")
        except:
            pass
    conn.commit()

def create_admin(conn):
    # Ensure at least one admin exists
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO admins (id, name, mobile, password_salt, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("admin_001", "Super Admin", "9999999999", "salt", "hash", datetime.now(), datetime.now()))
    conn.commit()

def seed_cabs_and_drivers(conn):
    print("Seeding Cabs & Drivers...")
    cur = conn.cursor()
    
    # 1. 5x 6-Seaters
    for i in range(1, 6):
        reg = f"MH12-SIX-{i:02d}"
        cur.execute("INSERT INTO cabs (reg_no, model, capacity, status) VALUES (?, 'Toyota Innova', 6, 'active')", (reg,))
        cab_id = cur.lastrowid
        
        # Driver
        drv_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, is_approved, password_hash, password_salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'hash', 'salt', ?, ?)
        """, (drv_id, f"Driver 6S-{i}", f"98765000{i:02d}", f"DL-6S-{i:02d}", reg, "6", datetime.now(), datetime.now()))

    # 2. 10x 4-Seaters
    for i in range(1, 11):
        reg = f"MH12-FOUR-{i:02d}"
        cur.execute("INSERT INTO cabs (reg_no, model, capacity, status) VALUES (?, 'Maruti Dzire', 4, 'active')", (reg,))
        cab_id = cur.lastrowid
        
        # Driver
        drv_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, is_approved, password_hash, password_salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'hash', 'salt', ?, ?)
        """, (drv_id, f"Driver 4S-{i}", f"91234000{i:02d}", f"DL-4S-{i:02d}", reg, "4", datetime.now(), datetime.now()))
    
    conn.commit()

def seed_employees(conn):
    print("Seeding Employees...")
    cur = conn.cursor()
    
    # Create 30 employees in a specific "Cluster" (e.g., Andheri)
    base_lat = 19.1136
    base_lng = 72.8697
    
    for i in range(1, 31):
        # Slightly vary location to simulate a cluster
        lat = base_lat + random.uniform(-0.01, 0.01)
        lng = base_lng + random.uniform(-0.01, 0.01)
        
        cur.execute("""
            INSERT INTO employees (name, mobile, email, login_time, logout_time, home_lat, home_lng, home_address, is_active, is_approved)
            VALUES (?, ?, ?, '09:00', '18:00', ?, ?, 'Andheri Cluster Area', 1, 1)
        """, (f"Employee {i}", f"90000000{i:02d}", f"emp{i}@test.com", lat, lng))
        
    conn.commit()

def run_seed():
    conn = get_db()
    clear_data(conn)
    create_admin(conn)
    seed_cabs_and_drivers(conn)
    seed_employees(conn)
    conn.close()
    print("Seed Step 14 Completed Successfully!")

if __name__ == "__main__":
    run_seed()
