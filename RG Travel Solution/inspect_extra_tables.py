import sqlite3
import os

db_path = os.path.join("rg_travel_backend", "rg_travel.db")
if not os.path.exists(db_path):
    db_path = "rg_travel.db"

output_file = "db_schema_extra.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        tables = ["driver_vehicle_swap_requests", "swap_requests"]
        for t in tables:
            f.write(f"\n--- {t} columns ---\n")
            try:
                cur.execute(f"PRAGMA table_info({t})")
                cols = cur.fetchall()
                if not cols:
                    f.write(f"Table '{t}' does not exist.\n")
                else:
                    for col in cols:
                        f.write(f"{col}\n")
            except Exception as e:
                f.write(f"Error: {e}\n")
        conn.close()
