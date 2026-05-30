#!/usr/bin/env python3
import sqlite3
import os

# Remove old database
db_path = 'rg_travel_backend/rg_travel.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted old database: {db_path}")

# Create new database
conn = sqlite3.connect(db_path)
conn.execute('PRAGMA foreign_keys = ON')

# Read and execute schema
with open('rg_travel_backend/db/schema.sql', 'r') as f:
    schema = f.read()
    
# Split by BEGIN/COMMIT and execute
try:
    conn.executescript(schema)
    conn.commit()
    print("✓ Database schema created successfully")
    
    # Verify employee_requests table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employee_requests'")
    if cursor.fetchone():
        print("✓ employee_requests table created successfully")
    else:
        print("✗ ERROR: employee_requests table not created")
        
    conn.close()
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
