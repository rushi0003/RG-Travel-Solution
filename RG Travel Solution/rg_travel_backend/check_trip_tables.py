
import sqlite3

def check_trips_schema():
    conn = sqlite3.connect('rg_travel.db')
    cur = conn.cursor()
    
    for table in ['trips', 'trip_employees', 'trip_group_members']:
        print(f"\n--- {table} ---")
        cur.execute(f"PRAGMA table_info({table});")
        cols = cur.fetchall()
        for col in cols:
            print(col)
    
    conn.close()

if __name__ == "__main__":
    check_trips_schema()
