
import sqlite3
import os

DB_PATH = 'rg_travel.db'

def inspect_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("--- Table: trip_employees ---")
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='trip_employees'")
    row = cur.fetchone()
    if row:
        print(row[0])
    else:
        print("Table trip_employees not found")

    print("\n--- Triggers on trip_employees ---")
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='trip_employees'")
    triggers = cur.fetchall()
    if triggers:
        for name, sql in triggers:
            print(f"Trigger: {name}")
            print(sql)
            print("-" * 20)
    else:
        print("No triggers found on trip_employees")

    print("\n--- Table: trips ---")
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='trips'")
    row = cur.fetchone()
    if row:
        print(row[0])


    conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Database file {DB_PATH} not found.")
    else:
        inspect_schema()
