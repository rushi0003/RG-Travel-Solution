"""
Database Migration: Add vehicle_type to driver_requests table
RG Travel Solution - Driver Management Fix
Date: 2026-02-06
"""

import sqlite3
import sys
from pathlib import Path

def migrate_driver_requests():
    """Add vehicle_type column to driver_requests table"""
    
    db_path = Path(__file__).parent / "rg_travel.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("PRAGMA table_info(driver_requests);")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'vehicle_type' in columns:
            print("✅ Column 'vehicle_type' already exists in driver_requests table")
            conn.close()
            return True
        
        # Add the column
        print("📝 Adding vehicle_type column to driver_requests table...")
        cur.execute("ALTER TABLE driver_requests ADD COLUMN vehicle_type TEXT;")
        conn.commit()
        
        # Verify the change
        cur.execute("PRAGMA table_info(driver_requests);")
        columns_after = [col[1] for col in cur.fetchall()]
        
        if 'vehicle_type' in columns_after:
            print("✅ Successfully added vehicle_type column!")
            print(f"📋 Current columns: {', '.join(columns_after)}")
            conn.close()
            return True
        else:
            print("❌ Failed to add column")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_driver_requests()
    sys.exit(0 if success else 1)
