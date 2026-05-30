import sqlite3
import os

db_path = os.path.join("rg_travel_backend", "rg_travel.db")
if not os.path.exists(db_path):
    db_path = "rg_travel.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    # Check if column exists first
    cur.execute("PRAGMA table_info(trips)")
    cols = [c[1] for c in cur.fetchall()]
    
    if "vehicle_no" not in cols:
        print("Adding vehicle_no to trips...")
        cur.execute("ALTER TABLE trips ADD COLUMN vehicle_no TEXT")
        conn.commit()
        print("Added vehicle_no column.")
    else:
        print("vehicle_no already exists in trips.")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
