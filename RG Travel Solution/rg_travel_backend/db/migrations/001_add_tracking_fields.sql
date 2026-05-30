-- 001_add_tracking_fields.sql
-- Migration: Add online status tracking to drivers table
-- Date: 2026-02-04
-- Purpose: Support live driver tracking feature

BEGIN;

-- Add online status tracking columns
ALTER TABLE drivers ADD COLUMN is_online INTEGER DEFAULT 0;
ALTER TABLE drivers ADD COLUMN last_seen TEXT;

-- Index for efficient online driver queries
CREATE INDEX IF NOT EXISTS idx_drivers_online ON drivers(is_online, last_seen);

-- Verify foreign key enforcement
PRAGMA foreign_keys = ON;

COMMIT;

-- Rollback if needed:
-- BEGIN;
-- ALTER TABLE drivers DROP COLUMN is_online;
-- ALTER TABLE drivers DROP COLUMN last_seen;
-- DROP INDEX IF EXISTS idx_drivers_online;
-- COMMIT;
