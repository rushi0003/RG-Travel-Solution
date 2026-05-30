-- =========================================================
-- RG Travel Solution: Admin Login Migration & Seed Data
-- =========================================================
-- File: backend/db/admin_login_migration.sql
-- Purpose: Seed admin record and provide verification queries
--
-- NOTE: The admins table already has the 'name' column.
--       No ALTER TABLE migration is needed.
-- =========================================================

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. SEED ADMIN RECORD (Rushi Gund)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- IMPORTANT: This is an example. The actual seed is done via Python script.
-- Password: Rushi123
-- The hash values below are generated using Python's hash_password() function.

-- Example insert (DO NOT RUN - use seed_admin_custom.py instead):
/*
INSERT INTO admins (
  id,
  name,
  mobile,
  email,
  office_name,
  office_location,
  office_address,
  password_salt,
  password_hash,
  created_at,
  updated_at
) VALUES (
  'adm_a1b2c3d4',           -- Unique admin ID
  'Rushi Gund',              -- Admin name
  '9325118627',              -- Mobile (10 digits)
  NULL,                      -- Email (optional)
  NULL,                      -- Office name (optional)
  NULL,                      -- Office location (optional)
  NULL,                      -- Office address (optional)
  'salt_value_here',         -- Generated salt
  'hash_value_here',         -- Password hash
  '2026-02-05T05:30:00Z',    -- Created timestamp
  '2026-02-05T05:30:00Z'     -- Updated timestamp
);
*/

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 2. VERIFICATION QUERIES
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- Check if admin exists
SELECT id, name, mobile, created_at 
FROM admins 
WHERE mobile = '9325118627';

-- Verify admin name (case-insensitive)
SELECT id, name, mobile 
FROM admins 
WHERE LOWER(name) = LOWER('Rushi Gund') 
  AND mobile = '9325118627';

-- List all admins
SELECT id, name, mobile, office_name, created_at 
FROM admins 
ORDER BY created_at DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 3. UPDATE EXISTING ADMIN RECORD
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- If you need to update an existing admin's name:
UPDATE admins 
SET 
  name = 'Rushi Gund',
  updated_at = CURRENT_TIMESTAMP
WHERE mobile = '9325118627';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 4. PRODUCTION MIGRATION (IF NEEDED)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- ✅ NO MIGRATION NEEDED - The 'name' column already exists in schema.sql
-- The table was created with:
-- CREATE TABLE IF NOT EXISTS admins (
--   id              TEXT PRIMARY KEY,
--   name            TEXT NOT NULL,  -- ✅ Already present
--   mobile          TEXT NOT NULL UNIQUE,
--   ...
-- );

-- If migrating from a very old database without the name column:
-- ALTER TABLE admins ADD COLUMN name TEXT NOT NULL DEFAULT 'Admin';
-- (This should NOT be needed for current schema)
