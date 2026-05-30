#!/usr/bin/env python3
import sqlite3

db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

try:
    cur = conn.cursor()
    sql = """
    SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved, is_online
    FROM drivers
    WHERE is_approved = 1
    ORDER BY name ASC
    """
    cur.execute(sql)
    rows = cur.fetchall() or []
    out = []
    for r in rows:
        out.append(dict(r))
    print(f'Success! Found {len(out)} drivers')
    print(f'Result: {out}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    conn.close()
