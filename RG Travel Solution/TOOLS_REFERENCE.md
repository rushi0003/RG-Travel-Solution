# RG Travel Solution - Tools & Utilities Reference

## 🎯 Essential Tools

### Project Setup & Deployment

#### 1. **Interactive Deployment Assistant**
**File**: `deploy.py`
**Purpose**: Interactive menu-driven deployment and setup
**Usage**:
```bash
python deploy.py                    # Interactive menu
python deploy.py --setup            # Full setup
python deploy.py --backend          # Backend only
python deploy.py --flutter          # Flutter only
python deploy.py --test-backend     # Test backend
python deploy.py --test-flutter     # Test Flutter
python deploy.py --quickstart       # Show guide
```

**Features**:
- ✅ Check Python version
- ✅ Check dependencies
- ✅ Setup .env file
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Initialize database
- ✅ Seed demo data
- ✅ Run verification tests
- ✅ Interactive menu

---

### Verification Scripts

#### 2. **Backend Verification**
**File**: `rg_travel_backend/verify_setup.py`
**Purpose**: Verify backend is properly configured
**Usage**:
```bash
cd rg_travel_backend
python verify_setup.py
```

**Checks**:
- ✅ Python version (3.8+)
- ✅ Required packages installed
- ✅ .env file exists
- ✅ Directory structure
- ✅ Database schema
- ✅ Python modules
- ✅ Flask imports
- ✅ Flask app creation

---

#### 3. **Flutter Verification**
**File**: `rg_travel_flutter/verify_setup.sh`
**Purpose**: Verify Flutter project setup
**Usage**:
```bash
cd rg_travel_flutter
bash verify_setup.sh          # Linux/Mac
powershell ./verify_setup.sh  # Windows (PowerShell)
```

**Checks**:
- ✅ Flutter installation
- ✅ Dart installation
- ✅ pubspec.yaml
- ✅ Project structure
- ✅ lib/ structure
- ✅ Entry points
- ✅ Dependencies cached
- ✅ Flutter doctor

---

### Quick Start Scripts

#### 4. **Windows Backend Startup**
**File**: `start-backend.bat`
**Purpose**: One-click backend startup (Windows)
**Usage**:
```bash
start-backend.bat
```

**Does**:
1. Checks Python installation
2. Creates/uses .env file
3. Creates virtual environment
4. Activates virtual environment
5. Installs dependencies
6. Runs verification
7. Starts Flask app

---

#### 5. **PowerShell Backend Startup**
**File**: `start-backend.ps1`
**Purpose**: PowerShell version of backend startup
**Usage**:
```powershell
.\start-backend.ps1
```

**Features**:
- Colored output
- Error handling
- Virtual environment setup
- Automatic .env creation
- Dependency installation

---

#### 6. **Flutter Startup Script**
**File**: `start-flutter.bat`
**Purpose**: One-click Flutter app startup (Windows)
**Usage**:
```bash
start-flutter.bat
```

**Does**:
1. Checks Flutter installation
2. Gets dependencies
3. Lists available devices
4. Starts Flutter app

---

## 📊 Information & Reference Files

### Documentation Files

#### 7. **Complete Project Index**
**File**: `PROJECT_INDEX.md`
**Purpose**: Navigation hub for all documentation
**Contains**:
- Quick navigation
- Documentation index
- Project structure
- Statistics
- Technology stack
- Configuration reference
- Testing instructions
- Deployment checklist

---

#### 8. **Debugging & Issue Resolution Guide**
**File**: `DEBUGGING_GUIDE.md`
**Purpose**: Troubleshooting and issue resolution
**Sections**:
- Quick issue finder
- Common errors & fixes
- Testing checklist
- Debug tips
- Performance issues
- Security checklist
- Deployment preparation
- Troubleshooting script

---

### JSON Reference Files

#### 9. **API Endpoints Reference**
**File**: `docs/API_ENDPOINTS.json`
**Purpose**: Complete API endpoint documentation
**Contains**:
- All 50+ endpoints
- Request/response examples
- Authentication details
- Status codes
- Error responses

**Example**:
```json
{
  "auth": {
    "POST /api/auth/login": {
      "description": "Authenticate user",
      "request": {"mobile": "1234567890", "password": "admin123"},
      "response": {"token": "jwt_token", "user": {...}}
    }
  }
}
```

---

#### 10. **Database Schema Reference**
**File**: `docs/DATABASE_SCHEMA.json`
**Purpose**: Database structure reference
**Contains**:
- All table definitions
- Column details
- Data types
- Constraints
- Relationships
- Indexes

---

#### 11. **Configuration Reference**
**File**: `docs/CONFIGURATION.json`
**Purpose**: All environment variables documented
**Contains**:
- Variable names
- Descriptions
- Default values
- Example values
- When to change
- Security notes

---

#### 12. **API Code Examples**
**File**: `docs/API_EXAMPLES.json`
**Purpose**: Working code examples
**Languages**:
- Python
- JavaScript
- cURL
- PHP
- Swift

---

#### 13. **Setup Guide**
**File**: `docs/SETUP_GUIDE.json`
**Purpose**: Installation steps
**Contains**:
- Prerequisites
- Step-by-step instructions
- Troubleshooting
- Verification steps

---

#### 14. **Project Inventory**
**File**: `docs/PROJECT_INVENTORY.json`
**Purpose**: Complete file manifest
**Contains**:
- All files
- File sizes
- Line counts
- Descriptions
- Dependencies

---

## 📚 Documentation Files

### Getting Started
- **[QUICKSTART_GUIDE.md](docs/QUICKSTART_GUIDE.md)** - 5-minute setup
- **[README.md](README.md)** - Project overview

### Development Guides
- **[API_TESTING_GUIDE.md](docs/API_TESTING_GUIDE.md)** - API testing with examples
- **[FLUTTER_INTEGRATION_GUIDE.md](docs/FLUTTER_INTEGRATION_GUIDE.md)** - Frontend development
- **[DATABASE_OPERATIONS_GUIDE.md](docs/DATABASE_OPERATIONS_GUIDE.md)** - Database operations
- **[PROJECT_COMPLETE_ANALYSIS.md](docs/PROJECT_COMPLETE_ANALYSIS.md)** - Architecture analysis

### Reference
- **[README_COMPLETE.md](docs/README_COMPLETE.md)** - Comprehensive guide
- **[DB_SCHEMA.md](docs/DB_SCHEMA.md)** - Schema documentation
- **[API_DOCS.md](docs/API_DOCS.md)** - API documentation
- **[FLOW.md](docs/FLOW.md)** - Application flow

---

## 🛠️ Database Tools

### SQLite Commands

**Open database**:
```bash
sqlite3 rg_travel_backend/rg_travel.db
```

**Common commands**:
```sql
-- List tables
.tables

-- Show schema
.schema table_name

-- Query data
SELECT * FROM admins LIMIT 10;

-- Count records
SELECT COUNT(*) FROM drivers;

-- Export data
.mode csv
.output export.csv
SELECT * FROM trips;

-- Show indexes
.indexes table_name
```

---

## 🧪 Testing Tools

### Python Testing

**Run tests**:
```bash
cd rg_travel_backend

# All tests
python -m pytest tests/

# Verbose output
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=.

# Specific test
python -m pytest tests/test_auth.py -v
```

### Flutter Testing

**Run tests**:
```bash
cd rg_travel_flutter

# All tests
flutter test

# Specific test
flutter test test/services/auth_service_test.dart

# With coverage
flutter test --coverage

# Watch mode
flutter test --watch
```

---

## 🔍 Analysis Tools

### Backend Analysis

**Code analysis**:
```bash
# Check code quality
pylint rg_travel_backend/

# Type checking
mypy rg_travel_backend/

# Format check
black --check rg_travel_backend/

# Security check
bandit -r rg_travel_backend/
```

### Flutter Analysis

**Code analysis**:
```bash
cd rg_travel_flutter

# Analyze Dart code
dart analyze

# Format Dart code
dart format lib/

# Check Flutter code
flutter analyze
```

---

## 📊 Monitoring & Logging

### Backend Logging

**Enable logging**:
```python
# In app.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Message")
```

**View logs**:
```bash
# Real-time logs
tail -f logs/app.log

# Last 100 lines
tail -100 logs/app.log

# Search logs
grep "error" logs/app.log
```

### Flutter Logging

**View logs**:
```bash
# Show logs
flutter logs

# Filter logs
flutter logs --grep="keyword"
```

---

## 🚀 Performance Tools

### Backend Performance

**Profile requests**:
```python
from flask import g
import time

@app.before_request
def before_request():
    g.start = time.time()

@app.after_request
def after_request(response):
    elapsed = time.time() - g.start
    print(f"Request took {elapsed:.2f}s")
    return response
```

### Database Performance

**Check query performance**:
```sql
-- Enable query timing
.timer on

-- Run query
SELECT * FROM trips WHERE status='active';

-- Check indexes
EXPLAIN QUERY PLAN SELECT * FROM trips WHERE status='active';
```

---

## 📦 Dependency Management

### Python Dependencies

**Update dependencies**:
```bash
# Check outdated packages
pip list --outdated

# Update all packages
pip install --upgrade pip

# Update specific package
pip install --upgrade flask

# Freeze dependencies
pip freeze > requirements.txt
```

### Flutter Dependencies

**Update dependencies**:
```bash
# Check outdated packages
flutter pub outdated

# Update dependencies
flutter pub get

# Update specific package
flutter pub add http

# Remove package
flutter pub remove http
```

---

## 🔐 Security Tools

### Security Checks

**Check Python security**:
```bash
# Check for vulnerabilities
safety check

# Security audit
bandit -r rg_travel_backend/

# Dependency check
pip-audit
```

**Check Flutter security**:
```bash
# Check pub.dev for vulnerabilities
pub publish --dry-run
```

---

## 🌐 API Testing Tools

### cURL Commands

**Test endpoints**:
```bash
# Health check
curl http://localhost:5000/api/health

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"mobile":"1234567890","password":"admin123"}'

# With token
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:5000/api/admin/profile
```

### Postman

**Import collection**:
1. Download `docs/API_EXAMPLES.json`
2. Open Postman
3. Click Import
4. Select file
5. Test all endpoints

### cURL Collections

**Save requests**:
```bash
# Save response
curl -o response.json http://localhost:5000/api/health

# Save with headers
curl -i -o response.txt http://localhost:5000/api/health

# Verbose output
curl -v http://localhost:5000/api/health
```

---

## 📋 Checklists

### Before Starting Development
- [ ] Run `python deploy.py --setup`
- [ ] Run `python rg_travel_backend/verify_setup.py`
- [ ] Start backend: `python app.py`
- [ ] Test health: `curl http://localhost:5000/api/health`
- [ ] Run `flutter pub get`
- [ ] Test Flutter: `flutter run`

### Before Commit
- [ ] Run tests
- [ ] Check code analysis
- [ ] Update documentation
- [ ] Verify no debug code
- [ ] Check .env not committed
- [ ] Verify all endpoints work

### Before Deployment
- [ ] Set `RG_DEBUG=0`
- [ ] Update environment variables
- [ ] Run security checks
- [ ] Run all tests
- [ ] Test production build
- [ ] Backup database
- [ ] Setup monitoring

---

## 💡 Pro Tips

### Speed Up Development

**Reload on changes**:
```bash
# Python
pip install watchdog
watchmedo auto-restart -d rg_travel_backend -p '*.py' -- python app.py

# Flutter
flutter run -d chrome  # Hot reload
```

**Use aliases**:
```bash
alias backend="cd rg_travel_backend && python app.py"
alias flutter="cd rg_travel_flutter && flutter run"
alias verify="python rg_travel_backend/verify_setup.py"
```

### Database Debugging

**Export data for testing**:
```bash
# Export as CSV
sqlite3 rg_travel.db ".mode csv" ".output data.csv" "SELECT * FROM trips;"

# Export as JSON
sqlite3 rg_travel.db ".mode json" "SELECT * FROM trips;"
```

### API Debugging

**Inspect requests/responses**:
```python
# Add to app.py
@app.before_request
def log_request():
    print(f"METHOD: {request.method}")
    print(f"PATH: {request.path}")
    print(f"DATA: {request.get_json()}")
```

---

## 📞 Tool Quick Reference

| Tool | Purpose | Command |
|------|---------|---------|
| `deploy.py` | Interactive setup | `python deploy.py` |
| `verify_setup.py` | Backend verification | `python verify_setup.py` |
| `sqlite3` | Database CLI | `sqlite3 rg_travel.db` |
| `curl` | API testing | `curl http://localhost:5000/api/health` |
| `flutter` | Mobile development | `flutter run` |
| `pytest` | Python testing | `python -m pytest tests/` |
| `pylint` | Code analysis | `pylint rg_travel_backend/` |
| `dart` | Dart tools | `dart analyze` |

---

## 🎓 Learning Resources

### Official Documentation
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flutter Documentation](https://flutter.dev/docs)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python Documentation](https://docs.python.org/3/)
- [Dart Documentation](https://dart.dev/guides)

### Tutorials
- [Flask Tutorial](https://flask.palletsprojects.com/tutorial/)
- [Flutter Codelabs](https://flutter.dev/docs/codelabs)
- [REST API Design](https://restfulapi.net/)
- [JWT Introduction](https://jwt.io/introduction)

---

**Need help?** Check [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md) for troubleshooting or [PROJECT_INDEX.md](PROJECT_INDEX.md) for navigation.
