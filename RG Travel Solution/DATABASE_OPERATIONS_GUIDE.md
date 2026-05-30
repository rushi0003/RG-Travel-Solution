# RG Travel Solution - Database & Backend Operations Guide

## 🗄️ Database Management

### Database Location

```
rg_travel_backend/
├── rg_travel.db                 # SQLite database file (auto-created)
└── db/schema.sql                # Schema definition
```

### Database Initialization

#### Automatic (First Run)
The database is automatically created on first run:
```bash
python app.py  # Creates rg_travel.db and initializes schema
```

#### Manual Initialization
```bash
curl -X POST http://localhost:5000/api/db/init
```

#### Check Database Status
```bash
curl -X GET http://localhost:5000/api/db/health

Response:
{
  "success": true,
  "data": {
    "database": "connected",
    "path": "/path/to/rg_travel.db",
    "size_mb": 2.5,
    "tables": 8
  }
}
```

---

## 📊 Database Tables Reference

### 1. admins
Stores admin user accounts and office profile.

**Schema:**
```sql
CREATE TABLE admins (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  mobile TEXT NOT NULL UNIQUE,
  email TEXT,
  office_name TEXT,
  office_location TEXT,
  office_address TEXT,
  password_salt TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

**Example Query:**
```sql
SELECT id, name, mobile, office_name FROM admins WHERE id = 'admin_123';
```

### 2. drivers
Stores driver profiles with vehicle and document information.

**Key Fields:**
- `id`: Unique identifier
- `mobile`: 10-digit phone number
- `dl_no`: Driving license number
- `vehicle_no`: Vehicle registration number
- `is_approved`: 0=pending, 1=approved, 2=rejected
- Document expiry dates: `dl_expiry`, `rc_expiry`, `insurance_expiry`

**Example Query:**
```sql
SELECT id, name, mobile, is_approved FROM drivers WHERE is_approved = 1;
```

### 3. employees
Stores employee information with drop location coordinates.

**Key Fields:**
- `id`: Employee identifier
- `mobile`: 10-digit phone
- `login_time`: HH:MM format (e.g., "09:00")
- `logout_time`: HH:MM format (e.g., "18:00")
- `drop_location`: Text address
- `drop_lat`, `drop_lng`: GPS coordinates
- `is_active`: 1=active, 0=inactive

**Example Query:**
```sql
SELECT * FROM employees WHERE is_active = 1 ORDER BY drop_location;
```

### 4. sessions
Stores authentication tokens for active sessions.

**Key Fields:**
- `id`: Session ID
- `user_id`: Reference to admin/driver/employee
- `role`: 'admin' | 'driver' | 'employee'
- `token`: Bearer token
- `expires_at`: ISO datetime
- `created_at`: ISO datetime

**Example Query:**
```sql
SELECT * FROM sessions WHERE token = 'eyJhbGciOiJIUzI1NiI...' AND expires_at > datetime('now');
```

### 5. route_numbers
Ensures unique 10-character route numbers per day.

**Key Fields:**
- `route_no`: 10-character alphanumeric code
- `trip_day`: YYYYMMDD format (day key)
- `created_at`: ISO datetime

**Example Query:**
```sql
SELECT route_no FROM route_numbers WHERE trip_day = '20260201' LIMIT 5;
```

### 6. trips
Master trip records with pickup/drop information.

**Key Fields:**
- `id`: Trip ID (auto-increment)
- `route_no`: 10-char unique identifier
- `trip_day`: YYYYMMDD
- `trip_type`: 'pickup' | 'drop'
- `status`: 'created' | 'assigned' | 'started' | 'completed' | 'cancelled'
- `admin_id`: Admin who created
- `driver_id`: Assigned driver
- `total_km`: Distance traveled
- OTP fields: `start_otp_hash`, `end_otp_hash`, `start_otp_expiry`, `end_otp_expiry`
- Location fields: `last_lat`, `last_lng`, `last_location_at`

**Example Query:**
```sql
SELECT id, route_no, status, driver_id, total_km 
FROM trips 
WHERE trip_day = '20260201' AND status = 'started';
```

### 7. trip_employees
Many-to-many relationship between trips and employees.

**Key Fields:**
- `trip_id`: Trip reference
- `employee_id`: Employee reference
- `sequence_no`: Order of pickup/drop
- `is_no_show`: 0=present, 1=no-show

**Example Query:**
```sql
SELECT e.name, te.sequence_no, te.is_no_show 
FROM trip_employees te
JOIN employees e ON te.employee_id = e.id
WHERE te.trip_id = 123
ORDER BY te.sequence_no;
```

---

## 🔧 Database Operations

### View All Tables

```bash
curl -X GET http://localhost:5000/api/db/tables

Response:
{
  "success": true,
  "data": {
    "tables": [
      "admins",
      "drivers",
      "employees",
      "sessions",
      "route_numbers",
      "trips",
      "trip_employees"
    ],
    "count": 7
  }
}
```

### Reset Database (Development Only)

```bash
curl -X POST http://localhost:5000/api/db/reset

# WARNING: This will delete all data and recreate schema
```

### Backup Database

```bash
# Create backup
cp rg_travel.db rg_travel.db.backup

# Or using Python
python -c "
import shutil
shutil.copy('rg_travel.db', 'rg_travel.db.backup')
print('Backup created')
"
```

### Restore Database

```bash
cp rg_travel.db.backup rg_travel.db
```

---

## 🌱 Seeding Data

### Seed Admin

```bash
curl -X POST http://localhost:5000/api/seed/admin

# Or with custom data
curl -X POST http://localhost:5000/api/seed/admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Admin",
    "mobile": "9876543210",
    "password": "secure@123",
    "office_name": "Head Office",
    "office_location": "Bangalore"
  }'
```

**Default Credentials:**
- Mobile: `9876543210`
- Password: `admin@123`

### Seed Drivers

```bash
curl -X POST http://localhost:5000/api/seed/drivers

# Check status
curl -X GET http://localhost:5000/api/seed/drivers/status

# Reset drivers
curl -X POST http://localhost:5000/api/seed/drivers/reset
```

**Default Drivers Created:**
- 5 drivers with different hometowns
- All with vehicle type "4" or "6"
- Document expiry dates set to future dates

### Seed Employees

```bash
curl -X POST http://localhost:5000/api/seed/employees

# List seeded employees
curl -X GET http://localhost:5000/api/seed/employees/list

# Check seed status
curl -X GET http://localhost:5000/api/seed/employees/status

# Reset employees
curl -X POST http://localhost:5000/api/seed/employees/reset
```

**Default Employees Created:**
- 15+ employees with different drop locations
- Login/logout times set (e.g., 09:00 to 18:00)
- GPS coordinates for Bangalore area

---

## 🔐 Database Security

### Enable Foreign Keys

Already enabled in schema.sql:
```sql
PRAGMA foreign_keys = ON;
```

### Connection Best Practices

```python
# In Python backend
import sqlite3

conn = sqlite3.connect('rg_travel.db', check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Enable foreign keys
cursor.execute('PRAGMA foreign_keys = ON')

# Always commit transactions
conn.commit()

# Close when done
conn.close()
```

### Prevent SQL Injection

✅ Always use parameterized queries:
```python
# CORRECT
cursor.execute("SELECT * FROM drivers WHERE mobile = ?", (mobile,))

# WRONG - vulnerable to injection
cursor.execute(f"SELECT * FROM drivers WHERE mobile = '{mobile}'")
```

---

## 🐛 Database Troubleshooting

### Issue 1: Database is Locked

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Causes:**
- Multiple connections writing simultaneously
- Process not closed properly
- Long-running transaction

**Solution:**
```bash
# Kill all Python processes
pkill -f "python.*app.py"

# Delete database and restart (development only)
rm rg_travel.db
python app.py  # Recreates database
```

### Issue 2: Table Not Found

**Error:**
```
sqlite3.OperationalError: no such table: admins
```

**Solution:**
```bash
# Initialize database
curl -X POST http://localhost:5000/api/db/init

# Or delete and restart
rm rg_travel.db
python app.py
```

### Issue 3: Foreign Key Constraint Failed

**Error:**
```
sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**Cause:** Trying to delete/reference non-existent parent record

**Solution:**
```bash
# Check referential integrity
curl -X GET http://localhost:5000/api/db/health

# Verify parent records exist before creating relations
SELECT * FROM trips WHERE driver_id = 'non_existent_id';
```

### Issue 4: Corrupted Database

**Error:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
```bash
# Backup current database
mv rg_travel.db rg_travel.db.corrupted

# Restore from backup (if available)
cp rg_travel.db.backup rg_travel.db

# Or recreate fresh
python app.py
```

---

## 📈 Performance Optimization

### Check Database Size

```bash
# Linux/Mac
du -h rg_travel.db

# Windows
dir rg_travel.db

# Or via API
curl -X GET http://localhost:5000/api/db/health | grep size_mb
```

### Analyze Queries

```python
# In Python
conn = sqlite3.connect('rg_travel.db')
cursor = conn.cursor()

# Enable query profiling
cursor.execute("PRAGMA query_only = ON")

# Run slow query
cursor.execute("SELECT * FROM trips JOIN trip_employees ...")

# Show execution plan
cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM trips WHERE trip_day = ?", ('20260201',))
for row in cursor:
    print(row)
```

### Add Indexes (if needed)

```sql
-- Already created in schema.sql, but examples:
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_employees_drop_location ON employees(drop_location);
CREATE INDEX idx_trip_employees_no_show ON trip_employees(is_no_show);
```

---

## 🔍 Query Examples

### Find Today's Trips

```sql
SELECT id, route_no, trip_type, status, employee_count 
FROM trips 
WHERE trip_day = date('now')
ORDER BY created_at DESC;
```

### Find No-Show Employees

```sql
SELECT e.name, e.mobile, t.route_no, t.trip_day
FROM trip_employees te
JOIN employees e ON te.employee_id = e.id
JOIN trips t ON te.trip_id = t.id
WHERE te.is_no_show = 1 AND t.trip_day = date('now');
```

### Find Expired Driver Documents

```sql
SELECT name, mobile, dl_expiry, rc_expiry, insurance_expiry
FROM drivers
WHERE dl_expiry < date('now')
   OR rc_expiry < date('now')
   OR insurance_expiry < date('now');
```

### Find Busy Routes (Most Trips)

```sql
SELECT route_no, COUNT(*) as trip_count, COUNT(DISTINCT driver_id) as drivers
FROM trips
WHERE trip_day = date('now')
GROUP BY route_no
ORDER BY trip_count DESC
LIMIT 5;
```

### Calculate Trip Statistics

```sql
SELECT 
  trip_day,
  trip_type,
  COUNT(*) as total_trips,
  SUM(total_km) as total_distance,
  AVG(total_km) as avg_distance,
  COUNT(DISTINCT driver_id) as drivers_used,
  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
FROM trips
WHERE trip_day BETWEEN date('now', '-7 days') AND date('now')
GROUP BY trip_day, trip_type
ORDER BY trip_day DESC;
```

---

## 📝 Data Export/Import

### Export as CSV

```python
import csv
import sqlite3

conn = sqlite3.connect('rg_travel.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Export employees
cursor.execute("SELECT * FROM employees")
rows = cursor.fetchall()

with open('employees.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))

print("Exported to employees.csv")
```

### Import from CSV

```python
import csv
import sqlite3

conn = sqlite3.connect('rg_travel.db')
cursor = conn.cursor()

with open('employees.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        cursor.execute("""
            INSERT INTO employees 
            (id, name, mobile, email, login_time, logout_time, 
             drop_location, drop_lat, drop_lng, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(row.values()))

conn.commit()
print("Imported from employees.csv")
```

---

## 🔄 Migration Strategy

### Add New Column

```sql
ALTER TABLE employees ADD COLUMN department TEXT;
UPDATE employees SET department = 'Engineering' WHERE id IS NOT NULL;
```

### Create New Table

```sql
CREATE TABLE IF NOT EXISTS employee_feedback (
  id TEXT PRIMARY KEY,
  trip_id INTEGER NOT NULL,
  employee_id TEXT NOT NULL,
  rating INTEGER CHECK(rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id),
  FOREIGN KEY(employee_id) REFERENCES employees(id)
);
```

### Update Schema

Edit [db/schema.sql](db/schema.sql) and:
1. Add new table definitions
2. Reset database: `rm rg_travel.db`
3. Restart backend: `python app.py`

---

**Last Updated**: 2026-02-01  
**Database**: SQLite 3.37+  
**Status**: ✅ Ready for Production
