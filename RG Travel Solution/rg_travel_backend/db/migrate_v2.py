#!/usr/bin/env python3
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'rg_travel.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("Running migration: Creating employee_trip_requests table...")

cur.execute("""
CREATE TABLE IF NOT EXISTS employee_trip_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    request_type TEXT NOT NULL, -- 'no_trip', 'extra_trip'
    request_date TEXT NOT NULL, -- YYYY-MM-DD
    status TEXT DEFAULT 'pending',
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")

# Also check for driver_hometown_requests if it needs any updates or just ensure it exists
cur.execute("""
CREATE TABLE IF NOT EXISTS driver_hometown_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id TEXT NOT NULL,
    requested_home_town TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
conn.close()
print("Migration completed successfully.")
