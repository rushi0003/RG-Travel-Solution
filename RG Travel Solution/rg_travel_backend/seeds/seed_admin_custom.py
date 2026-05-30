# backend/seeds/seed_admin_custom.py
from db import get_db
from utils.security import hash_password
from datetime import datetime
import secrets

def seed_admin():
    conn = get_db()
    cur = conn.cursor()
    
    # Check if exists
    cur.execute("SELECT id FROM admins WHERE mobile = '9325118627'")
    if cur.fetchone():
        print("Admin Rushi already exists.")
        conn.close()
        return

    print("Seeding Admin Rushi...")
    salt, p_hash = hash_password("Rushi123")
    admin_id = f"adm_{secrets.token_hex(4)}"
    
    cur.execute(
        """
        INSERT INTO admins (id, name, mobile, password_salt, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (admin_id, "Rushi Gund", "9325118627", salt, p_hash, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    print("Admin seeded successfully.")

if __name__ == "__main__":
    seed_admin()
