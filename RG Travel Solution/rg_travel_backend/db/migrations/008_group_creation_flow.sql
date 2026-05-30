-- rg_travel_backend/db/migrations/008_group_creation_flow.sql
-- Step 3: Schema hardening for Group Creation + Trip Assignment flow
-- Safe to run multiple times (idempotent where possible)

PRAGMA foreign_keys = ON;
BEGIN;

-- =========================================================
-- VEHICLES (new canonical table for assignment)
-- =========================================================
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_no      TEXT NOT NULL UNIQUE,
    vehicle_type    INTEGER NOT NULL CHECK(vehicle_type IN (4, 6)),
    is_available    INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0,1)),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vehicles_type_available
    ON vehicles(vehicle_type, is_available);

-- =========================================================
-- EMPLOYEES: required compatibility columns
-- =========================================================
ALTER TABLE employees ADD COLUMN employee_id TEXT;
ALTER TABLE employees ADD COLUMN is_assigned INTEGER NOT NULL DEFAULT 0 CHECK(is_assigned IN (0,1));

-- Backfill employee_id for existing rows if null
UPDATE employees
SET employee_id = CAST(id AS TEXT)
WHERE employee_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_employees_employee_id ON employees(employee_id);
CREATE INDEX IF NOT EXISTS idx_employees_login_logout ON employees(login_time, logout_time);

-- =========================================================
-- DRIVERS: required compatibility columns
-- =========================================================
ALTER TABLE drivers ADD COLUMN driver_id TEXT;
ALTER TABLE drivers ADD COLUMN phone TEXT;
ALTER TABLE drivers ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1));
ALTER TABLE drivers ADD COLUMN hometown_lat REAL;
ALTER TABLE drivers ADD COLUMN hometown_lng REAL;
ALTER TABLE drivers ADD COLUMN vehicle_id INTEGER;

-- Backfill compatibility values
UPDATE drivers SET driver_id = id WHERE driver_id IS NULL;
UPDATE drivers SET phone = mobile WHERE phone IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_drivers_driver_id ON drivers(driver_id);
CREATE INDEX IF NOT EXISTS idx_drivers_active_approved ON drivers(is_active, is_approved);
CREATE INDEX IF NOT EXISTS idx_drivers_vehicle_id ON drivers(vehicle_id);

-- =========================================================
-- TRIPS: add fields needed for group creation contract
-- =========================================================
ALTER TABLE trips ADD COLUMN time_slot TEXT;
ALTER TABLE trips ADD COLUMN vehicle_id INTEGER;
ALTER TABLE trips ADD COLUMN route_polyline TEXT;

-- Keep time_slot and route_polyline synchronized for existing rows
UPDATE trips
SET time_slot = schedule_time
WHERE time_slot IS NULL;

UPDATE trips
SET route_polyline = polyline
WHERE route_polyline IS NULL;

CREATE INDEX IF NOT EXISTS idx_trips_time_slot_status ON trips(time_slot, status);

-- =========================================================
-- TRIP GROUPS: align with route-based grouping contract
-- =========================================================
ALTER TABLE trip_groups ADD COLUMN group_id TEXT;
ALTER TABLE trip_groups ADD COLUMN route_no TEXT;
ALTER TABLE trip_groups ADD COLUMN capacity INTEGER CHECK(capacity IN (4,6));
ALTER TABLE trip_groups ADD COLUMN vehicle_id INTEGER;
ALTER TABLE trip_groups ADD COLUMN driver_id TEXT;

UPDATE trip_groups
SET group_id = 'GRP-' || id
WHERE group_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_groups_group_id ON trip_groups(group_id);
CREATE INDEX IF NOT EXISTS idx_trip_groups_route_no ON trip_groups(route_no);

-- =========================================================
-- TRIP GROUP MEMBERS: align naming for deterministic sequence
-- =========================================================
ALTER TABLE trip_group_members ADD COLUMN sequence_no INTEGER;
ALTER TABLE trip_group_members ADD COLUMN pickup_drop_status TEXT;

UPDATE trip_group_members
SET sequence_no = pickup_order
WHERE sequence_no IS NULL;

UPDATE trip_group_members
SET pickup_drop_status = status
WHERE pickup_drop_status IS NULL;

CREATE INDEX IF NOT EXISTS idx_trip_group_members_group
    ON trip_group_members(group_id);

COMMIT;
