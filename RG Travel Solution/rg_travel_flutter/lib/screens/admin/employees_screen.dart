import 'dart:async';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geocoding/geocoding.dart';
import 'package:latlong2/latlong.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/services/admin_service.dart';
import 'package:rg_travel_flutter/widgets/common/rg_logo.dart';

// -----------------------------------------------------------------------------
// ENUMS & MODELS
// -----------------------------------------------------------------------------
enum EmployeeSection {
  main,
  requests,
  absences,
  absentEmployees,
  changes, // Profile Change Requests
  add,
  list,
}

// -----------------------------------------------------------------------------
// MAIN SCREEN
// -----------------------------------------------------------------------------
class EmployeesScreen extends StatefulWidget {
  final String adminId;

  const EmployeesScreen({
    super.key,
    required this.adminId,
  });

  @override
  State<EmployeesScreen> createState() => _EmployeesScreenState();
}

class _EmployeesScreenState extends State<EmployeesScreen> {
  // Navigation & State
  EmployeeSection _currentSection = EmployeeSection.main;
  bool _isLoading = false;
  bool _isOnline = false;
  Timer? _healthTimer;

  // Data
  List<Map<String, dynamic>> _requests = []; // New registrations
  List<Map<String, dynamic>> _absenceRequests = [];
  List<Map<String, dynamic>> _approvedAbsences = [];
  List<Map<String, dynamic>> _changeRequests = []; // Profile updates
  List<Map<String, dynamic>> _employees = [];
  List<Map<String, dynamic>> _filteredEmployees = [];

  // Form Controllers
  final _addFormKey = GlobalKey<FormState>();
  final _searchController = TextEditingController();

  // Add/Edit Fields
  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _loginCtrl = TextEditingController();
  final _logoutCtrl = TextEditingController();
  final _addrCtrl = TextEditingController();
  double? _pickedLat;
  double? _pickedLng;
  Timer? _addressDebounce;
  bool _isResolvingAddress = false;
  String? _addressResolveNote;

  @override
  void initState() {
    super.initState();
    _checkHealth();
    _healthTimer =
        Timer.periodic(const Duration(seconds: 30), (_) => _checkHealth());
    _loadAllData(); // Initial load
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    _addressDebounce?.cancel();
    _searchController.dispose();
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _loginCtrl.dispose();
    _logoutCtrl.dispose();
    _addrCtrl.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // DATA OPERATIONS
  // ---------------------------------------------------------------------------

  Future<void> _checkHealth() async {
    // Determine API online status via a simple ping or checking if data loads
    try {
      // If we have data, we assume online. Or use specific health endpoint if available.
      // AdminService doesn't have a direct ping widely exposed, using dummy success for now or simple check.
      // For now, we'll assume online if we can fetch employees.
      _isOnline = true;
      if (mounted) setState(() {});
    } catch (_) {
      if (mounted) setState(() => _isOnline = false);
    }
  }

  Future<void> _loadAllData() async {
    await Future.wait([
      _loadRequests(),
      _loadAbsenceRequests(),
      _loadApprovedAbsences(),
      _loadChangeRequests(),
      _loadEmployees(),
    ]);
  }

  Future<void> _loadRequests() async {
    try {
      final list = await AdminService.getEmployeeRequests();
      if (mounted) setState(() => _requests = list);
    } catch (e) {
      if (kDebugMode) print("Req load err: $e");
    }
  }

  Future<void> _loadChangeRequests() async {
    try {
      final list =
          await AdminService.getEmployeeChangeRequests(status: "pending");
      if (!mounted) return;
      setState(() {
        _changeRequests = list
            .map((e) => _normalizeChangeRequest(e))
            .where((e) => _isPendingStatus(e["status"]))
            .toList();
      });
    } catch (e) {
      if (kDebugMode) print("Change Req load err: $e");
    }
  }

  Future<void> _loadAbsenceRequests() async {
    try {
      final list = await AdminService.getAbsenceRequests();
      if (!mounted) return;
      setState(() {
        _absenceRequests =
            list.map((e) => _normalizeAbsenceRequest(e)).toList();
      });
    } catch (e) {
      if (kDebugMode) print("Absence Req load err: $e");
    }
  }

  Future<void> _loadApprovedAbsences() async {
    try {
      final list = await AdminService.getAbsentEmployees();
      if (!mounted) return;
      setState(() {
        _approvedAbsences =
            list.map((e) => _normalizeApprovedAbsence(e)).toList();
      });
    } catch (e) {
      if (kDebugMode) print("Approved absence load err: $e");
    }
  }

  Future<void> _loadEmployees() async {
    try {
      final list = await AdminService.getEmployees();
      if (mounted) {
        setState(() {
          _employees = list;
          _filterEmployees();
        });
      }
    } catch (e) {
      _snack("Failed to load employees: $e", isError: true);
    }
  }

  void _filterEmployees() {
    final query = _searchController.text.toLowerCase();
    if (query.isEmpty) {
      _filteredEmployees = List.from(_employees);
      return;
    }
    _filteredEmployees = _employees.where((e) {
      final name =
          (e["name"] ?? e["employee_name"] ?? "").toString().toLowerCase();
      final mobile = (e["mobile"] ?? "").toString();
      final code = (e["employee_code"] ?? "").toString().toLowerCase();
      return name.contains(query) ||
          mobile.contains(query) ||
          code.contains(query);
    }).toList();
  }

  // ACTIONS

  Future<void> _approveReq(String reqId) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      await AdminService.approveEmployeeRequest(int.parse(reqId));
      _snack("Request Approved!", isError: false);
      await _loadRequests();
      await _loadEmployees();
    } catch (e) {
      _snack("Approval failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showRejectDialog(String reqId) async {
    final reasonCtrl = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        title: Text("Reject Employee Request",
            style: AppTypography.titleMedium
                .copyWith(color: AppThemeColors.textPrimary)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Please provide a reason for rejection (optional):",
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textSecondary)),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: reasonCtrl,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textPrimary),
              decoration: InputDecoration(
                filled: true,
                fillColor: AppThemeColors.background,
                hintText: "Reason...",
                hintStyle: AppTypography.bodyMedium
                    .copyWith(color: AppThemeColors.textTertiary),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    borderSide: BorderSide.none),
              ),
              maxLines: 3,
            )
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text("Cancel",
                style: AppTypography.labelMedium
                    .copyWith(color: AppThemeColors.textSecondary)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppThemeColors.error.withValues(alpha: 0.2),
              foregroundColor: AppThemeColors.error,
              elevation: 0,
            ),
            onPressed: () {
              Navigator.pop(context);
              _rejectReq(reqId, reason: reasonCtrl.text.trim());
            },
            child: const Text("Reject"),
          )
        ],
      ),
    );
  }

  Future<void> _rejectReq(String reqId, {String? reason}) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      await AdminService.rejectEmployeeRequest(int.parse(reqId),
          reason: reason ?? "");
      _snack("Request Rejected", isError: false);
      await _loadRequests();
    } catch (e) {
      _snack("Rejection failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _approveChangeReq(String reqId) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      await AdminService.approveEmployeeChange(int.parse(reqId));
      _snack("Profile update approved.", isError: false);
      await _loadChangeRequests();
      await _loadEmployees();
    } catch (e) {
      _snack("Approval failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showChangeRejectDialog(String reqId) async {
    final reasonCtrl = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        title: Text(
          "Reject Profile Update",
          style: AppTypography.titleMedium.copyWith(
            color: AppThemeColors.textPrimary,
          ),
        ),
        content: TextField(
          controller: reasonCtrl,
          maxLines: 3,
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textPrimary),
          decoration: InputDecoration(
            hintText: "Reason (optional)",
            hintStyle: AppTypography.bodyMedium
                .copyWith(color: AppThemeColors.textTertiary),
            filled: true,
            fillColor: AppThemeColors.background,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              "Cancel",
              style: AppTypography.labelMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _rejectChangeReq(reqId, reason: reasonCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppThemeColors.error.withValues(alpha: 0.18),
              foregroundColor: AppThemeColors.error,
              elevation: 0,
            ),
            child: const Text("Reject"),
          ),
        ],
      ),
    );
  }

  Future<void> _approveAbsenceReq(String reqId) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      await AdminService.approveAbsenceRequest(int.parse(reqId));
      _snack("Absence request approved.", isError: false);
      await _loadAbsenceRequests();
      await _loadApprovedAbsences();
      await _loadEmployees();
    } catch (e) {
      _snack("Approval failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showAbsenceRejectDialog(String reqId) async {
    final reasonCtrl = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        title: Text(
          "Reject Absence Request",
          style: AppTypography.titleMedium.copyWith(
            color: AppThemeColors.textPrimary,
          ),
        ),
        content: TextField(
          controller: reasonCtrl,
          maxLines: 3,
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textPrimary),
          decoration: InputDecoration(
            hintText: "Reason (optional)",
            hintStyle: AppTypography.bodyMedium
                .copyWith(color: AppThemeColors.textTertiary),
            filled: true,
            fillColor: AppThemeColors.background,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              "Cancel",
              style: AppTypography.labelMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _rejectAbsenceReq(reqId, reason: reasonCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppThemeColors.error.withValues(alpha: 0.18),
              foregroundColor: AppThemeColors.error,
              elevation: 0,
            ),
            child: const Text("Reject"),
          ),
        ],
      ),
    );
  }

  Future<void> _rejectAbsenceReq(String reqId, {String? reason}) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      await AdminService.rejectAbsenceRequest(
        int.parse(reqId),
        reason: reason ?? "",
      );
      _snack("Absence request rejected.", isError: false);
      await _loadAbsenceRequests();
    } catch (e) {
      _snack("Rejection failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showRemoveApprovedAbsenceDialog(
      Map<String, dynamic> req) async {
    final reasonCtrl = TextEditingController();
    final fromDate = (req["from_date"] ?? "").toString();
    final toDate = (req["to_date"] ?? "").toString();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        title: Text(
          "Remove From Absent",
          style: AppTypography.titleMedium.copyWith(
            color: AppThemeColors.textPrimary,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "${req["employee_name"]}\nFrom: ${fromDate.isEmpty ? "-" : fromDate}\nTo: ${toDate.isEmpty ? "-" : toDate}",
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textPrimary),
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: reasonCtrl,
              maxLines: 3,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textPrimary),
              decoration: InputDecoration(
                hintText: "Reason (optional)",
                hintStyle: AppTypography.bodyMedium
                    .copyWith(color: AppThemeColors.textTertiary),
                filled: true,
                fillColor: AppThemeColors.background,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              "Cancel",
              style: AppTypography.labelMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _removeApprovedAbsence(req, reason: reasonCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppThemeColors.warning.withValues(alpha: 0.18),
              foregroundColor: AppThemeColors.warning,
              elevation: 0,
            ),
            child: const Text("Remove"),
          ),
        ],
      ),
    );
  }

  Future<void> _removeApprovedAbsence(Map<String, dynamic> req,
      {String? reason}) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      final employeeId =
          int.tryParse((req["employee_id"] ?? "").toString()) ?? 0;
      final dates = ((req["dates"] as List?) ?? const <dynamic>[])
          .map((e) => e.toString())
          .where((e) => e.isNotEmpty)
          .toList();
      if (employeeId <= 0 || dates.isEmpty) {
        throw Exception("Invalid approved absence range");
      }
      await AdminService.removeAbsentEmployee(
        employeeId,
        dates: dates,
        reason: reason ?? "",
        adminId: widget.adminId,
      );
      _snack("Employee removed from absent list.", isError: false);
      await _loadApprovedAbsences();
      await _loadAbsenceRequests();
      await _loadEmployees();
    } catch (e) {
      _snack("Remove failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _rejectChangeReq(String reqId, {String? reason}) async {
    if (_isLoading) return;
    setState(() => _isLoading = true);
    try {
      await AdminService.rejectEmployeeChange(
        int.parse(reqId),
        reason: reason ?? "",
      );
      _snack("Profile update rejected.", isError: false);
      await _loadChangeRequests();
    } catch (e) {
      _snack("Rejection failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _addEmployee() async {
    if (!_addFormKey.currentState!.validate()) return;
    if (_isLoading) return;

    // Validate times logic if needed
    if (_loginCtrl.text == _logoutCtrl.text) {
      _snack("Login and Logout times must be different.", isError: true);
      return;
    }

    setState(() => _isLoading = true);
    try {
      final address = _addrCtrl.text.trim().isNotEmpty
          ? _addrCtrl.text.trim()
          : ((_pickedLat != null && _pickedLng != null)
              ? "${_pickedLat!.toStringAsFixed(6)}, ${_pickedLng!.toStringAsFixed(6)}"
              : "");
      final data = await AdminService.createEmployee({
        "admin_id": widget.adminId,
        "name": _nameCtrl.text.trim(),
        "mobile": _mobileCtrl.text.trim(),
        "login_time": _loginCtrl.text,
        "logout_time": _logoutCtrl.text,
        "address": address,
        "home_address": address,
        if (_pickedLat != null) "lat": _pickedLat,
        if (_pickedLng != null) "lng": _pickedLng,
        if (_pickedLat != null) "home_lat": _pickedLat,
        if (_pickedLng != null) "home_lng": _pickedLng,
      });

      final empCode = data["employee_code"] ?? "Generated";
      _snack("Employee Added! Code: $empCode", isError: false);
      _clearForm();
      _switchSection(EmployeeSection.list);
    } catch (e) {
      _snack("Failed to add employee: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _updateEmployee(String empId, Map<String, dynamic> data) async {
    // This is called from the modal
    setState(() => _isLoading = true);
    try {
      final normalized = Map<String, dynamic>.from(data);
      final address = (normalized["address"] ?? "").toString().trim();
      if (address.isNotEmpty) {
        normalized["address"] = address;
        normalized["home_address"] = address;
      }
      if (normalized["lat"] != null) {
        normalized["home_lat"] = normalized["lat"];
      }
      if (normalized["lng"] != null) {
        normalized["home_lng"] = normalized["lng"];
      }
      await AdminService.updateEmployee(
          empId, {"admin_id": widget.adminId, ...normalized});
      _snack("Employee details updated.", isError: false);
      if (mounted && Navigator.canPop(context))
        Navigator.pop(context); // Close modal
      await _loadEmployees();
    } catch (e) {
      _snack("Update failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _deleteEmployee(String empId) async {
    setState(() => _isLoading = true);
    try {
      await AdminService.deleteEmployee(empId);
      _snack("Employee removed.", isError: false);
      if (mounted && Navigator.canPop(context)) Navigator.pop(context);
      await _loadEmployees();
    } catch (e) {
      _snack("Deletion failed: $e", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ---------------------------------------------------------------------------
  // UI HELPERS
  // ---------------------------------------------------------------------------

  void _switchSection(EmployeeSection section) {
    setState(() {
      _currentSection = section;
    });
    if (section == EmployeeSection.requests) {
      _loadRequests();
    }
    if (section == EmployeeSection.absences) {
      _loadAbsenceRequests();
    }
    if (section == EmployeeSection.absentEmployees) {
      _loadApprovedAbsences();
    }
    if (section == EmployeeSection.changes) {
      _loadChangeRequests();
    }
    if (section == EmployeeSection.list) {
      _loadEmployees();
    } // Refresh list
    if (section == EmployeeSection.add) {
      _clearForm();
    }
  }

  void _clearForm() {
    _nameCtrl.clear();
    _mobileCtrl.clear();
    _loginCtrl.clear();
    _logoutCtrl.clear();
    _addrCtrl.clear();
    _pickedLat = null;
    _pickedLng = null;
    _isResolvingAddress = false;
    _addressResolveNote = null;
  }

  String _coordLabel() {
    if (_pickedLat == null || _pickedLng == null)
      return "No map point selected";
    return "${_pickedLat!.toStringAsFixed(6)}, ${_pickedLng!.toStringAsFixed(6)}";
  }

  Future<void> _pickLocationOnMap() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _MapCoordinatePicker(
        title: "Select Home Location",
        addressHint: _addrCtrl.text.trim(),
        initialLat: _pickedLat,
        initialLng: _pickedLng,
      ),
    );
    if (!mounted || selected == null) return;
    setState(() {
      _pickedLat = selected.latitude;
      _pickedLng = selected.longitude;
      _addressResolveNote = "Map location selected";
    });
    await _reverseGeocodeSelection();
  }

  Future<void> _reverseGeocodeSelection() async {
    final lat = _pickedLat;
    final lng = _pickedLng;
    if (lat == null || lng == null || !mounted) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = "Saving selected coordinates in address...";
    });
    setState(() {
      _addrCtrl.text = "${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}";
      _addressResolveNote = "Address set to selected map coordinates";
      _isResolvingAddress = false;
    });
  }

  void _onAddressChanged(String value) {
    _addressDebounce?.cancel();
    final address = value.trim();
    if (address.length < 5) {
      if (mounted) {
        setState(() {
          _addressResolveNote = null;
        });
      }
      return;
    }
    _addressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveAddress(address);
    });
  }

  Future<void> _autoResolveAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = "Resolving address on map...";
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final loc = locations.first;
        setState(() {
          _pickedLat = loc.latitude;
          _pickedLng = loc.longitude;
          _addressResolveNote = "Auto-centered from typed address";
        });
      } else {
        setState(() {
          _addressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _addressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (mounted) {
        setState(() {
          _isResolvingAddress = false;
        });
      }
    }
  }

  void _snack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg,
            style: AppTypography.bodySmall
                .copyWith(color: AppThemeColors.textPrimary)),
        backgroundColor:
            isError ? AppThemeColors.error : AppThemeColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md)),
      ),
    );
  }

  void _showEmployeeDetails(Map<String, dynamic> emp) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _EditEmployeeModal(
        emp: emp,
        onUpdate: (data) => _updateEmployee(emp["id"].toString(), data),
        onDelete: () => _deleteEmployee(emp["id"].toString()),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // BUILD
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent, // Background handled by container
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppGradients.backgroundGradient,
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              children: [
                _buildTopBar(),
                const SizedBox(height: AppSpacing.lg),
                Expanded(
                  child: SingleChildScrollView(
                    child: _buildCenterPanel(),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            const RGLogo(
              variant: RGLogoVariant.mark,
              width: 40,
              height: 40,
            ),
            const SizedBox(width: AppSpacing.sm),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("RG Travel Solution",
                    style: AppTypography.titleSmall.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.2)),
                Text(
                    "Employee Management (Requests • Absence • Updates • Add • List)",
                    style: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textSecondary)),
              ],
            ),
          ],
        ),
        Container(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            color: AppThemeColors.cardGlass,
            border: Border.all(color: AppThemeColors.border),
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
          child: Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color:
                      _isOnline ? AppThemeColors.success : AppThemeColors.error,
                  boxShadow: _isOnline
                      ? [
                          BoxShadow(
                              color:
                                  AppThemeColors.success.withValues(alpha: 0.6),
                              blurRadius: 12)
                        ]
                      : [],
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(_isOnline ? "Online" : "Offline",
                  style: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.textSecondary)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildCenterPanel() {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.xl),
        boxShadow: AppShadows.elevated,
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        children: [
          _buildCenterButtons(),
          const SizedBox(height: AppSpacing.md),
          _buildActiveSection(),
        ],
      ),
    );
  }

  Widget _buildCenterButtons() {
    return Wrap(
      spacing: 14,
      runSpacing: 14,
      alignment: WrapAlignment.center,
      children: [
        _buildPremiumButton(
          icon: Icons.mark_email_unread_outlined,
          title: "New Requests",
          subtitle: "Approve / Reject new employees",
          onTap: () => _switchSection(EmployeeSection.requests),
          badge: _requests.isNotEmpty ? "${_requests.length}" : null,
        ),
        _buildPremiumButton(
          icon: Icons.person_add_alt_1_outlined,
          title: "Add Employee",
          subtitle: "Create new employee record",
          onTap: () => _switchSection(EmployeeSection.add),
        ),
        _buildPremiumButton(
          icon: Icons.event_busy_outlined,
          title: "Absence Requests",
          subtitle: "Approve absence and cancel requests",
          onTap: () => _switchSection(EmployeeSection.absences),
          badge: _absenceRequests
                  .where((r) => _isPendingStatus(r["status"]))
                  .isNotEmpty
              ? "${_absenceRequests.where((r) => _isPendingStatus(r["status"])).length}"
              : null,
        ),
        _buildPremiumButton(
          icon: Icons.person_off_outlined,
          title: "Absent Employees",
          subtitle: "View approved absent ranges and remove",
          onTap: () => _switchSection(EmployeeSection.absentEmployees),
          badge: _approvedAbsences.isNotEmpty
              ? "${_approvedAbsences.length}"
              : null,
        ),
        _buildPremiumButton(
          icon: Icons.badge_outlined,
          title: "All Employees",
          subtitle: "Search & Manage Database",
          onTap: () => _switchSection(EmployeeSection.list),
        ),
        _buildPremiumButton(
          icon: Icons.sync_alt_outlined,
          title: "Profile Updates",
          subtitle: "Approve profile change requests",
          onTap: () => _switchSection(EmployeeSection.changes),
          badge:
              _changeRequests.isNotEmpty ? "${_changeRequests.length}" : null,
        ),
      ],
    );
  }

  Widget _buildPremiumButton({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    String? badge,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Container(
        constraints: const BoxConstraints(minWidth: 240),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md, vertical: AppSpacing.md),
        decoration: BoxDecoration(
          border: Border.all(color: AppThemeColors.border),
          gradient: AppGradients.cardGradient,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          boxShadow: AppShadows.card,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: AppThemeColors.secondary.withValues(alpha: 0.16),
                    border: Border.all(
                        color:
                            AppThemeColors.secondary.withValues(alpha: 0.30)),
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                  alignment: Alignment.center,
                  child:
                      Icon(icon, size: 18, color: AppThemeColors.textPrimary),
                ),
                if (badge != null)
                  Positioned(
                    top: -5,
                    right: -5,
                    child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(
                          color: AppThemeColors.error, shape: BoxShape.circle),
                      child: Text(badge,
                          style: AppTypography.labelSmall.copyWith(
                              color: AppThemeColors.textPrimary,
                              fontSize: 10,
                              fontWeight: FontWeight.bold)),
                    ),
                  )
              ],
            ),
            const SizedBox(width: AppSpacing.sm),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(title,
                      style: AppTypography.labelLarge.copyWith(
                          color: AppThemeColors.textPrimary,
                          fontWeight: FontWeight.w600)),
                  Text(subtitle,
                      style: AppTypography.labelSmall
                          .copyWith(color: AppThemeColors.textSecondary)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveSection() {
    if (_isLoading && _requests.isEmpty && _employees.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(40),
        child: CircularProgressIndicator(color: AppThemeColors.secondary),
      );
    }

    switch (_currentSection) {
      case EmployeeSection.main:
        return const SizedBox.shrink();
      case EmployeeSection.requests:
        return _buildRequestsSection();
      case EmployeeSection.absences:
        return _buildAbsenceRequestsSection();
      case EmployeeSection.absentEmployees:
        return _buildApprovedAbsencesSection();
      case EmployeeSection.changes:
        return _buildChangeRequestsSection();
      case EmployeeSection.add:
        return _buildAddSection();
      case EmployeeSection.list:
        return _buildListSection();
    }
  }

  // ---------------------------------------------------------------------------
  // SECTION: REQUESTS
  // ---------------------------------------------------------------------------
  Widget _buildRequestsSection() {
    return _sectionContainer(
      title: "New Employee Requests",
      count: "${_requests.length} pending",
      child: _requests.isEmpty
          ? Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text("No pending registration requests.",
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textTertiary)))
          : Column(
              children: _requests
                  .map((req) => _requestCard(
                        title: (req["name"] ?? "Unknown").toString(),
                        sub:
                            "Mobile: ${req["mobile"]}\nShift: ${req["login_time"]} - ${req["logout_time"]}",
                        onConnect: () => _approveReq(req["id"].toString()),
                        onReject: () => _showRejectDialog(req["id"].toString()),
                      ))
                  .toList(),
            ),
    );
  }

  Widget _buildChangeRequestsSection() {
    final pending =
        _changeRequests.where((r) => _isPendingStatus(r["status"])).toList();
    return _sectionContainer(
      title: "Profile Update Requests",
      count: "${pending.length} pending",
      child: pending.isEmpty
          ? Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text("No pending profile updates.",
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textTertiary)))
          : Column(
              children: pending
                  .map((req) => _requestCard(
                        title: (req["name"] ?? "Unknown").toString(),
                        sub:
                            "Mobile: ${req["mobile"]}\nRequested Address: ${req["home_address"]}\nStatus: ${(req["status"] ?? "pending").toString().toUpperCase()}",
                        onConnect: () =>
                            _approveChangeReq(req["id"].toString()),
                        onReject: () =>
                            _showChangeRejectDialog(req["id"].toString()),
                        accent: AppThemeColors.secondary,
                      ))
                  .toList(),
            ),
    );
  }

  Widget _buildAbsenceRequestsSection() {
    final pending =
        _absenceRequests.where((r) => _isPendingStatus(r["status"])).toList();
    return _sectionContainer(
      title: "Absence Requests",
      count: "${pending.length} pending",
      child: pending.isEmpty
          ? Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text(
                "No pending absence or cancellation requests.",
                style: AppTypography.bodyMedium
                    .copyWith(color: AppThemeColors.textTertiary),
              ),
            )
          : Column(
              children: pending
                  .map((req) => _requestCard(
                        title:
                            (req["employee_name"] ?? req["name"] ?? "Unknown")
                                .toString(),
                        sub:
                            "Type: ${_absenceRequestTypeLabel(req)}\nDates: ${_absenceRequestDateLabel(req)}\nReason: ${(req["reason"] ?? "-").toString()}",
                        onConnect: () =>
                            _approveAbsenceReq(req["id"].toString()),
                        onReject: () =>
                            _showAbsenceRejectDialog(req["id"].toString()),
                        accent: _absenceRequestAccent(req),
                      ))
                  .toList(),
            ),
    );
  }

  Widget _buildApprovedAbsencesSection() {
    return _sectionContainer(
      title: "Absent Employees",
      count: "${_approvedAbsences.length} active",
      child: _approvedAbsences.isEmpty
          ? Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text(
                "No approved absent employees found.",
                style: AppTypography.bodyMedium
                    .copyWith(color: AppThemeColors.textTertiary),
              ),
            )
          : Column(
              children: _approvedAbsences.map((req) {
                final mobile = (req["employee_mobile"] ?? "").toString();
                final fromDate = (req["from_date"] ?? "").toString();
                final toDate = (req["to_date"] ?? "").toString();
                final reviewedAt = (req["reviewed_at"] ?? "").toString();
                return _requestCard(
                  title: (req["employee_name"] ?? "Unknown").toString(),
                  sub:
                      "Mobile: ${mobile.isEmpty ? "-" : mobile}\nFrom: ${fromDate.isEmpty ? "-" : fromDate}\nTo: ${toDate.isEmpty ? "-" : toDate}\nDays: ${(req["total_days"] ?? 1).toString()}\nReason: ${(req["reason"] ?? "-").toString()}\nApproved: ${reviewedAt.isEmpty ? "-" : reviewedAt}",
                  onConnect: () => _showRemoveApprovedAbsenceDialog(req),
                  onReject: () => _showRemoveApprovedAbsenceDialog(req),
                  approveLabel: "Remove",
                  hideReject: true,
                  accent: AppThemeColors.warning,
                );
              }).toList(),
            ),
    );
  }

  Widget _requestCard({
    required String title,
    required String sub,
    required VoidCallback onConnect,
    required VoidCallback onReject,
    String approveLabel = "Approve",
    String rejectLabel = "Reject",
    bool hideReject = false,
    Color accent = AppThemeColors.secondary,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            accent.withValues(alpha: 0.08),
            AppThemeColors.cardGlass.withValues(alpha: 0.65),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: accent.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(sub,
                    style: AppTypography.labelSmall.copyWith(
                        color: AppThemeColors.textSecondary, height: 1.4)),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          if (!hideReject) ...[
            _actionBtn(rejectLabel, AppThemeColors.error, onReject),
            const SizedBox(width: AppSpacing.sm),
          ],
          _actionBtn(
              approveLabel,
              hideReject ? AppThemeColors.warning : AppThemeColors.success,
              onConnect),
        ],
      ),
    );
  }

  Widget _actionBtn(String label, Color color, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: Container(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md, vertical: AppSpacing.sm),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          border: Border.all(color: color.withValues(alpha: 0.3)),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Text(label,
            style: AppTypography.labelSmall
                .copyWith(color: color, fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _sectionContainer(
      {required String title, String? count, required Widget child}) {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(children: [
                IconButton(
                  icon: const Icon(Icons.arrow_back_ios_new,
                      size: 16, color: AppThemeColors.textPrimary),
                  onPressed: () => _switchSection(EmployeeSection.main),
                ),
                Text(title,
                    style: AppTypography.titleMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold)),
              ]),
              if (count != null)
                Text(count,
                    style: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textSecondary)),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          child,
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // SECTION: ADD
  // ---------------------------------------------------------------------------
  Widget _buildAddSection() {
    return _sectionContainer(
      title: "Add New Employee",
      child: Form(
        key: _addFormKey,
        child: Column(
          children: [
            _inputField(_nameCtrl, "Full Name", Icons.person),
            const SizedBox(height: AppSpacing.md),
            _inputField(_mobileCtrl, "Mobile Number (10 Digits)", Icons.phone,
                isNumber: true, validator: (v) {
              if (v == null || v.length < 10)
                return "Valid 10-digit mobile required";
              return null;
            }),
            const SizedBox(height: AppSpacing.md),
            Row(children: [
              Expanded(child: _timePickerField(_loginCtrl, "Login Time")),
              const SizedBox(width: AppSpacing.md),
              Expanded(child: _timePickerField(_logoutCtrl, "Logout Time")),
            ]),
            const SizedBox(height: AppSpacing.md),
            _inputField(
              _addrCtrl,
              "Home Address",
              Icons.home,
              lines: 3,
              onChanged: _onAddressChanged,
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _pickLocationOnMap,
                    icon: const Icon(Icons.map_outlined, size: 16),
                    label: const Text("Pick on Map"),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppThemeColors.border),
                      foregroundColor: AppThemeColors.textPrimary,
                      padding:
                          const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      backgroundColor: AppThemeColors.background,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "Coordinates: ${_coordLabel()}",
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ),
            if (_isResolvingAddress || _addressResolveNote != null) ...[
              const SizedBox(height: 4),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _isResolvingAddress
                      ? "Resolving address..."
                      : (_addressResolveNote ?? ""),
                  style: AppTypography.labelSmall.copyWith(
                    color: _isResolvingAddress
                        ? AppThemeColors.secondary
                        : AppThemeColors.textTertiary,
                  ),
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                    onPressed: _clearForm,
                    child: Text("Clear",
                        style: AppTypography.labelMedium
                            .copyWith(color: AppThemeColors.textSecondary))),
                const SizedBox(width: AppSpacing.sm),
                ElevatedButton.icon(
                  onPressed: _addEmployee,
                  icon: const Icon(Icons.check, size: 16),
                  label: const Text("Add Employee"),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppThemeColors.primary,
                    foregroundColor: AppThemeColors.textPrimary,
                    padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.lg, vertical: AppSpacing.md),
                  ),
                )
              ],
            )
          ],
        ),
      ),
    );
  }

  Widget _inputField(
    TextEditingController ctrl,
    String hint,
    IconData icon, {
    bool isNumber = false,
    int lines = 1,
    String? Function(String?)? validator,
    ValueChanged<String>? onChanged,
  }) {
    return TextFormField(
      controller: ctrl,
      keyboardType: isNumber ? TextInputType.number : TextInputType.text,
      maxLines: lines,
      style:
          AppTypography.bodyMedium.copyWith(color: AppThemeColors.textPrimary),
      validator:
          validator ?? (v) => (v == null || v.isEmpty) ? "Required" : null,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: hint,
        labelStyle: AppTypography.labelMedium
            .copyWith(color: AppThemeColors.textSecondary),
        prefixIcon: Icon(icon, color: AppThemeColors.textTertiary),
        filled: true,
        fillColor: AppThemeColors.background,
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            borderSide: BorderSide.none),
      ),
    );
  }

  Widget _timePickerField(TextEditingController ctrl, String label) {
    return TextFormField(
      controller: ctrl,
      readOnly: true,
      style:
          AppTypography.bodyMedium.copyWith(color: AppThemeColors.textPrimary),
      validator: (v) => (v == null || v.isEmpty) ? "Required" : null,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: AppTypography.labelMedium
            .copyWith(color: AppThemeColors.textSecondary),
        prefixIcon:
            const Icon(Icons.access_time, color: AppThemeColors.textTertiary),
        filled: true,
        fillColor: AppThemeColors.background,
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            borderSide: BorderSide.none),
      ),
      onTap: () async {
        final t = await showTimePicker(
            context: context, initialTime: TimeOfDay.now());
        if (t != null && mounted) {
          final h = t.hour.toString().padLeft(2, '0');
          final m = t.minute.toString().padLeft(2, '0');
          ctrl.text = "$h:$m";
        }
      },
    );
  }

  // ---------------------------------------------------------------------------
  // SECTION: LIST
  // ---------------------------------------------------------------------------
  Widget _buildListSection() {
    return _sectionContainer(
      title: "All Employees",
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  "Employee Directory",
                  style: AppTypography.titleSmall.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              IconButton(
                tooltip: "Refresh list",
                onPressed: _isLoading ? null : _loadEmployees,
                icon: const Icon(Icons.refresh,
                    color: AppThemeColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              _buildEmployeeStatChip(
                icon: Icons.groups_2_outlined,
                label: "Total",
                value: "${_employees.length}",
              ),
              _buildEmployeeStatChip(
                icon: Icons.filter_alt_outlined,
                label: "Visible",
                value: "${_filteredEmployees.length}",
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Container(
            decoration: BoxDecoration(
              color: AppThemeColors.background,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppThemeColors.border),
            ),
            child: TextField(
              controller: _searchController,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textPrimary),
              decoration: InputDecoration(
                hintText: "Search by name, mobile, employee code",
                hintStyle: AppTypography.bodyMedium
                    .copyWith(color: AppThemeColors.textTertiary),
                prefixIcon: const Icon(Icons.search,
                    color: AppThemeColors.textTertiary),
                suffixIcon: _searchController.text.isEmpty
                    ? null
                    : IconButton(
                        tooltip: "Clear",
                        onPressed: () {
                          _searchController.clear();
                          setState(_filterEmployees);
                        },
                        icon: const Icon(Icons.close,
                            color: AppThemeColors.textTertiary),
                      ),
                filled: true,
                fillColor: Colors.transparent,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (_) => setState(_filterEmployees),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
              child: Center(
                child:
                    CircularProgressIndicator(color: AppThemeColors.secondary),
              ),
            )
          else if (_filteredEmployees.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.lg),
              decoration: BoxDecoration(
                color: AppThemeColors.cardGlass.withValues(alpha: 0.45),
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(color: AppThemeColors.border),
              ),
              child: Column(
                children: [
                  const Icon(Icons.people_outline,
                      size: 28, color: AppThemeColors.textTertiary),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    "No employees found",
                    style: AppTypography.titleSmall
                        .copyWith(color: AppThemeColors.textPrimary),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    "Try another keyword or refresh the list.",
                    style: AppTypography.bodySmall
                        .copyWith(color: AppThemeColors.textSecondary),
                  ),
                ],
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _filteredEmployees.length,
              separatorBuilder: (_, __) =>
                  const SizedBox(height: AppSpacing.sm),
              itemBuilder: (_, i) =>
                  _buildEmployeeListCard(_filteredEmployees[i]),
            ),
        ],
      ),
    );
  }

  Map<String, dynamic> _normalizeChangeRequest(Map<String, dynamic> req) {
    final status = (req["status"] ?? "pending").toString().trim().toLowerCase();
    return {
      ...req,
      "status": status,
      "name": (req["name"] ??
              req["requested_name"] ??
              req["employee_name"] ??
              "Unknown")
          .toString(),
      "mobile": (req["mobile"] ?? req["requested_mobile"] ?? "").toString(),
      "home_address": (req["home_address"] ??
              req["address"] ??
              req["requested_address"] ??
              "")
          .toString(),
    };
  }

  Map<String, dynamic> _normalizeAbsenceRequest(Map<String, dynamic> req) {
    final status = (req["status"] ?? "pending").toString().trim().toLowerCase();
    final kind =
        (req["request_kind"] ?? "absence").toString().trim().toLowerCase();
    return {
      ...req,
      "status": status,
      "request_kind": kind,
      "employee_name":
          (req["employee_name"] ?? req["name"] ?? "Unknown").toString(),
      "from_date": (req["from_date"] ?? req["absent_date"] ?? "").toString(),
      "to_date": (req["to_date"] ?? req["absent_date"] ?? "").toString(),
      "reason": (req["reason"] ?? "").toString(),
    };
  }

  Map<String, dynamic> _normalizeApprovedAbsence(Map<String, dynamic> req) {
    final normalizedDates = (req["dates"] is List)
        ? (req["dates"] as List)
            .map((e) => e.toString())
            .where((e) => e.isNotEmpty)
            .toList()
        : <String>[];
    final fromDate = (req["from_date"] ?? "").toString();
    final toDate = (req["to_date"] ?? "").toString();
    return {
      ...req,
      "employee_id": (req["employee_id"] ?? "").toString(),
      "employee_name":
          (req["employee_name"] ?? req["name"] ?? "Unknown").toString(),
      "employee_mobile":
          (req["employee_mobile"] ?? req["mobile"] ?? "").toString(),
      "from_date": fromDate,
      "to_date": toDate,
      "reason": (req["reason"] ?? "").toString(),
      "dates": normalizedDates.isNotEmpty
          ? normalizedDates
          : <String>[
              if (fromDate.isNotEmpty) fromDate,
              if (toDate.isNotEmpty && toDate != fromDate) toDate,
            ],
      "total_days": int.tryParse((req["total_days"] ?? "").toString()) ??
          (normalizedDates.isNotEmpty ? normalizedDates.length : 1),
      "reviewed_at": (req["reviewed_at"] ?? "").toString(),
      "reviewed_by": (req["reviewed_by"] ?? "").toString(),
    };
  }

  bool _isPendingStatus(dynamic status) {
    final s = (status ?? "").toString().trim().toLowerCase();
    return s == "pending";
  }

  String _absenceRequestTypeLabel(Map<String, dynamic> req) {
    return (req["request_kind"] ?? "absence").toString().toLowerCase() ==
            "cancel"
        ? "Cancel approved absence"
        : "Absence";
  }

  String _absenceRequestDateLabel(Map<String, dynamic> req) {
    final fromDate = (req["from_date"] ?? req["absent_date"] ?? "").toString();
    final toDate = (req["to_date"] ?? req["absent_date"] ?? "").toString();
    final totalDays = int.tryParse((req["total_days"] ?? "").toString()) ?? 1;
    if (fromDate.isEmpty) return "-";
    if (fromDate == toDate || totalDays <= 1) return fromDate;
    return "$fromDate -> $toDate ($totalDays days)";
  }

  Color _absenceRequestAccent(Map<String, dynamic> req) {
    return (req["request_kind"] ?? "absence").toString().toLowerCase() ==
            "cancel"
        ? AppThemeColors.warning
        : AppThemeColors.secondary;
  }

  Widget _buildEmployeeStatChip({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppThemeColors.textSecondary),
          const SizedBox(width: 6),
          Text(
            "$label: $value",
            style: AppTypography.labelSmall.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmployeeListCard(Map<String, dynamic> emp) {
    final name = (emp["name"] ?? emp["employee_name"] ?? "-").toString();
    final employeeCode = (emp["employee_code"] ?? emp["id"] ?? "-").toString();
    final mobile = (emp["mobile"] ?? emp["phone"] ?? "-").toString();
    final login = (emp["login_time"] ?? emp["login"] ?? "--:--").toString();
    final logout = (emp["logout_time"] ?? emp["logout"] ?? "--:--").toString();
    final address =
        (emp["address"] ?? emp["home_address"] ?? "Address not available")
            .toString();

    return InkWell(
      onTap: () => _showEmployeeDetails(emp),
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          gradient: AppGradients.cardGradient,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: AppThemeColors.border),
          boxShadow: AppShadows.card,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: AppThemeColors.secondary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(
                      color: AppThemeColors.secondary.withValues(alpha: 0.35),
                    ),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    name.isNotEmpty ? name[0].toUpperCase() : "E",
                    style: AppTypography.labelLarge.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppThemeColors.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        "Code: $employeeCode",
                        style: AppTypography.labelSmall.copyWith(
                          color: AppThemeColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.arrow_forward_ios,
                  size: 14,
                  color: AppThemeColors.textTertiary,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                const Icon(
                  Icons.phone_iphone,
                  size: 14,
                  color: AppThemeColors.textTertiary,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    mobile,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textSecondary,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppThemeColors.primary.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    border: Border.all(
                      color: AppThemeColors.primary.withValues(alpha: 0.35),
                    ),
                  ),
                  child: Text(
                    "$login - $logout",
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.location_on_outlined,
                  size: 14,
                  color: AppThemeColors.textTertiary,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    address,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textSecondary,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// -----------------------------------------------------------------------------
// EDIT MODAL
// -----------------------------------------------------------------------------
class _EditEmployeeModal extends StatefulWidget {
  final Map<String, dynamic> emp;
  final void Function(Map<String, dynamic>) onUpdate;
  final VoidCallback onDelete;

  const _EditEmployeeModal(
      {required this.emp, required this.onUpdate, required this.onDelete});

  @override
  State<_EditEmployeeModal> createState() => _EditEmployeeModalState();
}

class _EditEmployeeModalState extends State<_EditEmployeeModal> {
  late TextEditingController _name;
  late TextEditingController _mobile;
  late TextEditingController _login;
  late TextEditingController _logout;
  late TextEditingController _addr;
  double? _pickedLat;
  double? _pickedLng;
  Timer? _addressDebounce;
  bool _isResolvingAddress = false;
  String? _addressResolveNote;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(
        text: (widget.emp["name"] ?? widget.emp["employee_name"]).toString());
    _mobile = TextEditingController(
        text: (widget.emp["mobile"] ?? widget.emp["phone"]).toString());
    _login = TextEditingController(
        text: (widget.emp["login_time"] ?? widget.emp["login"]).toString());
    _logout = TextEditingController(
        text: (widget.emp["logout_time"] ?? widget.emp["logout"]).toString());
    _addr = TextEditingController(
        text: (widget.emp["address"] ?? widget.emp["home_address"] ?? "")
            .toString());
    _pickedLat = _asDouble(
      widget.emp["home_lat"] ??
          widget.emp["lat"] ??
          widget.emp["home_location_lat"],
    );
    _pickedLng = _asDouble(
      widget.emp["home_lng"] ??
          widget.emp["lng"] ??
          widget.emp["home_location_lng"],
    );
  }

  @override
  void dispose() {
    _addressDebounce?.cancel();
    _name.dispose();
    _mobile.dispose();
    _login.dispose();
    _logout.dispose();
    _addr.dispose();
    super.dispose();
  }

  double? _asDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  String _coordLabel() {
    if (_pickedLat == null || _pickedLng == null)
      return "No map point selected";
    return "${_pickedLat!.toStringAsFixed(6)}, ${_pickedLng!.toStringAsFixed(6)}";
  }

  Future<void> _pickLocationOnMap() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _MapCoordinatePicker(
        title: "Update Home Location",
        addressHint: _addr.text.trim(),
        initialLat: _pickedLat,
        initialLng: _pickedLng,
      ),
    );
    if (!mounted || selected == null) return;
    setState(() {
      _pickedLat = selected.latitude;
      _pickedLng = selected.longitude;
      _addressResolveNote = "Map location selected";
    });
    await _reverseGeocodeSelection();
  }

  Future<void> _reverseGeocodeSelection() async {
    final lat = _pickedLat;
    final lng = _pickedLng;
    if (lat == null || lng == null || !mounted) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = "Saving selected coordinates in address...";
    });
    setState(() {
      _addr.text = "${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}";
      _addressResolveNote = "Address set to selected map coordinates";
      _isResolvingAddress = false;
    });
  }

  void _onAddressChanged(String value) {
    _addressDebounce?.cancel();
    final address = value.trim();
    if (address.length < 5) {
      if (mounted) {
        setState(() {
          _addressResolveNote = null;
        });
      }
      return;
    }
    _addressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveAddress(address);
    });
  }

  Future<void> _autoResolveAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = "Resolving address on map...";
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final loc = locations.first;
        setState(() {
          _pickedLat = loc.latitude;
          _pickedLng = loc.longitude;
          _addressResolveNote = "Auto-centered from typed address";
        });
      } else {
        setState(() {
          _addressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _addressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (mounted) {
        setState(() {
          _isResolvingAddress = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: BoxDecoration(
        color: AppThemeColors.surface, // Dark modal
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
        boxShadow: AppShadows.elevated,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Edit Employee",
                    style: AppTypography.titleMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold)),
                IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close,
                        color: AppThemeColors.textSecondary)),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            _field(_name, "Name"),
            const SizedBox(height: AppSpacing.md),
            _field(_mobile, "Mobile"),
            const SizedBox(height: AppSpacing.md),
            Row(children: [
              Expanded(child: _field(_login, "Login")),
              const SizedBox(width: AppSpacing.md),
              Expanded(child: _field(_logout, "Logout")),
            ]),
            const SizedBox(height: AppSpacing.md),
            _field(
              _addr,
              "Address",
              lines: 2,
              onChanged: _onAddressChanged,
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _pickLocationOnMap,
                    icon: const Icon(Icons.map_outlined, size: 16),
                    label: const Text("Pick on Map"),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppThemeColors.border),
                      foregroundColor: AppThemeColors.textPrimary,
                      padding:
                          const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      backgroundColor: AppThemeColors.background,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "Coordinates: ${_coordLabel()}",
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ),
            if (_isResolvingAddress || _addressResolveNote != null) ...[
              const SizedBox(height: 4),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _isResolvingAddress
                      ? "Resolving address..."
                      : (_addressResolveNote ?? ""),
                  style: AppTypography.labelSmall.copyWith(
                    color: _isResolvingAddress
                        ? AppThemeColors.secondary
                        : AppThemeColors.textTertiary,
                  ),
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.xl),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: widget.onDelete,
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppThemeColors.error),
                      foregroundColor: AppThemeColors.error,
                      padding:
                          const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                    child: const Text("Delete Employee"),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      final address = _addr.text.trim().isNotEmpty
                          ? _addr.text.trim()
                          : ((_pickedLat != null && _pickedLng != null)
                              ? "${_pickedLat!.toStringAsFixed(6)}, ${_pickedLng!.toStringAsFixed(6)}"
                              : "");
                      widget.onUpdate({
                        "name": _name.text,
                        "mobile": _mobile.text,
                        "login_time": _login.text,
                        "logout_time": _logout.text,
                        "address": address,
                        "home_address": address,
                        if (_pickedLat != null) "lat": _pickedLat,
                        if (_pickedLng != null) "lng": _pickedLng,
                        if (_pickedLat != null) "home_lat": _pickedLat,
                        if (_pickedLng != null) "home_lng": _pickedLng,
                      });
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppThemeColors.secondary,
                      foregroundColor: AppThemeColors.textPrimary,
                      padding:
                          const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                    child: const Text("Save Changes"),
                  ),
                )
              ],
            ),
            const SizedBox(height: AppSpacing.lg)
          ],
        ),
      ),
    );
  }

  Widget _field(
    TextEditingController ctrl,
    String label, {
    int lines = 1,
    ValueChanged<String>? onChanged,
  }) {
    return TextField(
      controller: ctrl,
      maxLines: lines,
      onChanged: onChanged,
      style:
          AppTypography.bodyMedium.copyWith(color: AppThemeColors.textPrimary),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: AppTypography.labelMedium
            .copyWith(color: AppThemeColors.textSecondary),
        filled: true,
        fillColor: AppThemeColors.background,
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            borderSide: BorderSide.none),
      ),
    );
  }
}

class _MapCoordinatePicker extends StatefulWidget {
  final String title;
  final String addressHint;
  final double? initialLat;
  final double? initialLng;

  const _MapCoordinatePicker({
    required this.title,
    required this.addressHint,
    this.initialLat,
    this.initialLng,
  });

  @override
  State<_MapCoordinatePicker> createState() => _MapCoordinatePickerState();
}

class _MapCoordinatePickerState extends State<_MapCoordinatePicker> {
  static const LatLng _defaultCenter = LatLng(18.5204, 73.8567);
  late final MapController _mapController;
  late LatLng _selected;
  double _zoom = 13.0;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _selected = (widget.initialLat != null && widget.initialLng != null)
        ? LatLng(widget.initialLat!, widget.initialLng!)
        : _defaultCenter;
  }

  @override
  Widget build(BuildContext context) {
    final height = MediaQuery.of(context).size.height * 0.82;
    return Container(
      height: height,
      decoration: const BoxDecoration(
        color: AppThemeColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.md,
              AppSpacing.lg,
              AppSpacing.sm,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: AppTypography.titleMedium.copyWith(
                          color: AppThemeColors.textPrimary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        widget.addressHint.isEmpty
                            ? "Tap map to select coordinates"
                            : widget.addressHint,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.labelSmall.copyWith(
                          color: AppThemeColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close,
                      color: AppThemeColors.textSecondary),
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.lg),
                child: FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: _selected,
                    initialZoom: _zoom,
                    onTap: (_, point) {
                      setState(() {
                        _selected = point;
                      });
                    },
                    onPositionChanged: (position, _) {
                      _zoom = position.zoom;
                    },
                  ),
                  children: [
                    TileLayer(
                      // Primary tiles: Carto (often more reliable on Flutter Web)
                      urlTemplate:
                          'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                      subdomains: const ['a', 'b', 'c', 'd'],
                      userAgentPackageName: 'com.rgtravel.app',
                    ),
                    TileLayer(
                      // Fallback tiles: OSM
                      urlTemplate:
                          'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                      subdomains: const ['a', 'b', 'c'],
                      userAgentPackageName: 'com.rgtravel.app',
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: _selected,
                          width: 48,
                          height: 48,
                          child: const Icon(
                            Icons.location_pin,
                            color: AppThemeColors.error,
                            size: 42,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.md,
              AppSpacing.lg,
              AppSpacing.lg,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    "Selected: ${_selected.latitude.toStringAsFixed(6)}, ${_selected.longitude.toStringAsFixed(6)}",
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textSecondary,
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                OutlinedButton(
                  onPressed: () {
                    _mapController.move(_selected, _zoom);
                  },
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppThemeColors.textPrimary,
                    side: const BorderSide(color: AppThemeColors.border),
                  ),
                  child: const Text("Center"),
                ),
                const SizedBox(width: AppSpacing.sm),
                ElevatedButton.icon(
                  onPressed: () => Navigator.pop(context, _selected),
                  icon: const Icon(Icons.check, size: 16),
                  label: const Text("Use Location"),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppThemeColors.primary,
                    foregroundColor: AppThemeColors.textPrimary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
