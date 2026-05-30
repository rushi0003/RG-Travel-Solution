# Trip Management - Code Reference & Quick Start

## Quick Links

| File | Purpose | Lines |
|------|---------|-------|
| [create_group_assign_screen.dart](rg_travel_flutter/lib/screens/admin/create_group_assign_screen.dart) | Trip creation & management UI | 800+ |
| [app.py](rg_travel_backend/app.py) | Backend trip endpoints | 872-1110 |
| [test_trip_endpoints.py](test_trip_endpoints.py) | Endpoint tests | Full suite |
| [TRIP_MANAGEMENT_REFACTOR.md](TRIP_MANAGEMENT_REFACTOR.md) | Complete documentation | Detailed |

---

## Flutter State Variables

```dart
// Tab selector
int _currentTab = 0; // 0=Create, 1=View

// Create Trip form
String? _selectedTripType; // "pickup" or "drop"
String? _selectedTripTime; // HH:MM
int? _selectedDriverId;
Set<String> _selectedEmployeeIds; // bulk selection
bool _manualOverride;
String? _generatedRouteNo;

// View Trips
List<Map<String, dynamic>> _liveTrips;
String? _cancelTripId;
TextEditingController _cancelReasonCtrl;

// Controllers
TextEditingController _driverSearchCtrl;
TextEditingController _employeeSearchCtrl;
```

---

## API Endpoint Summary

### 1. Create Trip
```
POST /api/admin/trips
Content-Type: application/json

{
  "route_no": "ABC123DEF456",
  "trip_type": "pickup",
  "schedule_time": "09:00",
  "driver_id": 1,
  "employee_ids": [1, 2, 3],
  "admin_id": 1,
  "vehicle_type": "4"
}

Response (201):
{
  "success": true,
  "data": {
    "trip_id": 42,
    "route_no": "ABC123DEF456",
    "status": "assigned"
  }
}
```

### 2. List Active Trips
```
GET /api/admin/trips

Response (200):
{
  "success": true,
  "data": [
    {
      "id": 42,
      "route_no": "ABC123DEF456",
      "trip_type": "pickup",
      "schedule_time": "09:00",
      "status": "assigned",
      "driver_id": 1,
      "driver_name": "John Doe",
      "driver_mobile": "9876543210",
      "vehicle_no": "DL01AB1234",
      "vehicle_type": "4",
      "employees": [
        {"id": 1, "name": "Alice", "mobile": "...", "drop_location": "..."},
        ...
      ]
    }
  ]
}
```

### 3. Update Trip Status
```
PUT /api/admin/trips/{trip_id}

Complete:
{
  "status": "completed"
}

Cancel:
{
  "status": "cancelled",
  "cancel_reason": "Driver unavailable"
}

Response (200):
{
  "success": true,
  "data": {
    "trip_id": 42,
    "status": "completed|cancelled",
    "cancel_reason": null|"..."
  }
}
```

---

## Testing Commands

### Run Backend Test Suite
```bash
cd "c:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution"
python test_trip_endpoints.py
```

### Test Manually with curl

```bash
# Create trip
curl -X POST http://127.0.0.1:5000/api/admin/trips \
  -H "Content-Type: application/json" \
  -d '{
    "route_no": "TEST001",
    "trip_type": "pickup",
    "schedule_time": "09:00",
    "driver_id": 1,
    "employee_ids": [1, 2],
    "admin_id": 1
  }'

# List trips
curl http://127.0.0.1:5000/api/admin/trips

# Complete trip
curl -X PUT http://127.0.0.1:5000/api/admin/trips/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'

# Cancel trip
curl -X PUT http://127.0.0.1:5000/api/admin/trips/2 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "cancelled",
    "cancel_reason": "Driver emergency"
  }'
```

---

## Key Functions in create_group_assign_screen.dart

### Data Fetching
```dart
_bootstrap()              // Loads all initial data
_fetchDrivers()          // GET /api/admin/drivers
_fetchEmployees()        // GET /api/admin/employees
_fetchLiveTrips()        // GET /api/admin/trips
_fetchDriverRequests()   // GET /api/admin/driver-requests
```

### Trip Operations
```dart
_createAndAssignTrip()   // POST /api/admin/trips
_completeTrip(tripId)    // PUT /api/admin/trips/{id}
_cancelTrip(tripId)      // PUT /api/admin/trips/{id}
```

### Filtering & Search
```dart
_filter(list, query)     // NLP search on name, mobile, etc.
_availableTimes()        // Get unique login/logout times
_generateRouteNo()       // Create 10-char random route number
```

### UI Builders
```dart
_buildCreateTripTab()    // Step 1-7 wizard
_buildViewTripsTab()     // Trip list + actions
_liveTripTile(trip)      // Individual trip card
_showCancelDialog(id)    // Modal for cancel reason
```

---

## Database Queries

### Create Trip
```sql
INSERT INTO trips 
(route_no, trip_type, schedule_time, status, admin_id, driver_id, vehicle_type, created_at, updated_at)
VALUES (?, ?, ?, 'assigned', ?, ?, ?, ?, ?);
```

### Link Employees
```sql
INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
VALUES (?, ?, ?, 0, ?);
```

### Complete Trip
```sql
UPDATE trips 
SET status = 'completed', end_time = ?, updated_at = ?
WHERE id = ?;
```

### Cancel Trip
```sql
UPDATE trips 
SET status = 'cancelled', cancel_reason = ?, updated_at = ?
WHERE id = ?;
```

### List Active Trips with Details
```sql
SELECT t.*, d.name as driver_name, d.mobile as driver_mobile, d.vehicle_no
FROM trips t
LEFT JOIN drivers d ON d.id = t.driver_id
WHERE t.status IN ('created', 'assigned', 'started')
ORDER BY t.created_at DESC;
```

---

## Error Handling Examples

### In Flutter
```dart
try {
  await _createAndAssignTrip();
} catch (e) {
  toast("Trip creation failed: $e");
} finally {
  safeSetState(() => _loading = false);
}
```

### In Backend
```python
if not driver:
    raise APIError("Driver not found.", 404, "DRIVER_NOT_FOUND")

if new_status == "cancelled" and not cancel_reason:
    raise APIError("cancel_reason required when cancelling.", 400, "VALIDATION_ERROR")
```

---

## Common Issues & Solutions

### Issue: "Driver not found"
- **Cause**: driver_id doesn't exist in DB
- **Fix**: Verify driver exists and is_approved=1

### Issue: "Employees not found"
- **Cause**: employee_ids contain invalid IDs
- **Fix**: Use only valid employee IDs from GET /api/admin/employees

### Issue: "No times found"
- **Cause**: Employees don't have login_time or logout_time
- **Fix**: Ensure employees have these fields populated

### Issue: Cancel button shows validation error
- **Cause**: Empty cancel_reason field
- **Fix**: Enter a reason before confirming cancellation

### Issue: Trip doesn't appear after creation
- **Cause**: Status not 'assigned' (required for listing)
- **Fix**: Check if trip created with correct status

---

## Performance Tips

1. **Large Employee Lists**: NLP search filters on every keystroke
   - Use debouncing if 1000+ employees
   - Add pagination to list view

2. **Trip Queries**: JOIN with drivers/employees
   - Use indexes on trip_id, driver_id, employee_id
   - Cache driver details if frequently accessed

3. **Bulk Operations**: Prefer batch inserts
   - Current code inserts employees one-by-one
   - Could optimize with multi-row INSERT for 100+ employees

---

## Deployment Notes

### Backend Requirements
- Python 3.8+
- Flask, Flask-CORS
- SQLite3
- Working database with trips table

### Flutter Requirements
- Flutter 3.0+
- http package: ^1.2.2
- Network access to backend (http://127.0.0.1:5000 for Web)

### Database Migrations
No migrations needed - all columns already exist in schema:
- ✓ trips.cancel_reason
- ✓ trip_employees with all required fields
- ✓ Foreign key constraints

---

## Next Steps

1. **Testing Phase**:
   ```bash
   python test_trip_endpoints.py
   ```

2. **Manual Testing**:
   - Create 3-4 sample trips
   - Test complete and cancel operations
   - Verify data persists in database

3. **Deployment**:
   - Deploy backend to production server
   - Update Flutter base URL if needed
   - Test end-to-end with real data

4. **Monitoring**:
   - Check server logs for errors
   - Monitor trip creation rate
   - Track cancellation reasons

---

## Support & Documentation

- **Full Documentation**: See [TRIP_MANAGEMENT_REFACTOR.md](TRIP_MANAGEMENT_REFACTOR.md)
- **API Schema**: Check [DATABASE_SCHEMA.json](DATABASE_SCHEMA.json)
- **Related Endpoints**: See driver approval and employee management in [app.py](rg_travel_backend/app.py)

---

**Last Updated**: 2026-02-03  
**Version**: 1.0  
**Status**: ✅ Ready for Testing
