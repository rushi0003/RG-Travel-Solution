-- rg_travel_backend/db/migrations/009_group_delete_support.sql
-- Step: Add delete support for preview groups.
-- NOTE:
--   This migration is applied via apply_migration_009_group_delete.py
--   to keep it idempotent across existing databases.

BEGIN;

-- Intended schema updates:
-- ALTER TABLE groups ADD COLUMN deleted_at TEXT;
-- CREATE INDEX IF NOT EXISTS idx_groups_status ON groups(status);
-- CREATE INDEX IF NOT EXISTS idx_groups_deleted_at ON groups(deleted_at);

COMMIT;
