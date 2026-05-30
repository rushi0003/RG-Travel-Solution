# RG Travel Solution - Debugging & Issue Resolution Guide

## Quick Issue Finder

### Backend Won't Start
**Problem**: `python app.py` fails
**Solutions**:
1. Check Python version: `python --version` (need 3.8+)
2. Activate virtual environment first
3. Install dependencies: `pip install -r requirements.txt`
4. Check .env file exists in project root
5. Run verification: `python verify_setup.py`

### Database Errors
**Problem**: "Database locked" or table not found errors
**Solutions**:
1. Delete old database: `rm rg_travel_backend/rg_travel.db`
2. Backend will recreate on next start
3. Check schema.sql syntax in `rg_travel_backend/db/schema.sql`

### CORS Errors in Flutter
**Problem**: "CORS policy: No 'Access-Control-Allow-Origin' header"
**Solutions**:
1. Verify backend running: `curl http://localhost:5000/api/health`
2. Check .env: `RG_CORS_ENABLED=1`
3. Check .env: `RG_CORS_ORIGINS=*` or add Flutter app URL
4. Restart backend after .env changes

### Flutter Build Fails
**Problem**: Build error with Gradle or CocoaPods
**Solutions**:
1. Run `flutter pub get`
2. Run `flutter clean`
3. Delete `.dart_tool/` directory
4. Run `flutter pub get` again
5. Run `flutter doctor` to check setup

### API Authentication Fails
**Problem**: "401 Unauthorized" errors
**Solutions**:
1. Get auth token first:
   ```bash
   curl -X POST http://localhost:5000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"mobile":"1234567890","password":"admin123"}'
   ```
2. Use token in header:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/admin/profile
   ```

### Port Already in Use
**Problem**: "Address already in use" on port 5000
**Solutions**:
1. Kill existing process:
   - Linux/Mac: `lsof -ti:5000 | xargs kill -9`
   - Windows: `netstat -ano | findstr :5000` then `taskkill /PID <PID> /F`
2. Or change port in .env: `RG_PORT=5001`

### Flutter Device Not Found
**Problem**: "No devices found"
**Solutions**:
1. List devices: `flutter devices`
2. For Android: `adb devices` (must show device)
3. For iOS: `xcrun simctl list devices`
4. Connect device via USB
5. Enable USB debugging on Android

---

## Common Errors & Fixes

### Error: `ModuleNotFoundError: No module named 'flask'`
**Cause**: Dependencies not installed
**Fix**: 
```bash
pip install -r requirements.txt
```

### Error: `FileNotFoundError: [Errno 2] No such file or directory: '.env'`
**Cause**: .env file missing
**Fix**: 
```bash
cp .env.example .env
```

### Error: `sqlite3.OperationalError: no such table: admins`
**Cause**: Database not initialized
**Fix**: 
```bash
# Delete corrupted database
rm rg_travel_backend/rg_travel.db

# Restart backend - it will recreate
python rg_travel_backend/app.py
```

### Error: `Connection refused` when Flutter tries to connect
**Cause**: Backend not running
**Fix**:
1. Start backend in terminal: `python rg_travel_backend/app.py`
2. Verify with: `curl http://localhost:5000/api/health`
3. Check backend URL in Flutter code (should be localhost:5000)

### Error: `SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`
**Cause**: SSL certificate issues
**Fix**: (Development only)
```python
# In Flutter/backend code, add:
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

---

## Testing Checklist

### Backend Tests
- [ ] Backend starts without errors: `python app.py`
- [ ] Health endpoint works: `curl http://localhost:5000/api/health`
- [ ] Database tables created: Check SQLite browser
- [ ] Can login: Admin credentials in `.env`
- [ ] JWT token returns: From login endpoint
- [ ] Token refresh works: Use refresh endpoint

### Flutter Tests
- [ ] App launches: `flutter run`
- [ ] Login screen appears
- [ ] Can enter credentials
- [ ] Can submit login form
- [ ] Gets response from backend
- [ ] App navigates to dashboard
- [ ] Dashboard displays data

### Integration Tests
- [ ] Backend running on localhost:5000
- [ ] Flutter app connects to backend
- [ ] Login works end-to-end
- [ ] Data displays in app
- [ ] No CORS errors in console
- [ ] No SSL errors in logs

---

## Debug Tips

### Enable Backend Debug Logging
In `.env`:
```
RG_DEBUG=1
RG_LOG_LEVEL=DEBUG
```

### Flutter Debug Logging
In code:
```dart
void main() {
  Logger.root.level = Level.ALL;
  Logger.root.onRecord.listen((record) {
    debugPrint('[${record.level.name}] ${record.message}');
  });
  runApp(MyApp());
}
```

### Monitor Backend Requests
```bash
# Terminal 1: Start backend with verbose logging
python -u rg_travel_backend/app.py

# Terminal 2: Watch logs
tail -f /var/log/app.log  # Linux/Mac
Get-Content app.log -Wait  # Windows PowerShell
```

### Check Network Requests
Flutter:
```dart
// In api_client.dart, add logging
print('Request: $url');
print('Headers: $headers');
print('Response: ${response.body}');
```

Browser (for web):
- Open DevTools (F12)
- Go to Network tab
- Make requests
- See request/response details

---

## Performance Issues

### Backend Slow
**Check**:
1. Database indexes: `SELECT * FROM sqlite_master WHERE type='index'`
2. Long-running queries: Add timing to logs
3. Too many requests: Implement rate limiting

**Fixes**:
```python
# Add caching
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function():
    pass
```

### Flutter App Slow
**Check**:
1. Large list rendering: Use ListView.builder
2. Image loading: Use cached_network_image
3. State updates: Use Provider efficiently

**Fix**:
```dart
// Use ListView.builder instead of ListView
ListView.builder(
  itemCount: items.length,
  itemBuilder: (context, index) => ListTile(
    title: Text(items[index].title),
  ),
)
```

---

## Security Checklist

- [ ] Never commit .env to git
- [ ] Use strong passwords in production
- [ ] Enable HTTPS in production (not localhost:5000)
- [ ] Change default admin credentials
- [ ] Validate all user inputs
- [ ] Use environment variables for secrets
- [ ] Implement rate limiting
- [ ] Add CORS origin whitelist in production
- [ ] Use secure cookies (HttpOnly, Secure flags)
- [ ] Implement request validation

---

## Deployment Preparation

### Before Production
1. Disable debug mode: `RG_DEBUG=0`
2. Set secure headers:
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True
   app.config['SESSION_COOKIE_HTTPONLY'] = True
   app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
   ```
3. Setup proper database (PostgreSQL instead of SQLite)
4. Configure CORS for production domain only
5. Setup SSL/HTTPS
6. Enable logging and monitoring
7. Setup backup strategy
8. Configure error tracking (Sentry)

### Deployment Commands
```bash
# Install production dependencies
pip install -r requirements.txt
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Run with environment
gunicorn -w 4 -b 0.0.0.0:5000 app:app --env-file .env.production
```

---

## Getting Help

### Resources
1. Check docs/ folder for detailed guides
2. Read API_TESTING_GUIDE.md for endpoint examples
3. Check CONFIGURATION.json for all settings
4. Read PROJECT_COMPLETE_ANALYSIS.md for architecture

### Common Help Paths
- **Backend issues**: See rg_travel_backend/app.py documentation
- **Database issues**: See db/schema.sql and DB_SCHEMA.md
- **Flutter issues**: See FLUTTER_INTEGRATION_GUIDE.md
- **API issues**: See API_TESTING_GUIDE.md
- **Architecture**: See PROJECT_COMPLETE_ANALYSIS.md

---

## Troubleshooting Script

Run this to diagnose issues:

```bash
# Linux/Mac
./diagnose.sh

# Windows PowerShell
.\diagnose.ps1
```

Or manually:
```bash
# Check Python
python --version

# Check pip
pip --version

# Check Flutter
flutter doctor

# Check backend
python rg_travel_backend/verify_setup.py

# Check database
sqlite3 rg_travel_backend/rg_travel.db "SELECT name FROM sqlite_master WHERE type='table';"
```

---

## Feature Requests & Bug Reports

### When reporting an issue:
1. Include error message verbatim
2. Provide steps to reproduce
3. List your Python/Flutter versions
4. Attach relevant logs
5. Describe expected behavior

### Issue Template
```
## Description
What's the issue?

## Steps to Reproduce
1. Step 1
2. Step 2
3. Expected result

## Actual Result
What happened instead?

## Environment
- Python: 3.x.x
- Flutter: x.x.x
- OS: Windows/Mac/Linux

## Logs
[Include error messages]
```

---

## Useful Commands Reference

### Backend
```bash
# Start backend
python app.py

# Run tests
python -m pytest tests/

# Check database
sqlite3 rg_travel.db
.tables
.schema

# Seed data
curl -X POST http://localhost:5000/api/seed/admin

# Health check
curl http://localhost:5000/api/health
```

### Flutter
```bash
# Clean build
flutter clean

# Get dependencies
flutter pub get

# Build APK
flutter build apk

# Build iOS
flutter build ios

# Run tests
flutter test

# Format code
dart format lib/

# Analyze code
dart analyze
```

### Database
```bash
# Open SQLite
sqlite3 rg_travel_backend/rg_travel.db

# List tables
.tables

# Show schema
.schema table_name

# Query data
SELECT * FROM admins LIMIT 10;

# Count records
SELECT COUNT(*) FROM drivers;
```

---

## Next Steps

1. **Stuck?** Read the QUICKSTART_GUIDE.md
2. **Want to test?** Use API_TESTING_GUIDE.md
3. **Integration issues?** Check FLUTTER_INTEGRATION_GUIDE.md
4. **Database questions?** See DATABASE_OPERATIONS_GUIDE.md
5. **Deep dive?** Read PROJECT_COMPLETE_ANALYSIS.md

Good luck! 🚀
