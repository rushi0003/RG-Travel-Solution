import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rg_travel.db")

def create_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("Creating helpdesk_tickets table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS helpdesk_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_type TEXT NOT NULL CHECK(user_type IN ('driver', 'employee')),
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        priority TEXT DEFAULT 'normal',
        status TEXT DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'resolved', 'closed')),
        
        admin_notes TEXT,
        resolved_by TEXT,
        resolved_at TEXT,
        
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_helpdesk_user ON helpdesk_tickets(user_id, user_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_helpdesk_status ON helpdesk_tickets(status);")
    
    conn.commit()
    conn.close()
    print("Table created successfully.")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
    else:
        create_table()
