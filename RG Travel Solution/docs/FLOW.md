# RG Travel Solution — System Flow (Lite)
**Frontend:** Flutter  
**Backend:** Flask REST API  
**Database:** SQLite  
**API Prefix:** `/api`  
**Android Emulator Base URL:** `http://10.0.2.2:5000`

---

## 0) Big Picture Flow (End-to-End)
1. **Backend starts** → initializes DB schema (`schema.sql`)  
2. **Seed data** (optional) → creates demo admin/driver/employee  
3. **Admin logs in** → gets token  
4. **Admin creates trip** (pickup/drop) → generates **unique 10-char route_no** (per day) → stores trip + employees  
5. **Admin assigns driver** → trip status becomes `assigned`  
6. **Driver logs in** → views assigned trip(s)  
7. **Driver generates OTP** and starts trip (OTP verify) → trip status becomes `started`  
8. **Driver sends live location updates** → admin/employee can see tracking  
9. **Driver marks no-shows** (optional)  
10. **Driver ends trip** by OTP verify → trip status becomes `completed`  
11. **Trip history** can be viewed by admin

---

## 1) System Initialization Flow

### 1.1 Backend Boot
- `python backend/app.py`
- DB auto init runs `backend/db/schema.sql`

**Key endpoints**
- `GET /api/utils/ping`
- `GET /api/db/health`
- `GET /api/db/tables`
- `GET /api/time/now`

If schema is not created:
- `POST /api/db/init`

---

## 2) Seed Flow (Development Only)

### 2.1 Seed Admin
**Request**
- `POST /api/admin/seed`

**Status**
- `GET /api/admin/seed/status`

**Reset**
- `POST /api/admin/seed/reset`

---

### 2.2 Seed Drivers
**Request**
- `POST /api/drivers/seed`

**Status**
- `GET /api/drivers/seed/status`

**Reset**
- `POST /api/drivers/seed/reset`

---

### 2.3 Seed Employees
**Request**
- `POST /api/employees/seed`

**Status**
- `GET /api/employees/seed/status`

**Reset**
- `POST /api/employees/seed/reset`

---

## 3) Authentication Flow

All protected endpoints require:
