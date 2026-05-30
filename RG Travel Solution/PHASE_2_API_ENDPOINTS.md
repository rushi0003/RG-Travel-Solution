# Phase 2 API Endpoints — OTP Integration & Live Tracking

**Status:** ✅ Implemented  
**Date:** February 2, 2026  
**Version:** 2.0  

---

## Overview

Phase 2 integrates **OTP (One-Time Password) verification** and **live driver tracking** into the backend.

### New Features:
1. **OTP Management** — Trip start/end verification with secure hashing
2. **Live Driver Tracking** — Real-time GPS location updates & history
3. **Admin OTP Dashboard** — View and regenerate OTPs
4. **Employee OTP Access** — Employees can fetch OTP for trip verification
5. **Driver Location API** — Driver sends GPS; Admin/Employee fetch location

---

## OTP Endpoints (OTP Service)

### Admin: Generate OTPs for Trip

**Endpoint:**
```
POST /api/admin/trips/{trip_id}/otps/generate
```

**Description:** Generate start & end OTPs for a trip.

**Authentication:** Bearer Token (Admin)

**Request Body:** None (path param only)

**Response (200):**
```json
{
  "success": true,
  "message": "OTPs generated.",
  "data": {
    "trip_id": 1,
    "start_otp": "123456",
    "end_otp": "654321",
    "expires_in_minutes": 5,
    "expires_at": "2026-02-02T10:35:00+00:00"
  }
}
```

**Error (400):**
```json
{
  "success": false,
  "message": "Trip not found."
}
```

---

### Admin: Get OTP Status for Trip

**Endpoint:**
```
GET /api/admin/trips/{trip_id}/otps/status
```

**Description:** Check if OTPs exist, are used, or expired.

**Authentication:** Bearer Token (Admin)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "trip_id": 1,
    "start": {
      "exists": true,
      "is_used": false,
      "expired": false,
      "expires_at": "2026-02-02T10:35:00+00:00"
    },
    "end": {
      "exists": true,
      "is_used": false,
      "expired": false,
      "expires_at": "2026-02-02T10:35:00+00:00"
    }
  }
}
```

---

### Driver: Verify OTP (Start or End Trip)

**Endpoint:**
```
POST /api/driver/{driver_id}/trip/{trip_id}/otp/verify
```

**Description:** Driver verifies OTP to start or end a trip. Updates trip status.

**Authentication:** Bearer Token (Driver)

**Request Body:**
```json
{
  "otp_type": "start",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "OTP verified.",
  "data": {
    "trip_id": 1,
    "status": "started",
    "trip_type": "pickup"
  }
}
```

**Errors:**
- `400` — Invalid OTP format (must be 6 digits)
- `400` — OTP not found, already used, or expired
- `400` — Trip status invalid for this OTP type
- `404` — Trip not found

---

### Employee: Get OTP for Trip

**Endpoint:**
```
GET /api/employee/trips/{route_no}/otp?employee_id={emp_id}&type=start
```

**Description:** Employee fetches OTP for a trip they are assigned to. OTP is regenerated each time.

**Authentication:** Bearer Token (Employee)

**Query Params:**
- `employee_id` (int, required) — Employee ID
- `type` (string, required) — `"start"` or `"end"`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "trip_id": 5,
    "otp_type": "start",
    "otp": "234567",
    "expires_at": "2026-02-02T10:40:00+00:00"
  }
}
```

**Errors:**
- `403` — Employee is not a member of this trip
- `400` — Trip already completed or cancelled
- `404` — Route not found

---

## Live Tracking Endpoints (Tracking Service)

### Driver: Send GPS Update

**Endpoint:**
```
POST /api/driver/{driver_id}/gps
```

**Description:** Driver sends real-time GPS location. Called every 5-10 seconds during trip.

**Authentication:** Bearer Token (Driver)

**Request Body:**
```json
{
  "lat": 18.5204,
  "lng": 73.8567,
  "accuracy": 10,
  "speed": 2.5,
  "bearing": 120,
  "route_no": "ABC1234567"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Location updated.",
  "data": {
    "driver_id": 1,
    "lat": 18.5204,
    "lng": 73.8567,
    "recorded_at": "2026-02-02T10:30:45+00:00"
  }
}
```

**Errors:**
- `400` — Invalid lat/lng coordinates
- `404` — Driver not found

---

### Driver: Get Latest Location

**Endpoint:**
```
GET /api/driver/{driver_id}/gps/latest
```

**Description:** Returns driver's most recent GPS location (debug/self-check).

**Authentication:** Bearer Token (Driver)

**Response (200):**
```json
{
  "success": true,
  "message": "Latest location.",
  "data": {
    "driver_id": 1,
    "lat": 18.5204,
    "lng": 73.8567,
    "accuracy": 10,
    "speed": 2.5,
    "bearing": 120,
    "recorded_at": "2026-02-02T10:30:45+00:00"
  }
}
```

**Errors:**
- `404` — No location found for driver

---

### Admin: Get All Online Drivers

**Endpoint:**
```
GET /api/admin/drivers/online
```

**Description:** List all currently online drivers with their latest location.

**Authentication:** Bearer Token (Admin)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "online_drivers": [
      {
        "driver_id": 1,
        "name": "Rajesh Kumar",
        "mobile": "9876543210",
        "cab_no": "MH12AB1234",
        "last_seen": "2026-02-02T10:30:45+00:00",
        "location": {
          "driver_id": 1,
          "lat": 18.5204,
          "lng": 73.8567,
          "accuracy": 10,
          "speed": 2.5,
          "bearing": 120,
          "recorded_at": "2026-02-02T10:30:45+00:00"
        }
      }
    ],
    "count": 1
  }
}
```

---

### Admin: Get Driver Location by Route

**Endpoint:**
```
GET /api/admin/routes/{route_no}/driver-location
```

**Description:** Get the assigned driver's latest location for a specific route.

**Authentication:** Bearer Token (Admin)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "driver_id": 1,
    "lat": 18.5204,
    "lng": 73.8567,
    "accuracy": 10,
    "speed": 2.5,
    "bearing": 120,
    "recorded_at": "2026-02-02T10:30:45+00:00"
  }
}
```

**Errors:**
- `404` — No driver assigned to route

---

### Employee: View Driver Location

**Endpoint:**
```
GET /api/employee/trips/{route_no}/driver-location?employee_id={emp_id}
```

**Description:** Employee views the driver's live location for their trip.

**Authentication:** Bearer Token (Employee)

**Query Params:**
- `employee_id` (int, required) — Employee ID (must be trip member)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "has_location": true,
    "location": {
      "driver_id": 1,
      "lat": 18.5204,
      "lng": 73.8567,
      "accuracy": 10,
      "speed": 2.5,
      "bearing": 120,
      "recorded_at": "2026-02-02T10:30:45+00:00"
    }
  }
}
```

**Errors:**
- `403` — Employee is not a member of this trip
- `404` — Route not found

---

### Driver: Get Location History

**Endpoint:**
```
GET /api/driver/{driver_id}/gps/history?limit=50
```

**Description:** Fetch driver's recent GPS history (max 500 records).

**Authentication:** Bearer Token (Driver/Admin)

**Query Params:**
- `limit` (int, optional, default=100) — Max records (1-500)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "driver_id": 1,
    "history": [
      {
        "lat": 18.5204,
        "lng": 73.8567,
        "accuracy": 10,
        "speed": 2.5,
        "bearing": 120,
        "recorded_at": "2026-02-02T10:30:45+00:00"
      }
    ],
    "count": 1
  }
}
```

---

## Admin: Trip Control with OTP Integration

### Admin: List Live Trips (with member details)

**Endpoint:**
```
GET /api/admin/trips/live
```

**Description:** Show all active/in-progress trips with member list.

**Authentication:** Bearer Token (Admin)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "route_no": "ABC1234567",
      "operation": "pickup",
      "trip_time": "09:30",
      "driver_id": 1,
      "vehicle_type": 6,
      "status": "started",
      "total_km": 12.5,
      "members": [
        {
          "id": 10,
          "name": "Priya Sharma",
          "mobile": "9988776655",
          "address": "Viman Nagar, Pune",
          "is_no_show": false
        }
      ]
    }
  ]
}
```

---

### Admin: Create & Assign Trip with OTPs

**Endpoint:**
```
POST /api/admin/groups/create-and-assign
```

**Description:** Create trip group, assign driver, generate route number, compute route, **generate OTPs automatically**.

**Authentication:** Bearer Token (Admin)

**Request Body (AUTO mode):**
```json
{
  "admin_id": 1,
  "operation": "pickup",
  "trip_time": "09:30",
  "vehicle_type": 6,
  "driver_id": 12,
  "origin_office": {
    "lat": 18.5204,
    "lng": 73.8567
  },
  "optimize_route": true
}
```

**Request Body (MANUAL mode):**
```json
{
  "admin_id": 1,
  "operation": "pickup",
  "trip_time": "09:30",
  "vehicle_type": 6,
  "driver_id": 12,
  "employee_ids": [1, 2, 3, 4, 5, 6],
  "manual_override": true,
  "origin_office": {
    "lat": 18.5204,
    "lng": 73.8567
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Trips created & assigned.",
  "data": [
    {
      "trip_id": 1,
      "route_no": "ABC1234567",
      "operation": "pickup",
      "trip_time": "09:30",
      "vehicle_type": 6,
      "driver_id": 12,
      "members": [1, 2, 3, 4, 5, 6],
      "route": {
        "total_km": 12.5,
        "polyline": "...",
        "estimated_duration_minutes": 45
      },
      "otps": {
        "trip_id": 1,
        "start_otp": "123456",
        "end_otp": "654321",
        "expires_in_minutes": 5,
        "expires_at": "2026-02-02T10:35:00+00:00"
      }
    }
  ]
}
```

---

## Database Tables (Phase 2)

### trip_otps
```sql
CREATE TABLE trip_otps (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL,
  otp_type TEXT NOT NULL,  -- 'start' or 'end'
  otp_hash TEXT NOT NULL,  -- SHA-256 hash (secure storage)
  is_used INTEGER DEFAULT 0,
  used_at TEXT,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (trip_id) REFERENCES trips(id)
);
```

### driver_locations (part of tracking_service)
```sql
CREATE TABLE driver_locations (
  id INTEGER PRIMARY KEY,
  driver_id INTEGER NOT NULL,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  accuracy REAL,
  speed REAL,
  bearing REAL,
  recorded_at TEXT NOT NULL,
  FOREIGN KEY (driver_id) REFERENCES drivers(id)
);
```

### otp_audit_log
```sql
CREATE TABLE otp_audit_log (
  id INTEGER PRIMARY KEY,
  trip_id INTEGER NOT NULL,
  otp_type TEXT,
  driver_id TEXT,
  action TEXT,  -- 'generated', 'verify_success', 'verify_failed', etc.
  reason TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (trip_id) REFERENCES trips(id)
);
```

---

## Error Codes & Messages

| Code | Message | Cause |
|------|---------|-------|
| 400 | OTP must be exactly 6 digits | Format error |
| 400 | OTP expired | Expiry time passed |
| 400 | OTP already used | OTP was verified before |
| 400 | Invalid OTP | Mismatch or not found |
| 400 | Trip cannot start. Current status: {status} | Wrong trip status for start OTP |
| 400 | Invalid GPS coordinates | lat/lng out of range |
| 404 | Trip not found | Trip ID doesn't exist |
| 404 | Driver not found | Driver ID doesn't exist |
| 404 | No location found for driver | No GPS history |
| 403 | Not allowed: employee not a member | Permission denied |

---

## Testing Workflow

### 1. Admin Creates Trip + OTPs
```bash
POST /api/admin/groups/create-and-assign
→ Returns trip_id, route_no, start_otp, end_otp
```

### 2. Driver Receives GPS Updates
```bash
POST /api/driver/{driver_id}/gps
→ Every 5-10 seconds (mock with curl loop)
```

### 3. Driver Verifies Start OTP
```bash
POST /api/driver/{driver_id}/trip/{trip_id}/otp/verify
Body: { "otp_type": "start", "otp": "123456" }
→ Trip status changes to "started"
```

### 4. Employee Checks Live Driver Location
```bash
GET /api/employee/trips/{route_no}/driver-location?employee_id=1
→ Returns driver's latest GPS coords
```

### 5. Admin Views All Online Drivers
```bash
GET /api/admin/drivers/online
→ Returns list of drivers + their locations
```

### 6. Driver Verifies End OTP
```bash
POST /api/driver/{driver_id}/trip/{trip_id}/otp/verify
Body: { "otp_type": "end", "otp": "654321" }
→ Trip status changes to "completed"
```

---

## Summary

| Component | Endpoints | Status |
|-----------|-----------|--------|
| OTP Generation | 2 admin + 1 employee | ✅ |
| OTP Verification | 1 driver | ✅ |
| Live Tracking | 5 endpoints (driver/admin/employee) | ✅ |
| Trip Management | Updated with OTP integration | ✅ |
| **Total Phase 2** | **9+ endpoints** | **✅ COMPLETE** |

---

**Next:** Phase 3 — Flutter UI Integration  
**Timeline:** 2-3 weeks
