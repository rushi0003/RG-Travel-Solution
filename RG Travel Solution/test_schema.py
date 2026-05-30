#!/usr/bin/env python3
import sqlite3

db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get schema for drivers table
cur.execute("PRAGMA table_info(drivers)")
columns = cur.fetchall()
print("drivers table columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
