-- backend/db/schema.sql
-- RG Travel Solution - Complete SQLite Schema
-- STEP 2: Database + Backend Contract Alignment
-- Date: 2026-02-19 (Fixed Duplications)

PRAGMA foreign_keys = ON;

BEGIN;

-- =========================================================
-- ADMINS
-- =========================================================
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

CREATE INDEX IF NOT EXISTS idx_admins_mobile ON admins(mobile);

-- =========================================================
-- DRIVERS
-- (Step 2: vehicle_type = '4' or '6' for capacity filtering)
-- =========================================================
CREATE TABLE IF NOT EXISTS drivers (
  id                TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  mobile            TEXT NOT NULL UNIQUE,
  dl_no             TEXT NOT NULL UNIQUE,
  vehicle_no        TEXT NOT NULL UNIQUE,
  vehicle_type      TEXT,
  home_town         TEXT,
  is_approved       INTEGER NOT NULL DEFAULT 0,
  password_salt     TEXT NOT NULL,
  password_hash     TEXT NOT NULL,
  dl_expiry         TEXT,
  rc_expiry         TEXT,
  insurance_expiry  TEXT,
  fitness_expiry    TEXT,
  permit_expiry     TEXT,
  is_online         INTEGER DEFAULT 0,
  last_seen         TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_drivers_mobile ON drivers(mobile);
CREATE INDEX IF NOT EXISTS idx_drivers_approved ON drivers(is_approved);
CREATE INDEX IF NOT EXISTS idx_drivers_vehicle_type ON drivers(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_drivers_home_town ON drivers(home_town);
CREATE INDEX IF NOT EXISTS idx_drivers_online ON drivers(is_online, last_seen);

-- =========================================================
-- EMPLOYEES
-- (Step 1: login_time = pickup slots, logout_time = drop slots; HH:MM)
-- =========================================================
CREATE TABLE IF NOT EXISTS employees (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  name             TEXT NOT NULL,
  mobile           TEXT NOT NULL UNIQUE,
  email            TEXT,
  employee_code    TEXT,
  login_time       TEXT,
  logout_time      TEXT,
  home_address     TEXT,
  home_lat         REAL,
  home_lng         REAL,
  pickup_address   TEXT,
  pickup_lat       REAL,
  pickup_lng       REAL,
  drop_location    TEXT,
  drop_lat         REAL,
  drop_lng         REAL,
  is_active        INTEGER NOT NULL DEFAULT 1,
  is_approved      INTEGER NOT NULL DEFAULT 0,
  created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_employees_mobile ON employees(mobile);
CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(is_active);
CREATE INDEX IF NOT EXISTS idx_employees_login_time ON employees(login_time);
CREATE INDEX IF NOT EXISTS idx_employees_logout_time ON employees(logout_time);
CREATE INDEX IF NOT EXISTS idx_employees_home_coords ON employees(home_lat, home_lng);
CREATE INDEX IF NOT EXISTS idx_employees_pickup_coords ON employees(pickup_lat, pickup_lng);
CREATE INDEX IF NOT EXISTS idx_employees_drop_coords ON employees(drop_lat, drop_lng);

-- =========================================================
-- SESSIONS
-- =========================================================
CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL,
  role        TEXT NOT NULL CHECK(role IN ('admin','driver','employee')),
  token       TEXT NOT NULL UNIQUE,
  expires_at  TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_role ON sessions(user_id, role);

-- =========================================================
-- ROUTE NUMBERS
-- =========================================================
CREATE TABLE IF NOT EXISTS route_numbers (
  id           TEXT PRIMARY KEY,
  route_no     TEXT NOT NULL UNIQUE,
  trip_day     TEXT NOT NULL,
  created_at   TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_route_no_global ON route_numbers(route_no);
CREATE INDEX IF NOT EXISTS idx_route_day ON route_numbers(trip_day);

-- =========================================================
-- TRIPS
-- =========================================================
CREATE TABLE IF NOT EXISTS trips (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  route_no         TEXT NOT NULL UNIQUE,
  trip_day         TEXT NOT NULL,
  operation        TEXT NOT NULL CHECK(operation IN ('pickup','drop')),
  trip_type        TEXT NOT NULL CHECK(trip_type IN ('pickup','drop')),
  schedule_time    TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'created'
                   CHECK(status IN ('created','assigned','started','completed','cancelled')),
  admin_id         TEXT,
  driver_id        TEXT,
  vehicle_type     TEXT,
  office_lat       REAL,
  office_lng       REAL,
  total_km         REAL DEFAULT 0,
  polyline         TEXT,
  route_json       TEXT,
  start_time       TEXT,
  end_time         TEXT,
  start_otp_hash   TEXT,
  start_otp_expiry TEXT,
  end_otp_hash     TEXT,
  end_otp_expiry   TEXT,
  last_lat         REAL,
  last_lng         REAL,
  last_location_at TEXT,
  cancel_reason    TEXT,
  cancelled_by     TEXT,
  cancelled_at     TEXT,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL,
  route_revision   INTEGER DEFAULT 1,
  FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE SET NULL,
  FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trips_route_no ON trips(route_no);
CREATE INDEX IF NOT EXISTS idx_trips_day ON trips(trip_day);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_driver ON trips(driver_id);
CREATE INDEX IF NOT EXISTS idx_trips_operation_time ON trips(operation, schedule_time);

-- =========================================================
-- TRIP EMPLOYEES
-- =========================================================
CREATE TABLE IF NOT EXISTS trip_employees (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id               INTEGER NOT NULL,
  employee_id           TEXT NOT NULL,
  sequence_no           INTEGER,
  is_no_show            INTEGER NOT NULL DEFAULT 0,
  no_show_marked_at     TEXT,
  no_show_marked_by     TEXT,
  no_show_reason        TEXT,
  created_at            TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
  FOREIGN KEY(no_show_marked_by) REFERENCES drivers(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_employee ON trip_employees(trip_id, employee_id);
CREATE INDEX IF NOT EXISTS idx_trip_employees_trip ON trip_employees(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_employees_employee ON trip_employees(employee_id);

-- =========================================================
-- DRIVER HOME TOWN REQUESTS
-- =========================================================
CREATE TABLE IF NOT EXISTS driver_hometown_requests (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  driver_id    TEXT NOT NULL,
  requested_home_town TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'pending'
               CHECK(status IN ('pending','approved','rejected')),
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
);

-- =========================================================
-- DRIVER REQUESTS
-- =========================================================
CREATE TABLE IF NOT EXISTS driver_requests (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  mobile       TEXT NOT NULL,
  dl_no        TEXT NOT NULL,
  cab_no       TEXT NOT NULL,
  vehicle_type TEXT,
  home_town    TEXT,
  status       TEXT NOT NULL DEFAULT 'Pending'
               CHECK(status IN ('Pending','Approved','Rejected')),
  review_note  TEXT,
  reviewed_at  TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT
);

-- =========================================================
-- EMPLOYEE REQUESTS
-- =========================================================
CREATE TABLE IF NOT EXISTS employee_requests (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  mobile       TEXT NOT NULL,
  email        TEXT,
  login_time   TEXT,
  logout_time  TEXT,
  home_address TEXT,
  lat          REAL,
  lng          REAL,
  status       TEXT NOT NULL DEFAULT 'Pending'
               CHECK(status IN ('Pending','Approved','Rejected')),
  review_note  TEXT,
  reviewed_at  TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT
);

-- =========================================================
-- EMPLOYEE ABSENCE REQUESTS
-- =========================================================
CREATE TABLE IF NOT EXISTS employee_absences (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id     TEXT NOT NULL,
  absence_date    TEXT NOT NULL,
  reason          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','approved','rejected')),
  requested_at    TEXT NOT NULL,
  reviewed_at     TEXT,
  reviewed_by     TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
  FOREIGN KEY(reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
);

-- Legacy-compatible absence table used by some older routes
CREATE TABLE IF NOT EXISTS employee_absence_requests (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id     TEXT NOT NULL,
  absent_date     TEXT NOT NULL,
  reason          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','approved','rejected')),
  created_at      TEXT NOT NULL,
  updated_at      TEXT,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS absence_request_batches (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id       TEXT NOT NULL,
  request_kind      TEXT NOT NULL
                    CHECK(request_kind IN ('absence', 'cancel')),
  original_request_id INTEGER,
  from_date         TEXT NOT NULL,
  to_date           TEXT NOT NULL,
  total_days        INTEGER NOT NULL DEFAULT 1,
  reason            TEXT,
  status            TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'approved', 'rejected')),
  admin_reason      TEXT,
  reviewed_by       TEXT,
  reviewed_at       TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
  FOREIGN KEY(original_request_id) REFERENCES absence_request_batches(id) ON DELETE SET NULL,
  FOREIGN KEY(reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS absence_request_batch_dates (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id        INTEGER NOT NULL,
  absence_date      TEXT NOT NULL,
  created_at        TEXT NOT NULL,
  UNIQUE(request_id, absence_date),
  FOREIGN KEY(request_id) REFERENCES absence_request_batches(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_absence_batch_employee_status
  ON absence_request_batches(employee_id, status, request_kind);

CREATE INDEX IF NOT EXISTS idx_absence_batch_dates_date
  ON absence_request_batch_dates(absence_date);

-- Canonical employee trip exception/preference requests (used in eligibility filters)
CREATE TABLE IF NOT EXISTS employee_trip_requests (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id     TEXT NOT NULL,
  request_type    TEXT NOT NULL,
  request_date    TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','approved','rejected')),
  reason          TEXT,
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(employee_id, request_type, request_date),
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_employee_trip_req_status_date
  ON employee_trip_requests(status, request_date);

-- =========================================================
-- VEHICLE / DRIVER SWAP REQUESTS
-- =========================================================
CREATE TABLE IF NOT EXISTS swap_requests (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id                 INTEGER NOT NULL,
  old_driver_id           TEXT NOT NULL,
  new_driver_id           TEXT,
  new_driver_name         TEXT,
  new_driver_mobile       TEXT,
  new_cab_no              TEXT,
  proof_image_path        TEXT,
  note                    TEXT,
  status                  TEXT NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending','approved','rejected')),
  admin_notes             TEXT,
  reviewed_by             TEXT,
  reviewed_at             TEXT,
  created_at              TEXT NOT NULL,
  updated_at              TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
  FOREIGN KEY(old_driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
  FOREIGN KEY(new_driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
  FOREIGN KEY(reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
);

-- =========================================================
-- DRIVER LOCATION HISTORY
-- =========================================================
CREATE TABLE IF NOT EXISTS driver_location_history (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id     INTEGER,
  driver_id   TEXT NOT NULL,
  route_no    TEXT,
  latitude    REAL NOT NULL,
  longitude   REAL NOT NULL,
  accuracy    REAL,
  speed       REAL,
  recorded_at TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE SET NULL,
  FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_driver_location_trip ON driver_location_history(trip_id);
CREATE INDEX IF NOT EXISTS idx_driver_location_route ON driver_location_history(route_no);
CREATE INDEX IF NOT EXISTS idx_driver_location_driver_time ON driver_location_history(driver_id, recorded_at);

-- =========================================================
-- DRIVER LOCATIONS (Latest)
-- =========================================================
CREATE TABLE IF NOT EXISTS driver_locations (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  driver_id     TEXT NOT NULL UNIQUE,
  trip_id       INTEGER,
  route_no      TEXT,
  latitude      REAL NOT NULL,
  longitude     REAL NOT NULL,
  accuracy      REAL,
  speed         REAL,
  updated_at    TEXT NOT NULL,
  FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE SET NULL
);

-- Real-time latest location per (driver, route), used by tracking routes/services
CREATE TABLE IF NOT EXISTS driver_live_locations (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  driver_id     TEXT NOT NULL,
  route_no      TEXT NOT NULL,
  trip_id       INTEGER,
  latitude      REAL NOT NULL,
  longitude     REAL NOT NULL,
  speed         REAL,
  heading       REAL,
  accuracy      REAL,
  device_time   TEXT,
  updated_at    TEXT NOT NULL,
  FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_live_route ON driver_live_locations(driver_id, route_no);
CREATE INDEX IF NOT EXISTS idx_driver_live_route ON driver_live_locations(route_no, updated_at);

-- =========================================================
-- TRIP OTPs
-- =========================================================
CREATE TABLE IF NOT EXISTS trip_otps (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id      INTEGER NOT NULL,
  employee_id  TEXT,
  otp_type     TEXT NOT NULL CHECK(otp_type IN ('start', 'end')),
  otp_hash     TEXT NOT NULL,
  otp_length   INTEGER DEFAULT 6,
  expires_at   TEXT NOT NULL,
  is_used      INTEGER NOT NULL DEFAULT 0,
  used_at      TEXT,
  verified_by  TEXT,
  attempts     INTEGER DEFAULT 0,
  last_attempt_at TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
  FOREIGN KEY(verified_by) REFERENCES drivers(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_otp_type ON trip_otps(trip_id, otp_type);

-- =========================================================
-- OTP AUDIT LOG
-- =========================================================
CREATE TABLE IF NOT EXISTS otp_audit_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id         INTEGER NOT NULL,
  otp_type        TEXT NOT NULL,
  employee_id     TEXT,
  driver_id       TEXT,
  action          TEXT NOT NULL CHECK(action IN ('generated', 'verify_attempt', 'verify_success', 'verify_failed', 'expired', 'marked_used')),
  otp_input       TEXT,
  reason          TEXT,
  created_at      TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

-- =========================================================
-- CAB ROTATION
-- =========================================================
CREATE TABLE IF NOT EXISTS cab_rotation_state (
  cab_no          TEXT PRIMARY KEY,
  last_bucket     TEXT,
  last_trip_day   TEXT,
  trip_count      INTEGER DEFAULT 0,
  total_km        REAL DEFAULT 0,
  updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trip_cab_history (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id         INTEGER NOT NULL,
  cab_no          TEXT NOT NULL,
  driver_id       TEXT,
  trip_day        TEXT NOT NULL,
  total_km        REAL DEFAULT 0,
  bucket          TEXT,
  operation       TEXT,
  created_at      TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
  FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL
);

-- =========================================================
-- SOS ALERTS
-- =========================================================
CREATE TABLE IF NOT EXISTS sos_alerts (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id      INTEGER,
  employee_id  TEXT NOT NULL,
  lat          REAL,
  lng          REAL,
  resolved     INTEGER DEFAULT 0,
  resolved_by  TEXT,
  resolved_at  TEXT,
  created_at   TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE SET NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
  FOREIGN KEY(resolved_by) REFERENCES admins(id) ON DELETE SET NULL
);

-- =========================================================
-- TRIP RATINGS
-- =========================================================
CREATE TABLE IF NOT EXISTS trip_ratings (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id      INTEGER NOT NULL,
  employee_id  TEXT NOT NULL,
  rating       INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
  feedback     TEXT,
  created_at   TEXT NOT NULL,
  FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- =========================================================
-- CABS (Stand-alone)
-- =========================================================
CREATE TABLE IF NOT EXISTS cabs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reg_no          TEXT NOT NULL UNIQUE,
    model           TEXT,
    capacity        INTEGER NOT NULL DEFAULT 4,
    fuel_type       TEXT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'maintenance', 'retired')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- TRIP GROUPS
-- =========================================================
CREATE TABLE IF NOT EXISTS trip_groups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER,
    group_type      TEXT NOT NULL CHECK(group_type IN ('pickup', 'drop')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trip_group_members (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id        INTEGER NOT NULL,
    employee_id     TEXT NOT NULL,
    pickup_order    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'assigned',
    FOREIGN KEY(group_id) REFERENCES trip_groups(id) ON DELETE CASCADE,
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- =========================================================
-- ADMIN AUDIT & NOTIFICATIONS
-- =========================================================
CREATE TABLE IF NOT EXISTS admin_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        TEXT,
    action          TEXT NOT NULL,
    target_type     TEXT,
    target_id       TEXT,
    details         TEXT,
    ip_address      TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS admin_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    is_read BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- TRIP ROUTES & EVENTS
-- =========================================================
CREATE TABLE IF NOT EXISTS trip_routes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER NOT NULL,
    route_index     INTEGER DEFAULT 0,
    polyline        TEXT,
    distance_km     REAL DEFAULT 0,
    duration_mins   REAL DEFAULT 0,
    via             TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trip_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER,
    route_no        TEXT,
    event_type      TEXT NOT NULL,
    actor_role      TEXT,
    actor_id        TEXT,
    payload_json    TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

-- =========================================================
-- PARTIAL INDEXES & FINAL SETUP
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_trips_driver_active ON trips(driver_id) WHERE status IN ('assigned', 'started');
CREATE INDEX IF NOT EXISTS idx_tgm_status_employee ON trip_group_members(status, employee_id) WHERE status IN ('assigned', 'picked_up');

COMMIT;
