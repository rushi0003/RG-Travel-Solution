# RG Travel Solution — API Docs (Lite)
**Backend:** Flask + SQLite  
**Frontend:** Flutter  
**Base URL (Android Emulator):** `http://10.0.2.2:5000`  
**API Prefix:** `/api`

---

## 1) Quick Start (Testing)

### 1.1 Health Checks
- `GET /`  
- `GET /api/utils/ping`
- `GET /api/db/health`
- `GET /api/time/now`

### 1.2 Seed Demo Data (Recommended first)
- `POST /api/admin/seed`
- `POST /api/drivers/seed`
- `POST /api/employees/seed`

> Seed endpoints can be disabled via env: `RG_ENABLE_SEED_API=0`

---

## 2) Authentication

### 2.1 Token-based Auth (Bearer)
After login, backend returns:
```json
{
  "success": true,
  "message": "Login success",
  "data": {
    "token": "....",
    "expires_at": "2026-02-01T14:30:00",
    "profile": { }
  }
}
