# Backend Improvements and Fixes - Implementation Guide

## Critical Backend Enhancements

### 1. Enhanced Tracking Service Improvements
The tracking service needs enhancements for:
- Driver online/offline transitions
- Location history cleanup (keep last 30 days)
- Trip-specific location filtering

### 2. Auto Grouping Enhancements  
Improve the grouping service with:
- Cab rotation tracking
- Hometown-based assignment validation
- Employee location-based nearest grouping algorithm refinement

### 3. Admin Routes Enhancements
Add missing endpoints for:
- Live trip modification (reassign driver, change time)
- Detailed trip history with filters
- Cab rotation status
- Driver hometown approval management

### 4. Driver Routes Enhancements
Add endpoints for:
- Emergency vehicle/driver swap request
- Comprehensive trip history with filters
- Document expiry tracking

### 5. Employee Routes Enhancements
Add endpoints for:
- Absence requests
- Profile update requests
- Detailed trip history

## API Endpoint Mapping

### Admin APIs (Complete List)

#### Profile Management
- `GET /api/admin/profile/<admin_id>` - Get profile
- `PUT /api/admin/profile/<admin_id>` - Update profile
- `POST /api/admin/logout` - Logout

#### Trip Management
- `POST /api/admin/groups/create-and-assign` - Create groups and assign
- `GET /api/admin/trips` - List all trips
- `GET /api/admin/trips/live` - List live trips
- `GET /api/admin/trips/<id>/details` - Get trip details
- `POST /api/admin/trips/<id>/cancel` - Cancel trip (requires reason)
- `POST /api/admin/trips/<id>/complete` - Mark trip completed
- `POST /api/admin/trips/<id>/modify` - Modify trip (driver, time)
- `GET /api/admin/routes/<route_no>/driver-location` - Get driver location for route

#### Driver Management
- `GET /api/admin/drivers` - List approved drivers
- `GET /api/admin/driver-requests` - List pending driver requests
- `POST /api/admin/driver-requests/<id>/approve` - Approve driver
- `POST /api/admin/driver-requests/<id>/reject` - Reject driver
- `POST /api/admin/drivers/<id>/approve-hometown` - Approve hometown request
- `GET /api/admin/drivers/online` - List online drivers

#### Employee Management
- `GET /api/admin/employees` - List active employees
- `GET /api/admin/employee-requests` - List pending employee requests
- `POST /api/admin/employee-requests/<id>/approve` - Approve employee
- `POST /api/admin/employee-requests/<id>/reject` - Reject employee

#### Swap Requests
- `GET /api/admin/swap-requests` - List swap requests
- `POST /api/admin/swap-requests/<id>/approve` - Approve swap
- `POST /api/admin/swap-requests/<id>/reject` - Reject swap

### Driver APIs

#### Trip Management
- `GET /api/driver/<id>/assigned-trip` - Get current assigned trip
- `GET /api/driver/<id>/trip-history` - Get trip history
- `POST /api/driver/<id>/trip/<trip_id>/start-otp` - Request start OTP
- `POST /api/driver/<id>/trip/<trip_id>/verify-otp` - Verify OTP
- `POST /api/driver/<id>/trip/<trip_id>/no-show` - Mark employee as no-show
- `POST /api/driver/<id>/trip/<trip_id>/swap-request` - Request vehicle/driver swap

#### Location Tracking
- `POST /api/driver/<id>/location` - Update driver location (GPS)
- `GET /api/driver/<id>/location/latest` - Get latest location

#### Profile
- `GET /api/driver/<id>/profile` - Get profile
- `PUT /api/driver/<id>/profile` - Request profile update
- `POST /api/driver/<id>/profile/change-request` - Request changes (hometown)

### Employee APIs

#### Trip Management
- `GET /api/employee/<id>/assigned-trip` - Get current assigned trip
- `GET /api/employee/<id>/trip-history` - Get trip history
- `GET /api/employee/<id>/trip/<trip_id>/otp` - Get OTP for trip
- `POST /api/employee/<id>/trip/<trip_id>/location` - Get driver location for trip

#### Profile
- `GET /api/employee/<id>/profile` - Get profile
- `PUT /api/employee/<id>/profile` - Request profile update

#### Requests
- `POST /api/employee/<id>/absence-request` - Request absence
- `GET /api/employee/<id>/absence-history` - Get absence history

## Database Improvements

### Indexing Strategy
Add indexes for:
- `trip_otps(trip_id, otp_type)` - Already present ✅
- `trip_employees(trip_id, is_no_show)` - Already present ✅
- `driver_location_history(driver_id, recorded_at DESC)` - For recent location lookup
- `drivers(is_online, last_seen DESC)` - For online driver queries

### Data Cleanup
Implement automatic cleanup:
- Delete location history older than 30 days
- Archive completed trips older than 90 days
- Cleanup expired OTPs

## Error Handling Standards

All API responses should follow:
```json
{
  "success": boolean,
  "message": string,
  "data": object|array|null,
  "error_code": string (optional)
}
```

Standard HTTP Status Codes:
- 200: Success
- 400: Bad Request (validation error)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 409: Conflict (resource already exists)
- 500: Server Error

## Validation Standards

### Mobile Number
- Must be exactly 10 digits
- Pattern: `^\d{10}$`

### Driving License
- Format: 2 letters + 13 digits
- Pattern: `^[A-Z]{2}\d{13}$`

### Vehicle Number
- Format: XX00XX0000 (vehicle registration)
- Pattern: `^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$`

### Route Number
- Format: 10 characters (YYYY + 4 digits + 2 month letters)
- Pattern: `^\d{4}\d{4}[A-Z]{2}$`
- Example: 20261234FE

### OTP
- Exactly 6 digits
- Pattern: `^\d{6}$`

### Time Format
- HH:MM format
- Pattern: `^([01]\d|2[0-3]):([0-5]\d)$`

## Security Considerations

1. **Password Hashing**
   - Use bcrypt or scrypt (not MD5/SHA)
   - Salt must be unique per password
   - Current: ✅ Using proper hash function

2. **OTP Storage**
   - Never store plain OTP text
   - Always hash with SHA-256
   - Current: ✅ Implemented

3. **GPS Location Privacy**
   - Don't store precise location when trip not active
   - Cleanup old location history
   - Encryption recommended for sensitive deployments

4. **Admin Override Tracking**
   - Log all admin actions with timestamp and reason
   - Audit trail for compliance

## Performance Optimization

1. **Query Optimization**
   - Add indexes as specified above
   - Use LIMIT for list endpoints
   - Implement pagination

2. **Connection Pooling**
   - SQLite doesn't support true pooling
   - Consider migration path to PostgreSQL for production

3. **Caching Strategy**
   - Cache online driver list (refresh every 5 seconds)
   - Cache active routes (refresh on modification)
   - Cache admin profile (refresh on update)

4. **Location History Management**
   - Store only recent history (last 24 hours for active trips)
   - Archive old data separately
   - Batch cleanup jobs

---

**Implementation Priority:**
1. ⚠️ High: All validation and error handling
2. ⚠️ High: All security measures
3. 🔄 Medium: Performance optimizations
4. 📋 Low: Additional reporting endpoints
