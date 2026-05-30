# RG Travel Solution - AI Project Deep Dive

Last updated: 2026-04-19

## 1. Document cha purpose

Hi single handoff document dusarya AI model la ha full project lavkar ani deeply samjawa mhanun tayar keli aahe. Repo madhe khup docs ahet, pan actual runtime understanding sathi hi file primary source manavi.

Ya document madhe:

- full repo structure samjun sangitle aahe
- runtime architecture explain kele aahe
- backend, main Flutter app, operations app yanche roles clarify kele aahet
- data models, DB schema, and role-wise workflows deep level var explain kele aahet
- important inconsistencies ani assumptions explicitly mention kele aahet

## 2. Big Picture Summary

`RG Travel Solution` ha commute / employee transport management system aahe.

System che 3 major runtime parts:

1. `rg_travel_backend`
   Flask + SQLite backend
   Auth, trip creation, approvals, tracking, OTP, SOS, absence, helpdesk, billing, swap/cancel workflows handle karto.

2. `rg_travel_flutter`
   Main end-user Flutter app
   Ekach app madhun Admin, Driver, Employee ya 3 roles sathi UI available aahe.

3. `rg_backend_operations_app`
   Separate Flutter operations dashboard
   Backend/admin operations monitoring, request queues, trip operations, support/fleet style admin tooling sathi.

Core business idea:

- Admin company-level transport manage karto
- Employees transport request/use kartat
- Drivers trips execute kartat
- Trips route number based track hotat
- OTP + live GPS + admin override + support workflows system la operational banavtat

## 3. Repo Structure

Main useful folders:

- `docs/`
  consolidated technical docs
- `rg_travel_backend/`
  Flask backend
- `rg_travel_flutter/`
  primary Flutter app
- `rg_backend_operations_app/`
  secondary Flutter operations app
- `tests/`
  root-level test/support scripts

Root madhe khup historical docs and reports aahet. Te useful aahet, pan current runtime samjun ghyaycha asel tar code-first reading karavi:

1. `rg_travel_backend/app.py`
2. `rg_travel_backend/routes/`
3. `rg_travel_backend/services/`
4. `rg_travel_backend/db/schema.sql`
5. `rg_travel_flutter/lib/main.dart`
6. `rg_travel_flutter/lib/app.dart`
7. `rg_travel_flutter/lib/services/`
8. `rg_backend_operations_app/lib/app.dart`

## 4. Runtime Architecture

### 4.1 Backend architecture

Backend hybrid style madhye build zala aahe:

- ek large central file: `rg_travel_backend/app.py`
- plus modular blueprints under `rg_travel_backend/routes/`
- plus domain/business services under `rg_travel_backend/services/`

`app.py`:

- Flask app create karto
- config apply karto
- DB init karto
- core routes register karto
- blueprints register karto
- Socket.IO initialize karto
- kahi legacy inline endpoints pan define karto

Mhanje backend pure-clean layered architecture nahi, tar "monolith + modular extensions" asa hybrid aahe.

### 4.2 Main Flutter app architecture

Main app `rg_travel_flutter` madhe:

- `main.dart` session varun initial route decide karto
- `app.dart` central route resolver aahe
- role-based screens आहेत
- services direct backend HTTP call kartat
- `SessionStore` shared_preferences madhe session store karto

He app strictly layered नाही. UI screens ani services direct coupling aahe. Pan structure understandable aahe:

- `models/`
- `services/`
- `screens/`
- `core/config`, `core/storage`, `core/theme`

### 4.3 Operations Flutter app architecture

`rg_backend_operations_app` main product app pasun separate aahe.

Purpose:

- operations dashboard
- request queue
- trip operations
- fleet operations
- support operations

He app existing Flask backend laच call karto. Separate backend नाही.

## 5. Main Product Flow

System cha end-to-end business flow roughly asa aahe:

1. Backend boot hoto
2. SQLite schema init होते
3. Admin login karto
4. Driver / Employee requests admin approval sathi create hotat
5. Admin employees and drivers onboard karto
6. Admin trip grouping / trip creation karto
7. Driver trip accept/execute karto
8. OTP verify करून trip start/end hoto
9. Driver live location push karto
10. Admin ani employee tracking पाहू shaktat
11. Driver no-show / swap / cancel request करू shakto
12. Employee absence / profile change / SOS / rating / helpdesk करू shakto
13. Admin review, override, support, billing, history handle karto

## 6. Role Model

### 6.1 Admin

Admin हा tenant/company owner saman aahe.

Admin responsibilities:

- own company profile
- approve driver requests
- approve employee requests
- create drivers/employees manually
- group employees into trips
- assign drivers/vehicles
- monitor live trips
- manage trip overrides
- resolve SOS/helpdesk
- review absence requests
- manage billing records

### 6.2 Driver

Driver operational executor aahe.

Driver responsibilities:

- login
- select/switch company context if mapped to multiple admins
- view assigned trip
- update profile through change request
- request hometown/go-home trip preference
- push live GPS
- verify OTP / start / complete trip
- mark employee no-show
- create emergency swap request
- create trip cancel request
- raise helpdesk ticket

### 6.3 Employee

Employee commute consumer aahe.

Employee responsibilities:

- login
- view own trip
- request profile changes
- request absence / cancel absence
- view live driver tracking
- fetch OTP visibility
- trigger SOS
- rate completed trip
- raise helpdesk ticket

### 6.4 Operations admin

Separate app madhla operations user technically admin auth use karto, pan UI focus backend operations var aahe.

## 7. Data / Tenant Model

System cha current conceptual tenancy model:

- one admin = one company / office transport domain
- employee belongs to one admin/company
- driver can be reused across multiple admins/companies
- trips are admin-scoped
- many APIs authenticated user role + admin scope enforce kartat

Important practical point:

Project history mule schema/docs kahi ठिकाणी old आहेत. Runtime intent मात्र clear aahe:

- admin isolation important aahe
- employee single-company aahe
- driver multi-company capable aahe
- driver current active company concept aahe

## 8. Backend Entry Points

Important files:

- `rg_travel_backend/app.py`
- `rg_travel_backend/__init__.py`
- `rg_travel_backend/wsgi.py`

Typical backend startup:

- `app.py` dev/runtime main entry
- `__init__.py` package export
- `wsgi.py` production-style app exposure

`create_app()` flow:

1. Flask app create
2. config apply
3. CORS setup
4. DB init
5. core utility routes register
6. blueprints register
7. Socket.IO attach

## 9. Important Backend Route Modules

### 9.1 `auth_routes.py`

Handles:

- admin login
- driver login
- employee login
- admin/company listing
- driver signup request
- employee signup request

### 9.2 `admin_routes.py`

Ha सर्वात मोठा operational route module aahe.

Handles:

- admin profile
- admin account management
- driver requests approval/rejection
- employee requests approval/rejection
- driver CRUD
- employee CRUD
- create group and assign trip
- live trips
- cancel/complete trip
- trip cab swap
- trip employee add/remove
- OTP generation
- online drivers
- route driver location
- trip cancel requests review
- swap requests review
- driver/employee change requests review
- helpdesk tickets review
- trip details and override
- SOS alerts review
- absence requests review
- billing APIs

### 9.3 `driver_routes.py`

Handles:

- driver company list / switch
- driver profile
- driver profile change request
- hometown/go-home request
- assigned trip
- trip history
- GPS update/latest
- OTP verify / trip start / trip complete
- employee no-show
- swap request
- trip cancel request
- helpdesk ticket
- list driver trips

### 9.4 `employee_routes.py`

Handles:

- employee profile
- employee profile update request
- absence request
- absence cancel request
- current trip
- trip history
- view driver location
- get trip OTP
- office location
- SOS trigger
- trip rating
- helpdesk ticket

### 9.5 `tracking_routes.py`

Handles:

- GPS ingestion
- route tracking authorization
- latest route tracking
- route history

### 9.6 `otp_routes.py`

Handles:

- fetch trip details by route
- generate/fetch OTP
- verify OTP
- OTP status

### 9.7 `grouping_routes.py`

Handles:

- admin time slots
- available vehicles
- available employees
- auto grouping
- groups create
- trip creation step flow
- override/assign trip

### 9.8 `trip_creation_v2_routes.py`

This is advanced orchestration layer.

Handles:

- preview trip
- create trip
- get trip details
- active trips
- start trip
- trip history export/list
- move employee between trips
- swap driver
- complete trip
- available drivers
- scheduled times
- NLP-like search for vehicles/employees
- group creation/list/delete/edit

### 9.9 Supporting route modules

- `health_routes.py`
- `notification_routes.py`
- `availability_routes.py`
- `admin_requests_routes.py`
- `driver_v2_routes.py`

## 10. Backend Services Map

Backend services business logic cha main source aahet. Important services:

### 10.1 Grouping / planning services

- `grouping_service.py`
- `auto_grouping_service.py`
- `geo_clustering.py`
- `capacity_optimizer.py`
- `hybrid_group_planner.py`
- `route_planning.py`
- `routing_service.py`

Purpose:

- employee proximity grouping
- 4-seater / 6-seater capacity planning
- stop ordering
- route distance estimation
- hybrid planning provider integration

### 10.2 Assignment / orchestration services

- `assignment_service.py`
- `driver_assignment.py`
- `trip_orchestration_service.py`
- `trip_validation_service.py`

Purpose:

- eligible drivers select karne
- workload/rotation consider karne
- go-home request aware assignment
- trip preview/create/assign pipeline
- resource sufficiency validation

### 10.3 Lifecycle / override services

- `trip_lifecycle_service.py`
- `trip_override_service.py`
- `admin_override_service.py`
- `trip_schedule_guard.py`

Purpose:

- trip complete/cancel
- no-show mark
- swap approval apply
- move employee / change driver
- schedule gate evaluation

### 10.4 Tracking / realtime services

- `tracking_service.py`
- `socket_service.py`
- `audit_service.py`

Purpose:

- driver location store
- latest route data
- websocket join/broadcast
- audit logs for tracking/security

### 10.5 Employee support services

- `absence_flow_service.py`
- helpdesk and SOS logic route layer + tables madhye integrated

### 10.6 Billing and history services

- `admin_billing_service.py`
- `trip_history_service.py`

### 10.7 Validation and utility services

- `validation_service.py`
- geocoding related services

## 11. Database Overview

Primary schema source:

- `rg_travel_backend/db/schema.sql`

Runtime schema static नाही because:

- migrations/scripts आहेत
- code-level ensure-table / ensure-column patterns आहेत
- old schema docs kahi ठिकाणी lag hotat

Mhanun dusarya AI model ne "schema.sql + route code + ensure_* helpers" he tinhi पाहावे.

## 12. Core Database Tables

### 12.1 Identity and auth

- `admins`
- `drivers`
- `employees`
- `sessions`

### 12.2 Trip core

- `route_numbers`
- `trips`
- `trip_employees`

### 12.3 Request workflows

- `driver_requests`
- `employee_requests`
- `driver_hometown_requests`
- `employee_absences`
- `employee_absence_requests`
- `employee_trip_requests`
- `swap_requests`
- trip cancel request related tables are created/ensured by code
- profile change request related tables are created/ensured by code

### 12.4 Tracking / OTP / audit

- `driver_location_history`
- `driver_locations`
- `driver_live_locations`
- `trip_otps`
- `otp_audit_log`
- `trip_events`
- `admin_audit`
- `admin_notifications`

### 12.5 Additional operations

- `cabs`
- `trip_groups`
- `trip_group_members`
- `trip_routes`
- `trip_cab_history`
- `cab_rotation_state`
- `sos_alerts`
- `trip_ratings`

## 13. Core Data Models

### 13.1 Admin model

Backend conceptual fields:

- `id`
- `name`
- `mobile`
- `email`
- `office_name`
- `office_location`
- `office_address`
- `office_lat`
- `office_lng`
- password hash/salt

Flutter `AdminModel` contains simplified subset:

- `id`
- `name`
- `mobile`
- `officeName`
- `officeAddress`

Important mismatch:

- backend admin ids often TEXT based
- Flutter `AdminModel.id` currently `int`

AI model ne admin id handling करताना type mismatch लक्षात घ्यावा.

### 13.2 Driver model

Backend conceptual fields:

- `id`
- `name`
- `mobile`
- `dl_no`
- `vehicle_no` / `cab_no`
- `vehicle_type`
- `home_town`
- `primary_admin_id`
- `current_admin_id`
- `is_approved`
- `is_online`
- expiry fields

Flutter `DriverModel`:

- `id`
- `name`
- `mobile`
- `dlNo`
- `cabNo`
- `vehicleType`
- `homeTown`
- `homeLat`
- `homeLng`
- `status`
- `goHomeRequested`

### 13.3 Employee model

Backend conceptual fields:

- `id`
- `name`
- `mobile`
- `email`
- `employee_code`
- `login_time`
- `logout_time`
- `home_address`
- `home_lat/home_lng`
- pickup/drop coordinates
- `admin_id`
- active/approved flags

Flutter `EmployeeModel`:

- `id`
- `name`
- `mobile`
- `employeeCode`
- `loginTime`
- `logoutTime`
- `homeAddress`
- optional absence/workflow fields

### 13.4 Trip model

Trip system cha center aahe.

Backend conceptual trip fields:

- `id`
- `route_no`
- `trip_day`
- `operation`
- `trip_type`
- `schedule_time`
- `status`
- `admin_id`
- `driver_id`
- `vehicle_type`
- route geometry and office coords
- `start_time`
- `end_time`
- OTP hash/expiry fields
- live last lat/lng
- cancel metadata

Flutter `TripModel` abstractions:

- `routeNo`
- `id`
- `tripType`
- `status`
- date/time fields
- office info
- cab/driver
- employees/stops
- polyline
- totalKm / duration
- start/end OTP info
- no-show and absent employee ids

### 13.5 Secondary models

Main app madhye additional helper models:

- `DriverRequest`
- `HelpdeskTicket`
- billing models under `admin_billing_model.dart`

Operations app madhye:

- `AdminOperationsSnapshot`

## 14. Authentication Flow

### 14.1 Session style

System bearer token return karto, ani Flutter `SessionStore` madhe he store hote:

- logged_in
- role
- userId
- token
- optional profile fields
- optional extra JSON

Driver sathi extra important:

- selected/current admin context store hou shakto

### 14.2 Main login flows

Admin:

- login screen वर credentials
- backend `/api/auth/admin/login`
- token + profile + admin id expected
- session saved
- route `/admin/dashboard`

Driver:

- `/api/auth/driver/login`
- session saved
- dashboard open
- multi-company असल्यास current admin context important

Employee:

- `/api/auth/employee/login`
- session saved
- dashboard open

### 14.3 Route bootstrap

`rg_travel_flutter/lib/main.dart`:

- Flutter binding initialize
- `SessionStore.isLoggedIn()`
- role + userId read
- initial route choose

`app.dart`:

- `MaterialApp`
- central route handling
- admin routes may resolve admin id from session if explicit argument missing

## 15. Main Flutter App Screen Map

### 15.1 Login

- `screens/login/login_screen.dart`

Single entry point for role-based access.

### 15.2 Admin screens

Important admin screens:

- `admin_dashboard.dart`
- `create_group_assign_screen.dart`
- `drivers_screen.dart`
- `employees_screen.dart`
- `live_trips_screen.dart`
- `live_tracking_screen.dart`
- `trip_history_screen.dart`
- `admin_requests_screen.dart`
- `admin_billing_screen.dart`
- `admin_sos_screen.dart`
- `admin_helpdesk_screen.dart`
- `admin_notifications_screen.dart`

### 15.3 Driver screens

- `driver_dashboard.dart`
- `assigned_trip_screen.dart`
- `driver_profile_screen.dart`
- `otp_screen.dart`
- `driver_history_screen.dart`
- `driver_hometown_screen.dart`
- `driver_emergency_swap_screen.dart`

### 15.4 Employee screens

- `employee_dashboard.dart`
- `my_trip_screen.dart`
- `driver_tracking_screen.dart`
- `employee_absence_screen.dart`
- `employee_history_screen.dart`
- `employee_profile_update.dart`
- `help_desk_screen.dart`

### 15.5 Tracking screens

Separate tracking-oriented screens pan आहेत:

- `screens/tracking/live_tracking_screen.dart`
- `screens/tracking/employee_live_tracking_screen.dart`

## 16. Main Flutter Services Map

### 16.1 `auth_service.dart`

Handles:

- health check
- admin login
- driver login
- employee login
- signup request APIs
- company list APIs

### 16.2 `admin_service.dart`

Most overloaded service.

Handles:

- admin profile
- request approvals
- driver CRUD
- employee CRUD
- trip/group/live tracking/history
- OTP generation
- billing helpers
- admin actions across many modules

### 16.3 `driver_service.dart`

Handles:

- driver profile/trips
- admin driver request support methods
- GPS/trip action APIs
- company switching and related driver flows

Important note:

`driver_service.dart` keval driver UI sathi नाही; kahi admin-drivers screen support methods pan यात आहेत.

### 16.4 `employee_service.dart`

Handles:

- employee profile
- profile change request
- absence request/cancel
- my trip
- trip history
- tracking
- OTP visibility
- helpdesk and related employee operations

### 16.5 Realtime and location services

- `socket_service.dart`
- `location_service.dart`

## 17. Operations App Deep Summary

`rg_backend_operations_app` हा secondary control plane aahe.

Main files:

- `lib/app.dart`
- `lib/screens/backend_operations_dashboard.dart`
- `lib/screens/request_queue_screen.dart`
- `lib/screens/trip_operations_screen.dart`
- `lib/screens/fleet_operations_screen.dart`
- `lib/screens/support_operations_screen.dart`
- `lib/screens/admin_access_screen.dart`

Main services:

- `ops_auth_service.dart`
- `ops_session_store.dart`
- `admin_service.dart`
- `admin_operations_service.dart`
- `admin_access_service.dart`

App flow:

1. bootstrap checks saved base URL
2. saved login present असल्यास dashboard
3. nahi tar ops login screen
4. dashboard sections madhe operations views

He app production customer-facing flow नाही; internal operational tool aahe.

## 18. Trip Creation Flow Deep Dive

Trip creation project cha most complex part aahe.

High-level flow:

1. Admin selects operation
   pickup or drop
2. Employees filter/select hotat
3. Available vehicles/drivers scan hotat
4. Grouping algorithm employees clusters madhe split karto
5. Capacity optimizer 4/6 seat balance karto
6. Route planning stop order / distance estimate karto
7. Driver assignment logic driver select karto
8. Trip record + trip members + route metadata save hote
9. Route number generate hoto
10. Trip assigned/live list madhe दिसतो

Yasathi multiple implementations आहेत:

- old grouping routes
- newer `trip_creation_v2_routes.py`
- orchestration + validation services

Dusarya AI model ne trip-related bug/fix करताना old vs v2 path identify karne फार महत्त्वाचे आहे.

## 19. Driver Trip Execution Flow

Typical runtime:

1. Driver login
2. Driver current company context resolve
3. Assigned trip fetch
4. Driver GPS updates push
5. OTP fetch/verify
6. Trip start
7. Tracking visible to admin/employee
8. Employee no-show mark optionally
9. Swap/cancel request optionally
10. Trip complete

Trip state transitions generally:

- `created`
- `assigned`
- `started` or in UI `in_progress`
- `completed`
- `cancelled`

Important:

UI enums and backend status names fully identical nahi. Mapping check karavi.

## 20. Employee Usage Flow

Employee side main flow:

1. login
2. current trip view
3. trip route / driver details
4. live tracking
5. absence request if needed
6. profile change request
7. SOS if emergency
8. post-trip rating/helpdesk

Employee access always own scope var asava. Direct unrestricted trip visibility expected nahi.

## 21. Tracking Flow

Tracking 2 modes madhye aahe:

1. REST polling
2. Socket.IO realtime support

Backend:

- location tables maintain karto
- latest route/driver location देतो
- websocket join/broadcast routes support karto

Frontend:

- periodic polling intervals `Env` madhe defined आहेत
- location and socket services available आहेत

Tracking consumers:

- driver pushes data
- admin monitors
- employee trip route track karto

## 22. OTP Flow

OTP use trip start/end control sathi hoto.

Backend pieces:

- trip OTP endpoints
- trip OTP tables
- OTP hash/expiry fields
- audit logging

Frontend pieces:

- `otp_screen.dart`
- trip model `OtpInfo`
- admin/employee/driver related service calls

Conceptually:

- trip route or trip id basis var OTP generate/fetch होते
- verification नंतर lifecycle status update hoto

## 23. Request and Approval Workflows

Project madhe multiple approval pipelines आहेत:

### 23.1 Driver signup request

- driver request create
- admin review
- approve or reject
- actual driver entity create/update

### 23.2 Employee signup request

- employee request create
- admin review
- approve or reject

### 23.3 Profile change requests

- driver change request
- employee change request
- admin approve/reject

### 23.4 Absence workflow

- employee submits absence
- admin review
- absence affects trip eligibility
- cancel request also supported

### 23.5 Go-home / hometown workflow

- driver requests hometown preference
- admin review
- assignment logic may bias future trips

### 23.6 Emergency swap / trip cancel workflow

- driver raises request
- admin reviews
- approved change affects trip data/lifecycle

## 24. Billing Flow

Billing functionality exists mainly admin side.

Backend:

- `admin_billing_service.py`
- billing endpoints in `admin_routes.py`

Flutter:

- `admin_billing_model.dart`
- `admin_billing_pdf_service.dart`
- billing screen

Likely purpose:

- billable vehicle assignments
- billable trip summaries
- billing prefill/settings
- billing record generation
- PDF export/save

## 25. Notifications, SOS, Helpdesk

### 25.1 Notifications

Route module:

- `notification_routes.py`

Tables:

- `admin_notifications`

### 25.2 SOS

Employee can SOS trigger karu shakto.
Admin SOS screen ani backend SOS tables/API support आहेत.

### 25.3 Helpdesk

Driver and employee tickets raise karu shaktat.
Admin resolves through helpdesk review APIs/screens.

## 26. Environment and Configuration

### 26.1 Flutter env

Main env file:

- `rg_travel_flutter/lib/core/config/env.dart`

Important defaults:

- dev mode by default
- web base URL: `http://127.0.0.1:5000`
- Android emulator base URL: `http://10.0.2.2:5000`
- API prefix: `/api`

Flags:

- live tracking
- OTP
- auto grouping
- emergency swap
- smart search

### 26.2 Backend env

Root `.env` and backend config modules used आहेत.
Actual secrets/config resolve:

- `rg_travel_backend/config/`

## 27. Important Inconsistencies and Caveats

Dusarya AI model sathi हा section khup important aahe.

### 27.1 Docs > code mismatch

Repo madhe khup docs आहेत. Saglya docs latest नाहीत.
Always trust:

1. route code
2. service code
3. current schema/runtime helpers

### 27.2 Backend is not purely modular

`app.py` itself still contains legacy endpoints.
Same domain sathi multiple route sources asu shaktat.

### 27.3 ID type mismatch

Admin IDs especially:

- conceptual backend type TEXT asu shakto
- some Flutter models/services int assume kartat

### 27.4 Status naming mismatch

Backend statuses and Flutter enums exact same नसतात:

- backend may use `started`
- Flutter may map `in_progress`
- old code may say `pending` or `created`

### 27.5 Old and v2 trip flows coexist

Trip/group logic duplicate/overlap honyachi शक्यता आहे:

- `grouping_routes.py`
- `trip_creation_v2_routes.py`
- various services

Bug fix before, AI model ne call path identify karava.

### 27.6 Runtime schema evolves in code

Kahi tables/columns code-level ensure hotat.
Mhanun schema.sql only पाहून final assumptions करू नयेत.

## 28. Fast Onboarding Path for Another AI Model

Jar dusarya AI model ne project samjun पुढे काम करायcha asel tar hi reading order best aahe:

1. `docs/AI_PROJECT_DEEP_DIVE.md`
2. `rg_travel_backend/app.py`
3. `rg_travel_backend/routes/admin_routes.py`
4. `rg_travel_backend/routes/driver_routes.py`
5. `rg_travel_backend/routes/employee_routes.py`
6. `rg_travel_backend/routes/trip_creation_v2_routes.py`
7. `rg_travel_backend/services/trip_orchestration_service.py`
8. `rg_travel_backend/services/grouping_service.py`
9. `rg_travel_backend/db/schema.sql`
10. `rg_travel_flutter/lib/main.dart`
11. `rg_travel_flutter/lib/app.dart`
12. `rg_travel_flutter/lib/services/admin_service.dart`
13. `rg_travel_flutter/lib/services/driver_service.dart`
14. `rg_travel_flutter/lib/services/employee_service.dart`
15. relevant screen file for target feature

## 29. Suggested Mental Model

Ha project samjun ghyaycha easiest mental model:

- company-scoped transport system
- admin = planner + approver + controller
- employee = passenger
- driver = executor
- trip = central operational object
- route number = human/runtime tracking identity
- OTP + GPS + approvals = operational trust layer
- billing/SOS/helpdesk = support layer
- operations app = internal control plane

## 30. Final Summary

`RG Travel Solution` हा simple CRUD app नाही. Ha operational transport orchestration system aahe jyat:

- multi-role auth
- tenant-aware data separation
- request approval pipelines
- employee grouping and cab capacity planning
- trip orchestration
- realtime tracking
- OTP-guarded trip lifecycle
- support/SOS/helpdesk
- billing and operations monitoring

Dusarya AI model ne kaam करताना सर्वात important goshti:

- exact route path identify karne
- old flow vs v2 flow differentiate karne
- admin scope and role access respect karne
- model/status/id mismatches manually verify karne
- docs पेक्षा runtime code वर trust thevne

