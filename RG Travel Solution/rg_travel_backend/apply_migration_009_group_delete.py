"""
Safe, idempotent apply script for preview group delete support.

Usage:
  python apply_migration_009_group_delete.py
"""

import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "rg_travel.db"
MIGRATION_PATH = ROOT / "db" / "migrations" / "009_group_delete_support.sql"


def table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def column_exists(cur: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cur.fetchall())


def index_exists(cur: sqlite3.Cursor, index_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cur.fetchone() is not None


def apply_migration(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    if not table_exists(cur, "groups"):
        raise RuntimeError("groups table not found. Apply group creation migration first.")

    if not column_exists(cur, "groups", "deleted_at"):
        cur.execute("ALTER TABLE groups ADD COLUMN deleted_at TEXT")

    if not index_exists(cur, "idx_groups_status"):
        cur.execute("CREATE INDEX idx_groups_status ON groups(status)")

    if not index_exists(cur, "idx_groups_deleted_at"):
        cur.execute("CREATE INDEX idx_groups_deleted_at ON groups(deleted_at)")


def verify_schema(cur: sqlite3.Cursor) -> list[str]:
    missing: list[str] = []

    if not table_exists(cur, "groups"):
        missing.append("table:groups")
    else:
        if not column_exists(cur, "groups", "deleted_at"):
            missing.append("column:groups.deleted_at")
        if not index_exists(cur, "idx_groups_status"):
            missing.append("index:idx_groups_status")
        if not index_exists(cur, "idx_groups_deleted_at"):
            missing.append("index:idx_groups_deleted_at")

    return missing


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        return 1

    if not MIGRATION_PATH.exists():
        print(f"ERROR: Migration SQL missing: {MIGRATION_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN")
        apply_migration(conn)
        conn.commit()

        cur = conn.cursor()
        missing = verify_schema(cur)
        if missing:
            print("ERROR: Verification failed.")
            for item in missing:
                print(f" - missing {item}")
            return 1

        print("SUCCESS: Group delete migration applied and verified.")
        print(f"DB: {DB_PATH}")
        print(f"Migration SQL: {MIGRATION_PATH}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: Migration failed and rolled back: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
