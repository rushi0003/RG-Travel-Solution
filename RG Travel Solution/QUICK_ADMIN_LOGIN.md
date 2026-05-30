# 🔑 Quick Admin Login Reference

## Credentials
```
Name:     Rushi Gund
Mobile:   9325118627
Password: Rushi123
ID:       admin_rg_001
```

## Login (3 Ways)

### 1️⃣ Flutter App
- Tab: **Admin**
- Name: `Rushi Gund`
- Mobile: `9325118627`
- Password: `Rushi123`

### 2️⃣ cURL
```bash
curl -X POST http://127.0.0.1:5000/api/auth/admin/login \
  -H 'Content-Type: application/json' \
  -d '{"mobile":"9325118627","password":"Rushi123"}'
```

### 3️⃣ Python
```python
import requests
r = requests.post('http://127.0.0.1:5000/api/auth/admin/login',
    json={'mobile':'9325118627','password':'Rushi123'})
token = r.json()['data']['token']
```

## Database Location
```
rg_travel_backend/db/app.db
Table: admins
```

## Files Updated
- ✅ `seeds/seed_admin.py` - Default credentials
- ✅ `utils/jwt_utils.py` - Import fix
- ✅ `API_EXAMPLES.json` - Examples
- ✅ `API_ENDPOINTS.json` - Docs
- ✅ `README_COMPLETE.md` - Usage
- ✅ `ADMIN_CREDENTIALS.md` - Full guide
- ✅ `IMPLEMENTATION_SUMMARY_ADMIN_LOGIN.md` - Technical details

## Status
✅ **FULLY IMPLEMENTED & TESTED**
- Database: Verified
- Password: Hashed & verified
- API: Working
- Token: Generated & valid
- All endpoints: Accessible
