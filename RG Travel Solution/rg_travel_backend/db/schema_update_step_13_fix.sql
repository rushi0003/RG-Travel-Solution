-- Step 13 Fix: Add trip_routes and partial indexes

BEGIN TRANSACTION;

-- 1. TRIP ROUTES TABLE (Detailed route segments)
CREATE TABLE IF NOT EXISTS trip_routes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER NOT NULL,
    route_index     INTEGER DEFAULT 0,          -- 0 = primary route
    polyline        TEXT,                       -- Google Maps Polyline
    distance_km     REAL DEFAULT 0,
    duration_mins   REAL DEFAULT 0,
    via             TEXT,                       -- "Via Main St"
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_trip_routes_trip ON trip_routes(trip_id);

-- 2. PARTIAL INDEXES (Optimized for "Active Trip" checks)

-- Find active trip for a driver (assigned or started)
CREATE INDEX IF NOT EXISTS idx_trips_driver_active 
ON trips(driver_id) 
WHERE status IN ('assigned', 'started');

-- Find active trip for an employee (assigned or assigned to a group in an active trip)
-- Note: SQLite partial indexes are powerful. 
-- For trip_group_members, status 'assigned' usually implies active if the trip is active.
-- We can index the status to make filtering fast.
CREATE INDEX IF NOT EXISTS idx_tgm_status_employee 
ON trip_group_members(status, employee_id)
WHERE status IN ('assigned', 'picked_up');

COMMIT;
