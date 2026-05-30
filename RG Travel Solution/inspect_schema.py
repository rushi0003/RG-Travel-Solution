#!/usr/bin/env python3
import sqlite3

# Connect to database
db = sqlite3.connect('rg_travel_backend/rg_travel.db')
cursor = db.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 80)
print("DATABASE SCHEMA INSPECTION")
print("=" * 80)

for table_name in tables:
    table = table_name[0]
    print(f"\nTable: {table}")
    print("-" * 40)
    
    # Get table info
    cursor.execute(f"PRAGMA table_info({table});")
    columns = cursor.fetchall()
    
    for col in columns:
        cid, name, dtype, notnull, default, pk = col
        print(f"  {name:30} {dtype:15} {'NOT NULL' if notnull else 'nullable':10} {'PRIMARY KEY' if pk else '':12}")

# Now specifically check driver_requests and employee_requests tables with sample data
print("\n" + "=" * 80)
print("SAMPLE DATA FROM KEY TABLES")
print("=" * 80)

for table_name in ['driver_hometown_requests', 'employee_requests', 'trips']:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"\n{table_name}: {count} rows")
        
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            row = cursor.fetchone()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for i, col in enumerate(columns):
                print(f"  {col[1]}: {row[i] if i < len(row) else 'NULL'}")
    except Exception as e:
        print(f"\nERROR querying {table_name}: {e}")

db.close()
