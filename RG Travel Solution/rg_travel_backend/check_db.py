
import sqlite3
import os

DB_PATH = "rg_travel.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT sql FROM sqlite_master WHERE name='trips'")
        row = cur.fetchone()
        if row:
            print("\nTrips Table SQL:")
            print(row[0])
        else:
            print("Trips table not found.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
