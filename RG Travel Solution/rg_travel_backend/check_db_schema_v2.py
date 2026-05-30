
import sqlite3

def list_tables():
    conn = sqlite3.connect('rg_travel.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    print("Tables in database:", tables)
    
    for table in tables:
        print(f"\n--- {table} ---")
        cur.execute(f"PRAGMA table_info({table});")
        cols = cur.fetchall()
        for col in cols:
            print(col)
    
    conn.close()

if __name__ == "__main__":
    list_tables()
