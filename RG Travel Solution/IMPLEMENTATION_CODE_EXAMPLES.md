# RG Travel Solution - Implementation Code Examples
## Ready-to-Use Code Snippets for Remaining Features

---

## 1. TRIP MODIFICATION ENDPOINT (Backend)

### Add to `routes/admin_routes.py`

```python
@admin_bp.post("/api/admin/trips/<int:trip_id>/modify")
def modify_trip(trip_id: int):
    """
    Modify an existing trip (reassign driver or change time).
    
    POST /api/admin/trips/<trip_id>/modify
    {
        "driver_id": 5,
        "schedule_time": "10:30",
        "reason": "Driver requested change"
    }
    """
    data = request.get_json(silent=True) or {}
    new_driver_id = data.get("driver_id")
    new_schedule_time = data.get("schedule_time")
    reason = (data.get("reason") or "").strip()
    
    if not any([new_driver_id, new_schedule_time]):
        return _bad("Must provide driver_id or schedule_time to modify", 400)
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Get current trip
        cur.execute("""
            SELECT id, status, driver_id, schedule_time, trip_type
            FROM trips
            WHERE id = ?
        """, (trip_id,))
        trip = cur.fetchone()
        
        if not trip:
            return _bad("Trip not found", 404)
        
        trip_status = str(trip[1] or "").lower()
        trip_type = str(trip[4] or "").lower()
        
        # Can only modify "assigned" trips (not started or completed)
        if trip_status not in ("created", "assigned"):
            return _bad(f"Cannot modify trip in '{trip_status}' status", 400)
        
        # Validate new driver if provided
        if new_driver_id:
            cur.execute("""
                SELECT id, name, mobile
                FROM drivers
                WHERE id = ? AND is_approved = 1
            """, (new_driver_id,))
            if not cur.fetchone():
                return _bad("Driver not found or not approved", 404)
        
        # Validate new time if provided
        if new_schedule_time:
            if not validate_hhmm(new_schedule_time):
                return _bad("Invalid time format (use HH:MM)", 400)
            
            # Verify employees match this time
            cur.execute("""
                SELECT e.id, e.name
                FROM employees e
                JOIN trip_employees te ON e.id = te.employee_id
                WHERE te.trip_id = ?
                AND (
                    (? = 'pickup' AND e.login_time != ?)
                    OR
                    (? = 'drop' AND e.logout_time != ?)
                )
            """, (trip_id, trip_type, new_schedule_time, trip_type, new_schedule_time))
            
            mismatched = cur.fetchall()
            if mismatched:
                names = [m[1] for m in mismatched]
                return _bad(f"New time doesn't match employees: {', '.join(names)}", 400)
        
        # Update trip
        updates = []
        params = []
        
        if new_driver_id:
            updates.append("driver_id = ?")
            params.append(new_driver_id)
        
        if new_schedule_time:
            updates.append("schedule_time = ?")
            params.append(new_schedule_time)
        
        params.append(_now_iso())
        params.append(trip_id)
        
        cur.execute(f"""
            UPDATE trips
            SET {', '.join(updates)}, updated_at = ?
            WHERE id = ?
        """, params)
        
        conn.commit()
        
        # Log the change (optional: add to audit table if exists)
        log_msg = f"Trip modified by admin: "
        if new_driver_id:
            log_msg += f"driver_id={new_driver_id} "
        if new_schedule_time:
            log_msg += f"schedule_time={new_schedule_time}"
        
        return _ok({
            "trip_id": trip_id,
            "driver_id": new_driver_id or trip[2],
            "schedule_time": new_schedule_time or trip[3],
            "reason": reason
        }, message="Trip modified successfully")
        
    except Exception as e:
        conn.rollback()
        return _bad(f"Modification failed: {str(e)}", 500)
    finally:
        conn.close()
```

---

## 2. SWAP REQUEST WORKFLOW (Backend)

### Add to `routes/driver_routes.py`

```python
@driver_bp.post("/api/driver/<int:driver_id>/trip/<int:trip_id>/swap-request")
def request_swap(driver_id: int, trip_id: int):
    """
    Driver requests emergency vehicle/driver replacement.
    
    POST /api/driver/<driver_id>/trip/<trip_id>/swap-request
    {
        "new_driver_name": "John Replacement",
        "new_mobile": "9876543211",
        "cab_number": "MH01AB1234",
        "reason": "Original driver is sick"
    }
    """
    data = request.get_json(silent=True) or {}
    
    new_driver_name = (data.get("new_driver_name") or "").strip()
    new_mobile = (data.get("new_mobile") or "").strip()
    cab_number = (data.get("cab_number") or "").strip().upper()
    reason = (data.get("reason") or "").strip()
    
    if not all([new_driver_name, new_mobile, cab_number, reason]):
        return _bad("All fields required: name, mobile, cab_number, reason", 400)
    
    if not validate_mobile_10(new_mobile):
        return _bad("Mobile must be 10 digits", 400)
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Verify trip exists and is active
        cur.execute("""
            SELECT id, status, route_no, driver_id
            FROM trips
            WHERE id = ?
        """, (trip_id,))
        trip = cur.fetchone()
        
        if not trip:
            return _bad("Trip not found", 404)
        
        if str(trip[1]).lower() not in ("assigned", "started"):
            return _bad("Can only request swap for active trips", 400)
        
        # Create swap request
        cur.execute("""
            INSERT INTO swap_requests (
                trip_id, requested_by_driver_id,
                new_driver_name, new_mobile, cab_number,
                note, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            trip_id, driver_id,
            new_driver_name, new_mobile, cab_number,
            reason,
            _now_iso(), _now_iso()
        ))
        
        swap_id = cur.lastrowid
        conn.commit()
        
        return _ok({
            "swap_id": swap_id,
            "trip_id": trip_id,
            "route_no": trip[2],
            "status": "pending"
        }, message="Swap request created successfully")
        
    except Exception as e:
        conn.rollback()
        return _bad(f"Failed to create swap request: {str(e)}", 500)
    finally:
        conn.close()
```

### Add to `routes/admin_routes.py`

```python
@admin_bp.post("/api/admin/swap-requests/<int:swap_id>/approve")
def approve_swap_request(swap_id: int):
    """
    Admin approves vehicle/driver replacement request.
    
    POST /api/admin/swap-requests/<swap_id>/approve
    """
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Get swap request
        cur.execute("""
            SELECT id, trip_id, requested_by_driver_id, new_driver_name, 
                   new_mobile, cab_number, status
            FROM swap_requests
            WHERE id = ?
        """, (swap_id,))
        swap = cur.fetchone()
        
        if not swap:
            return _bad("Swap request not found", 404)
        
        if str(swap[6]).lower() != "pending":
            return _bad(f"Request is already {swap[6]}", 400)
        
        # Update swap request
        cur.execute("""
            UPDATE swap_requests
            SET status = 'approved', updated_at = ?
            WHERE id = ?
        """, (_now_iso(), swap_id))
        
        # Update trip (if tracking replacement driver info)
        cur.execute("""
            UPDATE trips
            SET swap_approved_at = ?, updated_at = ?
            WHERE id = ?
        """, (_now_iso(), _now_iso(), swap[1]))
        
        conn.commit()
        
        return _ok({
            "swap_id": swap_id,
            "trip_id": swap[1],
            "status": "approved"
        }, message="Swap request approved")
        
    except Exception as e:
        conn.rollback()
        return _bad(f"Approval failed: {str(e)}", 500)
    finally:
        conn.close()


@admin_bp.post("/api/admin/swap-requests/<int:swap_id>/reject")
def reject_swap_request(swap_id: int):
    """Reject swap request with optional reason."""
    data = request.get_json(silent=True) or {}
    reject_reason = (data.get("reason") or "").strip()
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, status FROM swap_requests WHERE id = ?
        """, (swap_id,))
        swap = cur.fetchone()
        
        if not swap:
            return _bad("Swap request not found", 404)
        
        if str(swap[1]).lower() != "pending":
            return _bad(f"Request is already {swap[1]}", 400)
        
        # Update status
        cur.execute("""
            UPDATE swap_requests
            SET status = 'rejected', updated_at = ?
            WHERE id = ?
        """, (_now_iso(), swap_id))
        
        conn.commit()
        
        return _ok({
            "swap_id": swap_id,
            "status": "rejected",
            "reason": reject_reason
        }, message="Swap request rejected")
        
    except Exception as e:
        conn.rollback()
        return _bad(f"Rejection failed: {str(e)}", 500)
    finally:
        conn.close()
```

---

## 3. CAB ROTATION SERVICE (Backend)

### Create new file: `services/cab_rotation_service.py`

```python
"""
Cab Rotation Service - Ensures fair distribution and prevents repeats.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from ..db import get_db
except Exception:
    from db import get_db


def get_available_cab(conn, route_no: str, vehicle_type: int) -> Dict[str, Any]:
    """
    Get the next available cab for a trip on this route.
    
    Rules:
    1. Never use a cab that's already assigned to this route
    2. Prefer cabs with least recent usage (fair distribution)
    3. Only 4-seater or 6-seater based on vehicle_type
    """
    cur = conn.cursor()
    
    # Get cabs already used on this route
    cur.execute("""
        SELECT DISTINCT d.vehicle_no
        FROM trips t
        JOIN drivers d ON t.driver_id = d.id
        WHERE t.route_no = ? AND t.vehicle_type = ?
    """, (route_no, vehicle_type))
    
    used_cabs = [row[0] for row in cur.fetchall()]
    
    # Get all available cabs, sorted by last usage (least recent first)
    placeholders = ",".join("?" * len(used_cabs)) if used_cabs else "NULL"
    query = f"""
        SELECT id, vehicle_no, last_trip_date, total_trips
        FROM drivers
        WHERE vehicle_type = ?
        AND is_approved = 1
        AND vehicle_no NOT IN ({placeholders if used_cabs else "NULL"})
        ORDER BY last_trip_date ASC, total_trips ASC
        LIMIT 1
    """
    
    params = [vehicle_type]
    params.extend(used_cabs)
    
    cur.execute(query, params)
    result = cur.fetchone()
    
    if not result:
        return {"success": False, "message": "No available cabs"}
    
    return {
        "success": True,
        "data": {
            "driver_id": result[0],
            "vehicle_no": result[1],
            "last_trip": result[2],
            "total_trips": result[3]
        }
    }


def record_trip_for_cab(conn, driver_id: int, distance_km: float) -> None:
    """Update cab usage statistics after trip completion."""
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    cur.execute("""
        UPDATE drivers
        SET last_trip_date = ?, total_trips = total_trips + 1
        WHERE id = ?
    """, (now, driver_id))
    
    conn.commit()
```

---

## 4. MATERIAL 3 ENHANCED ADMIN DASHBOARD (Flutter)

### Replace styling in `lib/screens/admin/admin_dashboard.dart`

```dart
// Add to AdminDashboard class - replace existing _buildTheme or create new method

ThemeData _buildMaterial3Theme() {
  const primaryColor = Color(0xFF4A9EFF);
  const secondaryColor = Color(0xFF00D9FF);
  const tertiaryColor = Color(0xFFFF6B9D);
  const backgroundColor = Color(0xFF121212);
  const surfaceColor = Color(0xFF262626);
  
  final colorScheme = ColorScheme(
    brightness: Brightness.dark,
    primary: primaryColor,
    onPrimary: Colors.white,
    secondary: secondaryColor,
    onSecondary: Colors.black,
    tertiary: tertiaryColor,
    onTertiary: Colors.white,
    error: const Color(0xFFFF5252),
    onError: Colors.white,
    background: backgroundColor,
    onBackground: Colors.white,
    surface: surfaceColor,
    onSurface: Colors.white,
  );
  
  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    
    // AppBar styling
    appBarTheme: AppBarTheme(
      backgroundColor: surfaceColor,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: const TextStyle(
        color: Colors.white,
        fontSize: 20,
        fontWeight: FontWeight.w600,
      ),
    ),
    
    // Card styling
    cardTheme: CardThemeData(
      color: surfaceColor,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
    ),
    
    // Button styling
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        textStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
    
    filledTonalButtonTheme: FilledTonalButtonThemeData(
      style: FilledTonalButton.styleFrom(
        backgroundColor: primaryColor.withOpacity(0.2),
        foregroundColor: primaryColor,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    ),
    
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: primaryColor,
        side: BorderSide(color: primaryColor.withOpacity(0.5)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    ),
    
    // Input decoration
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white.withOpacity(0.05),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(
          color: Colors.white.withOpacity(0.2),
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(
          color: Colors.white.withOpacity(0.2),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(
          color: primaryColor,
          width: 2,
        ),
      ),
      labelStyle: TextStyle(
        color: Colors.white.withOpacity(0.7),
        fontSize: 14,
      ),
      hintStyle: TextStyle(
        color: Colors.white.withOpacity(0.35),
      ),
    ),
    
    // Chip styling
    chipTheme: ChipThemeData(
      backgroundColor: Colors.white.withOpacity(0.1),
      labelStyle: const TextStyle(color: Colors.white),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(
          color: Colors.white.withOpacity(0.2),
        ),
      ),
    ),
  );
}

// Add status badge widget
Widget _buildStatusBadge(String status) {
  final colors = {
    'pending': const Color(0xFFFFB74D),
    'assigned': const Color(0xFF4A9EFF),
    'started': const Color(0xFF00D9FF),
    'completed': const Color(0xFF4CAF50),
    'cancelled': const Color(0xFFFF5252),
  };
  
  final color = colors[status] ?? const Color(0xFF999999);
  
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    decoration: BoxDecoration(
      color: color.withOpacity(0.2),
      borderRadius: BorderRadius.circular(6),
      border: Border.all(
        color: color.withOpacity(0.5),
        width: 1,
      ),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          status.replaceFirst(status[0], status[0].toUpperCase()),
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.w600,
            fontSize: 12,
          ),
        ),
      ],
    ),
  );
}
```

---

## 5. DRIVER SWAP REQUEST UI (Flutter)

### Add to `lib/screens/driver/assigned_trip_screen.dart`

```dart
// Add method to show emergency swap dialog

Future<void> _showSwapRequestDialog() async {
  final swapForm = {
    'driverName': TextEditingController(),
    'mobile': TextEditingController(),
    'cabNumber': TextEditingController(),
    'reason': TextEditingController(),
  };
  
  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Request Driver/Vehicle Replacement'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: swapForm['driverName'],
              decoration: const InputDecoration(
                label: Text('New Driver Name'),
                hintText: 'Full name of replacement driver',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: swapForm['mobile'],
              decoration: const InputDecoration(
                label: Text('Mobile Number'),
                hintText: '10-digit mobile number',
              ),
              keyboardType: TextInputType.phone,
              maxLength: 10,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: swapForm['cabNumber'],
              decoration: const InputDecoration(
                label: Text('Vehicle Number'),
                hintText: 'e.g., MH01AB1234',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: swapForm['reason'],
              decoration: const InputDecoration(
                label: Text('Reason for Replacement'),
                hintText: 'Describe why replacement is needed',
              ),
              maxLines: 3,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            Navigator.pop(context);
            _submitSwapRequest(swapForm);
          },
          child: const Text('Submit Request'),
        ),
      ],
    ),
  );
}

Future<void> _submitSwapRequest(Map<String, TextEditingController> form) async {
  final driverName = form['driverName']!.text.trim();
  final mobile = form['mobile']!.text.trim();
  final cabNumber = form['cabNumber']!.text.trim().toUpperCase();
  final reason = form['reason']!.text.trim();
  
  if (driverName.isEmpty || mobile.isEmpty || cabNumber.isEmpty) {
    _showErrorDialog('All fields required');
    return;
  }
  
  if (mobile.length != 10 || !mobile.allMatches(RegExp(r'\d'))) {
    _showErrorDialog('Mobile must be 10 digits');
    return;
  }
  
  try {
    setState(() => _loading = true);
    
    final payload = {
      'new_driver_name': driverName,
      'new_mobile': mobile,
      'cab_number': cabNumber,
      'reason': reason,
    };
    
    final response = await http.post(
      Uri.parse('$_baseUrl/api/driver/$_driverId/trip/${_assignedTrip?['id']}/swap-request'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _showSuccessDialog('Swap request submitted. Waiting for admin approval.');
      // Refresh trip status
      await _fetchAssignedTrip();
    } else {
      _showErrorDialog('Failed to submit: ${response.body}');
    }
  } catch (e) {
    _showErrorDialog('Error: $e');
  } finally {
    if (mounted) {
      setState(() => _loading = false);
    }
  }
}

void _showSuccessDialog(String message) {
  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.check_circle, color: Colors.green),
          SizedBox(width: 12),
          Text('Success'),
        ],
      ),
      content: Text(message),
      actions: [
        FilledButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('OK'),
        ),
      ],
    ),
  );
}

void _showErrorDialog(String message) {
  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.error_outline, color: Colors.red),
          SizedBox(width: 12),
          Text('Error'),
        ],
      ),
      content: Text(message),
      actions: [
        FilledButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('OK'),
        ),
      ],
    ),
  );
}
```

---

## 6. TRIP HISTORY FILTERING (Flutter)

### Add to `lib/screens/employee/trip_history_screen.dart`

```dart
class TripHistoryFilters {
  DateTime? dateFrom;
  DateTime? dateTo;
  String? statusFilter; // completed, cancelled, etc.
  TextEditingController searchController = TextEditingController();
  
  void reset() {
    dateFrom = null;
    dateTo = null;
    statusFilter = null;
    searchController.clear();
  }
}

class _TripHistoryScreenState extends State<TripHistoryScreen> {
  final _filters = TripHistoryFilters();
  List<Map<String, dynamic>> _allTrips = [];
  List<Map<String, dynamic>> _filteredTrips = [];
  
  @override
  void initState() {
    super.initState();
    _fetchTrips();
    _filters.searchController.addListener(_applyFilters);
  }
  
  Future<void> _fetchTrips() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/employee/$_employeeId/trip-history'),
        headers: {'Authorization': 'Bearer $_token'},
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _allTrips = List<Map<String, dynamic>>.from(data['data']);
          _filteredTrips = _allTrips;
        });
      }
    } catch (e) {
      print('Error fetching trips: $e');
    }
  }
  
  void _applyFilters() {
    setState(() {
      _filteredTrips = _allTrips.where((trip) {
        // Date filter
        if (_filters.dateFrom != null) {
          final tripDate = DateTime.tryParse(trip['trip_date'] ?? '');
          if (tripDate == null || tripDate.isBefore(_filters.dateFrom!)) {
            return false;
          }
        }
        
        if (_filters.dateTo != null) {
          final tripDate = DateTime.tryParse(trip['trip_date'] ?? '');
          if (tripDate == null || tripDate.isAfter(_filters.dateTo!)) {
            return false;
          }
        }
        
        // Status filter
        if (_filters.statusFilter != null && _filters.statusFilter!.isNotEmpty) {
          if (trip['status'] != _filters.statusFilter) {
            return false;
          }
        }
        
        // Search filter
        final searchText = _filters.searchController.text.toLowerCase();
        if (searchText.isNotEmpty) {
          final routeNo = (trip['route_no'] ?? '').toString().toLowerCase();
          final driverName = (trip['driver_name'] ?? '').toString().toLowerCase();
          
          if (!routeNo.contains(searchText) && !driverName.contains(searchText)) {
            return false;
          }
        }
        
        return true;
      }).toList();
    });
  }
  
  Future<void> _selectDateRange() async {
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    
    if (picked != null) {
      setState(() {
        _filters.dateFrom = picked.start;
        _filters.dateTo = picked.end;
      });
      _applyFilters();
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Trip History')),
      body: Column(
        children: [
          // Filters section
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Search
                TextField(
                  controller: _filters.searchController,
                  decoration: InputDecoration(
                    hintText: 'Search by route no or driver name',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                
                // Date range
                FilledButton.icon(
                  onPressed: _selectDateRange,
                  icon: const Icon(Icons.calendar_today),
                  label: Text(
                    _filters.dateFrom != null
                        ? '${_filters.dateFrom!.toLocal()}'.split(' ')[0] +
                            ' - ' +
                            '${_filters.dateTo!.toLocal()}'.split(' ')[0]
                        : 'Select Date Range',
                  ),
                ),
                
                const SizedBox(height: 12),
                
                // Status filter
                Wrap(
                  spacing: 8,
                  children: [
                    FilterChip(
                      label: const Text('Completed'),
                      selected: _filters.statusFilter == 'completed',
                      onSelected: (selected) {
                        setState(() {
                          _filters.statusFilter = selected ? 'completed' : null;
                        });
                        _applyFilters();
                      },
                    ),
                    FilterChip(
                      label: const Text('Cancelled'),
                      selected: _filters.statusFilter == 'cancelled',
                      onSelected: (selected) {
                        setState(() {
                          _filters.statusFilter = selected ? 'cancelled' : null;
                        });
                        _applyFilters();
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
          
          // Results
          Expanded(
            child: _filteredTrips.isEmpty
                ? const Center(child: Text('No trips found'))
                : ListView.builder(
                    itemCount: _filteredTrips.length,
                    itemBuilder: (_, i) => _buildTripCard(_filteredTrips[i]),
                  ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildTripCard(Map<String, dynamic> trip) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        title: Text('Route: ${trip['route_no']}'),
        subtitle: Text('Driver: ${trip['driver_name']} | ${trip['trip_date']}'),
        trailing: Chip(
          label: Text(trip['status'] ?? ''),
          backgroundColor: trip['status'] == 'completed'
              ? Colors.green.withOpacity(0.2)
              : Colors.red.withOpacity(0.2),
        ),
        onTap: () {
          // Show trip details
        },
      ),
    );
  }
}
```

---

## 7. DATABASE MIGRATION HELPER (Python)

### Create file: `backend/migrations/add_missing_fields.py`

```python
"""
Database migration - Add missing columns and tables if needed.
Run after schema update.
"""

import sqlite3
from db import get_db


def add_columns_if_missing():
    """Add missing columns to existing tables."""
    conn = get_db()
    cur = conn.cursor()
    
    # Check and add columns to drivers table if missing
    try:
        cur.execute("SELECT total_trips FROM drivers LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding total_trips to drivers...")
        cur.execute("ALTER TABLE drivers ADD COLUMN total_trips INTEGER DEFAULT 0")
        conn.commit()
    
    try:
        cur.execute("SELECT last_trip_date FROM drivers LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding last_trip_date to drivers...")
        cur.execute("ALTER TABLE drivers ADD COLUMN last_trip_date TEXT")
        conn.commit()
    
    # Check and add columns to trips table if missing
    try:
        cur.execute("SELECT swap_approved_at FROM trips LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding swap_approved_at to trips...")
        cur.execute("ALTER TABLE trips ADD COLUMN swap_approved_at TEXT")
        conn.commit()
    
    conn.close()
    print("Migration complete")


if __name__ == "__main__":
    add_columns_if_missing()
```

---

## 📝 USAGE INSTRUCTIONS

1. **Backend APIs:** Copy code snippets to appropriate route files
2. **Flutter UI:** Copy code snippets to respective screen files
3. **Services:** Create new files (e.g., cab_rotation_service.py)
4. **Tests:** Run `python test_comprehensive_v2.py` after each change

---

**Ready to implement! 🚀**
