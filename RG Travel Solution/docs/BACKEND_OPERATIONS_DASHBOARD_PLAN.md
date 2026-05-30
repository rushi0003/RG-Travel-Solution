# Backend Operations Dashboard Plan

## Purpose

Create a separate Flutter dashboard for backend operations without breaking the current travel flow. The new dashboard should sit on top of the existing Flask admin/trip APIs and reuse stable screens and services where possible.

This document is Step 1: project audit, scope freeze, and implementation plan.

## Current Project Read

### Frontend

- Entry flow starts in `rg_travel_flutter/lib/main.dart` and routes through `rg_travel_flutter/lib/app.dart`.
- Admin navigation currently lands on `rg_travel_flutter/lib/screens/admin/admin_dashboard.dart`.
- The current admin dashboard is a large, stateful, all-in-one screen that already mixes:
  - create group and assign
  - live trips
  - drivers
  - employees
  - trip history
  - live tracking
  - helpdesk
  - SOS
- Separate admin feature screens already exist and can be reused:
  - `create_group_assign_screen.dart`
  - `live_trips_screen.dart`
  - `drivers_screen.dart`
  - `employees_screen.dart`
  - `trip_history_screen.dart`
  - `live_tracking_screen.dart`
  - `admin_sos_screen.dart`
  - `admin_notifications_screen.dart`
  - `admin_helpdesk_screen.dart`

### Backend

- Flask app bootstraps in `rg_travel_backend/app.py`.
- Core admin operations are exposed from `rg_travel_backend/routes/admin_routes.py`.
- Advanced trip orchestration is exposed from `rg_travel_backend/routes/trip_creation_v2_routes.py`.
- Existing backend operations already cover most dashboard needs:
  - admin profile
  - driver requests and driver changes
  - employee requests and employee changes
  - drivers CRUD-lite
  - employees CRUD-lite
  - create groups and assign trips
  - live trips
  - trip cancel and complete
  - cab swap and trip override
  - online drivers and route tracking
  - swap requests
  - helpdesk
  - SOS alerts
  - absence requests and absent employees

### Service Layer

- Flutter already has `rg_travel_flutter/lib/services/admin_service.dart`.
- Backend already has orchestration and lifecycle services for trip creation, validation, overrides, tracking, routing, audit, availability, and notifications.

## Problem With Current Admin UI

- `admin_dashboard.dart` is acting as both dashboard shell and feature implementation.
- Data fetching, polling, form logic, and navigation are tightly coupled in one screen.
- Backend operations exist, but the UI does not present them as a dedicated operations console.
- This makes expansion risky and slows backend-facing admin work.

## Target Outcome

Build a separate `Backend Operations Dashboard` in Flutter that becomes the new admin operations shell while keeping existing backend APIs and existing business rules intact.

## Proposed Dashboard Information Architecture

### Primary Sections

1. Overview
2. Trip Operations
3. Request Queue
4. Fleet and Drivers
5. Employees
6. Tracking
7. Safety and Support
8. History and Audit

### Section Mapping

- Overview
  - KPI cards
  - active trips
  - pending approvals
  - online drivers
  - SOS count
  - unresolved helpdesk count
- Trip Operations
  - create group and assign
  - live trips
  - trip overrides
  - cancel and complete actions
- Request Queue
  - driver requests
  - employee requests
  - employee change requests
  - driver change requests
  - swap requests
  - trip cancel requests
  - absence requests
- Fleet and Drivers
  - drivers list
  - add and edit driver
  - vehicle type and cab allocation visibility
  - driver availability and online status
- Employees
  - employees list
  - employee updates
  - absent employees
- Tracking
  - online drivers
  - route tracking
  - trip-level driver location
- Safety and Support
  - SOS alerts
  - helpdesk tickets
- History and Audit
  - trip history
  - later extension: audit events from backend audit service

## Reuse Strategy

### Reuse Without Rewrite

- Reuse the existing admin feature screens as content panels where they are already stable.
- Reuse `AdminService` first, then refactor it only where the new dashboard needs cleaner grouped methods.
- Reuse backend endpoints as-is for Step 2 and Step 3 unless a hard blocker appears.

### New UI Layer To Add

- New screen:
  - `rg_travel_flutter/lib/screens/admin/backend_operations_dashboard.dart`
- New supporting widgets:
  - dashboard sidebar
  - overview stat cards
  - operations section header
  - request queue badges
  - responsive content shell

### Routing Change

- Add a dedicated route for the new dashboard.
- Point admin login flow to the new operations dashboard after Step 2 is stable.
- Keep the current `AdminDashboard` reachable during migration as fallback.

## API Mapping For The New Dashboard

### Already Available From `admin_routes.py`

- `/api/admin/profile/<admin_id>`
- `/api/admin/driver-requests`
- `/api/admin/driver-requests/<id>/approve`
- `/api/admin/driver-requests/<id>/reject`
- `/api/admin/driver-change-requests`
- `/api/admin/driver-change-requests/<id>/approve`
- `/api/admin/driver-change-requests/<id>/reject`
- `/api/admin/employee-requests`
- `/api/admin/employee-requests/<id>/approve`
- `/api/admin/employee-requests/<id>/reject`
- `/api/admin/employee-change-requests`
- `/api/admin/employee-change-requests/<id>/approve`
- `/api/admin/employee-change-requests/<id>/reject`
- `/api/admin/drivers`
- `/api/admin/drivers/<driver_id>`
- `/api/admin/employees`
- `/api/admin/employees/<emp_id>`
- `/api/admin/groups/create-and-assign`
- `/api/admin/trips/live`
- `/api/admin/trips/<trip_id>`
- `/api/admin/trips/<trip_id>/cancel`
- `/api/admin/trips/<trip_id>/complete`
- `/api/admin/trips/<trip_id>/override`
- `/api/admin/trips/<trip_id>/swap-cab`
- `/api/admin/drivers/online`
- `/api/admin/routes/<route_no>/driver-location`
- `/api/admin/trip-cancel-requests`
- `/api/admin/trip-cancel-requests/<id>/approve`
- `/api/admin/trip-cancel-requests/<id>/reject`
- `/api/admin/swap-requests`
- `/api/admin/swap-requests/<id>/approve`
- `/api/admin/swap-requests/<id>/reject`
- `/api/admin/helpdesk`
- `/api/admin/helpdesk/<ticket_id>/resolve`
- `/api/admin/sos-alerts`
- `/api/admin/sos-alerts/<alert_id>/resolve`
- `/api/admin/absence-requests`
- `/api/admin/absence-requests/<id>/approve`
- `/api/admin/absence-requests/<id>/reject`
- `/api/admin/absent-employees`
- `/api/admin/absent-employees/<employee_id>/remove`

### Available From `trip_creation_v2_routes.py`

- `/api/v2/trips/preview`
- `/api/v2/trips/create`
- `/api/v2/trips/assign`
- `/api/v2/trips/active`
- `/api/v2/trips/<trip_id>`

## Delivery Plan

### Step 1

Audit the existing frontend and backend, freeze scope, define dashboard structure, define route and API reuse plan, and identify migration-safe entry points.

Status: complete

### Step 2

Create the new dashboard shell with:

- dedicated route
- responsive sidebar
- top summary area
- section switching
- fallback navigation to current admin screens

### Step 3

Plug existing modules into the new shell:

- trip operations
- request queue
- drivers
- employees
- tracking
- support
- history

### Step 4

Refactor shared data loading and actions:

- central section state
- polling rules
- badge counts
- action feedback
- loading and error states

### Step 5

Verify:

- admin login lands correctly
- every section loads
- major approve/reject/cancel/complete actions work
- mobile and desktop layout both hold

## Guardrails

- Do not replace backend business logic while building the new dashboard.
- Do not delete the current admin dashboard until the new route is stable.
- Prefer composition over another large single-file screen.
- Keep existing API paths unless backend gaps are proven.

## Immediate Next Build Step

Step 2 will create the new operations dashboard shell and wire it into Flutter routing without breaking the current admin flow.
