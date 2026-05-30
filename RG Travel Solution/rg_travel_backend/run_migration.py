import sqlite3
import os

DB_PATH = 'rg_travel.db'
SQL_FILE = 'create_change_request_tables.sql'

def execute_sql_file():
    print(f"Connecting to database at: {os.path.abspath(DB_PATH)}")
    try:
        conn = sqlite3.connect(DB_PATH)
        with open(SQL_FILE, 'r') as f:
            sql_script = f.read()
        
        print(f"Executing SQL from {SQL_FILE}...")
        conn.executescript(sql_script)
        conn.commit()
        print("SQL executed successfully.")
        
        # Verify table creation
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(employee_change_requests)")
        rows = cur.fetchall()
        if rows:
             print("Verification: 'employee_change_requests' table exists.")
             print([r[1] for r in rows]) # Print column names
        else:
             print("Verification FAILED: 'employee_change_requests' table NOT found.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if not os.path.exists(SQL_FILE):
        print(f"Error: SQL file '{SQL_FILE}' not found.")
    else:
        execute_sql_file()
