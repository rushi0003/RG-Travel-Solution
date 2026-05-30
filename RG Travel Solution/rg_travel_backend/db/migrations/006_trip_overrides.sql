-- backend/db/migrations/006_trip_overrides.sql
-- Add trip versioning and audit trail for admin override operations
-- STEP 10: Manual trip modifications with audit trail

-- Trips table: Add versioning and modification tracking
ALTER TABLE trips ADD COLUMN route_revision INTEGER DEFAULT 1;  -- Version: v1, v2, v3...
ALTER TABLE trips ADD COLUMN last_modified_by TEXT;             -- admin_id who last modified
ALTER TABLE trips ADD COLUMN last_modified_at TEXT;             -- ISO timestamp of last modification

-- Create trip audit log table for tracking all changes
CREATE TABLE IF NOT EXISTS trip_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    route_no TEXT NOT NULL,
    revision_number INTEGER NOT NULL,           -- Which version (1, 2, 3...)
    
    action_type TEXT NOT NULL,                  -- 'move_employee_in', 'move_employee_out', 'change_driver'
    performed_by TEXT NOT NULL,                 -- admin_id
    performed_at TEXT NOT NULL,                 -- ISO timestamp
    
    -- Change details (stored as JSON)
    old_state TEXT,                             -- JSON: old driver/employees/etc
    new_state TEXT,                             -- JSON: new driver/employees/etc
    
    -- Optional reason for change
    reason TEXT,
    
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_trip_audit_trip ON trip_audit_log(trip_id, revision_number);
CREATE INDEX IF NOT EXISTS idx_trip_audit_time ON trip_audit_log(performed_at);
CREATE INDEX IF NOT EXISTS idx_trip_audit_action ON trip_audit_log(action_type);
