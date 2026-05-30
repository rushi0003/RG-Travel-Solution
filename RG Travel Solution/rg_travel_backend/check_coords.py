
import sqlite3

def check_coords():
    conn = sqlite3.connect('rg_travel.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT id, name, home_lat, home_lng, pickup_lat, pickup_lng FROM employees LIMIT 10")
    rows = cur.fetchall()
    print("--- EMPLOYEE COORDINATES ---")
    for r in rows:
        print(dict(r))
    conn.close()

if __name__ == "__main__":
    check_coords()
