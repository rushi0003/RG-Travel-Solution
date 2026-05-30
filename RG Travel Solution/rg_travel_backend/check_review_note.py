import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "rg_travel.db")

def check_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(driver_requests)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns in driver_requests: {columns}")
    if 'review_note' in columns:
        print("✅ review_note column exists.")
    else:
        print("❌ review_note column MISSING.")
    conn.close()

if __name__ == "__main__":
    check_schema()
