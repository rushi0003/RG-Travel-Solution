import sqlite3

def check():
    conn = sqlite3.connect('rg_travel.db')
    cur = conn.cursor()
    
    # Check Table
    print("--- Table: trip_routes ---")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trip_routes'")
    print(cur.fetchone())
    
    # Check Partial Indexes
    print("\n--- Partial Indexes ---")
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql LIKE '%WHERE status%'")
    for row in cur.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check()
