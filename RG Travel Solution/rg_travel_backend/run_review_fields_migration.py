import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "rg_travel.db")

def run_migration():
    print("Running migration: add_review_fields_to_requests.sql")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(driver_requests)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'review_note' not in columns:
            cursor.execute("ALTER TABLE driver_requests ADD COLUMN review_note TEXT")
            print("✓ Added 'review_note' column")
        else:
            print("✓ 'review_note' column already exists")
            
        if 'reviewed_at' not in columns:
            cursor.execute("ALTER TABLE driver_requests ADD COLUMN reviewed_at TEXT")
            print("✓ Added 'reviewed_at' column")
        else:
            print("✓ 'reviewed_at' column already exists")
        
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
