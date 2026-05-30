import sqlite3

# Connect to database
conn = sqlite3.connect('rg_travel.db')
cur = conn.cursor()

with open('schema_report.txt', 'w', encoding='utf-8') as f:
    # Get driver_requests schema
    f.write("=" * 60 + "\n")
    f.write("DRIVER_REQUESTS TABLE\n")
    f.write("=" * 60 + "\n")
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='driver_requests';")
    result = cur.fetchone()
    if result:
        f.write(result[0] + "\n")
    else:
        f.write("⚠️  Table 'driver_requests' does NOT exist in the database!\n")
        # List all tables to see what's available
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cur.fetchall()
        f.write("\n📋 Available tables:\n")
        for t in tables:
            f.write(f"   - {t[0]}\n")

    f.write("\n" + "=" * 60 + "\n")
    f.write("DRIVERS TABLE\n")
    f.write("=" * 60 + "\n")
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='drivers';")
    result = cur.fetchone()
    if result:
        f.write(result[0] + "\n")
    else:
        f.write("⚠️  Table 'drivers' does NOT exist!\n")

    # Check what columns exist in drivers table
    f.write("\n" + "=" * 60 + "\n")
    f.write("ACTUAL DRIVERS TABLE COLUMNS (PRAGMA)\n")
    f.write("=" * 60 + "\n")
    cur.execute("PRAGMA table_info(drivers);")
    columns = cur.fetchall()
    for col in columns:
        cid, name, dtype, notnull, default, pk = col
        pk_str = " PRIMARY KEY" if pk else ""
        notnull_str = " NOT NULL" if notnull else ""
        default_str = f" DEFAULT {default}" if default else ""
        f.write(f"   {name:20s} {dtype:15s}{pk_str}{notnull_str}{default_str}\n")

conn.close()
print("Schema report saved to schema_report.txt")
