
import sys
import os

# Add parent dir to sys.path to allow imports from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import get_db

def reset_data():
    """
    Wipes all operational data (Trips, Employees, Drivers) but KEEPS Admins.
    """
    print("🚀 Starting Data Reset (Preserving Admins)...")
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Disable foreign keys temporarily to allow deleting in any order?
        # Better to delete in correct order or just force it.
        # SQLite respects FKs if enabled. Let's try correct order.
        
        from db import init_db
        
        tables_to_clear = [
            "trip_employees",
            "trip_otps",
            "otp_audit_log",
            "driver_location_history",
            "driver_locations",
            "trip_cab_history",
            "swap_requests",
            "trips",
            
            "employee_requests",
            "employee_absences",
            "employees",
            
            "driver_hometown_requests",
            "drivers",
            
            "cab_rotation_state",
            "sessions" # logout everyone
        ]
        
        for table in tables_to_clear:
            try:
                # Check if table exists first
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cur.fetchone():
                    # DROP TABLE to ensure schema updates (e.g. adding columns) are applied on re-init
                    cur.execute(f"DROP TABLE {table}")
                    print(f"  🔥 Dropped {table}")
                else:
                    print(f"  ⚠️  Table {table} not found (skipping)")
            except Exception as e:
                print(f"  ❌ Failed to drop {table}: {e}")

        conn.commit()
        
        # Re-init DB to recreate tables from schema.sql
        print("🔄 Re-initializing Database Schema...")
        init_db()
        print("✨ Data reset & Schema update complete. Admin accounts preserved.")
        
    except Exception as e:
        print(f"🔥 Critical Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_data()
