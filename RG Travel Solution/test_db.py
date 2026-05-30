#!/usr/bin/env python3
import sqlite3
import os

db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check if drivers table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print(f'Tables: {tables}')

# Check if drivers table exists
if 'drivers' in tables:
    cur.execute('SELECT COUNT(*) as cnt FROM drivers')
    count = cur.fetchone()[0]
    print(f'drivers count: {count}')
else:
    print('drivers table does not exist')

# Check admins
if 'admins' in tables:
    cur.execute('SELECT COUNT(*) as cnt FROM admins')
    count = cur.fetchone()[0]
    print(f'admins count: {count}')
    cur.execute('SELECT id, mobile FROM admins')
    admins = cur.fetchall()
    print(f'admins: {[dict(row) for row in admins]}')

conn.close()
