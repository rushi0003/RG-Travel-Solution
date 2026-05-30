# RG Travel Solution DB Schema

Database: SQLite  
Primary runtime schema source: backend code (`init_db`, `schema_guard`, route-level guards)  
Default DB file: `rg_travel_backend/rg_travel.db` or `RG_DB_PATH`

## Overview

Current system is a multi-admin transportation platform with strict tenant separation:

- One `admin` manages one company/transport system.
- `employees` belong to exactly one admin/company.
- `drivers` can belong to multiple admins/companies.
- `trips`, signup requests, and operational views are scoped by `admin_id`.
- Driver dashboard uses a selected company (`drivers.current_admin_id`) to decide which data and trips are visible.

This document reflects the effective runtime schema after backend guards/migrations, not just the oldest base SQL file.

## Core tenant model

### `admins`
Stores admin account and office/company profile.

Important columns:
- `id` TEXT primary key
- `name`
- `mobile`
- `email`
- `office_name`
- `office_location`
- `office_address`
- `office_lat` optional
- `office_lng` optional
- `password_salt`
- `password_hash`
- `created_at`
- `updated_at`

### `employees`
Employee is single-company.

Important columns:
- `id` INTEGER or TEXT depending on deployment
- `name`
- `mobile`
- `employee_code`
- `login_time`
- `logout_time`
- `home_address`
- `home_lat`
- `home_lng`
- `admin_id` TEXT -> `admins.id`
- `is_active`
- `is_approved`
- `created_at`
- `updated_at`

Rules:
- one employee belongs to one admin/company only
- employee profile, dashboard, trips, history, absence, SOS, helpdesk must resolve through employee's `admin_id`

Indexes commonly enforced:
- employee mobile
- employee timing columns
- `employees.admin_id`

### `drivers`
Driver can work for multiple companies.

Important columns:
- `id` TEXT primary key
- `name`
- `mobile`
- `dl_no`
- `vehicle_no` or legacy `cab_no`
- `vehicle_type`
- `home_town` or legacy `hometown`
- `primary_admin_id` TEXT -> `admins.id`
- `current_admin_id` TEXT -> currently selected company in driver dashboard
- `is_approved`
- `is_online`
- `password_salt`
- `password_hash`
- `created_at`
- `updated_at`

Rules:
- `primary_admin_id` is the original/main company link
- `current_admin_id` is the active company context for dashboard and trip actions
- driver data visibility is constrained through admin mapping, not global visibility

### `driver_admin_assignments`
Join table for multi-company driver access.

Important columns:
- `id` INTEGER primary key
- `driver_id` TEXT -> `drivers.id`
- `admin_id` TEXT -> `admins.id`
- `is_active` INTEGER default 1
- `created_at` optional
- `updated_at` optional

Rules:
- one driver can map to many admins
- admin driver list uses this mapping
- driver company switch dropdown is built from this table

Indexes:
- `driver_id`
- `admin_id`
- `(driver_id, admin_id)` uniqueness/lookup depending on deployment

## Trip domain

### `trips`
Master trip record. This is tenant-scoped.

Important columns:
- `id` INTEGER primary key
- `route_no`
- `trip_day` (`YYYYMMDD` or compatible day key)
- `operation` and/or `trip_type` (`pickup` / `drop`)
- `schedule_time`
- `status`
- `admin_id` TEXT -> `admins.id`
- `driver_id` TEXT -> `drivers.id`
- `vehicle_type`
- `vehicle_no` optional
- `total_km`
- `polyline`
- `start_time`
- `end_time`
- `cancel_reason`
- `office_lat` optional
- `office_lng` optional
- `created_at`
- `updated_at`

Rules:
- every operational trip must belong to one admin/company via `admin_id`
- admin live trips/history must filter by authenticated admin
- driver assigned trips/history/actions must filter by selected `current_admin_id`
- employee trip visibility must filter by employee's own `admin_id`

Indexes commonly used:
- `trip_day`
- `status`
- `driver_id`
- `admin_id`
- `(route_no, trip_day)` uniqueness

### `trip_employees`
Trip membership table.

Important columns:
- `id`
- `trip_id`
- `employee_id`
- `sequence_no`
- `is_no_show` or legacy `no_show`
- `estimated_arrival_time` optional
- `created_at`

Rules:
- employee can be in a trip only through their company-scoped trip
- employee trip history and active trip APIs filter through joined `trips.admin_id`

## Request and workflow tables

### `driver_requests`
Driver signup/approval flow.

Important columns:
- request identity fields
- `admin_id` TEXT -> admin/company receiving the signup
- `status`
- timestamps

Rule:
- driver signup request can be company-specific

### `employee_requests`
Employee signup/approval flow.

Important columns:
- employee request fields
- `admin_id` TEXT -> target admin/company
- `status`
- timestamps

Rule:
- approved employee must be created with that same `admin_id`

### `driver_change_requests`
Pending profile edits from driver.

Common columns:
- `driver_id`
- proposed driver fields
- `status`
- timestamps

### `employee_change_requests`
Pending profile edits from employee.

Common columns:
- `employee_id`
- proposed employee fields
- `status`
- timestamps

### `driver_hometown_requests`
Go-home / hometown priority request flow.

Common columns:
- `driver_id`
- `requested_home_town`
- `home_town` optional legacy mirror
- `travel_date` optional
- `status`
- timestamps

### `swap_requests`
Emergency driver/cab replacement workflow.

Common columns:
- `trip_id`
- `old_driver_id`
- `new_driver_id` optional after approval
- `new_driver_name`
- `new_driver_mobile`
- `new_cab_no`
- `note`
- `proof_image_path`
- `status`
- timestamps

### `trip_cancel_requests`
Driver asks admin to cancel a pre-assigned trip.

Common columns:
- `id`
- `trip_id`
- `driver_id`
- `reason`
- `status`
- `admin_note`
- `reviewed_by`
- `created_at`
- `updated_at`

### Absence-related tables
Exact names can vary by deployment/service layer, but active system supports:

- employee absence request
- absence cancellation request
- admin review state

These flows are logically employee-scoped and therefore indirectly company-scoped through `employees.admin_id`.

## Auth/session tables

### `sessions`
Token/session storage for all roles.

Important columns:
- `id`
- `user_id`
- `role` (`admin`, `driver`, `employee`)
- `token`
- `expires_at`
- `created_at`

Rules:
- admin routes require authenticated admin
- employee routes now require authenticated employee and same-user access
- driver routes now require authenticated driver and same-user access

## Operational notes

### Effective tenant isolation

- Admin sees only their own:
  - employees
  - mapped drivers
  - live trips
  - trip creation resources
  - signup/change/absence requests
- Employee sees only:
  - own profile
  - own company office context
  - own company trips/history
- Driver sees only:
  - companies from `driver_admin_assignments`
  - trips/history/actions for selected `current_admin_id`

### Legacy compatibility

Runtime schema guards handle missing legacy columns/tables and backfill where possible:

- add `employees.admin_id`
- add `drivers.primary_admin_id`
- add `drivers.current_admin_id`
- add request-level `admin_id`
- create `driver_admin_assignments`
- backfill orphan records from existing single-admin/trip data when feasible

## Relationship summary

- `admins 1 -> many employees`
- `admins many <-> many drivers` via `driver_admin_assignments`
- `admins 1 -> many trips`
- `drivers 1 -> many trips`
- `trips 1 -> many trip_employees`
- `employees 1 -> many trip_employees`
- `drivers 1 -> many hometown/swap/cancel workflow records`

## Current implementation references

Primary schema/runtime enforcement lives in:

- `rg_travel_backend/db/schema_guard.py`
- `rg_travel_backend/routes/admin_routes.py`
- `rg_travel_backend/routes/driver_routes.py`
- `rg_travel_backend/routes/employee_routes.py`
- `rg_travel_backend/services/trip_validation_service.py`
- `rg_travel_backend/services/trip_history_service.py`

If this document and runtime differ, treat runtime/backend guards as source of truth.
