
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "rg_travel.db")

def migrate_db():
    print("--- Migrating DB for Live Tracking ---")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create driver_live_locations table
    print("Creating table: driver_live_locations...")
    # Drop first to ensure schema update (for development)
    cur.execute("DROP TABLE IF EXISTS driver_live_locations")
    
    cur.execute("""
    CREATE TABLE driver_live_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id TEXT NOT NULL,
        route_no TEXT NOT NULL,
        trip_id INTEGER,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        speed REAL,
        heading REAL,
        accuracy REAL,
        device_time TEXT,
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(driver_id) REFERENCES drivers(id),
        FOREIGN KEY(trip_id) REFERENCES trips(id),
        UNIQUE(driver_id, route_no)
    );
    """)
    
    print("Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_live_route ON driver_live_locations(route_no);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_live_driver ON driver_live_locations(driver_id);")

    # Ensure foreign key constraints if needed (optional for SQLite unless PRAGMA foreign_keys=ON)
    # But good for documentation: driver_id references drivers(id)
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
