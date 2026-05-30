-- backend/db/migrations/005_driver_assignment.sql
-- Add driver assignment tracking fields
-- STEP 8: Fair rotation and workload balancing

-- Trips table: Add assignment metadata
ALTER TABLE trips ADD COLUMN assignment_score REAL;      -- Workload score at assignment time
ALTER TABLE trips ADD COLUMN assignment_reason TEXT;     -- Why this driver was chosen
ALTER TABLE trips ADD COLUMN route_area TEXT;            -- Geographic area identifier for rotation tracking

-- Create driver_assignments table for historical tracking
CREATE TABLE IF NOT EXISTS driver_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id TEXT NOT NULL,
    trip_id INTEGER NOT NULL,
    route_area TEXT,                    -- Geographic area (e.g., "area_19.08_72.88")
    assigned_at TEXT NOT NULL,          -- ISO timestamp
    trip_distance_km REAL,              -- Trip distance for workload tracking
    workload_score REAL,                -- Score at time of assignment
    assignment_reason TEXT,             -- Reason for selection
    
    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_driver_assignments_driver ON driver_assignments(driver_id, assigned_at);
CREATE INDEX IF NOT EXISTS idx_driver_assignments_route ON driver_assignments(route_area, assigned_at);
CREATE INDEX IF NOT EXISTS idx_driver_assignments_trip ON driver_assignments(trip_id);
