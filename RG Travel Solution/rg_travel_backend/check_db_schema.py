import sqlite3
import os

db_path = r"c:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\rg_travel.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Schema for drivers:")
cursor.execute("PRAGMA table_info(drivers)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nSchema for groups:")
cursor.execute("PRAGMA table_info(groups)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

conn.close()
