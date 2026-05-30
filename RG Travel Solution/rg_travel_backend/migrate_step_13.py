import sqlite3
import os
from datetime import datetime

DB_PATH = "rg_travel.db"

def migrate():
    print(f"Starting migration for Step 13 on {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Run Schema Update SQL
    print("Applying schema updates...")
    with open("db/schema_update_step_13.sql", "r") as f:
        sql_script = f.read()
        cur.executescript(sql_script)
    
    # 2. Add 'cab_id' to trips if missing
    print("Checking 'cab_id' column in trips...")
    cur.execute("PRAGMA table_info(trips)")
    columns = [col[1] for col in cur.fetchall()]
    if "cab_id" not in columns:
        print("Adding 'cab_id' column to trips table...")
        cur.execute("ALTER TABLE trips ADD COLUMN cab_id INTEGER REFERENCES cabs(id) ON DELETE SET NULL")
    else:
        print("'cab_id' column already exists.")

    conn.commit()

    # 3. Data Migration: Extract Cabs from Drivers
    print("Migrating Driver Vehicles to Cabs table...")
    
    # Get all drivers with vehicle info
    cur.execute("SELECT id, vehicle_no, vehicle_type FROM drivers WHERE vehicle_no IS NOT NULL AND vehicle_no != ''")
    drivers = cur.fetchall()
    
    for drv in drivers:
        drv_id, reg_no, v_type = drv
        reg_no = reg_no.strip().upper()
        
        # Determine capacity from vehicle_type (default 4)
        try:
            capacity = int(v_type) if v_type and v_type.isdigit() else 4
        except:
            capacity = 4

        # Insert into cabs if not exists
        try:
            # Check if exists
            cur.execute("SELECT id FROM cabs WHERE reg_no = ?", (reg_no,))
            row = cur.fetchone()
            
            if row:
                cab_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO cabs (reg_no, capacity, status) VALUES (?, ?, 'active')",
                    (reg_no, capacity)
                )
                cab_id = cur.lastrowid
                print(f"Created Cab: {reg_no} (ID: {cab_id})")
            
            # Backfill trip history: Update trips for this driver to use this cab_id
            # ONLY for trips where vehicle details match (simplified assumption: driver uses same car)
            cur.execute(
                "UPDATE trips SET cab_id = ? WHERE driver_id = ? AND cab_id IS NULL",
                (cab_id, drv_id)
            )

        except Exception as e:
            print(f"Error processing driver {drv_id} vehicle {reg_no}: {e}")

    conn.commit()
    conn.close()
    print("Migration Step 13 Completed Successfully.")

if __name__ == "__main__":
    migrate()
