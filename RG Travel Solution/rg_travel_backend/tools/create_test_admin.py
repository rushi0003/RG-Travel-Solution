
import sys
import os
import sqlite3
from datetime import datetime

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.security import hash_password
from db import get_db

def create_admin():
    print("🚀 Creating/Updating Test Admin...")
    
    mobile = "9325118627"
    password = "admin123"
    name = "Test Admin"
    admin_id = "admin_test_001"
    
    salt, pwd_hash = hash_password(password)
    now = datetime.now().isoformat()
    
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check if exists
        cur.execute("SELECT id FROM admins WHERE mobile = ?", (mobile,))
        row = cur.fetchone()
        
        if row:
            print(f"  Existing admin found (id={row['id']}). Updating password...")
            cur.execute(
                """
                UPDATE admins 
                SET password_salt = ?, password_hash = ?, updated_at = ?
                WHERE mobile = ?
                """,
                (salt, pwd_hash, now, mobile)
            )
        else:
            print("  Creating new admin...")
            cur.execute(
                """
                INSERT INTO admins (id, name, mobile, password_salt, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (admin_id, name, mobile, salt, pwd_hash, now, now)
            )
            
        conn.commit()
        print(f"✅ Admin ready. Mobile: {mobile}, Password: {password}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin()
