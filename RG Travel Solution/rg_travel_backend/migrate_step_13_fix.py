import sqlite3
import os

DB_PATH = "rg_travel.db"

def migrate_fix():
    print(f"Starting migration FIX for Step 13 on {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        print("Applying schema fix updates...")
        with open("db/schema_update_step_13_fix.sql", "r") as f:
            sql_script = f.read()
            cur.executescript(sql_script)
            print("Schema fixes applied successfully.")
        conn.commit()
    except Exception as e:
        print(f"Error applying schema fixes: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_fix()
