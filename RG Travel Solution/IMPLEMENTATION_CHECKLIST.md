# RG TRAVEL SOLUTION - IMPLEMENTATION CHECKLIST v2.0

**Status:** Phase 1 Complete ✅ | Phase 2 Ready 🚀  
**Last Updated:** February 2, 2026

---

## Phase 1: Analysis & Database (✅ COMPLETE)

### Database Schema
- [x] Analyzed current 10 tables
- [x] Added `driver_location_history` table (GPS tracking)
- [x] Added `trip_otps` table (OTP state management)
- [x] Added `otp_audit_log` table (audit trail)
- [x] Enhanced `trip_employees` (no-show tracking)
- [x] Created all required indexes
- [x] Updated [docs/DB_SCHEMA.md](../docs/DB_SCHEMA.md)

### Backend Services
- [x] Analyzed existing services (otp, grouping, routing, tracking)
- [x] Consolidated OTP files (merged duplicates)
- [x] Implemented `create_otp_for_trip()` function
- [x] Implemented `verify_otp_and_mark_used()` function
- [x] Implemented `get_otp_status()` function
- [x] Added `_log_otp_event()` audit logging
- [x] Added security features (constant-time comparison, attempt limiting, expiry)

### Documentation
- [x] Created [ARCHITECTURE_ANALYSIS_AND_FIXES.md](../ARCHITECTURE_ANALYSIS_AND_FIXES.md)
- [x] Created [WINDOWS_SETUP_GUIDE.md](../WINDOWS_SETUP_GUIDE.md)
- [x] Updated [docs/API_DOCS.md](../docs/API_DOCS.md)
- [x] Created [docs/DB_SCHEMA.md](../docs/DB_SCHEMA.md)
- [x] Created [PROJECT_UPDATE_SUMMARY_v2.md](../PROJECT_UPDATE_SUMMARY_v2.md)
- [x] Created [DEVELOPER_QUICK_REFERENCE.md](../DEVELOPER_QUICK_REFERENCE.md)

### Testing
- [x] Created `test_backend.py` test suite
- [x] Added health check tests
- [x] Added OTP service tests
- [x] Added database schema validation tests

---

## Phase 2: Backend Integration (🚀 READY TO START)

### Update Admin Routes (`rg_travel_backend/routes/admin_routes.py`)

#### Task 2.1: Trip Assignment Endpoint
```
Endpoint: POST /api/admin/trips/assign
Current: May use old OTP logic
Required: Call create_otp_for_trip(conn, trip_id)
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `admin_routes.py`
- [ ] Find `POST /api/admin/trips/assign` endpoint
- [ ] Replace old OTP generation with:
  ```python
  from services.otp_service import create_otp_for_trip
  otp_result = create_otp_for_trip(conn, trip_id)
  if not otp_result["success"]:
      return error_response(message=otp_result["message"], code=400)
  ```
- [ ] Test: `curl -X POST http://127.0.0.1:5000/api/admin/trips/assign -d '{"trip_id":42}'`
- [ ] Verify OTP codes generated correctly

#### Task 2.2: Live Tracking Integration
```
Endpoint: GET /api/admin/trips/live
Current: May not use new tracking service fully
Required: Integrate driver_location_history table
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `admin_routes.py`
- [ ] Find live tracking endpoint
- [ ] Add location query: JOIN driver_location_history on active trips
- [ ] Return latest GPS coords (lat, lng, recorded_at)
- [ ] Test: `curl http://127.0.0.1:5000/api/admin/trips/live`

#### Task 2.3: Trip History with No-Show Data
```
Endpoint: GET /api/admin/trips/history
Current: May not include no-show info
Required: Include no_show_marked_at, no_show_marked_by, no_show_reason
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `admin_routes.py`
- [ ] Find trip history endpoint
- [ ] Update query to SELECT no_show fields
- [ ] Return no-show details in response
- [ ] Test: `curl http://127.0.0.1:5000/api/admin/trips/history`

### Update Driver Routes (`rg_travel_backend/routes/driver_routes.py`)

#### Task 2.4: Start OTP Verification
```
Endpoint: POST /api/driver/{driver_id}/trip/{trip_id}/otp/verify/start
Current: Old OTP verification logic
Required: Call verify_otp_and_mark_used(conn, trip_id, "start", otp_input, driver_id)
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `driver_routes.py`
- [ ] Find start OTP endpoint
- [ ] Replace with:
  ```python
  from services.otp_service import verify_otp_and_mark_used
  result = verify_otp_and_mark_used(conn, trip_id, "start", otp_input, driver_id)
  return success_response(data=result["data"], message=result["message"]) if result["success"] else error_response(message=result["message"])
  ```
- [ ] Test: `curl -X POST http://127.0.0.1:5000/api/driver/driver_456/trip/42/otp/verify/start -d '{"otp":"123456"}'`

#### Task 2.5: End OTP Verification
```
Endpoint: POST /api/driver/{driver_id}/trip/{trip_id}/otp/verify/end
Current: Old OTP verification logic
Required: Call verify_otp_and_mark_used(conn, trip_id, "end", otp_input, driver_id)
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `driver_routes.py`
- [ ] Find end OTP endpoint
- [ ] Replace with same logic as start (change "start" to "end")
- [ ] Test: `curl -X POST http://127.0.0.1:5000/api/driver/driver_456/trip/42/otp/verify/end -d '{"otp":"654321"}'`

#### Task 2.6: GPS Submission Integration
```
Endpoint: POST /api/driver/{driver_id}/gps
Current: May not use driver_location_history
Required: Store GPS in driver_location_history table (lat, lng, recorded_at)
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `driver_routes.py`
- [ ] Find GPS submission endpoint
- [ ] Verify it calls INSERT into driver_location_history:
  ```python
  cur.execute("""
    INSERT INTO driver_location_history 
    (trip_id, driver_id, latitude, longitude, accuracy, recorded_at)
    VALUES (?, ?, ?, ?, ?, ?)
  """, (trip_id, driver_id, lat, lng, accuracy, now_iso()))
  conn.commit()
  ```
- [ ] Test: `curl -X POST http://127.0.0.1:5000/api/driver/driver_456/gps -d '{"trip_id":42,"lat":18.52,"lng":73.85}'`

### Update Employee Routes (`rg_travel_backend/routes/employee_routes.py`)

#### Task 2.7: Trip Tracking with Live Polyline
```
Endpoint: GET /api/employee/{employee_id}/tracking/{trip_id}
Current: May not return live polyline data
Required: Query driver_location_history, return ordered GPS points
Status: [ ] PENDING
```

**Checklist:**
- [ ] Open `employee_routes.py`
- [ ] Find tracking endpoint
- [ ] Update query to:
  ```python
  cur.execute("""
    SELECT latitude, longitude, recorded_at 
    FROM driver_location_history
    WHERE trip_id = ? AND driver_id = ?
    ORDER BY recorded_at ASC
  """, (trip_id, driver_id))
  locations = cur.fetchall()
  ```
- [ ] Return as list of {lat, lng, recorded_at} objects
- [ ] Test: `curl http://127.0.0.1:5000/api/employee/emp_123/tracking/42`

### New Endpoints to Add

#### Task 2.8: OTP Status Check (Admin)
```
Endpoint: GET /api/admin/trips/{trip_id}/otp/status
Purpose: Check if OTPs exist, are used, expired
Status: [ ] PENDING
```

**Checklist:**
- [ ] Add new route in `admin_routes.py`:
  ```python
  @admin_bp.route("/trips/<int:trip_id>/otp/status", methods=["GET"])
  def get_otp_status_endpoint(trip_id):
      conn = get_db()
      result = get_otp_status(conn, trip_id)
      conn.close()
      if result["success"]:
          return success_response(data=result["data"])
      return error_response(message=result["message"])
  ```
- [ ] Test: `curl http://127.0.0.1:5000/api/admin/trips/42/otp/status`

#### Task 2.9: Mark Employee No-Show (Driver)
```
Endpoint: POST /api/driver/{driver_id}/trip/{trip_id}/no-show
Purpose: Driver marks employee as no-show during trip
Status: [ ] PENDING
```

**Checklist:**
- [ ] Add new route in `driver_routes.py`:
  ```python
  @driver_bp.route("/<driver_id>/trip/<int:trip_id>/no-show", methods=["POST"])
  def mark_no_show(driver_id, trip_id):
      data = request.get_json()
      employee_id = data.get("employee_id")
      reason = data.get("reason", "No reason provided")
      
      conn = get_db()
      cur = conn.cursor()
      cur.execute("""
        UPDATE trip_employees 
        SET is_no_show=1, no_show_marked_at=?, no_show_marked_by=?, no_show_reason=?
        WHERE trip_id=? AND employee_id=?
      """, (now_iso(), driver_id, reason, trip_id, employee_id))
      conn.commit()
      conn.close()
      
      return success_response(message="No-show marked")
  ```
- [ ] Test: `curl -X POST http://127.0.0.1:5000/api/driver/driver_456/trip/42/no-show -d '{"employee_id":"emp_123","reason":"Not present"}'`

---

## Phase 3: Flutter Integration (⏳ PENDING)

### Fix Widget Lifecycle (`rg_travel_flutter/lib/screens/`)

#### Task 3.1: Live Tracking Screen
```
File: lib/screens/live_tracking_screen.dart
Issues: Timer.periodic without dispose, setState after dispose
Status: [ ] PENDING
```

**Checklist:**
- [ ] Find Timer.periodic usage
- [ ] Add _controller property for disposing
- [ ] Implement dispose() method that cancels timer
- [ ] Check mounted before setState: `if (mounted) setState(...)`

#### Task 3.2: Assigned Trip Screen
```
File: lib/screens/assigned_trip_screen.dart
Issues: Multiple timers, no cleanup
Status: [ ] PENDING
```

**Checklist:**
- [ ] Find all Timer.periodic calls
- [ ] Add dispose() that cancels all timers
- [ ] Check mounted in setState calls

#### Task 3.3: OTP Verification Screen
```
File: lib/screens/otp_screen.dart
Issues: Timer for OTP expiry not disposed
Status: [ ] PENDING
```

**Checklist:**
- [ ] Find OTP expiry timer
- [ ] Implement dispose() with timer cancellation
- [ ] Check mounted in setState

### Fix API Client (`rg_travel_flutter/lib/core/network/api_client.dart`)

#### Task 3.4: URI Building
```
Issue: Inconsistent endpoint formatting (missing /api/, extra slashes)
Status: [ ] PENDING
```

**Checklist:**
- [ ] Review buildUri() function
- [ ] Ensure all endpoints become: `/api/<path>`
- [ ] Handle cases: `/api/`, `api/`, `/admin/`, `admin/`
- [ ] Test: 
  ```dart
  final uri = buildUri("/admin/drivers");  // Should be /api/admin/drivers
  final uri2 = buildUri("/api/drivers");   // Should be /api/drivers
  ```

#### Task 3.5: Error Handling
```
Issue: Poor error messages, missing null checks
Status: [ ] PENDING
```

**Checklist:**
- [ ] Add try-catch for JSON parsing
- [ ] Validate response structure before accessing fields
- [ ] Provide meaningful error messages to UI

### Add Health Check Banner

#### Task 3.6: Offline Detection
```
File: lib/widgets/offline_banner.dart (NEW)
Purpose: Show "Backend Offline" banner on app startup
Status: [ ] PENDING
```

**Checklist:**
- [ ] Create new offline_banner.dart widget
- [ ] Implement health check on app startup
- [ ] Show/hide banner based on backend status
- [ ] Integrate into main.dart

### Complete Custom Widgets

#### Task 3.7: RgButton Widget
```
File: lib/widgets/rg_button.dart
Status: [ ] PENDING - DESIGN & IMPLEMENTATION
```

#### Task 3.8: RgCard Widget
```
File: lib/widgets/rg_card.dart
Status: [ ] PENDING - DESIGN & IMPLEMENTATION
```

---

## Phase 4: Feature Implementation (📋 PLANNING)

### Feature 1: Live Driver Tracking ✅ Ready
- [x] Database schema (driver_location_history)
- [x] Backend storage (GPS submission)
- [ ] Backend retrieval (location query)
- [ ] Flutter map display
- [ ] Polyline animation

### Feature 2: OTP-Based Trip Control ✅ Ready
- [x] Database schema (trip_otps, otp_audit_log)
- [x] OTP service (generate, verify, audit)
- [x] Backend endpoints (defined)
- [ ] Flutter UI (input, verification)
- [ ] Error handling (expired, invalid)

### Feature 3: Auto Employee Grouping ⏳ Partial
- [x] Database schema (trip_employees)
- [x] Service skeleton (grouping_service.py)
- [ ] Algorithm implementation
- [ ] Integration in trip creation
- [ ] Flutter display

### Feature 4: Google Maps Route Planning ⏳ Partial
- [x] Database schema (pickup_locations)
- [x] Service skeleton (routing_service.py)
- [ ] Google Directions API integration
- [ ] Multi-stop route calculation
- [ ] Flutter map display

### Feature 5: Trip KM Calculation ⏳ Pending
- [ ] Database schema (trips.total_km)
- [ ] Distance calculation algorithm
- [ ] Integration with Google Directions API
- [ ] Update on trip completion
- [ ] Flutter display

### Feature 6: Emergency Driver/Cab Swap ⏳ Pending
- [x] Database schema (swap_requests)
- [ ] Swap request creation
- [ ] Admin approval workflow
- [ ] Driver assignment update
- [ ] Flutter UI workflow

### Feature 7: No-Show Employee Handling ✅ Ready
- [x] Database schema (trip_employees.is_no_show)
- [x] Mark no-show endpoint (defined)
- [ ] Admin view no-shows
- [ ] Flutter UI for marking

### Feature 8: Unique 10-Character Route Numbers ⏳ Partial
- [x] Database schema (route_numbers)
- [x] Service skeleton (route_no_service.py)
- [ ] Generation algorithm
- [ ] Integration in trip creation
- [ ] Format: DDMMHHPPTT (day, month, hour, person_count, trip_type)

### Feature 9: Admin Manual Overrides ⏳ Pending
- [ ] Define override operations (change driver, change route, etc.)
- [ ] Create endpoints for overrides
- [ ] Add audit logging
- [ ] Flutter admin UI

### Feature 10: Driver Hometown & Fair Cab Rotation ⏳ Pending
- [ ] Database schema (drivers.hometown)
- [ ] Rotation algorithm
- [ ] Preference-based assignment
- [ ] Admin configuration

---

## Success Criteria Checklist

### Backend Completion
- [ ] All 30+ API endpoints working
- [ ] OTP service fully integrated
- [ ] GPS tracking storing correctly
- [ ] No-show tracking functional
- [ ] All tests passing: `pytest test_backend.py -v`
- [ ] Health check responding: `curl http://127.0.0.1:5000/api/health`

### Flutter Completion
- [ ] No widget lifecycle errors
- [ ] API client handling all endpoints
- [ ] Health check banner displaying
- [ ] Custom widgets implemented
- [ ] All screens displaying correctly
- [ ] Error messages user-friendly
- [ ] No null pointer exceptions

### Database Completion
- [ ] All 13 tables created
- [ ] Foreign key constraints working
- [ ] Indexes created for performance
- [ ] Sample data seeded
- [ ] Backups automated

### Documentation
- [ ] API docs complete
- [ ] Database docs complete
- [ ] Setup guide complete
- [ ] Architecture docs complete
- [ ] Developer reference complete

### Testing
- [ ] Backend tests: 100%+ pass
- [ ] Flutter tests: All passing
- [ ] Integration tests: Working
- [ ] Manual testing checklist completed

---

## Priority Matrix

| Phase | Task | Priority | Effort | Est. Time |
|-------|------|----------|--------|-----------|
| 2 | Admin routes integration | 🔴 CRITICAL | 2h | 2 hours |
| 2 | Driver routes integration | 🔴 CRITICAL | 2h | 2 hours |
| 3 | Widget lifecycle fixes | 🔴 CRITICAL | 1h | 1 hour |
| 3 | API client fixes | 🟠 HIGH | 1h | 1 hour |
| 2 | GPS submission integration | 🟠 HIGH | 1h | 1 hour |
| 3 | Health check banner | 🟠 HIGH | 1h | 1 hour |
| 4 | Live tracking display | 🟡 MEDIUM | 2h | 2 hours |
| 4 | OTP UI screens | 🟡 MEDIUM | 3h | 3 hours |
| 4 | Route planning | 🟡 MEDIUM | 4h | 4 hours |
| 4 | Auto grouping | 🟡 MEDIUM | 3h | 3 hours |

---

## Getting Help

- **Backend Issues**: See [ARCHITECTURE_ANALYSIS_AND_FIXES.md](../ARCHITECTURE_ANALYSIS_AND_FIXES.md)
- **Setup Issues**: See [WINDOWS_SETUP_GUIDE.md](../WINDOWS_SETUP_GUIDE.md)
- **API Reference**: See [docs/API_DOCS.md](../docs/API_DOCS.md)
- **Database Help**: See [docs/DB_SCHEMA.md](../docs/DB_SCHEMA.md)
- **Quick Reference**: See [DEVELOPER_QUICK_REFERENCE.md](../DEVELOPER_QUICK_REFERENCE.md)

---

**Next Step:** Start with Task 2.1 - Update Admin Routes for Trip Assignment

---

**Version History:**
- v2.0 (Feb 2, 2026) - Phase 1 complete, Phase 2 ready to start
- v1.0 (Jan 28, 2026) - Initial project analysis
