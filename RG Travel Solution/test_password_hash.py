#!/usr/bin/env python3
import sqlite3
import hashlib
import secrets

# Connect to database
db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the admin record
cursor.execute("SELECT id, password_salt, password_hash FROM admins WHERE id='admin_rg_001'")
row = cursor.fetchone()

if row:
    admin_id, stored_salt, stored_hash = row
    print(f"Admin ID: {admin_id}")
    print(f"Stored Salt: {stored_salt}")
    print(f"Stored Hash: {stored_hash}")
    
    # Test password
    password = "admin123"
    calc_hash = hashlib.sha256((stored_salt + password).encode("utf-8")).hexdigest()
    print(f"\nPassword: {password}")
    print(f"Calculated Hash: {calc_hash}")
    print(f"Match: {calc_hash == stored_hash}")
else:
    print("Admin not found!")

conn.close()
