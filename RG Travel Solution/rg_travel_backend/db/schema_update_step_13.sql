-- Step 13 Schema Update
-- Tables: cabs, trip_groups, trip_group_members, admin_audit, otp_store

BEGIN TRANSACTION;

-- 1. CABS TABLE (Decouple vehicles from drivers)
CREATE TABLE IF NOT EXISTS cabs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reg_no          TEXT NOT NULL UNIQUE,       -- Standardized Registration Number (e.g., MH12AB1234)
    model           TEXT,                       -- e.g., "Toyota Etios"
    capacity        INTEGER NOT NULL DEFAULT 4, -- 4 or 6
    fuel_type       TEXT,                       -- Petrol/Diesel/CNG/EV
    status          TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'maintenance', 'retired')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. TRIP GROUPS (Hierarchical grouping for trips)
CREATE TABLE IF NOT EXISTS trip_groups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER,                    -- Link to trip (nullable if group created before trip)
    group_type      TEXT NOT NULL CHECK(group_type IN ('pickup', 'drop')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

-- 3. TRIP GROUP MEMBERS (Linking employees to groups)
CREATE TABLE IF NOT EXISTS trip_group_members (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id        INTEGER NOT NULL,
    employee_id     TEXT NOT NULL,
    pickup_order    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'assigned',    -- assigned, picked_up, dropped, no_show
    
    FOREIGN KEY(group_id) REFERENCES trip_groups(id) ON DELETE CASCADE,
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- 4. ADMIN AUDIT (Comprehensive logging)
CREATE TABLE IF NOT EXISTS admin_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        TEXT,
    action          TEXT NOT NULL,              -- e.g., "APPROVE_DRIVER", "MANUAL_TRIP_EDIT"
    target_type     TEXT,                       -- e.g., "driver", "trip"
    target_id       TEXT,
    details         TEXT,                       -- JSON payload or description
    ip_address      TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

-- 5. OTP STORE (Centralized OTP handling)
CREATE TABLE IF NOT EXISTS otp_store (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL,              -- 'trip', 'login'
    entity_id       TEXT NOT NULL,              -- trip_id or mobile_number
    otp_hash        TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    is_used         INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. UPDATE TRIPS TABLE
-- Add cab_id column if it doesn't exist
-- SQLite does not support IF NOT EXISTS for ADD COLUMN, so we generally just run it and catch error or check first.
-- We will handle this in the python migration script or rely on this running once.
-- ALTER TABLE trips ADD COLUMN cab_id INTEGER REFERENCES cabs(id) ON DELETE SET NULL; 
-- (Commented out to run safely in python script which checks existence)

-- 7. INDEXES
-- Cabs
CREATE INDEX IF NOT EXISTS idx_cabs_status ON cabs(status);
CREATE INDEX IF NOT EXISTS idx_cabs_capacity ON cabs(capacity);

-- Trip Groups
CREATE INDEX IF NOT EXISTS idx_trip_groups_trip ON trip_groups(trip_id);

-- Group Members (Active Trip Check optimized)
CREATE INDEX IF NOT EXISTS idx_trip_group_members_employee ON trip_group_members(employee_id);

-- Admin Audit
CREATE INDEX IF NOT EXISTS idx_admin_audit_action ON admin_audit(action);
CREATE INDEX IF NOT EXISTS idx_admin_audit_target ON admin_audit(target_type, target_id);

-- OTP Store
CREATE INDEX IF NOT EXISTS idx_otp_store_lookup ON otp_store(entity_type, entity_id, is_used);

COMMIT;
