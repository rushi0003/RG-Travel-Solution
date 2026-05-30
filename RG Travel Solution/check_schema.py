#!/usr/bin/env python3
import sqlite3

db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print(f'All tables: {tables}')

# Check if driver_requests and employee_requests exist
for table_name in ['driver_requests', 'employee_requests', 'trips']:
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = cur.fetchall()
    if columns:
        print(f'\n{table_name} columns:')
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    else:
        print(f'\n{table_name} - TABLE DOES NOT EXIST')

conn.close()
