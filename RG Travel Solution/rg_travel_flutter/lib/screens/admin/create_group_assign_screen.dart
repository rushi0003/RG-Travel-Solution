// create_group_assign_screen.dart
//
// RG Travel Solution — Group Creation & Trip Assignment (FULL REDESIGN)
// ✅ Same backend/API connection via AdminService (NO endpoint changes here)
// ✅ Keeps full flow + all buttons from your HTML:
//    - Clear / Submit
//    - Trip Type (Pickup/Drop)
//    - Time Slot (from API)
//    - Vehicle Type (4/6, allow one or both)
//    - Vehicles list + Select All / Clear
//    - Go Home request list (priority selectable)
//    - Employees list + Select All / Clear
//    - Create Group / View & Modify Groups / Assign Trip
//
// NOTE:
// - This file assumes your existing AdminService methods already work:
//   getScheduledTimes, getDrivers, getEmployees, getGoHomeRequests, getNoTripRequests,
//   createGroups, getGroups, removeEmployeeFromGroup, addEmployeeToGroup, changeGroupVehicle,
//   getAvailableDrivers, assignGroupTrip, copyToClipboard, startTrip, finishTrip,
//   searchVehiclesNLP, searchEmployeesNLP, getAdminProfile
//
// - UI is redesigned to match your HTML layout (card + sections + modal dialogs).

import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';

import '../../services/admin_service.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/common/rg_search_field.dart';
import '../../widgets/common/rg_loader.dart';

class CreateGroupAssignScreen extends StatefulWidget {
  final String adminId;

  const CreateGroupAssignScreen({
    super.key,
    required this.adminId,
  });

  @override
  State<CreateGroupAssignScreen> createState() =>
      _CreateGroupAssignScreenState();
}

class _CreateGroupAssignScreenState extends State<CreateGroupAssignScreen> {
  static String _todayKey() {
    final now = DateTime.now();
    return '${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}';
  }

  // ===== Config =====
  String _tripType = 'pickup'; // pickup | drop
  final Set<int> _vehicleTypes = {
    6,
    4
  }; // allow one or both (like your HTML checkbox)
  String? _selectedTime;
  List<String> _times = [];
  String _tripDay = _todayKey(); // YYYYMMDD

  // ===== Data =====
  bool _loading = false;
  bool _loadingTimes = false;

  List<Map<String, dynamic>> _drivers = [];
  List<Map<String, dynamic>> _employees = [];
  List<Map<String, dynamic>> _goHomeRequests = [];
  List<Map<String, dynamic>> _noTripRequests = [];
  List<Map<String, dynamic>> _approvedGoHomeRequests = [];
  List<Map<String, dynamic>> _pendingGoHomeRequests = [];
  int _slotEmployeesTotal = 0;
  int _slotAvailableEmployees = 0;

  // ===== Search + Filter =====
  final TextEditingController _vehicleSearch = TextEditingController();
  final TextEditingController _employeeSearch = TextEditingController();

  Timer? _vehDebounce;
  Timer? _empDebounce;

  bool _vehNlpSearching = false;
  bool _empNlpSearching = false;

  List<Map<String, dynamic>> _filteredDrivers = [];
  List<Map<String, dynamic>> _filteredEmployees = [];

  // ===== Selection =====
  final Set<int> _selectedVehicleIds = {};
  final Set<int> _selectedEmployeeIds = {};

  // ===== Groups =====
  bool _creatingGroups = false;
  List<dynamic> _groups = [];
  Map<int, dynamic> _tripHistory = {}; // track created trips
  final Set<int> _assigningGroupKeys = {};
  bool _assigningAllGroups = false;

  // Driver assignment per group index
  final Map<int, int?> _selectedDriversByGroupIndex = {};
  final Map<int, List<Map<String, dynamic>>> _availableDriversForGroup = {};

  // Go Home request management
  final Map<int, String> _goHomeRequestStatus =
      {}; // driver_id -> 'pending'|'approved'|'assigned'

  @override
  void initState() {
    super.initState();
    _boot();
  }

  void _safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  @override
  void setState(VoidCallback fn) {
    if (!mounted) return;
    super.setState(fn);
  }

  @override
  void dispose() {
    _vehicleSearch.dispose();
    _employeeSearch.dispose();
    _vehDebounce?.cancel();
    _empDebounce?.cancel();
    super.dispose();
  }

  Future<void> _boot() async {
    _safeSetState(() => _loading = true);
    try {
      await _loadTimes();
      await _loadLists();
      _applyLocalFilters();
    } finally {
      _safeSetState(() => _loading = false);
    }
  }

  Future<void> _loadTimes() async {
    _safeSetState(() => _loadingTimes = true);
    try {
      final t = await AdminService.getScheduledTimes(
        tripType: _tripType,
        adminId: widget.adminId,
      );
      _safeSetState(() {
        _times = t;
        if (_times.isNotEmpty) {
          _selectedTime =
              (_selectedTime != null && _times.contains(_selectedTime))
                  ? _selectedTime
                  : _times.first;
        } else {
          _selectedTime = null;
        }
      });
    } catch (e) {
      debugPrint("getScheduledTimes error: $e");
    } finally {
      _safeSetState(() => _loadingTimes = false);
    }
  }

  Future<void> _loadLists() async {
    try {
      final drivers = await AdminService.getDrivers();
      final employees = await AdminService.getEmployees();
      final goHomeRaw =
          await AdminService.getGoHomeRequests(adminId: widget.adminId);
      final goHome = goHomeRaw.where(_isRealGoHomeRequest).toList();
      final noTrip = await AdminService.getNoTripRequests(
        adminId: widget.adminId,
      );
      List<Map<String, dynamic>> availableVehicles = [];
      List<Map<String, dynamic>> availableEmployees = [];

      final selectedTime = _selectedTime;
      var slotEmployeesTotal = 0;
      if (selectedTime != null && selectedTime.isNotEmpty) {
        final timeKey = _tripType == 'pickup' ? 'login_time' : 'logout_time';
        slotEmployeesTotal = employees.where((e) {
          final t = (e[timeKey] ?? '').toString().trim();
          return t == selectedTime;
        }).length;
        final selectedType =
            _vehicleTypes.contains(4) && _vehicleTypes.contains(6)
                ? 'both'
                : (_vehicleTypes.contains(6) ? '6' : '4');

        final tripDay = _currentTripDay();
        availableVehicles = await AdminService.getAvailableVehicles(
          adminId: widget.adminId,
          tripType: _tripType,
          scheduledTime: selectedTime,
          vehicleTypes: selectedType,
          date: tripDay,
          excludeAssigned: true,
        );
        availableEmployees = await AdminService.getAvailableEmployees(
          adminId: widget.adminId,
          tripType: _tripType,
          timeSlot: selectedTime,
          tripDay: tripDay,
        );
      }

      // ===== ENHANCED: Separate Go Home requests by approval status =====
      final approved = goHome
          .where((r) =>
              (r['status'] ?? '').toString().toLowerCase() == 'approved' ||
              (r['approved'] ?? false) == true)
          .toList();

      final pending = goHome
          .where((r) =>
              (r['status'] ?? '').toString().toLowerCase() == 'pending' ||
              (r['approved'] ?? false) == false)
          .toList();

      _safeSetState(() {
        final hasSlotContext = selectedTime != null && selectedTime.isNotEmpty;
        _drivers = _dedupeDrivers(hasSlotContext
            ? (availableVehicles.isNotEmpty ? availableVehicles : drivers)
            : drivers);
        // Keep strict slot-based eligibility when time is selected.
        // Do not fallback to full employee list, otherwise ineligible users
        // can be selected and backend rightfully rejects them.
        _employees =
            _dedupeEmployees(hasSlotContext ? availableEmployees : employees);
        _goHomeRequests = _dedupeDrivers(goHome);
        _approvedGoHomeRequests = _dedupeDrivers(approved);
        _pendingGoHomeRequests = _dedupeDrivers(pending);
        _noTripRequests = noTrip;
        _slotEmployeesTotal = hasSlotContext ? slotEmployeesTotal : 0;
        _slotAvailableEmployees = hasSlotContext ? _employees.length : 0;

        // Initialize Go Home request status map
        for (var r in goHome) {
          final did = _asInt(r['driver_id']) ?? 0;
          _goHomeRequestStatus[did] =
              (r['status'] ?? 'pending').toString().toLowerCase();
        }
      });
      _applyLocalFilters();
    } catch (e) {
      debugPrint("loadLists error: $e");
    }
  }

  bool _isRealGoHomeRequest(Map<String, dynamic> request) {
    final requestId = _asInt(request['id'] ?? request['request_id']) ?? 0;
    final driverId = _asInt(request['driver_id']) ?? 0;
    if (requestId <= 0 || driverId <= 0) return false;

    // If backend sends explicit intent flags, enforce them.
    if (request.containsKey('go_home_request') &&
        request['go_home_request'] != true) {
      return false;
    }
    final requestType =
        (request['request_type'] ?? '').toString().toLowerCase();
    if (requestType.isNotEmpty &&
        !requestType.contains('go_home') &&
        !requestType.contains('hometown')) {
      return false;
    }

    bool hasDemoKeyword(dynamic value) {
      final text = (value ?? '').toString().trim().toLowerCase();
      if (text.isEmpty) return false;
      return RegExp(r'\b(demo|dummy|sample|mock|test)\b').hasMatch(text);
    }

    if (hasDemoKeyword(request['driver_name'])) return false;
    if (hasDemoKeyword(request['cab_number'] ?? request['cab_no']))
      return false;
    if (hasDemoKeyword(request['home_address'])) return false;

    return true;
  }

  // ===== ENHANCED: Go Home Request Approval Workflow =====
  Future<void> _approveGoHomeRequest(Map<String, dynamic> request) async {
    final driverId = _asInt(request['driver_id']) ?? 0;
    final requestId = _asInt(request['id'] ?? request['request_id']) ?? 0;
    if (requestId == 0) return;
    if (driverId == 0) return;

    try {
      // Call backend to approve (if endpoint exists)
      final resp = await AdminService.approveGoHomeRequest(
        requestId: requestId,
        driverId: driverId,
        adminId: widget.adminId,
      );

      if (resp['success'] == true) {
        setState(() {
          _goHomeRequestStatus[driverId] = 'approved';
          _selectedVehicleIds.add(driverId);
        });
        await _loadLists();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content:
                  Text("Go Home request approved for Driver ID $driverId")),
        );
      }
    } catch (e) {
      debugPrint("approveGoHomeRequest error: $e");
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error approving request: $e")),
      );
    }
  }

  Future<void> _rejectGoHomeRequest(Map<String, dynamic> request) async {
    final driverId = _asInt(request['driver_id']) ?? 0;
    final requestId = _asInt(request['id'] ?? request['request_id']) ?? 0;
    if (requestId == 0) return;
    if (driverId == 0) return;

    try {
      final resp = await AdminService.rejectGoHomeRequest(
        requestId: requestId,
        driverId: driverId,
        adminId: widget.adminId,
      );

      if (resp['success'] == true) {
        setState(() {
          _goHomeRequestStatus[driverId] = 'rejected';
          _selectedVehicleIds.remove(driverId);
        });
        await _loadLists();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Go Home request rejected")),
        );
      }
    } catch (e) {
      debugPrint("rejectGoHomeRequest error: $e");
    }
  }

  // ===== ENHANCED: Find nearest available trip for Go Home request =====
  Future<void> _findAndAssignNearestTripForDriver(
      Map<String, dynamic> request) async {
    var loadingShown = false;
    try {
      final driverId = _asInt(request['driver_id']) ?? 0;
      if (driverId == 0) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text("Invalid driver ID")));
        return;
      }

      final homeLat =
          _asDouble(request['home_location_lat'] ?? request['home_lat'] ?? 0.0);
      final homeLng =
          _asDouble(request['home_location_lng'] ?? request['home_lng'] ?? 0.0);

      if (homeLat == 0.0 || homeLng == 0.0) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Driver home location not set")));
        return;
      }

      // Show loading dialog
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => Dialog(
          backgroundColor: AppThemeColors.surface,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const CircularProgressIndicator(),
                const SizedBox(height: 16),
                const Text("Finding nearest trip..."),
                const SizedBox(height: 8),
                Text(
                  "Searching within 15 km radius",
                  style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textTertiary, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      );
      loadingShown = true;

      // Call backend to find nearest trip
      final resp = await AdminService.findNearestTripForDriver(
        driverId: driverId.toString(),
        homeLat: homeLat,
        homeLng: homeLng,
        tripType: _tripType,
        maxDistanceKm: 15.0,
        adminId: widget.adminId,
        excludeTripIds: [],
      );

      if (!mounted) return;
      if (loadingShown) {
        Navigator.pop(context); // Close loading dialog
        loadingShown = false;
      }

      List<Map<String, dynamic>> trips = [];
      final rawData = resp['data'];
      if (rawData is List) {
        trips = rawData
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => e.cast<String, dynamic>())
            .toList();
      } else if (rawData is Map<dynamic, dynamic>) {
        trips = [rawData.cast<String, dynamic>()];
      }

      trips = trips
          .map((t) => {
                ...t,
                'distance_from_home_km':
                    _asDouble(t['distance_from_home_km'] ?? t['distance_km']),
              })
          .toList();

      if (resp['success'] == true && trips.isNotEmpty) {
        // Show dialog to select from available trips
        _showSelectNearestTripDialog(request, trips);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text("No nearby trips found within 15 km range")),
        );
      }
    } catch (e) {
      if (mounted) {
        if (loadingShown) {
          Navigator.pop(context); // Close loading dialog if still open
        }
        debugPrint("findNearestTripForDriver error: $e");
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error finding trip: $e")),
        );
      }
    }
  }

  // ===== Show dialog to select from nearest trips =====
  void _showSelectNearestTripDialog(
    Map<String, dynamic> goHomeRequest,
    List<Map<String, dynamic>> nearestTrips,
  ) {
    int? selectedTripIndex = 0;

    showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (_, setS) => Dialog(
          backgroundColor: AppThemeColors.surface,
          insetPadding: const EdgeInsets.all(16),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          child: SizedBox(
            width: 500,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Select Trip for Auto-Assignment",
                        style:
                            AppTypography.headlineLarge.copyWith(fontSize: 18),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "Choose the best trip from ${nearestTrips.length} nearest options",
                        style: AppTypography.bodyMedium.copyWith(
                            color: AppThemeColors.textTertiary, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                const Divider(color: AppThemeColors.border),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    itemCount: nearestTrips.length,
                    itemBuilder: (_, i) {
                      final trip = nearestTrips[i];
                      final isSel = selectedTripIndex == i;
                      final dist =
                          _asDouble(trip['distance_from_home_km'] ?? 0.0);
                      final eta = _asInt(trip['eta_minutes'] ?? 0);
                      final empCount = _asInt(trip['employee_count'] ?? 0);

                      return InkWell(
                        onTap: () => setS(() => selectedTripIndex = i),
                        child: Container(
                          margin: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isSel
                                ? AppThemeColors.primary.withValues(alpha: 0.12)
                                : AppThemeColors.cardGlass,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isSel
                                  ? AppThemeColors.primary
                                      .withValues(alpha: 0.35)
                                  : AppThemeColors.border,
                            ),
                          ),
                          child: Row(
                            children: [
                              Radio<int>(
                                value: i,
                                // Warning fix: keeping legacy Radio API preserves current selection behavior.
                                // ignore: deprecated_member_use
                                groupValue: selectedTripIndex,
                                // Warning fix: keeping legacy Radio API preserves current selection behavior.
                                // ignore: deprecated_member_use
                                onChanged: (v) =>
                                    setS(() => selectedTripIndex = v),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          "Trip ${i + 1} • Route ${(trip['route_no'] ?? 'N/A').toString().substring(0, min(8, (trip['route_no'] ?? '').toString().length))}",
                                          style: AppTypography.bodyMedium
                                              .copyWith(
                                                  fontWeight: FontWeight.w700),
                                        ),
                                        const Spacer(),
                                        _pill(
                                            "${dist.toStringAsFixed(1)} km away"),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Row(
                                      children: [
                                        _statBadge("ETA: ${eta}m",
                                            color: AppThemeColors.info),
                                        const SizedBox(width: 8),
                                        _statBadge("$empCount employees",
                                            color: AppThemeColors.success),
                                        const SizedBox(width: 8),
                                        _statBadge(
                                            _tripType == 'pickup'
                                                ? 'Pickup'
                                                : 'Drop',
                                            color: AppThemeColors.warning),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                const Divider(color: AppThemeColors.border),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () => Navigator.pop(ctx),
                          style: ElevatedButton.styleFrom(
                              backgroundColor:
                                  AppThemeColors.error.withValues(alpha: 0.18)),
                          child: const Text("Cancel"),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () async {
                            if (selectedTripIndex != null &&
                                selectedTripIndex! < nearestTrips.length) {
                              final selectedTrip =
                                  nearestTrips[selectedTripIndex!];
                              Navigator.pop(ctx);
                              await _assignGoHomeTripToDriver(
                                  goHomeRequest, selectedTrip);
                            }
                          },
                          style: ElevatedButton.styleFrom(
                              backgroundColor: AppThemeColors.primary),
                          child: const Text("Assign",
                              style: TextStyle(fontWeight: FontWeight.w900)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ===== Auto-assign selected trip to driver =====
  Future<void> _assignGoHomeTripToDriver(
    Map<String, dynamic> goHomeRequest,
    Map<String, dynamic> selectedTrip,
  ) async {
    try {
      final requestId =
          _asInt(goHomeRequest['id'] ?? goHomeRequest['request_id']) ?? 0;
      final driverId = _asInt(goHomeRequest['driver_id']) ?? 0;
      final tripId = _asInt(selectedTrip['trip_id']) ?? 0;

      if (requestId == 0 || driverId == 0 || tripId == 0) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Missing required data")));
        return;
      }

      final resp = await AdminService.assignGoHomeTripToDriver(
        driverId: driverId.toString(),
        goHomeRequestId: requestId,
        tripId: tripId,
        adminId: widget.adminId,
        distanceFromHomeKm: _asDouble(selectedTrip['distance_from_home_km'] ??
            selectedTrip['distance_km'] ??
            0),
        overrideOriginalDriver: false,
      );

      if (resp['success'] == true) {
        setState(() {
          _goHomeRequestStatus[driverId] = 'assigned';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(
                  "Trip assigned to driver! Assignment: ${resp['data']?['assignment_id'] ?? 'N/A'}")),
        );
        // Reload go home requests to reflect changes
        await _loadLists();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(
                  "Failed to assign trip: ${resp['message'] ?? 'Unknown error'}")),
        );
      }
    } catch (e) {
      debugPrint("assignGoHomeTripToDriver error: $e");
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text("Error: $e")));
    }
  }

  double _asDouble(dynamic v) {
    if (v == null) return 0.0;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    try {
      return double.parse(v.toString());
    } catch (_) {
      return 0.0;
    }
  }

  String _currentTripDay() {
    return _tripDay;
  }

  String _formatTripDay(String yyyymmdd) {
    if (yyyymmdd.length != 8) return yyyymmdd;
    final y = yyyymmdd.substring(0, 4);
    final m = yyyymmdd.substring(4, 6);
    final d = yyyymmdd.substring(6, 8);
    return '$d-$m-$y';
  }

  Future<void> _pickTripDay() async {
    DateTime initialDate = DateTime.now();
    if (_tripDay.length == 8) {
      final y = int.tryParse(_tripDay.substring(0, 4));
      final m = int.tryParse(_tripDay.substring(4, 6));
      final d = int.tryParse(_tripDay.substring(6, 8));
      if (y != null && m != null && d != null) {
        initialDate = DateTime(y, m, d);
      }
    }
    final picked = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime.now().subtract(const Duration(days: 30)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked == null) return;
    setState(() {
      _tripDay =
          '${picked.year}${picked.month.toString().padLeft(2, '0')}${picked.day.toString().padLeft(2, '0')}';
    });
    await _loadLists();
    _applyLocalFilters();
  }

  // ===== ENHANCED: Better employee filtering (exclude assigned, on leave, no-trip) =====
  List<Map<String, dynamic>> _getEligibleEmployees() {
    final noTripIds = _noTripRequests
        .map((r) => _asInt(r['employee_id'] ?? r['id']) ?? 0)
        .toSet();

    return _employees.where((e) {
      final eid = _employeeId(e);

      // Exclude no-trip request employees
      if (noTripIds.contains(eid)) return false;

      // Exclude already assigned employees (from previous groups)
      if (_selectedEmployeeIds.contains(eid)) return false;

      // Check for leave/approved absence status
      final status = (e['status'] ?? '').toString().toLowerCase();
      if (status.contains('leave') || status.contains('absent')) return false;

      // Check for no-trip request
      if ((e['trip_required'] ?? true) == false) return false;

      return true;
    }).toList();
  }

  // ===== ENHANCED: Vehicle sorting with priority (6-seater first) =====
  List<Map<String, dynamic>> _sortVehiclesByPriority(
      List<Map<String, dynamic>> vehicles) {
    final sorted = [...vehicles];
    sorted.sort((a, b) {
      final seatsA = _vehicleSeats(a);
      final seatsB = _vehicleSeats(b);

      // 6-seater has priority (comes first)
      if (seatsA != seatsB) {
        return seatsB.compareTo(seatsA); // Higher seats first
      }

      // Secondary sort by availability status
      final statusA = (a['status'] ?? '').toString().toLowerCase();
      final statusB = (b['status'] ?? '').toString().toLowerCase();

      if (statusA.contains('available') && !statusB.contains('available'))
        return -1;
      if (!statusA.contains('available') && statusB.contains('available'))
        return 1;

      return 0;
    });
    return sorted;
  }

  // ===== Helpers =====
  int? _asInt(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    final raw = v.toString().trim();
    final direct = int.tryParse(raw);
    if (direct != null) return direct;
    final digits = RegExp(r'\d+').firstMatch(raw)?.group(0);
    if (digits != null) return int.tryParse(digits);
    return null;
  }

  int _driverId(Map<String, dynamic> d) =>
      _asInt(d['driver_id'] ?? d['id'] ?? d['driverId']) ?? 0;
  int _employeeId(Map<String, dynamic> e) =>
      _asInt(e['employee_id'] ?? e['id'] ?? e['employeeId']) ?? 0;

  List<Map<String, dynamic>> _dedupeRecords(
    List<Map<String, dynamic>> items, {
    required int Function(Map<String, dynamic>) idOf,
    required String Function(Map<String, dynamic>) labelOf,
  }) {
    final byKey = <String, Map<String, dynamic>>{};
    for (final item in items) {
      final id = idOf(item);
      final label = labelOf(item).trim().toLowerCase();
      final key = id > 0 ? 'id:$id' : 'label:$label';
      if (!byKey.containsKey(key)) {
        byKey[key] = item;
      }
    }
    return byKey.values.toList(growable: false);
  }

  List<Map<String, dynamic>> _dedupeDrivers(List<Map<String, dynamic>> items) {
    return _dedupeRecords(
      items,
      idOf: _driverId,
      labelOf: (d) => [
        (d['driver_id_raw'] ?? '').toString(),
        (d['cab_no'] ?? d['vehicle_no'] ?? d['cab_number'] ?? '').toString(),
        _driverName(d),
      ].where((part) => part.trim().isNotEmpty).join('|'),
    );
  }

  List<Map<String, dynamic>> _dedupeEmployees(
      List<Map<String, dynamic>> items) {
    return _dedupeRecords(
      items,
      idOf: _employeeId,
      labelOf: (e) => [
        (e['employee_code'] ?? '').toString(),
        (e['mobile'] ?? '').toString(),
        (e['name'] ?? e['employee_name'] ?? '').toString(),
      ].where((part) => part.trim().isNotEmpty).join('|'),
    );
  }

  String _driverName(Map<String, dynamic> d) =>
      (d['driver_name'] ?? d['name'] ?? 'Unknown').toString();
  String _cabNo(Map<String, dynamic> d) =>
      (d['cab_no'] ?? d['cab_number'] ?? 'N/A').toString();

  int _vehicleSeats(Map<String, dynamic> d) {
    final raw = d['vehicle_type'] ?? d['cab_type'] ?? d['seats'];
    if (raw is int) return raw;
    final s = raw?.toString() ?? '';
    if (s.contains('6')) return 6;
    if (s.contains('4')) return 4;
    return int.tryParse(s) ?? 4;
  }

  bool _driverMatchesVehicleType(Map<String, dynamic> d) {
    final seats = _vehicleSeats(d);
    return _vehicleTypes.contains(seats);
  }

  void _applyLocalFilters() {
    if (!mounted) return;
    final vq = _vehicleSearch.text.trim().toLowerCase();
    final eq = _employeeSearch.text.trim().toLowerCase();

    _safeSetState(() {
      // ===== ENHANCED: Vehicle filtering with priority sorting =====
      _filteredDrivers =
          _drivers.where((d) => _driverMatchesVehicleType(d)).where((d) {
        if (vq.isEmpty) return true;
        final blob =
            "${_driverName(d)} ${_cabNo(d)} ${(d['mobile'] ?? '')} ${(d['status'] ?? '')}"
                .toLowerCase();
        return blob.contains(vq);
      }).toList();

      // Apply priority sorting (6-seater first)
      _filteredDrivers = _sortVehiclesByPriority(_filteredDrivers);

      // ===== ENHANCED: Employee filtering with eligibility check =====
      _filteredEmployees = _getEligibleEmployees().where((e) {
        if (eq.isEmpty) return true;
        final blob =
            "${(e['name'] ?? e['employee_name'] ?? '')} ${(e['employee_code'] ?? e['employee_id'] ?? e['id'] ?? '')} "
                    "${(e['home_address'] ?? e['address'] ?? '')} ${(e['mobile'] ?? '')}"
                .toLowerCase();
        return blob.contains(eq);
      }).toList();
    });
  }

  // ===== NLP Search (optional, keeps your API ability) =====
  void _debouncedVehicleSearch(String v) {
    _vehDebounce?.cancel();
    _vehDebounce = Timer(const Duration(milliseconds: 450), () async {
      final q = v.trim();
      if (q.isEmpty) {
        _applyLocalFilters();
        return;
      }
      _safeSetState(() => _vehNlpSearching = true);
      try {
        // ===== ENHANCED: Include context-aware search with vehicle priority =====
        final res = await AdminService.searchVehiclesNLP(
          searchQuery: q,
          adminId: widget.adminId,
          context: {
            'vehicle_types': _vehicleTypes.toList(),
            'trip_type': _tripType,
            'scheduled_time': _selectedTime,
            'proximity_enabled': true,
          },
        );
        _safeSetState(() {
          _filteredDrivers =
              res.where((d) => _driverMatchesVehicleType(d)).toList();
          // Apply priority sorting
          _filteredDrivers = _sortVehiclesByPriority(_filteredDrivers);
        });
      } catch (e) {
        debugPrint("searchVehiclesNLP error: $e");
        _applyLocalFilters();
      } finally {
        _safeSetState(() => _vehNlpSearching = false);
      }
    });
  }

  void _debouncedEmployeeSearch(String v) {
    _empDebounce?.cancel();
    _empDebounce = Timer(const Duration(milliseconds: 450), () async {
      final q = v.trim();
      if (q.isEmpty) {
        _applyLocalFilters();
        return;
      }
      _safeSetState(() => _empNlpSearching = true);
      try {
        // ===== ENHANCED: Include no-trip requests and leave status in search context =====
        final res = await AdminService.searchEmployeesNLP(
          searchQuery: q,
          adminId: widget.adminId,
          tripType: _tripType,
          selectedTime: _selectedTime,
          context: {
            'exclude_no_trip_users': true,
            'exclude_on_leave': true,
            'vehicle_types': _vehicleTypes.toList(),
          },
        );
        _safeSetState(() => _filteredEmployees = res);
      } catch (e) {
        debugPrint("searchEmployeesNLP error: $e");
        _applyLocalFilters();
      } finally {
        _safeSetState(() => _empNlpSearching = false);
      }
    });
  }

  // ===== Top Buttons =====
  void _clearAll() {
    setState(() {
      _selectedVehicleIds.clear();
      _selectedEmployeeIds.clear();
      _vehicleSearch.clear();
      _employeeSearch.clear();
      _groups = [];
      _assigningGroupKeys.clear();
      _selectedDriversByGroupIndex.clear();
      _availableDriversForGroup.clear();
    });
    _applyLocalFilters();
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text("Cleared.")));
  }

  // ===== Core Flow Buttons =====
  Future<void> _createGroups() async {
    if (_selectedTime == null || _selectedTime!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Please select time slot")));
      return;
    }
    if (_vehicleTypes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Please select vehicle type")));
      return;
    }
    if (_selectedVehicleIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Select at least 1 vehicle/driver")));
      return;
    }
    if (_selectedEmployeeIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Select at least 1 employee")));
      return;
    }

    setState(() => _creatingGroups = true);
    try {
      // ===== ENHANCED: Include Go Home request priority list in group creation =====
      // Note: goHomeDriverIds, proximitySorting, and officeLocation are handled backend-side
      // Pass selected Go Home drivers in the selectedDriverIds if approved
      final res = await AdminService.createGroups(
        adminId: widget.adminId,
        tripType: _tripType,
        selectedTime: _selectedTime ?? '',
        vehicleTypes: _vehicleTypes.toList(),
        selectedDriverIds: _selectedDriverIdsForApi(),
        selectedEmployeeIds: _selectedEmployeeIds.toList(),
        vehiclePriorityEnabled: _vehicleTypes.length > 1, // 6-seater first
        batchSize: _selectedVehicleIds.length >= 200 ? 150 : null,
        tripDay: _currentTripDay(),
      );

      if ((res['success'] == true) && res['data'] != null) {
        final data = (res['data'] as Map).cast<String, dynamic>();
        List<dynamic> latestGroups = (data['groups'] as List?) ?? [];
        try {
          final tripDay = _currentTripDay();
          final fetched = await AdminService.getGroups(
            adminId: widget.adminId,
            tripType: _tripType,
            selectedTime: _selectedTime,
            tripDay: tripDay,
          );
          if (fetched.isNotEmpty) {
            latestGroups = fetched;
          }
        } catch (_) {
          // Keep local response groups if backend refresh fails.
        }

        setState(() {
          _groups = latestGroups;
          if (data['trip_metadata'] != null) {
            _tripHistory[DateTime.now().millisecondsSinceEpoch] =
                data['trip_metadata'];
          }
        });
        final unassigned = (data['unassigned_employees'] ??
            data['unassignedEmployees']) as List?;
        final unassignedCount = unassigned?.length ?? 0;
        final unassignedVehicles =
            (data['unassigned_vehicles'] as List?) ?? const [];
        final unassignedVehicleCount = unassignedVehicles.length;
        final hybridProvider = (data['hybrid_provider'] ??
                data['trip_metadata']?['hybrid_provider'] ??
                '')
            .toString()
            .trim();
        final vehicleBatches = int.tryParse((data['vehicle_batches'] ??
                    data['trip_metadata']?['vehicle_batches'] ??
                    1)
                .toString()) ??
            1;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              unassignedCount > 0 || unassignedVehicleCount > 0
                  ? "Groups: ${_groups.length}. Unassigned employees: $unassignedCount, vehicles: $unassignedVehicleCount${vehicleBatches > 1 ? ', batches: $vehicleBatches' : ''}."
                  : "Groups created: ${_groups.length}${hybridProvider.isNotEmpty ? ' ($hybridProvider hybrid)' : ''}${vehicleBatches > 1 ? ', batches: $vehicleBatches' : ''}.",
            ),
          ),
        );
      } else {
        final msg = (res['message'] ?? 'Failed to create groups').toString();
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(msg)));
      }
    } catch (e) {
      debugPrint("createGroups error: $e");
      final raw = e.toString().toLowerCase();
      if (raw.contains('hybrid route provider') || raw.contains('(503)')) {
        String detail = '';
        try {
          final h = await AdminService.getHybridHealth();
          final provider = (h['provider'] ?? '').toString();
          final err = (h['error'] ?? '').toString();
          if (provider.isNotEmpty || err.isNotEmpty) {
            detail = ' Provider: $provider${err.isNotEmpty ? ' | $err' : ''}';
          }
        } catch (_) {}
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              "Hybrid route provider unavailable. Check backend /api/health/hybrid.$detail",
            ),
          ),
        );
      } else {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text("Error creating groups: $e")));
      }
    } finally {
      if (mounted) setState(() => _creatingGroups = false);
    }
  }

  Future<void> _refreshGroupsFromBackend() async {
    try {
      final tripDay = _currentTripDay();
      final gs = await AdminService.getGroups(
        adminId: widget.adminId,
        tripType: _tripType,
        selectedTime: _selectedTime,
        tripDay: tripDay,
      );
      // Always trust backend snapshot so View & Modify updates immediately.
      setState(() => _groups = gs);
    } catch (e) {
      debugPrint("getGroups error: $e");
    }
  }

  Future<void> _openViewModifyGroups() async {
    await _refreshGroupsFromBackend();
    if (!mounted) return;
    if (_groups.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No groups found. Create groups first.')),
      );
      return;
    }

    final orderedSelectedDrivers = _orderedSelectedDriverIds();
    for (var i = 0; i < _groups.length; i++) {
      final g = (_groups[i] as Map).cast<String, dynamic>();
      final preset = _driverLocalIdFromRaw(
        g['assigned_driver_id'] ??
            g['driver_id'] ??
            g['suggested_vehicle']?['driver_id'],
      );
      if (preset != null && preset > 0) {
        _selectedDriversByGroupIndex[i] = preset;
      } else if (i < orderedSelectedDrivers.length) {
        _selectedDriversByGroupIndex[i] = orderedSelectedDrivers[i];
      }
    }
    final missingMappings = List.generate(
      _groups.length,
      (i) => _resolveDriverForGroup(
          i, (_groups[i] as Map).cast<String, dynamic>()),
    ).where((id) => id == null).length;
    if (missingMappings > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(
                "$missingMappings group(s) have no mapped driver. Select more vehicles in previous step.")),
      );
    }

    showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        int? selectedIdx = _groups.isNotEmpty ? 0 : null;
        dynamic selectedGroup = _groups.isNotEmpty ? _groups.first : null;

        return StatefulBuilder(builder: (ctx2, setS) {
          return Dialog(
            backgroundColor: AppThemeColors.surface,
            insetPadding: const EdgeInsets.all(14),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            child: SizedBox(
              width: 980,
              height: 560,
              child: Column(
                children: [
                  _modalHeader(
                    title: "View & Modify Groups",
                    subtitle:
                        "Step 7: Add/Remove • Swap • Change vehicle • Delete • Refresh",
                    onClose: () => Navigator.pop(ctx2),
                  ),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        children: [
                          // Left: Group list
                          Expanded(
                            flex: 6,
                            child: _panelCard(
                              title: "Created Groups",
                              child: ListView.builder(
                                itemCount: _groups.length,
                                itemBuilder: (_, i) {
                                  final g = _groups[i] as Map<String, dynamic>;
                                  final gid =
                                      _asInt(g['id'] ?? g['group_index']) ?? i;
                                  final members = (g['members'] as List?) ??
                                      (g['employees'] as List?) ??
                                      [];
                                  final type = _asInt(g['assigned_cab_type'] ??
                                          g['vehicle_type'] ??
                                          4) ??
                                      4;

                                  final isSel = selectedIdx == i;
                                  return InkWell(
                                    onTap: () {
                                      setS(() {
                                        selectedIdx = i;
                                        selectedGroup = g;
                                      });
                                    },
                                    child: Container(
                                      margin: const EdgeInsets.only(bottom: 10),
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: isSel
                                            ? AppThemeColors.primary
                                                .withValues(alpha: 0.12)
                                            : AppThemeColors.cardGlass,
                                        borderRadius: BorderRadius.circular(14),
                                        border: Border.all(
                                            color: AppThemeColors.border),
                                      ),
                                      child: Row(
                                        children: [
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Text("Group ${i + 1}",
                                                    style: AppTypography
                                                        .bodyLarge
                                                        .copyWith(
                                                            fontWeight:
                                                                FontWeight
                                                                    .w900)),
                                                const SizedBox(height: 4),
                                                Text(
                                                  "Vehicle: $type-Seater • Members: ${members.length} • ID: $gid",
                                                  style: AppTypography
                                                      .bodyMedium
                                                      .copyWith(
                                                          color: AppThemeColors
                                                              .textTertiary,
                                                          fontSize: 12),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                          ),
                          const SizedBox(width: 14),

                          // Right: Selected group editor
                          Expanded(
                            flex: 8,
                            child: _panelCard(
                              title: "Modify Selected Group",
                              child: selectedGroup == null
                                  ? Center(
                                      child: Text(
                                        "Select a group to modify",
                                        style: AppTypography.bodyMedium
                                            .copyWith(
                                                color: AppThemeColors
                                                    .textSecondary),
                                      ),
                                    )
                                  : _groupEditor(
                                      group: (selectedGroup
                                          as Map<String, dynamic>),
                                      groupIndex: selectedIdx ?? 0,
                                      refresh: () async {
                                        await _refreshGroupsFromBackend();
                                        setS(() {
                                          if (selectedIdx != null &&
                                              selectedIdx! < _groups.length) {
                                            selectedGroup =
                                                _groups[selectedIdx!];
                                          } else {
                                            selectedIdx = null;
                                            selectedGroup = null;
                                          }
                                        });
                                      },
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () async {
                            await _refreshGroupsFromBackend();
                            setS(() {});
                          },
                          child: const Text("Refresh"),
                        ),
                        const SizedBox(width: 10),
                        ElevatedButton(
                          onPressed: () => Navigator.pop(ctx2),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppThemeColors.primary,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12)),
                          ),
                          child: const Text("Done"),
                        ),
                      ],
                    ),
                  )
                ],
              ),
            ),
          );
        });
      },
    );
  }

  Future<void> _openAssignTrip() async {
    await _refreshGroupsFromBackend();
    if (!mounted) return;
    if (_groups.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No groups found. Create groups first.')),
      );
      return;
    }

    showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        return Dialog(
          backgroundColor: AppThemeColors.surface,
          insetPadding: const EdgeInsets.all(14),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          child: SizedBox(
            width: 980,
            height: 620,
            child: Column(
              children: [
                _modalHeader(
                  title: "Assign Trip",
                  subtitle:
                      "Step 8: Assign Trip • Driver auto-assigned • Route No. + OTP • Trip becomes LIVE",
                  onClose: () => Navigator.pop(ctx),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                "${_groups.length} group(s) ready for assignment",
                                style: AppTypography.bodyMedium.copyWith(
                                  color: AppThemeColors.textSecondary,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            ElevatedButton.icon(
                              onPressed: _assigningAllGroups
                                  ? null
                                  : () => _assignAllGroupTrips(),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppThemeColors.primary,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              icon: Icon(
                                _assigningAllGroups
                                    ? Icons.hourglass_top_rounded
                                    : Icons.done_all_rounded,
                                size: 18,
                              ),
                              label: Text(
                                _assigningAllGroups
                                    ? "Assigning All..."
                                    : "Assign All",
                                style: const TextStyle(
                                    fontWeight: FontWeight.w900),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Expanded(
                          child: ListView.builder(
                            itemCount: _groups.length,
                            itemBuilder: (_, i) {
                              final g = _groups[i] as Map<String, dynamic>;
                              return _assignTripGroupCard(
                                  groupIndex: i, group: g);
                            },
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () {
                          _showTripHistory(ctx);
                        },
                        child: const Text("View Trip History",
                            style: TextStyle(
                                color: AppThemeColors.info,
                                fontWeight: FontWeight.w900)),
                      ),
                      TextButton(
                          onPressed: () => Navigator.pop(ctx),
                          child: const Text("Close")),
                    ],
                  ),
                )
              ],
            ),
          ),
        );
      },
    );
  }

  // ===== ENHANCED: View trip history =====
  void _showTripHistory(BuildContext ctx) {
    showDialog<void>(
      context: ctx,
      builder: (_) => AlertDialog(
        title: const Text("Trip History"),
        content: _tripHistory.isEmpty
            ? const Text("No completed trips yet")
            : SizedBox(
                width: 500,
                height: 400,
                child: ListView.builder(
                  itemCount: _tripHistory.length,
                  itemBuilder: (_, i) {
                    final entry = _tripHistory.entries.toList()[i];
                    final data = entry.value as Map<String, dynamic>;
                    return Card(
                      child: ListTile(
                        title: Text("Route: ${data['route_no'] ?? 'N/A'}"),
                        subtitle: Text(
                          "Type: ${data['trip_type']} • Distance: ${data['final_distance_km']} km\n"
                          "Scheduled: ${data['scheduled_time']} • Employees: ${(data['employees'] as List?)?.length ?? 0}",
                        ),
                        isThreeLine: true,
                        trailing: const Icon(Icons.check_circle,
                            color: AppThemeColors.success),
                      ),
                    );
                  },
                ),
              ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(_), child: const Text("Close")),
        ],
      ),
    );
  }

  // ===== Assign trip per group (uses your existing backend flow) =====
  Future<void> _assignGroupTrip(
      int groupIndex, Map<String, dynamic> group) async {
    final groupKey = _groupIdentity(group, fallbackIndex: groupIndex);
    if (_assigningGroupKeys.contains(groupKey)) {
      return;
    }
    final driverId = _resolveDriverForGroup(groupIndex, group);
    final driverApiId = _resolveDriverApiId(driverId);
    if (_selectedTime == null || _selectedTime!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Please select time slot")));
      return;
    }

    var loadingShown = false;
    try {
      setState(() => _assigningGroupKeys.add(groupKey));
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: RGLoader()),
      );
      loadingShown = true;

      final tripResp = await AdminService.assignGroupTrip(
        groupData: group,
        driverId: driverApiId,
        cabNo: "", // handled by backend v2
        adminId: widget.adminId,
        tripType: _tripType,
        scheduledTime: _selectedTime!,
        vehicleTypes: _vehicleTypes.toList(),
        tripDay: _currentTripDay(),
      );

      if (mounted && loadingShown) {
        Navigator.pop(context); // close loader
        loadingShown = false;
      }

      final routeNo =
          (tripResp["route_no"] ?? tripResp["routeNo"] ?? "").toString();
      final startOtp =
          (tripResp["start_otp"] ?? tripResp["startOtp"] ?? "").toString();
      final endOtp =
          (tripResp["end_otp"] ?? tripResp["endOtp"] ?? "").toString();
      final totalKm = tripResp["total_distance_km"];
      final tripId = tripResp["trip_id"];
      final assignedEmployeeIds = _groupMemberIds(group);

      if (mounted) {
        setState(() {
          _groups = _groups.where((item) {
            if (item is! Map) return true;
            return _groupIdentity(
                  item.cast<String, dynamic>(),
                  fallbackIndex: _groups.indexOf(item),
                ) !=
                groupKey;
          }).toList();
          _selectedEmployeeIds.removeAll(assignedEmployeeIds);
        });
      }
      await _loadLists();

      if (!mounted) return;
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text("Trip Created Successfully"),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (routeNo.isNotEmpty) _tripDetailRow("Route No.", routeNo),
              if (startOtp.isNotEmpty) _tripDetailRow("Start OTP", startOtp),
              if (endOtp.isNotEmpty) _tripDetailRow("End OTP", endOtp),
              if (totalKm != null)
                _tripDetailRow("Distance", "${totalKm.toString()} km"),
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 12),
              Text(
                driverId == null
                    ? "Trip Status: Ready to Go (Driver auto-assigned)"
                    : "Trip Status: Ready to Go",
                style: AppTypography.bodyMedium.copyWith(
                  color: AppThemeColors.success,
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                AdminService.copyToClipboard(startOtp);
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                    content: Text("Start OTP copied to clipboard")));
              },
              child: const Text("Copy OTP"),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                  content:
                      Text("Trip assigned. Driver will start from dashboard."),
                ));
              },
              child: const Text("Done",
                  style: TextStyle(
                      color: AppThemeColors.success,
                      fontWeight: FontWeight.w900)),
            ),
            TextButton(
              onPressed: () async {
                Navigator.pop(context);
                final kmText = await showDialog<String?>(
                  context: context,
                  builder: (ctx) {
                    final ctl = TextEditingController();
                    return AlertDialog(
                      title: const Text("Complete Trip - Final Distance"),
                      content: TextField(
                        controller: ctl,
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        decoration: const InputDecoration(
                            hintText: "Total KM traveled"),
                      ),
                      actions: [
                        TextButton(
                            onPressed: () => Navigator.of(ctx).pop(null),
                            child: const Text("Cancel")),
                        TextButton(
                            onPressed: () => Navigator.of(ctx).pop(ctl.text),
                            child: const Text("Complete")),
                      ],
                    );
                  },
                );

                double? finalKm;
                if (kmText != null && kmText.isNotEmpty)
                  finalKm = double.tryParse(kmText);

                try {
                  // ===== ENHANCED: Save full trip history with polyline and metadata =====
                  final r = await AdminService.finishTrip(
                    tripId as int,
                    widget.adminId,
                    totalKm: finalKm,
                    tripMetadata: {
                      'route_no': routeNo,
                      'trip_type': _tripType,
                      'scheduled_time': _selectedTime,
                      'group_index': groupIndex,
                      'driver_id': driverApiId ?? driverId,
                      'employees':
                          group['members'] ?? group['employees'] ?? <dynamic>[],
                      'vehicle_type': (group['assigned_cab_type'] ??
                          group['vehicle_type'] ??
                          4),
                      'final_distance_km': finalKm,
                      'start_otp': startOtp,
                      'end_otp': endOtp,
                      'start_time': DateTime.now().toIso8601String(),
                    },
                  );

                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                    content: Text(
                        (r["message"] ?? "Trip completed successfully")
                            .toString()),
                    backgroundColor:
                        AppThemeColors.success.withValues(alpha: 0.18),
                  ));
                } catch (e) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text("Failed to complete trip: $e")));
                }
              },
              child: const Text("Complete Trip",
                  style: TextStyle(
                      color: AppThemeColors.warning,
                      fontWeight: FontWeight.w900)),
            ),
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text("Close")),
          ],
        ),
      );

      await _refreshGroupsFromBackend();
    } catch (e) {
      if (mounted) {
        if (loadingShown) {
          Navigator.pop(context); // close loader if open
        }
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text("Assign trip error: $e")));
      }
    } finally {
      if (mounted) {
        setState(() => _assigningGroupKeys.remove(groupKey));
      }
    }
  }

  Future<void> _assignAllGroupTrips() async {
    if (_assigningAllGroups || _groups.isEmpty) return;
    if (_selectedTime == null || _selectedTime!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please select time slot")),
      );
      return;
    }

    final payloadGroups = <Map<String, dynamic>>[];
    final originalGroups = _groups
        .whereType<Map<dynamic, dynamic>>()
        .map((g) => g.cast<String, dynamic>())
        .toList(growable: false);

    for (var i = 0; i < originalGroups.length; i++) {
      final group = originalGroups[i];
      final driverId = _resolveDriverForGroup(i, group);
      final driverApiId = _resolveDriverApiId(driverId);
      payloadGroups.add({
        "group_data": group,
        if (driverApiId != null && driverApiId.isNotEmpty)
          "driver_id": driverApiId,
        "cab_no": "",
      });
    }

    var loadingShown = false;
    try {
      setState(() {
        _assigningAllGroups = true;
        for (var i = 0; i < originalGroups.length; i++) {
          _assigningGroupKeys
              .add(_groupIdentity(originalGroups[i], fallbackIndex: i));
        }
      });

      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: RGLoader()),
      );
      loadingShown = true;

      final tripResp = await AdminService.assignMultipleGroupTrips(
        groupsToCreate: payloadGroups,
        adminId: widget.adminId,
        tripType: _tripType,
        scheduledTime: _selectedTime!,
        vehicleTypes: _vehicleTypes.toList(),
        tripDay: _currentTripDay(),
      );

      if (mounted && loadingShown) {
        Navigator.pop(context);
        loadingShown = false;
      }

      final createdTrips = (tripResp["trips_created"] is List)
          ? (tripResp["trips_created"] as List)
              .whereType<Map<dynamic, dynamic>>()
              .map((t) => t.cast<String, dynamic>())
              .toList()
          : const <Map<String, dynamic>>[];

      final assignedEmployeeIds = <int>{};
      for (final group in originalGroups) {
        assignedEmployeeIds.addAll(_groupMemberIds(group));
      }

      if (mounted) {
        setState(() {
          _groups = [];
          _selectedEmployeeIds.removeAll(assignedEmployeeIds);
        });
      }
      await _loadLists();
      await _refreshGroupsFromBackend();

      if (!mounted) return;
      final firstTrip = createdTrips.isNotEmpty ? createdTrips.first : null;
      final routeNos = createdTrips
          .map((trip) => (trip["route_no"] ?? trip["routeNo"] ?? "").toString())
          .where((route) => route.isNotEmpty)
          .toList();
      final startOtps = createdTrips
          .map((trip) =>
              (trip["start_otp"] ?? trip["startOtp"] ?? "").toString())
          .where((otp) => otp.isNotEmpty)
          .toList();

      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text("All Trips Assigned"),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _tripDetailRow("Trips", "${createdTrips.length}"),
              _tripDetailRow("Groups", "${originalGroups.length}"),
              if (routeNos.isNotEmpty)
                _tripDetailRow("First Route", routeNos.first),
              if (startOtps.isNotEmpty)
                _tripDetailRow("First OTP", startOtps.first),
              const SizedBox(height: 10),
              Text(
                createdTrips.length == originalGroups.length
                    ? "All groups were assigned in one action."
                    : "Assigned ${createdTrips.length} trip(s) for ${originalGroups.length} group(s).",
                style: AppTypography.bodyMedium.copyWith(
                  color: AppThemeColors.success,
                  fontWeight: FontWeight.w800,
                ),
              ),
              if (firstTrip != null &&
                  firstTrip["summary"] != null &&
                  firstTrip["summary"].toString().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  firstTrip["summary"].toString(),
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
          actions: [
            if (startOtps.isNotEmpty)
              TextButton(
                onPressed: () {
                  AdminService.copyToClipboard(startOtps.first);
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("First Start OTP copied")),
                  );
                },
                child: const Text("Copy First OTP"),
              ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      "Assigned ${createdTrips.length} trip(s) successfully.",
                    ),
                  ),
                );
              },
              child: const Text(
                "Done",
                style: TextStyle(
                  color: AppThemeColors.success,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ],
        ),
      );
    } catch (e) {
      if (mounted) {
        if (loadingShown) {
          Navigator.pop(context);
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Assign all trips error: $e")),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _assigningAllGroups = false;
          _assigningGroupKeys.clear();
        });
      }
    }
  }

  int _groupIdentity(
    Map<String, dynamic> group, {
    required int fallbackIndex,
  }) {
    return _asInt(group['id'] ?? group['group_index']) ?? -(fallbackIndex + 1);
  }

  Set<int> _groupMemberIds(Map<String, dynamic> group) {
    final members = (group['members'] as List?) ??
        (group['employees'] as List?) ??
        const [];
    return members
        .whereType<Map<dynamic, dynamic>>()
        .map((member) => _asInt(member['id'] ?? member['employee_id']) ?? 0)
        .where((id) => id > 0)
        .toSet();
  }

  // ===== ENHANCED: Trip detail row helper =====
  Widget _tripDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
              width: 100,
              child: Text(label,
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textSecondary))),
          Expanded(
            child: Text(
              value,
              style: AppTypography.bodyMedium.copyWith(
                fontWeight: FontWeight.w800,
                fontFamily: 'monospace',
                color: AppThemeColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ===== UI =====
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      body: SafeArea(
        child: _loading
            ? const Center(child: RGLoader())
            : Column(
                children: [
                  _topHeader(),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
                      child: Column(
                        children: [
                          _overviewStrip(),
                          const SizedBox(height: 12),
                          _card(
                            title: "Group Creation Form",
                            badge: "Planner",
                            child: Column(
                              children: [
                                _sectionTripType(),
                                const SizedBox(height: 12),
                                _sectionTimeSlot(),
                                const SizedBox(height: 12),
                                _sectionVehicleType(),
                                const SizedBox(height: 12),
                                _sectionVehicles(),
                                const SizedBox(height: 12),
                                _sectionEmployees(),
                                const SizedBox(height: 12),
                                _sectionGroupActions(),
                              ],
                            ),
                          ),
                          const SizedBox(height: 14),
                          if (_creatingGroups)
                            const Padding(
                                padding: EdgeInsets.all(18), child: RGLoader()),
                          if (!_creatingGroups && _groups.isNotEmpty) ...[
                            _card(
                              title: "Created Groups (Preview)",
                              badge: "Step 6",
                              child: Column(
                                children: [
                                  Align(
                                    alignment: Alignment.centerLeft,
                                    child: Text(
                                      "View groups for this time slot/day. Use View & Modify Groups to edit members or change vehicle.",
                                      style: AppTypography.bodyMedium.copyWith(
                                          color: AppThemeColors.textTertiary,
                                          fontSize: 12),
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  ListView.builder(
                                    shrinkWrap: true,
                                    physics:
                                        const NeverScrollableScrollPhysics(),
                                    itemCount: _groups.length,
                                    itemBuilder: (_, i) =>
                                        _compactGroupPreviewCard(i,
                                            _groups[i] as Map<String, dynamic>),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          const SizedBox(height: 16),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _overviewStrip() {
    return Row(
      children: [
        Expanded(
          child: _overviewTile(
            label: "Vehicles",
            value: "${_visibleVehicleDrivers().length}",
            icon: Icons.local_taxi_outlined,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _overviewTile(
            label: "Employees",
            value: "${_filteredEmployees.length}",
            icon: Icons.people_alt_outlined,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _overviewTile(
            label: "Groups",
            value: "${_groups.length}",
            icon: Icons.groups_2_outlined,
          ),
        ),
      ],
    );
  }

  Widget _overviewTile({
    required String label,
    required String value,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppThemeColors.textSecondary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: AppTypography.titleSmall.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  label,
                  style: AppTypography.labelSmall.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _topHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      decoration: BoxDecoration(
        gradient: AppGradients.cardGradient,
        border: Border(bottom: BorderSide(color: AppThemeColors.border)),
        boxShadow: [
          BoxShadow(
            color: AppThemeColors.background.withValues(alpha: 0.55),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          InkWell(
            onTap: () => Navigator.pop(context),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppThemeColors.cardGlass,
                shape: BoxShape.circle,
                border: Border.all(color: AppThemeColors.border),
              ),
              child: const Icon(Icons.arrow_back_ios_new,
                  color: AppThemeColors.textPrimary, size: 18),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Group Creation & Trip Assignment",
                  style: AppTypography.titleMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Build groups, review members, and assign trips",
                  style: AppTypography.bodySmall
                      .copyWith(color: AppThemeColors.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _card(
      {required String title, required String badge, required Widget child}) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppThemeColors.border),
        boxShadow: [
          BoxShadow(
            color: AppThemeColors.background.withValues(alpha: 0.55),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 12),
            decoration: BoxDecoration(
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(20)),
              border: Border(bottom: BorderSide(color: AppThemeColors.border)),
              gradient: LinearGradient(
                colors: [
                  AppThemeColors.primary.withValues(alpha: 0.14),
                  AppThemeColors.cardGlass,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: AppTypography.titleMedium.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppThemeColors.primary.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                        color: AppThemeColors.primary.withValues(alpha: 0.34)),
                  ),
                  child: Text(
                    badge,
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.primary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(padding: const EdgeInsets.all(16), child: child),
        ],
      ),
    );
  }

  Widget _sectionShell(
      {required String title,
      required String tag,
      Color? tagColor,
      required Widget child}) {
    final tc = tagColor ?? AppThemeColors.textSecondary;
    final hasTag = tag.trim().isNotEmpty;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
      decoration: BoxDecoration(
        color: AppThemeColors.surfaceLight.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                  child: Text(title,
                      style: AppTypography.bodyLarge
                          .copyWith(fontWeight: FontWeight.w900))),
              if (hasTag)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppThemeColors.background.withValues(alpha: 0.35),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: tc.withValues(alpha: 0.35)),
                  ),
                  child: Text(tag,
                      style: AppTypography.bodyMedium.copyWith(
                          color: tc,
                          fontSize: 12,
                          fontWeight: FontWeight.w700)),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Container(height: 1, color: AppThemeColors.border),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }

  Widget _sectionTripType() {
    return _sectionShell(
      title: "Trip Type",
      tag: "Step 1",
      tagColor: AppThemeColors.success,
      child: Row(
        children: [
          Expanded(child: _radioChip("Pickup", value: 'pickup')),
          const SizedBox(width: 10),
          Expanded(child: _radioChip("Drop", value: 'drop')),
        ],
      ),
    );
  }

  Widget _radioChip(String label, {required String value}) {
    final sel = _tripType == value;
    return InkWell(
      onTap: () async {
        setState(() => _tripType = value);
        await _loadTimes();
        await _loadLists();
        _applyLocalFilters();
      },
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: sel
              ? AppThemeColors.primary.withValues(alpha: 0.14)
              : AppThemeColors.background.withValues(alpha: 0.35),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: sel
                ? AppThemeColors.primary.withValues(alpha: 0.35)
                : AppThemeColors.border,
          ),
        ),
        child: Row(
          children: [
            Icon(
              sel ? Icons.radio_button_checked : Icons.radio_button_off,
              color:
                  sel ? AppThemeColors.primary : AppThemeColors.textSecondary,
              size: 18,
            ),
            const SizedBox(width: 10),
            Text(
              label,
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionTimeSlot() {
    return _sectionShell(
      title: "Time Slot",
      tag: "Step 1",
      tagColor: AppThemeColors.success,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  "Trip Day: ${_formatTripDay(_currentTripDay())}",
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ),
              TextButton.icon(
                onPressed: () async => _pickTripDay(),
                icon: const Icon(Icons.calendar_today, size: 14),
                label: const Text("Change Day"),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (_loadingTimes)
            const Padding(
                padding: EdgeInsets.symmetric(vertical: 10), child: RGLoader()),
          if (!_loadingTimes && _times.isNotEmpty)
            DropdownButtonFormField<String>(
              // Warning fix: keep controlled dropdown behavior; `initialValue` would not track later state changes safely here.
              // ignore: deprecated_member_use
              value: _selectedTime,
              items: _times
                  .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                  .toList(),
              onChanged: (v) async {
                setState(() => _selectedTime = v);
                await _loadLists();
                _applyLocalFilters();
              },
              decoration: InputDecoration(
                labelText: "Select Time",
                filled: true,
                fillColor: AppThemeColors.background.withValues(alpha: 0.35),
                border:
                    OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          if (!_loadingTimes && _times.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Text(
                _tripType == 'pickup'
                    ? "No time slots. Add employees with login time (HH:MM) for Pickup."
                    : "No time slots. Add employees with logout time (HH:MM) for Drop.",
                style: AppTypography.bodyMedium.copyWith(
                  color: AppThemeColors.textSecondary,
                  fontSize: 13,
                ),
              ),
            ),
          const SizedBox(height: 8),
          Text(
            _times.isEmpty
                ? "Slots come from employees' login (pickup) or logout (drop) time."
                : "Only one time can be selected.",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "Eligibility is calculated for selected day + time slot.",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textTertiary,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionVehicleType() {
    return _sectionShell(
      title: "Vehicle Type",
      tag: "Step 2",
      tagColor: AppThemeColors.success,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: _checkChip("6-Seater", seats: 6)),
              const SizedBox(width: 10),
              Expanded(child: _checkChip("4-Seater", seats: 4)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            "Select at least one. When both are selected, 6-seater gets priority.",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _checkChip(String label, {required int seats}) {
    final sel = _vehicleTypes.contains(seats);
    return InkWell(
      onTap: () async {
        setState(() {
          if (sel) {
            if (_vehicleTypes.length > 1)
              _vehicleTypes.remove(seats); // keep at least one
          } else {
            _vehicleTypes.add(seats);
          }
        });
        await _loadLists();
        _applyLocalFilters();
      },
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: sel
              ? AppThemeColors.primary.withValues(alpha: 0.14)
              : AppThemeColors.background.withValues(alpha: 0.35),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: sel
                ? AppThemeColors.primary.withValues(alpha: 0.35)
                : AppThemeColors.border,
          ),
        ),
        child: Row(
          children: [
            Icon(
              sel ? Icons.check_box : Icons.check_box_outline_blank,
              color:
                  sel ? AppThemeColors.primary : AppThemeColors.textSecondary,
              size: 18,
            ),
            const SizedBox(width: 10),
            Text(
              label,
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionVehicles() {
    final visibleVehicles = _visibleVehicleDrivers();
    final visibleVehicleIds =
        visibleVehicles.map(_driverId).where((id) => id > 0).toSet();
    final allVisibleVehiclesSelected = visibleVehicleIds.isNotEmpty &&
        _selectedVehicleIds.containsAll(visibleVehicleIds);
    return _sectionShell(
      title: "Vehicles & Drivers",
      tag: "Step 3",
      child: Column(
        children: [
          // ===== ENHANCED: NLP Search Bar with context =====
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppThemeColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Vehicle Search (NLP)",
                  style: AppTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppThemeColors.primary),
                ),
                const SizedBox(height: 8),
                Text(
                  "Search using natural language: '4 seater', 'driver name', 'vehicle number', etc.",
                  style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textSecondary, fontSize: 11),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: RGSearchField(
                        hint: "Search vehicle / driver / number...",
                        controller: _vehicleSearch,
                        onChanged: (v) {
                          _debouncedVehicleSearch(v);
                          _applyLocalFilters();
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    _smallBtn(
                        allVisibleVehiclesSelected
                            ? "Unselect All"
                            : "Select All", onTap: () {
                      setState(() {
                        for (final id in visibleVehicleIds) {
                          if (allVisibleVehiclesSelected) {
                            _selectedVehicleIds.remove(id);
                          } else {
                            _selectedVehicleIds.add(id);
                          }
                        }
                      });
                    }),
                  ],
                ),
                if (_vehNlpSearching)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      children: [
                        const SizedBox(
                            width: 4,
                            height: 4,
                            child: CircularProgressIndicator(strokeWidth: 2)),
                        const SizedBox(width: 8),
                        Text("Searching with NLP...",
                            style: AppTypography.bodyMedium.copyWith(
                                color: AppThemeColors.textSecondary,
                                fontSize: 11)),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // ===== ENHANCED: Go home requests section with better UI =====
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppThemeColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text("Go Home Request List",
                        style: TextStyle(
                            fontWeight: FontWeight.w900, fontSize: 13)),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppThemeColors.warning.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                            color:
                                AppThemeColors.warning.withValues(alpha: 0.30)),
                      ),
                      child: Text(
                        "Pending: ${_pendingGoHomeRequests.length} | Approved: ${_approvedGoHomeRequests.length}",
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppThemeColors.warning,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  "Review driver go-home requests, approve/reject, then find nearest trip for assignment",
                  style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textSecondary, fontSize: 10),
                ),
                const SizedBox(height: 10),
                _goHomeRequests.isEmpty
                    ? Text(
                        "No Go Home requests from drivers.",
                        style: AppTypography.bodyMedium
                            .copyWith(color: AppThemeColors.textSecondary),
                      )
                    : _tableGoHome(),
              ],
            ),
          ),

          const SizedBox(height: 14),

          // ===== ENHANCED: Available Drivers section =====
          Align(
              alignment: Alignment.centerLeft,
              child: Text("Available Drivers & Vehicles",
                  style: AppTypography.bodyLarge
                      .copyWith(fontWeight: FontWeight.w900))),
          const SizedBox(height: 8),
          _tableVehicles(),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Text(
                  "${_selectedVehicleIds.length} vehicle(s) selected • ${visibleVehicles.length} available",
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textSecondary),
                ),
              ),
              if (visibleVehicles.isEmpty)
                Tooltip(
                  message:
                      "No more vehicles/drivers available for selected criteria",
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppThemeColors.warning.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text("Limited Options",
                        style: TextStyle(
                            color: AppThemeColors.warning, fontSize: 11)),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _sectionEmployees() {
    final visibleEmployeeIds =
        _filteredEmployees.map(_employeeId).where((id) => id > 0).toSet();
    final allVisibleEmployeesSelected = visibleEmployeeIds.isNotEmpty &&
        _selectedEmployeeIds.containsAll(visibleEmployeeIds);
    final noEligibleForSlot =
        (_selectedTime != null && _selectedTime!.isNotEmpty) &&
            _slotEmployeesTotal > 0 &&
            _slotAvailableEmployees == 0;
    final selectedDayIsToday = _currentTripDay() == _todayKey();
    return _sectionShell(
      title: "Employees",
      tag: "Step 4",
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Eligible for selected time slot. Excludes: already in trip, approved no-trip.",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
              fontSize: 12,
            ),
          ),
          if (noEligibleForSlot) ...[
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: AppThemeColors.warning.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: AppThemeColors.warning.withValues(alpha: 0.35),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline,
                      size: 16, color: AppThemeColors.warning),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      selectedDayIsToday
                          ? "No employees are currently eligible for today at $_selectedTime. This slot may already be assigned. Use 'Change Day' to plan for another date."
                          : "No employees are currently eligible for ${_formatTripDay(_currentTripDay())} at $_selectedTime.",
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.warning,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: RGSearchField(
                  hint: "Search employee / id / address...",
                  controller: _employeeSearch,
                  onChanged: (v) {
                    _debouncedEmployeeSearch(v);
                    _applyLocalFilters();
                  },
                ),
              ),
              const SizedBox(width: 10),
              _smallBtn(
                  allVisibleEmployeesSelected ? "Unselect All" : "Select All",
                  onTap: () {
                setState(() {
                  for (final id in visibleEmployeeIds) {
                    if (allVisibleEmployeesSelected) {
                      _selectedEmployeeIds.remove(id);
                    } else {
                      _selectedEmployeeIds.add(id);
                    }
                  }
                });
              }),
            ],
          ),
          const SizedBox(height: 10),
          if (_empNlpSearching)
            Align(
              alignment: Alignment.centerLeft,
              child: Text("Searching...",
                  style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textSecondary, fontSize: 12)),
            ),
          // ===== ENHANCED: Show statistics =====
          if (!_empNlpSearching)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  _statBadge(
                      "Total Eligible: ${_getEligibleEmployees().length}"),
                  const SizedBox(width: 8),
                  _statBadge("Filtered: ${_filteredEmployees.length}"),
                  const SizedBox(width: 8),
                  _statBadge("Selected: ${_selectedEmployeeIds.length}",
                      color: AppThemeColors.success),
                ],
              ),
            ),
          _tableEmployees(),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              "${_selectedEmployeeIds.length} selected • Excluded: ${_noTripRequests.length} (no-trip) + ${_employees.length - _getEligibleEmployees().length} (leave/assigned)",
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textSecondary, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  // ===== ENHANCED: Statistics badge =====
  Widget _statBadge(String text, {Color? color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: (color ?? AppThemeColors.primary).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
            color: (color ?? AppThemeColors.primary).withValues(alpha: 0.25)),
      ),
      child: Text(
        text,
        style: AppTypography.bodyMedium.copyWith(
          color: color ?? AppThemeColors.primary,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _sectionGroupActions() {
    return _sectionShell(
      title: "Group Actions",
      tag: "Step 5",
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Create nearest-employee groups by capacity. Go-home drivers get priority; 6-seater first when both types selected.",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "Step 7: Use View & Modify Groups to add/remove employees, swap members, change vehicle, or delete a group (before assign).",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              SizedBox(
                width: 180,
                child: _actionBtn("Clear", onTap: _clearAll),
              ),
              SizedBox(
                width: 220,
                child: _actionBtn("Create Group",
                    primary: true,
                    onTap: _creatingGroups ? null : _createGroups),
              ),
              SizedBox(
                width: 220,
                child: _actionBtn("View & Modify Groups",
                    onTap: _openViewModifyGroups),
              ),
              SizedBox(
                width: 220,
                child: _actionBtn("Assign Trip",
                    primary: true, onTap: _openAssignTrip),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ===== Tables =====
  List<Map<String, dynamic>> _visibleVehicleDrivers() {
    return _filteredDrivers.where((d) {
      // Do not duplicate drivers already shown in Go Home request list.
      final did = _driverId(d);
      return !_goHomeRequests.any((r) => _asInt(r['driver_id']) == did);
    }).toList();
  }

  Widget _tableHeader({
    required String title,
    required String subtitle,
    String? trailing,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: AppTypography.bodySmall
                      .copyWith(color: AppThemeColors.textSecondary),
                ),
              ],
            ),
          ),
          if (trailing != null) _pill(trailing),
        ],
      ),
    );
  }

  Widget _tableVehicles() {
    final list = _visibleVehicleDrivers();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _tableHeader(
          title: "Vehicle List",
          subtitle: "Select drivers and vehicles for grouping",
          trailing: "${_selectedVehicleIds.length} selected",
        ),
        const SizedBox(height: 10),
        if (list.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 12),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppThemeColors.border),
            ),
            child: Text(
              "No vehicles available for selected filters",
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          )
        else
          _scrollTable(
            DataTable(
              headingRowColor:
                  WidgetStateProperty.all(AppThemeColors.cardGlass),
              dataRowColor: WidgetStateProperty.all(
                  AppThemeColors.background.withValues(alpha: 0.35)),
              headingTextStyle: AppTypography.labelMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
              dataTextStyle: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textPrimary,
              ),
              columns: const [
                DataColumn(label: Text("")),
                DataColumn(label: Text("Driver")),
                DataColumn(label: Text("Mobile")),
                DataColumn(label: Text("Vehicle No.")),
                DataColumn(label: Text("Type")),
                DataColumn(label: Text("Status")),
                DataColumn(label: Text("Home Loc")),
              ],
              rows: list.map((d) {
                final id = _driverId(d);
                final seats = _vehicleSeats(d);
                final sel = _selectedVehicleIds.contains(id);
                final homeLat = _asDouble(d["home_location_lat"] ?? 0);
                final homeLng = _asDouble(d["home_location_lng"] ?? 0);
                final homeHasLocation = homeLat != 0 && homeLng != 0;
                final goHome = d['go_home_request'] == true;

                return DataRow(
                  selected: sel,
                  cells: [
                    DataCell(
                      Checkbox(
                        value: sel,
                        onChanged: id <= 0
                            ? null
                            : (v) => setState(() => v == true
                                ? _selectedVehicleIds.add(id)
                                : _selectedVehicleIds.remove(id)),
                      ),
                    ),
                    DataCell(Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_driverName(d),
                            style: AppTypography.bodyMedium
                                .copyWith(fontWeight: FontWeight.w700)),
                        if (goHome) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppThemeColors.primary
                                  .withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                  color: AppThemeColors.primary
                                      .withValues(alpha: 0.4)),
                            ),
                            child: Text('Go Home',
                                style: AppTypography.labelSmall.copyWith(
                                  color: AppThemeColors.primary,
                                  fontWeight: FontWeight.w700,
                                )),
                          ),
                        ],
                      ],
                    )),
                    DataCell(Text(
                        (d["mobile"] ?? "N/A").toString().substring(
                            0, min(10, (d["mobile"] ?? "").toString().length)),
                        style: const TextStyle(fontFamily: "monospace"))),
                    DataCell(Text(_cabNo(d),
                        style: const TextStyle(
                            fontFamily: "monospace",
                            fontWeight: FontWeight.w700))),
                    DataCell(_pill("$seats-Seater")),
                    DataCell(_statusPill(
                        (d["status"] ?? "available").toString().toLowerCase())),
                    DataCell(
                      homeHasLocation
                          ? Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppThemeColors.success
                                    .withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                    color: AppThemeColors.success
                                        .withValues(alpha: 0.25)),
                              ),
                              child: const Text("Set",
                                  style: TextStyle(
                                      color: AppThemeColors.success,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700)),
                            )
                          : Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppThemeColors.warning
                                    .withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                    color: AppThemeColors.warning
                                        .withValues(alpha: 0.25)),
                              ),
                              child: const Text("Not Set",
                                  style: TextStyle(
                                      color: AppThemeColors.warning,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700)),
                            ),
                    ),
                  ],
                );
              }).toList(),
            ),
          ),
      ],
    );
  }

  Widget _tableGoHome() {
    return _scrollTable(
      DataTable(
        headingRowColor: WidgetStateProperty.all(AppThemeColors.cardGlass),
        dataRowColor: WidgetStateProperty.all(
            AppThemeColors.background.withValues(alpha: 0.35)),
        headingTextStyle: AppTypography.labelMedium.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        dataTextStyle: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
        ),
        columns: const [
          DataColumn(label: Text("")),
          DataColumn(label: Text("Driver")),
          DataColumn(label: Text("Vehicle No.")),
          DataColumn(label: Text("Home Location")),
          DataColumn(label: Text("Status")),
          DataColumn(label: Text("Action")),
        ],
        rows: _goHomeRequests.map((r) {
          final did = _asInt(r['driver_id']) ?? 0;
          final sel = _selectedVehicleIds.contains(did);
          final status = _goHomeRequestStatus[did] ?? 'pending';
          final homeAddr = (r['home_address'] ?? 'Not set').toString();

          return DataRow(
            selected: sel,
            cells: [
              DataCell(Checkbox(
                value: sel,
                onChanged: did <= 0
                    ? null
                    : (v) => setState(() => v == true
                        ? _selectedVehicleIds.add(did)
                        : _selectedVehicleIds.remove(did)),
              )),
              DataCell(Text((r['driver_name'] ?? 'Driver').toString())),
              DataCell(Text(
                  (r['cab_number'] ?? r['cab_no'] ?? 'N/A').toString(),
                  style: const TextStyle(fontFamily: 'monospace'))),
              DataCell(
                Tooltip(
                  message: homeAddr,
                  child: Text(
                    homeAddr.length > 20
                        ? '${homeAddr.substring(0, 17)}...'
                        : homeAddr,
                    style: AppTypography.bodyMedium.copyWith(fontSize: 11),
                  ),
                ),
              ),
              DataCell(_statusPill(status)),
              DataCell(Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (status == 'pending') ...[
                    TextButton(
                      onPressed: () async {
                        await _approveGoHomeRequest(r);
                      },
                      style: TextButton.styleFrom(
                          foregroundColor: AppThemeColors.success,
                          padding: EdgeInsets.zero),
                      child: const Text("Approve",
                          style: TextStyle(
                              fontWeight: FontWeight.w900, fontSize: 11)),
                    ),
                    const SizedBox(width: 4),
                    TextButton(
                      onPressed: () async {
                        await _rejectGoHomeRequest(r);
                      },
                      style: TextButton.styleFrom(
                          foregroundColor: AppThemeColors.error,
                          padding: EdgeInsets.zero),
                      child: const Text("Reject",
                          style: TextStyle(
                              fontWeight: FontWeight.w900, fontSize: 11)),
                    ),
                  ] else if (status == 'approved') ...[
                    TextButton(
                      onPressed: () async {
                        await _findAndAssignNearestTripForDriver(r);
                      },
                      style: TextButton.styleFrom(
                          foregroundColor: AppThemeColors.primary,
                          padding: EdgeInsets.zero),
                      child: const Text("Find & Assign",
                          style: TextStyle(
                              color: AppThemeColors.primary,
                              fontWeight: FontWeight.w900,
                              fontSize: 11)),
                    ),
                    const SizedBox(width: 4),
                    TextButton(
                      onPressed: () async {
                        await _rejectGoHomeRequest(r);
                      },
                      style: TextButton.styleFrom(
                          foregroundColor: AppThemeColors.error,
                          padding: EdgeInsets.zero),
                      child: const Text("Remove",
                          style: TextStyle(
                              fontWeight: FontWeight.w900, fontSize: 11)),
                    ),
                  ] else if (status == 'assigned') ...[
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppThemeColors.success.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text("Assigned",
                          style: TextStyle(
                              color: AppThemeColors.success,
                              fontWeight: FontWeight.w700,
                              fontSize: 11)),
                    ),
                  ] else if (status == 'rejected') ...[
                    const Text("Rejected",
                        style: TextStyle(
                            color: AppThemeColors.error,
                            fontWeight: FontWeight.w700,
                            fontSize: 11)),
                  ],
                ],
              )),
            ],
          );
        }).toList(),
      ),
    );
  }

  // ===== ENHANCED: Status pill with color coding =====
  Widget _statusPill(String status) {
    Color statusColor = AppThemeColors.textSecondary;
    String displayStatus = status;

    switch (status.toLowerCase()) {
      case 'pending':
        statusColor = AppThemeColors.warning;
        displayStatus = 'Pending Review';
        break;
      case 'approved':
        statusColor = AppThemeColors.success;
        displayStatus = 'Approved';
        break;
      case 'rejected':
        statusColor = AppThemeColors.error;
        displayStatus = 'Rejected';
        break;
      case 'assigned':
        statusColor = AppThemeColors.primary;
        displayStatus = 'Auto-Assigned';
        break;
      case 'available':
        statusColor = AppThemeColors.success;
        displayStatus = 'Available';
        break;
      case 'assigned_trip':
        statusColor = AppThemeColors.primary;
        displayStatus = 'On Trip';
        break;
      case 'on_trip':
        statusColor = AppThemeColors.primary;
        displayStatus = 'On Trip';
        break;
      case 'active':
        statusColor = AppThemeColors.success;
        displayStatus = 'Active';
        break;
      case 'inactive':
        statusColor = AppThemeColors.error;
        displayStatus = 'Inactive';
        break;
      default:
        displayStatus = status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: statusColor.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: statusColor.withValues(alpha: 0.35)),
      ),
      child: Text(
        displayStatus,
        style: AppTypography.bodyMedium.copyWith(
            color: statusColor, fontSize: 11, fontWeight: FontWeight.w700),
      ),
    );
  }

  Widget _tableEmployees() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _tableHeader(
          title: "Employee List",
          subtitle: "Choose eligible employees for this trip slot",
          trailing: "${_selectedEmployeeIds.length} selected",
        ),
        const SizedBox(height: 10),
        if (_filteredEmployees.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 12),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppThemeColors.border),
            ),
            child: Text(
              "No eligible employees found for current filters",
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          )
        else
          _scrollTable(
            DataTable(
              headingRowColor:
                  WidgetStateProperty.all(AppThemeColors.cardGlass),
              dataRowColor: WidgetStateProperty.all(
                  AppThemeColors.background.withValues(alpha: 0.35)),
              headingTextStyle: AppTypography.labelMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
              dataTextStyle: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textPrimary,
              ),
              columns: const [
                DataColumn(label: Text("")),
                DataColumn(label: Text("Employee")),
                DataColumn(label: Text("Employee ID")),
                DataColumn(label: Text("Login")),
                DataColumn(label: Text("Logout")),
                DataColumn(label: Text("Status")),
              ],
              rows: _filteredEmployees.map((e) {
                final id = _employeeId(e);
                final sel = _selectedEmployeeIds.contains(id);
                final status = _getEmployeeEligibilityStatus(e);

                return DataRow(
                  selected: sel,
                  cells: [
                    DataCell(Checkbox(
                        value: sel,
                        onChanged: (v) => setState(() => v == true
                            ? _selectedEmployeeIds.add(id)
                            : _selectedEmployeeIds.remove(id)))),
                    DataCell(Text(
                        (e["name"] ?? e["employee_name"] ?? "Employee")
                            .toString())),
                    DataCell(Text(
                        (e["employee_code"] ??
                                e["employee_id"] ??
                                e["id"] ??
                                "E000")
                            .toString(),
                        style: const TextStyle(fontFamily: "monospace"))),
                    DataCell(Text((e["login_time"] ?? "--").toString(),
                        style: const TextStyle(
                            fontFamily: "monospace", fontSize: 11))),
                    DataCell(Text((e["logout_time"] ?? "--").toString(),
                        style: const TextStyle(
                            fontFamily: "monospace", fontSize: 11))),
                    DataCell(_statusPill(status)),
                  ],
                );
              }).toList(),
            ),
          ),
      ],
    );
  }

  String _getEmployeeEligibilityStatus(Map<String, dynamic> e) {
    final noTripIds = _noTripRequests
        .map((r) => _asInt(r['employee_id'] ?? r['id']) ?? 0)
        .toSet();
    final eid = _employeeId(e);

    if (noTripIds.contains(eid)) return 'no-trip-requested';
    if (_selectedEmployeeIds.contains(eid)) return 'selected';

    final status = (e['status'] ?? '').toString().toLowerCase();
    if (status.contains('leave') || status.contains('absent'))
      return 'on-leave';
    if ((e['trip_required'] ?? true) == false) return 'no-trip-required';

    return 'eligible';
  }

  // Warning fix: kept for possible future reuse; currently not referenced by the active flow.
  // ignore: unused_element
  Widget _tableNoTrip() {
    return _scrollTable(
      DataTable(
        headingRowColor: WidgetStateProperty.all(AppThemeColors.cardGlass),
        dataRowColor: WidgetStateProperty.all(
            AppThemeColors.background.withValues(alpha: 0.35)),
        headingTextStyle: AppTypography.labelMedium.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        dataTextStyle: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
        ),
        columns: const [
          DataColumn(label: Text("Employee")),
          DataColumn(label: Text("Employee ID")),
          DataColumn(label: Text("Reason")),
          DataColumn(label: Text("Approved")),
        ],
        rows: _noTripRequests.map((r) {
          final reason =
              (r['reason'] ?? r['remarks'] ?? 'No trip required').toString();
          final approved =
              (r['approved'] ?? r['status'] ?? 'Pending').toString();

          return DataRow(cells: [
            DataCell(Text(
                (r['employee_name'] ?? r['name'] ?? 'Employee').toString())),
            DataCell(Text((r['employee_id'] ?? r['id'] ?? 'E000').toString(),
                style: const TextStyle(fontFamily: 'monospace'))),
            DataCell(
              Tooltip(
                message: reason,
                child: Text(
                  reason.length > 30 ? '${reason.substring(0, 27)}…' : reason,
                  style: AppTypography.bodyMedium.copyWith(fontSize: 12),
                ),
              ),
            ),
            DataCell(_statusPill(approved.toLowerCase().contains('yes') ||
                    approved.toLowerCase().contains('true')
                ? 'approved'
                : 'pending')),
          ]);
        }).toList(),
      ),
    );
  }

  Widget _scrollTable(Widget table) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppThemeColors.background.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: table,
        ),
      ),
    );
  }

  Widget _pill(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Text(
        text,
        style: AppTypography.bodyMedium.copyWith(
          color: AppThemeColors.textSecondary,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _smallBtn(String label,
      {required VoidCallback onTap, bool danger = false}) {
    final c = danger ? AppThemeColors.error : AppThemeColors.primary;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(11),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: c.withValues(alpha: 0.34)),
        ),
        child: Text(
          label,
          style: AppTypography.bodyMedium.copyWith(
            fontWeight: FontWeight.w800,
            color: c,
          ),
        ),
      ),
    );
  }

  Widget _actionBtn(String label, {VoidCallback? onTap, bool primary = false}) {
    final enabled = onTap != null;
    final bg = primary
        ? AppThemeColors.primary.withValues(alpha: 0.20)
        : AppThemeColors.cardGlass;
    final border = primary
        ? AppThemeColors.primary.withValues(alpha: 0.45)
        : AppThemeColors.border;

    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        decoration: BoxDecoration(
          color: enabled ? bg : AppThemeColors.cardGlass,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: enabled ? border : AppThemeColors.border),
          boxShadow: enabled
              ? [
                  BoxShadow(
                    color: (primary
                            ? AppThemeColors.primary
                            : AppThemeColors.background)
                        .withValues(alpha: 0.18),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ]
              : null,
        ),
        child: Center(
          child: Text(
            label,
            style: AppTypography.bodyMedium.copyWith(
              fontWeight: FontWeight.w900,
              color: enabled
                  ? (primary
                      ? AppThemeColors.primary
                      : AppThemeColors.textPrimary)
                  : AppThemeColors.textDisabled,
            ),
          ),
        ),
      ),
    );
  }

  // ===== Modal + Editor =====
  Widget _modalHeader(
      {required String title,
      required String subtitle,
      required VoidCallback onClose}) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppThemeColors.border),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title,
                  style: AppTypography.bodyLarge
                      .copyWith(fontWeight: FontWeight.w900)),
              const SizedBox(height: 4),
              Text(subtitle,
                  style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textTertiary, fontSize: 12)),
            ]),
          ),
          IconButton(
              onPressed: onClose,
              icon: const Icon(Icons.close, color: AppThemeColors.textPrimary)),
        ],
      ),
    );
  }

  Widget _panelCard({required String title, required Widget child}) {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
            child: Row(
              children: [
                Expanded(
                    child: Text(title,
                        style: AppTypography.bodyLarge
                            .copyWith(fontWeight: FontWeight.w900))),
              ],
            ),
          ),
          Expanded(
              child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                  child: child)),
        ],
      ),
    );
  }

  int _groupRefForEdit(Map<String, dynamic> group) {
    final byIndex = _asInt(group['group_index']) ?? 0;
    if (byIndex > 0) return byIndex;
    return _asInt(group['id']) ?? 0;
  }

  Future<bool> _openSwapEmployeeDialog({
    required Map<String, dynamic> currentGroup,
    required int currentEmployeeId,
  }) async {
    final sourceGroupRef = _groupRefForEdit(currentGroup);
    if (sourceGroupRef <= 0) return false;

    final targetGroups = _groups
        .map((e) => (e as Map).cast<String, dynamic>())
        .where((g) =>
            _groupRefForEdit(g) > 0 && _groupRefForEdit(g) != sourceGroupRef)
        .where((g) =>
            ((g['members'] as List?) ?? (g['employees'] as List?) ?? [])
                .isNotEmpty)
        .toList();
    if (targetGroups.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("No other group available for swap")),
      );
      return false;
    }

    int? selectedTargetGroupRef;
    int? selectedTargetEmployeeId;

    final shouldSwap = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx2, setS) {
            Map<String, dynamic>? selectedTargetGroup;
            if (selectedTargetGroupRef != null) {
              for (final g in targetGroups) {
                if (_groupRefForEdit(g) == selectedTargetGroupRef) {
                  selectedTargetGroup = g;
                  break;
                }
              }
            }
            final targetMembers = ((selectedTargetGroup?['members'] as List?) ??
                    (selectedTargetGroup?['employees'] as List?) ??
                    [])
                .map((e) => (e as Map).cast<String, dynamic>())
                .toList();

            return AlertDialog(
              title: const Text("Swap Employee"),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    DropdownButtonFormField<int>(
                      // Warning fix: keep controlled dropdown behavior; `initialValue` would not track dialog state changes safely here.
                      // ignore: deprecated_member_use
                      value: selectedTargetGroupRef,
                      decoration:
                          const InputDecoration(labelText: "Target Group"),
                      items: targetGroups
                          .map(
                            (g) => DropdownMenuItem<int>(
                              value: _groupRefForEdit(g),
                              child: Text(
                                  "Group ${_asInt(g['group_index']) ?? _groupRefForEdit(g)}"),
                            ),
                          )
                          .toList(),
                      onChanged: (v) {
                        setS(() {
                          selectedTargetGroupRef = v;
                          selectedTargetEmployeeId = null;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      // Warning fix: keep controlled dropdown behavior; `initialValue` would not track dialog state changes safely here.
                      // ignore: deprecated_member_use
                      value: selectedTargetEmployeeId,
                      decoration: const InputDecoration(
                          labelText: "Employee to Swap With"),
                      items: targetMembers
                          .map((m) {
                            final eid =
                                _asInt(m['id'] ?? m['employee_id']) ?? 0;
                            return DropdownMenuItem<int>(
                              value: eid,
                              child: Text((m['name'] ??
                                      m['employee_name'] ??
                                      'Employee')
                                  .toString()),
                            );
                          })
                          .where(
                              (item) => item.value != null && item.value! > 0)
                          .toList(),
                      onChanged: (v) =>
                          setS(() => selectedTargetEmployeeId = v),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx2, false),
                  child: const Text("Cancel"),
                ),
                TextButton(
                  onPressed: (selectedTargetGroupRef == null ||
                          selectedTargetEmployeeId == null)
                      ? null
                      : () => Navigator.pop(ctx2, true),
                  child: const Text("Swap"),
                ),
              ],
            );
          },
        );
      },
    );

    if (shouldSwap != true ||
        selectedTargetGroupRef == null ||
        selectedTargetEmployeeId == null) {
      return false;
    }

    return AdminService.swapEmployees(
      groupA: sourceGroupRef,
      employeeA: currentEmployeeId,
      groupB: selectedTargetGroupRef!,
      employeeB: selectedTargetEmployeeId!,
    );
  }

  Widget _groupEditor(
      {required Map<String, dynamic> group,
      required int groupIndex,
      required Future<void> Function() refresh}) {
    final members =
        (group['members'] as List?) ?? (group['employees'] as List?) ?? [];
    final gidRaw = group['id'] ?? group['group_index'];
    final gid = _asInt(gidRaw) ?? 0;
    final capacity =
        _asInt(group['assigned_cab_type'] ?? group['vehicle_type'] ?? 4) ?? 4;
    final groupLabel = _asInt(group['group_index']) ?? (groupIndex + 1);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _miniAction("Add Employee", onTap: () async {
              final picked = await showDialog<int?>(
                context: context,
                builder: (ctx) {
                  List<Map<String, dynamic>> results = [];
                  return AlertDialog(
                    title: const Text("Add Employee"),
                    content: SizedBox(
                      width: 420,
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        RGSearchField(
                          hint: "Search employee...",
                          onChanged: (v) async {
                            final res = await AdminService.searchEmployeesNLP(
                              searchQuery: v,
                              adminId: widget.adminId,
                              tripType: _tripType,
                              selectedTime: _selectedTime,
                            );
                            results = res;
                            (ctx as Element).markNeedsBuild();
                          },
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 220,
                          child: ListView.builder(
                            itemCount: results.length,
                            itemBuilder: (_, i) {
                              final r = results[i];
                              final rid = _asInt(r['id']) ??
                                  _asInt(r['employee_id']) ??
                                  0;
                              return ListTile(
                                title: Text(
                                    (r['name'] ?? r['employee_name'] ?? '')
                                        .toString()),
                                subtitle: Text((r['mobile'] ?? '').toString()),
                                onTap: () => Navigator.pop(ctx, rid),
                              );
                            },
                          ),
                        ),
                      ]),
                    ),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(ctx, null),
                          child: const Text("Cancel"))
                    ],
                  );
                },
              );

              if (picked != null) {
                final ok = await AdminService.addEmployeeToGroup(
                    groupId: gid, employeeId: picked);
                if (!ok) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text("Failed to add employee")));
                }
                await refresh();
              }
            }),
            _miniAction("Change Vehicle", onTap: () async {
              final current = _asInt(group['assigned_cab_type'] ??
                      group['vehicle_type'] ??
                      4) ??
                  4;
              final next = current == 6 ? 4 : 6;
              final resp = await AdminService.changeGroupVehicle(
                groupId: gid,
                vehicleType: next,
                tripType: _tripType,
                selectedTime: _selectedTime ?? '',
                tripDay: _currentTripDay(),
              );
              if (resp['success'] != true) {
                final msg =
                    (resp['message'] ?? "Failed to change vehicle").toString();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(msg)),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Vehicle changed")),
                );
              }
              await refresh();
            }),
            _miniAction("Delete Group", danger: true, onTap: () async {
              if (gid <= 0) {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Invalid group id")));
                return;
              }

              final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text("Delete Group"),
                      content: const Text(
                          "Are you sure you want to delete this group from preview?"),
                      actions: [
                        TextButton(
                            onPressed: () => Navigator.pop(ctx, false),
                            child: const Text("Cancel")),
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, true),
                          child: const Text("Delete",
                              style: TextStyle(color: AppThemeColors.error)),
                        ),
                      ],
                    ),
                  ) ??
                  false;

              if (!confirmed) return;

              final ok = await AdminService.deleteGroup(groupId: gid);
              if (!ok) {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Failed to delete group")));
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Group deleted")));
              }
              await refresh();
            }),
          ],
        ),
        const SizedBox(height: 12),
        Text("Selected Group Details",
            style:
                AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w900)),
        const SizedBox(height: 6),
        Text(
          "Group $groupLabel • ${members.length}/$capacity seats used",
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textSecondary, fontSize: 12),
        ),
        const SizedBox(height: 10),
        Expanded(
          child: _scrollTable(
            DataTable(
              headingRowColor:
                  WidgetStateProperty.all(AppThemeColors.cardGlass),
              dataRowColor: WidgetStateProperty.all(
                  AppThemeColors.background.withValues(alpha: 0.18)),
              columns: const [
                DataColumn(label: Text("Employee")),
                DataColumn(label: Text("Employee ID")),
                DataColumn(label: Text("Swap")),
                DataColumn(label: Text("Remove")),
              ],
              rows: members.map((m) {
                final mm = (m as Map).cast<String, dynamic>();
                final empId = _asInt(mm['id'] ?? mm['employee_id']) ?? 0;
                return DataRow(cells: [
                  DataCell(Text(
                      (mm['name'] ?? mm['employee_name'] ?? 'Employee')
                          .toString())),
                  DataCell(Text(empId.toString(),
                      style: const TextStyle(fontFamily: 'monospace'))),
                  DataCell(
                    TextButton(
                      onPressed: () async {
                        final ok = await _openSwapEmployeeDialog(
                          currentGroup: group,
                          currentEmployeeId: empId,
                        );
                        if (!ok) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                                content: Text("Failed to swap employee")),
                          );
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text("Employee swapped")),
                          );
                        }
                        await refresh();
                      },
                      child: const Text("Swap"),
                    ),
                  ),
                  DataCell(
                    TextButton(
                      onPressed: () async {
                        final ok = await AdminService.removeEmployeeFromGroup(
                            groupId: gid, employeeId: empId);
                        if (!ok)
                          ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                  content: Text("Failed to remove employee")));
                        await refresh();
                      },
                      child: const Text("Remove",
                          style: TextStyle(color: AppThemeColors.error)),
                    ),
                  ),
                ]);
              }).toList(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _miniAction(String label,
      {required VoidCallback onTap, bool danger = false}) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: AppThemeColors.cardGlass,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: (danger ? AppThemeColors.error : AppThemeColors.border)
                  .withValues(alpha: danger ? 0.35 : 1)),
        ),
        child: Text(label,
            style: AppTypography.bodyMedium.copyWith(
                fontWeight: FontWeight.w900,
                color: danger
                    ? AppThemeColors.error
                    : AppThemeColors.textPrimary)),
      ),
    );
  }

  // ===== Assign Trip modal group card =====
  Widget _assignTripGroupCard(
      {required int groupIndex, required Map<String, dynamic> group}) {
    final groupKey = _groupIdentity(group, fallbackIndex: groupIndex);
    final assigning = _assigningGroupKeys.contains(groupKey);
    final members = (group['members'] as List?) ??
        (group['employees'] as List?) ??
        <dynamic>[];
    final vehicleType =
        _asInt(group['assigned_cab_type'] ?? group['vehicle_type'] ?? 4) ?? 4;
    final assignedDriverId = _resolveDriverForGroup(groupIndex, group);
    final assignedDriverLabel = _driverLabel(assignedDriverId);
    final dist = (group['distance_km_estimate'] ?? '?').toString();
    final eta = (group['eta_min_estimate'] ?? '?').toString();

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Expanded(
                  child: Text("Group ${groupIndex + 1}",
                      style: AppTypography.bodyLarge
                          .copyWith(fontWeight: FontWeight.w900))),
              _pill("$vehicleType-Seater"),
              const SizedBox(width: 8),
              Text("$dist km • $eta min",
                  style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.primary,
                      fontWeight: FontWeight.w900,
                      fontSize: 12)),
            ]),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: members.map((m) {
                final mm = (m as Map).cast<String, dynamic>();
                return _pill(
                    (mm['name'] ?? mm['employee_name'] ?? 'Emp').toString());
              }).toList(),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 14),
                    decoration: BoxDecoration(
                      color: AppThemeColors.background.withValues(alpha: 0.24),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppThemeColors.border),
                    ),
                    child: Text(
                      assignedDriverId == null
                          ? "Driver will be auto-assigned on Assign"
                          : "Assigned Driver: $assignedDriverLabel",
                      style: AppTypography.bodyMedium.copyWith(
                        color: assignedDriverId == null
                            ? AppThemeColors.warning
                            : AppThemeColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: assigning
                      ? null
                      : () => _assignGroupTrip(groupIndex, group),
                  style: ElevatedButton.styleFrom(
                      backgroundColor: AppThemeColors.primary,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12))),
                  child: Text(assigning ? "Assigning..." : "Assign",
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  List<int> _orderedSelectedDriverIds() {
    final ordered = <int>[];
    final seen = <int>{};

    for (final d in _sortVehiclesByPriority(_visibleVehicleDrivers())) {
      final id = _driverId(d);
      if (id > 0 && _selectedVehicleIds.contains(id) && seen.add(id)) {
        ordered.add(id);
      }
    }

    for (final d in _sortVehiclesByPriority(_drivers)) {
      final id = _driverId(d);
      if (id > 0 && _selectedVehicleIds.contains(id) && seen.add(id)) {
        ordered.add(id);
      }
    }

    final leftovers = _selectedVehicleIds
        .where((id) => id > 0 && !seen.contains(id))
        .toList()
      ..sort();
    ordered.addAll(leftovers);
    return ordered;
  }

  List<dynamic> _selectedDriverIdsForApi() {
    final selected = _orderedSelectedDriverIds();
    final out = <dynamic>[];
    final seen = <String>{};
    for (final sid in selected) {
      Map<String, dynamic>? match;
      for (final d in _drivers) {
        if (_driverId(d) == sid) {
          match = d;
          break;
        }
      }
      if (match == null) continue;
      final raw = match['driver_id_raw'] ?? match['driver_id'] ?? match['id'];
      if (raw == null) continue;
      final key = raw.toString();
      if (key.isEmpty || !seen.add(key)) continue;
      out.add(raw);
    }
    if (out.isNotEmpty) return out;
    return _selectedVehicleIds.toList();
  }

  int? _resolveDriverForGroup(int groupIndex, Map<String, dynamic> group) {
    final explicit = _driverLocalIdFromRaw(
      group['assigned_driver_id'] ??
          group['driver_id'] ??
          group['suggested_vehicle']?['driver_id'],
    );
    if (explicit != null && explicit > 0) return explicit;

    final mapped = _selectedDriversByGroupIndex[groupIndex];
    if (mapped != null && mapped > 0) return mapped;

    final selected = _orderedSelectedDriverIds();
    if (groupIndex < selected.length) return selected[groupIndex];
    return null;
  }

  int? _driverLocalIdFromRaw(dynamic rawId) {
    if (rawId == null) return null;
    final raw = rawId.toString().trim();
    if (raw.isEmpty) return null;

    for (final d in _drivers) {
      final candidate =
          (d['driver_id_raw'] ?? d['driver_id'] ?? d['id'])?.toString().trim();
      if (candidate != null && candidate.isNotEmpty && candidate == raw) {
        final id = _driverId(d);
        if (id > 0) return id;
      }
    }

    final numeric = int.tryParse(raw);
    if (numeric != null && numeric > 0) return numeric;
    return null;
  }

  String? _resolveDriverApiId(int? resolvedDriverId) {
    if (resolvedDriverId == null || resolvedDriverId <= 0) return null;
    for (final d in _drivers) {
      if (_driverId(d) == resolvedDriverId) {
        final raw = d['driver_id_raw'] ?? d['driver_id'] ?? d['id'];
        if (raw == null) break;
        final value = raw.toString().trim();
        if (value.isNotEmpty) return value;
        break;
      }
    }
    return resolvedDriverId.toString();
  }

  String _driverLabel(int? driverId) {
    if (driverId == null || driverId <= 0) return "N/A";
    for (final d in _drivers) {
      if (_driverId(d) == driverId) {
        return "${_driverName(d)} (${_cabNo(d)})";
      }
    }
    return "Driver #$driverId";
  }

  // Warning fix: retained for potential future reconnect, but currently not used by the active UI.
  // ignore: unused_element
  Future<List<Map<String, dynamic>>> _loadAvailableDriversForGroup(
      int groupIndex, Map<String, dynamic> group) async {
    if (_availableDriversForGroup.containsKey(groupIndex))
      return _availableDriversForGroup[groupIndex]!;
    try {
      final int? vType =
          _asInt(group['assigned_cab_type'] ?? group['vehicle_type']);
      final list = await AdminService.getAvailableDrivers(
        tripType: _tripType,
        scheduledTime: _selectedTime ?? '',
        vehicleType: vType,
        adminId: widget.adminId,
      );
      _availableDriversForGroup[groupIndex] = list;
      return list;
    } catch (e) {
      debugPrint("getAvailableDrivers error: $e");
      return <Map<String, dynamic>>[];
    }
  }

  // ===== Small Preview card (below main form) =====
  Widget _compactGroupPreviewCard(int i, Map<String, dynamic> group) {
    final members = (group['members'] as List?) ??
        (group['employees'] as List?) ??
        <dynamic>[];
    final vehicleType =
        _asInt(group['assigned_cab_type'] ?? group['vehicle_type'] ?? 4) ?? 4;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
                child: Text("Group ${i + 1}",
                    style: AppTypography.bodyLarge
                        .copyWith(fontWeight: FontWeight.w900))),
            _pill("$vehicleType-Seater"),
          ]),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: members.take(8).map((m) {
              final mm = (m as Map).cast<String, dynamic>();
              return _pill(
                  (mm['name'] ?? mm['employee_name'] ?? 'Emp').toString());
            }).toList(),
          ),
          if (members.length > 8)
            Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text("+${members.length - 8} more",
                    style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textTertiary, fontSize: 12))),
        ],
      ),
    );
  }
}
