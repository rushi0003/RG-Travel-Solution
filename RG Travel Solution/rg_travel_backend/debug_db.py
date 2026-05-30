import sqlite3
import os

DB_PATH = 'rg_travel.db'
OUTPUT_FILE = 'db_dump_utf8.txt'

def run_query_to_file(f, query):
    f.write(f"--- Running: {query} ---\n")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        if not rows:
            f.write("No results.\n")
            if cur.description:
                 f.write(str([d[0] for d in cur.description]) + "\n")
            return

        # Print column names
        if cur.description:
            f.write(str([d[0] for d in cur.description]) + "\n")
        
        for row in rows:
            f.write(str(dict(row)) + "\n")
        conn.close()
    except Exception as e:
        f.write(f"Error: {e}\n")

print(f"Checking database at: {os.path.abspath(DB_PATH)}")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(f"Checking database at: {os.path.abspath(DB_PATH)}\n")
    
    f.write("\n=== Table Info: driver_requests ===\n")
    run_query_to_file(f, "PRAGMA table_info(driver_requests)")

    f.write("\n=== Table Info: employee_requests ===\n")
    run_query_to_file(f, "PRAGMA table_info(employee_requests)")

    f.write("\n=== Table Info: employee_change_requests ===\n")
    run_query_to_file(f, "PRAGMA table_info(employee_change_requests)")

    f.write("\n=== Content: driver_requests (first 3) ===\n")
    run_query_to_file(f, "SELECT * FROM driver_requests LIMIT 3")

    f.write("\n=== Content: employee_requests (first 3) ===\n")
    run_query_to_file(f, "SELECT * FROM employee_requests LIMIT 3")

    f.write("\n=== Content: employee_change_requests (first 3) ===\n")
    run_query_to_file(f, "SELECT * FROM employee_change_requests LIMIT 3")

print(f"Done. Output written to {OUTPUT_FILE}")
