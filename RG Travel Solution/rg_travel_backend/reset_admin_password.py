
import sqlite3
import hashlib
import secrets

DB_PATH = "rg_travel.db"

def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, pwd_hash

def reset_password():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if admin exists
    cur.execute("SELECT id, name FROM admins WHERE mobile = '9325118627'")
    row = cur.fetchone()
    
    if not row:
        print("Admin not found. Cannot reset.")
        conn.close()
        return

    admin_id, name = row
    print(f"Resetting password for {name} ({admin_id})...")
    
    salt, p_hash = hash_password("Rushi123")
    
    cur.execute(
        "UPDATE admins SET password_salt = ?, password_hash = ? WHERE id = ?",
        (salt, p_hash, admin_id)
    )
    conn.commit()
    conn.close()
    print("Password reset to 'Rushi123' successfully.")

if __name__ == "__main__":
    reset_password()
