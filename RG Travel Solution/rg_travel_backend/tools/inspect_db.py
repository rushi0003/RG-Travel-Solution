
import sqlite3
import os

DB_PATH = "rg_travel.db"

def inspect():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        print("--- Table: employees ---")
        cur.execute("PRAGMA table_info(employees)")
        rows = cur.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    inspect()
