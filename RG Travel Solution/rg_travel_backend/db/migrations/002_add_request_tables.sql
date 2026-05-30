-- backend/db/migrations/002_add_request_tables.sql

BEGIN;

-- 1. Ensure admins table has correct structure (add if missing)
CREATE TABLE IF NOT EXISTS admins (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  mobile          TEXT NOT NULL UNIQUE,
  email           TEXT,
  office_name     TEXT,
  office_location TEXT,
  office_address  TEXT,
  password_salt   TEXT NOT NULL,
  password_hash   TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

-- 2. Create driver_requests table (Separate table pattern)
CREATE TABLE IF NOT EXISTS driver_requests (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  mobile       TEXT NOT NULL, -- normalized
  dl_no        TEXT NOT NULL,
  cab_no       TEXT NOT NULL, -- normalized
  home_town    TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
  created_at   TEXT NOT NULL,
  reviewed_at  TEXT,
  review_note  TEXT
);

-- Index for admin dashboard filtering
CREATE INDEX IF NOT EXISTS idx_driver_requests_status ON driver_requests(status);


-- 3. Create employee_requests table
CREATE TABLE IF NOT EXISTS employee_requests (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  mobile        TEXT NOT NULL,
  login_time    TEXT NOT NULL, -- HH:MM
  logout_time   TEXT NOT NULL, -- HH:MM
  home_address  TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
  created_at    TEXT NOT NULL,
  reviewed_at   TEXT,
  review_note   TEXT
);

CREATE INDEX IF NOT EXISTS idx_employee_requests_status ON employee_requests(status);

COMMIT;
