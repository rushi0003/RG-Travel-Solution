#!/usr/bin/env python3
import sqlite3

# Connect to database
db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check if admin exists
cursor.execute("SELECT * FROM admins WHERE mobile='9325118627'")
row = cursor.fetchone()

if row:
    print("✓ Admin found by mobile")
    for key in row.keys():
        print(f"  {key}: {row[key]}")
else:
    print("✗ Admin not found by mobile")
    
    # List all admins
    cursor.execute("SELECT id, name, mobile FROM admins")
    admins = cursor.fetchall()
    if admins:
        print("\nExisting admins:")
        for admin in admins:
            print(f"  {admin[0]}: {admin[1]} ({admin[2]})")
    else:
        print("\nNo admins found in database!")

conn.close()
