# RG Travel Solution - Admin Login Credentials

## ✅ Primary Admin Account

**Name:** Rushi Gund  
**Mobile:** `9325118627`  
**Password:** `Rushi123`  
**Admin ID:** `admin_rg_001`

---

## 📝 How to Login

### Via Flutter App
1. Launch the Flutter frontend (Chrome web or Windows desktop)
2. Select **Admin** tab on login screen
3. Enter:
   - **Name:** Rushi Gund
   - **Mobile:** 9325118627
   - **Password:** Rushi123
4. Click **Login**

### Via API (cURL)
```bash
curl -X POST http://localhost:5000/api/auth/admin/login \
  -H 'Content-Type: application/json' \
  -d '{"mobile": "9325118627", "password": "Rushi123"}'
```

**Response:**
```json
{
  "success": true,
  "message": "Login success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2026-02-05T21:59:00",
    "profile": {
      "id": "admin_rg_001",
      "name": "Rushi Gund",
      "mobile": "9325118627",
      "email": "admin@rgtravelsolution.com",
      "office_name": "RG Travel Solution",
      "office_location": "Pune",
      "office_address": "RG Office Address, Pune, Maharashtra"
    }
  }
}
```

### Via Python
```python
import requests

response = requests.post(
    'http://localhost:5000/api/auth/admin/login',
    json={
        'mobile': '9325118627',
        'password': 'Rushi123'
    }
)

data = response.json()
token = data['data']['token']
print(f'Login successful! Token: {token}')

# Use token for authenticated requests
headers = {'Authorization': f'Bearer {token}'}
profile = requests.get(
    'http://localhost:5000/api/admin/profile',
    headers=headers
).json()
print(f"Admin: {profile['data']['name']}")
```

### Via Postman
1. **Method:** POST
2. **URL:** `http://localhost:5000/api/auth/admin/login`
3. **Headers:** `Content-Type: application/json`
4. **Body (JSON):**
   ```json
   {
     "mobile": "9325118627",
     "password": "Rushi123"
   }
   ```
5. **Send** → Copy token from response

---

## 🔧 Backend Database

The admin credentials are stored in the **SQLite database** at:
```
rg_travel_backend/db/app.db
```

**Table:** `admins`

**Columns:**
- `id`: admin_rg_001
- `name`: Rushi Gund
- `mobile`: 9325118627 (unique, 10 digits)
- `email`: admin@rgtravelsolution.com
- `office_name`: RG Travel Solution
- `office_location`: Pune
- `office_address`: RG Office Address, Pune, Maharashtra
- `password_salt`: (encrypted)
- `password_hash`: (hashed, verified against "Rushi123")

---

## 🛠️ Admin Features Available

Once logged in as Rushi Gund, you can:

1. **View Driver Requests** - `/api/admin/driver-requests`
2. **View Employee Requests** - `/api/admin/employee-requests`
3. **Create & Manage Trips** - `/api/admin/trips`
4. **Approve/Reject Drivers** - `/api/admin/drivers/approve`, `/api/admin/drivers/reject`
5. **View Live Tracking** - `/api/admin/trips/{trip_id}`
6. **Manage Employees** - `/api/admin/employees`
7. **Update Profile** - `/api/admin/profile`

---

## 📡 Integration Points Updated

- ✅ **seeds/seed_admin.py** - Default credentials updated
- ✅ **API_EXAMPLES.json** - Example requests updated
- ✅ **API_ENDPOINTS.json** - Documentation updated
- ✅ **README_COMPLETE.md** - Usage examples updated
- ✅ **app.py** - Traceback enabled for debugging

---

## ✅ Verification Checklist

- [x] Admin account created in database
- [x] Password hashing verified (Rushi123)
- [x] Seed endpoint tested (`/api/admin/seed`)
- [x] Direct password verification confirmed
- [x] Database record confirmed
- [x] API documentation updated
- [x] JSON examples updated
- [x] README updated with new credentials

---

## 🔐 Security Notes

- Token TTL: 24 hours (configurable in `config/keys.py`)
- Password stored as SHA256(salt + password)
- Mobile number is unique (constraint in database)
- Use HTTPS in production
- Rotate credentials regularly

---

## 📞 Support

For login issues:
1. Verify backend is running: `http://localhost:5000/api/health`
2. Check database: Run `test_admin_login.py`
3. Enable traceback in `app.py` for debugging
4. Check browser console for Flutter errors
