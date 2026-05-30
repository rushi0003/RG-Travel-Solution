
"""
Migration: Add SOS and Ratings tables
"""
import sys
import os
import sqlite3

# Add parent dir to path to find db module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import get_db

def migrate():
    print("Migrating: Adding SOS and Ratings tables...")
    conn = get_db()
    try:
        # We can just execute the CREATE TABLE IF NOT EXISTS statements
        # Copied from schema.sql
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sos_alerts (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          trip_id      INTEGER,
          employee_id  TEXT NOT NULL,
          lat          REAL,
          lng          REAL,
          
          resolved     INTEGER DEFAULT 0,
          resolved_by  TEXT,
          resolved_at  TEXT,
          
          created_at   TEXT NOT NULL,
          
          FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE SET NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
          FOREIGN KEY(resolved_by) REFERENCES admins(id) ON DELETE SET NULL
        );
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sos_trip ON sos_alerts(trip_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sos_resolved ON sos_alerts(resolved);")
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS trip_ratings (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          trip_id      INTEGER NOT NULL,
          employee_id  TEXT NOT NULL,
          
          rating       INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
          feedback     TEXT,
          
          created_at   TEXT NOT NULL,
          
          FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """)
        
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_rating ON trip_ratings(trip_id, employee_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rating_trip ON trip_ratings(trip_id);")
        
        conn.commit()
        print("Migration successful.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
