import sqlite3
import os

db_path = os.path.join("rg_travel_backend", "rg_travel.db")
if not os.path.exists(db_path):
    # Try current directory
    db_path = "rg_travel.db"

output_file = "db_schema.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(db_path):
        f.write(f"Inspecting DB at {db_path}\n")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            f.write("\n--- swap_requests columns ---\n")
            try:
                cur.execute("PRAGMA table_info(swap_requests)")
                cols = cur.fetchall()
                if not cols:
                    f.write("Table 'swap_requests' does not exist.\n")
                else:
                    for col in cols: # (cid, name, type, notnull, dflt_value, pk)
                        f.write(f"{col}\n")
            except Exception as e:
                f.write(f"Error reading table info: {e}\n")
            
            f.write("\n--- drivers columns ---\n")
            try:
                cur.execute("PRAGMA table_info(drivers)")
                cols = cur.fetchall()
                for col in cols: # (cid, name, type, notnull, dflt_value, pk)
                    f.write(f"{col}\n")
            except Exception as e:
                f.write(f"Error reading drivers table: {e}\n")

            conn.close()
        except Exception as e:
            f.write(f"Connection error: {e}\n")
    else:
        f.write(f"Could not find rg_travel.db at {db_path}\n")
