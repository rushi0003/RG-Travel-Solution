import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "rg_travel.db")

def run_migration():
    print("Running migration: add_vehicle_type_to_requests.sql")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(driver_requests)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'vehicle_type' in columns:
            print("✓ Column 'vehicle_type' already exists in driver_requests table")
        else:
            # Add column
            cursor.execute("ALTER TABLE driver_requests ADD COLUMN vehicle_type TEXT DEFAULT '4'")
            print("✓ Added 'vehicle_type' column to driver_requests table")
            
            # Update existing records
            cursor.execute("UPDATE driver_requests SET vehicle_type = '4' WHERE vehicle_type IS NULL")
            rows_updated = cursor.rowcount
            print(f"✓ Updated {rows_updated} existing records with default value '4'")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
