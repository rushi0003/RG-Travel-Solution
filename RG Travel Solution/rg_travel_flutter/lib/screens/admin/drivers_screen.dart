import 'dart:async';
import 'package:geocoding/geocoding.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/theme/app_theme.dart';
import '../../models/driver_model.dart';
import '../../models/driver_request.dart';
import '../../services/driver_service.dart';
import '../../services/admin_service.dart';
import '../../widgets/common/map_coordinate_picker_sheet.dart';
import '../../widgets/common/rg_logo.dart';

class DriversScreen extends StatefulWidget {
  const DriversScreen({super.key});

  @override
  State<DriversScreen> createState() => _DriversScreenState();
}

enum DriverSection {
  main,
  requests,
  changes, // New: Profile Change Requests
  add,
  list,
}

class _DriversScreenState extends State<DriversScreen> {
  // Navigation & State
  DriverSection _currentSection = DriverSection.main;
  bool _isLoading = false;
  bool _isOnline = false;
  Timer? _healthTimer;

  // Data
  List<DriverRequest> _requests = [];
  List<Map<String, dynamic>> _changeRequests = []; // New
  List<Driver> _drivers = [];
  List<Driver> _filteredDrivers = [];

  // Controllers
  final _searchController = TextEditingController();
  final _addFormKey = GlobalKey<FormState>();

  // Add/Edit Form Controllers
  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _licenseCtrl = TextEditingController();
  final _vehicleCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  int _selectedVehicleType = 4;
  Timer? _addressDebounce;
  bool _isResolvingAddress = false;
  String? _addressResolveNote;
  double? _pickedHomeLat;
  double? _pickedHomeLng;

  @override
  void initState() {
    super.initState();
    _checkHealth();
    _healthTimer =
        Timer.periodic(const Duration(seconds: 30), (_) => _checkHealth());
    // Don't auto-switch to list - stay on main view with 3 buttons
    // _switchSection(DriverSection.list);
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    _addressDebounce?.cancel();
    _searchController.dispose();
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _licenseCtrl.dispose();
    _vehicleCtrl.dispose();
    _addressCtrl.dispose();
    super.dispose();
  }

  Future<void> _checkHealth() async {
    final online = await DriverService.checkHealth();
    if (mounted) setState(() => _isOnline = online);
  }

  // ===========================================================================
  // DATA OPERATIONS
  // ===========================================================================

  Future<void> _loadRequests() async {
    setState(() {
      _isLoading = true;
    });
    try {
      final data = await DriverService.instance.getPendingRequests();
      setState(() {
        _requests = data;
      });
    } catch (e) {
      _snack("Failed to load requests: $e", isError: true);
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _loadDrivers() async {
    setState(() {
      _isLoading = true;
    });
    try {
      final data = await DriverService.instance.getAllDrivers();
      setState(() {
        _drivers = data;
        _filterDrivers();
      });
    } catch (e) {
      _snack("Failed to load drivers: $e", isError: true);
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _approveRequest(String id) async {
    setState(() => _isLoading = true);
    try {
      await DriverService.instance.approveRequest(id);
      _snack("Request Approved!", isError: false);
      await _loadRequests();
      await _loadDrivers();
    } catch (e) {
      _snack("Approval failed: $e", isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showRejectDialog(String id) {
    final reasonCtrl = TextEditingController();
    // Warning fix: add explicit type argument to satisfy strict inference.
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            side: const BorderSide(color: AppThemeColors.border)),
        title: Text("Reject Driver Request",
            style: AppTypography.titleMedium
                .copyWith(color: AppThemeColors.textPrimary)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              "Are you sure you want to reject this driver? This action cannot be undone.",
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textPrimary),
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: reasonCtrl,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textPrimary),
              decoration: InputDecoration(
                labelText: "Reason (Optional)",
                labelStyle: AppTypography.labelMedium
                    .copyWith(color: AppThemeColors.textTertiary),
                filled: true,
                fillColor: AppThemeColors.background,
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md)),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text("Cancel",
                style: AppTypography.labelLarge
                    .copyWith(color: AppThemeColors.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              _rejectRequest(id, reason: reasonCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(
              // Warning fix: `withOpacity` is deprecated; `withValues` preserves the same intent.
              backgroundColor: AppThemeColors.error.withValues(alpha: 0.2),
              foregroundColor: AppThemeColors.error,
            ),
            child: const Text("Reject"),
          ),
        ],
      ),
    );
  }

  Future<void> _rejectRequest(String id, {String? reason}) async {
    setState(() => _isLoading = true);
    try {
      await DriverService.instance.rejectRequest(id, reason: reason);
      _snack("Request Rejected", isError: false);
      await _loadRequests();
    } catch (e) {
      _snack("Rejection failed: $e", isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // --- Profile Change Requests ---

  Future<void> _loadChangeRequests() async {
    setState(() {
      _isLoading = true;
    });
    try {
      final data = await AdminService.getDriverChangeRequests();
      setState(() {
        _changeRequests = data;
      });
    } catch (e) {
      _snack("Failed to load changes: $e", isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _approveChange(int id) async {
    setState(() => _isLoading = true);
    try {
      await AdminService.approveDriverChange(id);
      _snack("Change Approved!", isError: false);
      await _loadChangeRequests();
      await _loadDrivers(); // Refresh drivers list to see updates
    } catch (e) {
      _snack("Approval failed: $e", isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _rejectChange(int id) async {
    setState(() => _isLoading = true);
    try {
      await AdminService.rejectDriverChange(id);
      _snack("Change Rejected", isError: false);
      await _loadChangeRequests();
    } catch (e) {
      _snack("Rejection failed: $e", isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _createDriver() async {
    if (!_addFormKey.currentState!.validate()) return;
    final homeTown = _addressCtrl.text.trim().isNotEmpty
        ? _addressCtrl.text.trim()
        : ((_pickedHomeLat != null && _pickedHomeLng != null)
            ? '${_pickedHomeLat!.toStringAsFixed(6)}, ${_pickedHomeLng!.toStringAsFixed(6)}'
            : '');

    final driver = Driver(
      id: '',
      name: _nameCtrl.text.trim(),
      mobile: _mobileCtrl.text.trim(),
      dlNo: _licenseCtrl.text.trim(),
      cabNo: _vehicleCtrl.text.trim(),
      homeTown: homeTown,
      vehicleType: _selectedVehicleType,
      homeLat: _pickedHomeLat,
      homeLng: _pickedHomeLng,
    );

    setState(() => _isLoading = true);
    try {
      await DriverService.instance.createDriver(driver);
      _snack("Driver Added Successfully!", isError: false);
      _clearForm();
      _switchSection(DriverSection.list);
    } catch (e) {
      _snack("Failed to add driver: $e", isError: true);
      setState(() => _isLoading = false);
    }
  }

  Future<void> _deleteDriver(String id) async {
    setState(() => _isLoading = true);
    try {
      await DriverService.instance.deleteDriver(id);
      _snack("Driver Removed", isError: false);
      Navigator.of(context).pop();
      await _loadDrivers();
    } catch (e) {
      _snack("Failed to delete: $e", isError: true);
      setState(() => _isLoading = false);
    }
  }

  Future<void> _updateDriver(Driver driver) async {
    setState(() => _isLoading = true);
    try {
      await DriverService.instance.updateDriver(driver.id, driver);
      _snack("Driver Updated", isError: false);
      Navigator.of(context).pop();
      await _loadDrivers();
    } catch (e) {
      _snack("Update failed: $e", isError: true);
      setState(() => _isLoading = false);
    }
  }

  void _filterDrivers() {
    final query = _searchController.text.toLowerCase();
    if (query.isEmpty) {
      _filteredDrivers = List.from(_drivers);
      return;
    }
    _filteredDrivers = _drivers.where((d) {
      return d.name.toLowerCase().contains(query) ||
          d.mobile.contains(query) ||
          d.licenseNo.toLowerCase().contains(query) ||
          d.vehicleNo.toLowerCase().contains(query) ||
          d.hometownAddress.toLowerCase().contains(query);
    }).toList();
  }

  Future<void> _searchDriversBackend(String query) async {
    if (query.isEmpty) {
      _filterDrivers();
      setState(() {});
      return;
    }
    setState(() => _isLoading = true);
    try {
      final results = await DriverService.instance.searchDrivers(query);
      setState(() {
        _filteredDrivers = results;
      });
    } catch (e) {
      _filterDrivers();
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // ===========================================================================
  // UI HELPERS
  // ===========================================================================

  void _switchSection(DriverSection section) {
    setState(() {
      _currentSection = section;
    });
    if (section == DriverSection.requests) _loadRequests();
    if (section == DriverSection.list) _loadDrivers();
    if (section == DriverSection.add) _clearForm();
  }

  void _clearForm() {
    _addressDebounce?.cancel();
    _nameCtrl.clear();
    _mobileCtrl.clear();
    _licenseCtrl.clear();
    _vehicleCtrl.clear();
    _addressCtrl.clear();
    if (!mounted) {
      _selectedVehicleType = 4;
      _pickedHomeLat = null;
      _pickedHomeLng = null;
      _isResolvingAddress = false;
      _addressResolveNote = null;
      return;
    }
    setState(() {
      _selectedVehicleType = 4;
      _pickedHomeLat = null;
      _pickedHomeLng = null;
      _isResolvingAddress = false;
      _addressResolveNote = null;
    });
  }

  void _snack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor:
            isError ? AppThemeColors.error : AppThemeColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md)),
      ),
    );
  }

  void _showDriverDetails(Driver driver) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _EditDriverModal(
        driver: driver,
        onUpdate: _updateDriver,
        onDelete: _deleteDriver,
      ),
    );
  }

  // ===========================================================================
  // UI BUILD - MATCHING HTML DESIGN
  // ===========================================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppGradients.backgroundGradient,
        ),
        child: Stack(
          children: [
            // Radial gradient overlays
            Positioned(
              top: -200,
              left: -200,
              child: Container(
                width: 1200,
                height: 600,
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    colors: [
                      AppThemeColors.secondary.withValues(alpha: 0.25),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              top: -100,
              right: -300,
              child: Container(
                width: 900,
                height: 500,
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    colors: [
                      AppThemeColors.primary.withValues(alpha: 0.18),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -200,
              left: 0,
              right: 0,
              child: Container(
                width: 1000,
                height: 700,
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    colors: [
                      AppThemeColors.success.withValues(alpha: 0.12),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
            // Main content
            SafeArea(
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
          ],
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
                Text(
                  "RG Travel Solution",
                  style: AppTypography.titleMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                  ),
                ),
                Text(
                  "Driver Management (Main • Requests • Add • List)",
                  style: AppTypography.labelSmall.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
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
                            blurRadius: 12,
                          ),
                        ]
                      : [],
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              Text(
                _isOnline ? "Ready" : "Offline",
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
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
          icon: "🧾",
          title: "New Driver Request",
          subtitle: "Approve / Reject new registrations",
          onTap: () => _switchSection(DriverSection.requests),
        ),
        _buildPremiumButton(
          icon: "➕",
          title: "Add New Driver",
          subtitle: "Validated form + save to DB",
          onTap: () => _switchSection(DriverSection.add),
        ),
        _buildPremiumButton(
          icon: "👤",
          title: "All Driver List",
          subtitle: "NLP search + view/edit/remove",
          onTap: () => _switchSection(DriverSection.list),
        ),
        _buildPremiumButton(
          icon: "🔄",
          title: "Profile Updates",
          subtitle: "Driver change requests",
          onTap: () {
            _switchSection(DriverSection.changes);
            _loadChangeRequests();
          },
        ),
      ],
    );
  }

  Widget _buildPremiumButton({
    required String icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Container(
        constraints: const BoxConstraints(minWidth: 240),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md, vertical: AppSpacing.sm),
        decoration: BoxDecoration(
          border: Border.all(color: AppThemeColors.border),
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AppThemeColors.cardGlassHover,
              AppThemeColors.cardGlass,
            ],
          ),
          borderRadius: BorderRadius.circular(AppRadius.lg),
          boxShadow: AppShadows.card,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: AppThemeColors.secondary.withValues(alpha: 0.16),
                border: Border.all(
                    color: AppThemeColors.secondary.withValues(alpha: 0.28)),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Center(
                child: Text(
                  icon,
                  style: AppTypography.headlineSmall.copyWith(fontSize: 18),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: AppTypography.labelLarge.copyWith(
                      color: AppThemeColors.textPrimary,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveSection() {
    if (_isLoading && _requests.isEmpty && _drivers.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(40.0),
        child: CircularProgressIndicator(color: AppThemeColors.secondary),
      );
    }

    switch (_currentSection) {
      case DriverSection.main:
        // Main view - only show the 3 buttons above, no active section
        return const SizedBox.shrink();
      case DriverSection.requests:
        return _buildRequestsSection();
      case DriverSection.changes:
        return _buildChangeRequestsSection();
      case DriverSection.add:
        return _buildAddSection();
      case DriverSection.list:
        return _buildListSection();
    }
  }

  // ---------------------------------------------------------------------------
  // REQUESTS SECTION
  // ---------------------------------------------------------------------------
  Widget _buildRequestsSection() {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  IconButton(
                    onPressed: () => _switchSection(DriverSection.main),
                    icon: const Icon(Icons.arrow_back_ios_new,
                        color: AppThemeColors.textPrimary, size: 18),
                    tooltip: "Back to Main",
                  ),
                  const SizedBox(width: 4),
                  Text(
                    "New Driver Requests",
                    style: AppTypography.titleSmall
                        .copyWith(color: AppThemeColors.textPrimary),
                  ),
                ],
              ),
              Text(
                "${_requests.length} request(s)",
                style: AppTypography.labelSmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          if (_requests.isEmpty)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Text(
                "No pending driver requests.",
                style: TextStyle(color: AppThemeColors.textTertiary),
              ),
            )
          else
            ..._requests.map((req) => _buildRequestCard(req)).toList(),
          const SizedBox(height: AppSpacing.sm),
          Container(
            padding: const EdgeInsets.all(AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(AppRadius.full),
            ),
            child: Text(
              "Tip: Approve will create driver record, Reject will remove request.",
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRequestCard(DriverRequest req) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlassHover,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      req.name,
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      "Mobile: ${req.mobile} • Vehicle: ${req.vehicleNo}",
                      style: AppTypography.labelSmall
                          .copyWith(color: AppThemeColors.textSecondary),
                    ),
                  ],
                ),
              ),
              Row(
                children: [
                  ElevatedButton(
                    onPressed: () => _showRejectDialog(req.id),
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.error.withValues(alpha: 0.12),
                      foregroundColor: AppThemeColors.textPrimary,
                      side: BorderSide(
                          color: AppThemeColors.error.withValues(alpha: 0.5)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                    child: Text("Reject",
                        style: AppTypography.labelSmall
                            .copyWith(fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  ElevatedButton(
                    onPressed: () => _approveRequest(req.id),
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.success.withValues(alpha: 0.15),
                      foregroundColor: AppThemeColors.textPrimary,
                      side: BorderSide(
                          color:
                              AppThemeColors.success.withValues(alpha: 0.45)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                    child: Text("Approve",
                        style: AppTypography.labelSmall
                            .copyWith(fontWeight: FontWeight.w700)),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.xs,
            children: [
              _buildChip("License: ${req.licenseNo}"),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildChip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppThemeColors.secondary.withValues(alpha: 0.18),
        border:
            Border.all(color: AppThemeColors.secondary.withValues(alpha: 0.28)),
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Text(
        text,
        style: AppTypography.labelSmall.copyWith(
          color: AppThemeColors.textPrimary.withValues(alpha: 0.88),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // CHANGE REQUESTS SECTION
  // ---------------------------------------------------------------------------
  Widget _buildChangeRequestsSection() {
    final pendingCount = _changeRequests.where((r) {
      final status = (r['status'] ?? 'pending').toString().trim().toLowerCase();
      return status == 'pending';
    }).length;
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  IconButton(
                    onPressed: () => _switchSection(DriverSection.main),
                    icon: const Icon(Icons.arrow_back_ios_new,
                        color: AppThemeColors.textPrimary, size: 18),
                    tooltip: "Back to Main",
                  ),
                  const SizedBox(width: 4),
                  Text(
                    "Profile Change Requests",
                    style: AppTypography.titleSmall
                        .copyWith(color: AppThemeColors.textPrimary),
                  ),
                ],
              ),
              Text(
                "$pendingCount pending / ${_changeRequests.length} total",
                style: AppTypography.labelSmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          if (_changeRequests.isEmpty)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Text(
                "No pending profile changes.",
                style: TextStyle(color: AppThemeColors.textTertiary),
              ),
            )
          else
            ..._changeRequests
                .map((req) => _buildChangeRequestCard(req))
                .toList(),
        ],
      ),
    );
  }

  Widget _buildChangeRequestCard(Map<String, dynamic> req) {
    final id =
        req['id'] is int ? req['id'] as int : int.tryParse('${req['id']}') ?? 0;
    final status = (req['status'] ?? 'pending').toString().trim().toLowerCase();
    final isPending = status == 'pending';
    final currentName = (req['current_name'] ?? '').toString().trim();
    final proposedName = (req['name'] ?? '').toString().trim();
    final currentMobile = (req['current_mobile'] ?? '').toString().trim();
    final proposedMobile = (req['mobile'] ?? '').toString().trim();
    final currentCab =
        (req['current_cab_no'] ?? req['current_vehicle_no'] ?? '')
            .toString()
            .trim();
    final proposedCab =
        (req['cab_no'] ?? req['vehicle_no'] ?? '').toString().trim();
    final proposedTown =
        (req['home_town'] ?? req['hometown'] ?? '').toString().trim();
    final proposedLat = _asDouble(
      req['home_lat'] ?? req['hometown_lat'] ?? req['lat'],
    );
    final proposedLng = _asDouble(
      req['home_lng'] ?? req['hometown_lng'] ?? req['lng'],
    );
    final coordLabel = _formatCoord(proposedLat, proposedLng);

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlassHover,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Driver: ${currentName.isEmpty ? 'Unknown' : currentName}",
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (currentCab.isNotEmpty)
                      Text(
                        "Current Vehicle: $currentCab",
                        style: AppTypography.labelSmall
                            .copyWith(color: AppThemeColors.textSecondary),
                      ),
                    Text(
                      "Status: ${status.toUpperCase()}",
                      style: AppTypography.labelSmall.copyWith(
                        color: isPending
                            ? AppThemeColors.warning
                            : AppThemeColors.textTertiary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              Row(
                children: [
                  ElevatedButton(
                    onPressed: (_isLoading || !isPending || id <= 0)
                        ? null
                        : () {
                            _rejectChange(id);
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.error.withValues(alpha: 0.12),
                      foregroundColor: AppThemeColors.textPrimary,
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                    ),
                    child: Text("Reject", style: AppTypography.labelSmall),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  ElevatedButton(
                    onPressed: (_isLoading || !isPending || id <= 0)
                        ? null
                        : () {
                            _approveChange(id);
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.success.withValues(alpha: 0.15),
                      foregroundColor: AppThemeColors.textPrimary,
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                    ),
                    child: Text("Approve", style: AppTypography.labelSmall),
                  ),
                ],
              ),
            ],
          ),
          const Divider(color: AppThemeColors.border),
          _buildChangeRow("Name", currentName, proposedName),
          _buildChangeRow("Mobile", currentMobile, proposedMobile),
          _buildChangeRow("Vehicle No", currentCab, proposedCab),
          _buildChangeRow("Address", null, proposedTown),
          if (coordLabel != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: [
                  Row(
                    children: [
                      SizedBox(
                        width: 80,
                        child: Text(
                          "Map",
                          style: AppTypography.labelSmall
                              .copyWith(color: AppThemeColors.textTertiary),
                        ),
                      ),
                      Expanded(
                        child: Text(
                          "New: $coordLabel",
                          style: AppTypography.bodySmall.copyWith(
                            color: AppThemeColors.success,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () => _showLocationPreview(
                        address: proposedTown,
                        lat: proposedLat!,
                        lng: proposedLng!,
                      ),
                      icon: const Icon(Icons.map_outlined, size: 16),
                      label: const Text("View on Map"),
                    ),
                  ),
                ],
              ),
            ),
          if (!isPending)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                "Action locked: this request is already ${status.toUpperCase()}.",
                style: AppTypography.labelSmall
                    .copyWith(color: AppThemeColors.textTertiary),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildChangeRow(String label, String? current, String? proposed) {
    if (proposed == null || proposed.isEmpty || proposed == current)
      return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textTertiary),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (current != null)
                  Text(
                    "Current: $current",
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.textTertiary,
                      decoration: TextDecoration.lineThrough,
                    ),
                  ),
                Text(
                  "New: $proposed",
                  style: AppTypography.bodySmall.copyWith(
                    color: AppThemeColors.success,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _coordLabel() {
    if (_pickedHomeLat == null || _pickedHomeLng == null) return 'Not selected';
    return '${_pickedHomeLat!.toStringAsFixed(6)}, ${_pickedHomeLng!.toStringAsFixed(6)}';
  }

  Future<void> _openAddMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Set Driver Home Location',
        addressHint: _addressCtrl.text.trim(),
        initialLat: _pickedHomeLat,
        initialLng: _pickedHomeLng,
      ),
    );
    if (selected == null) return;
    if (!mounted) return;
    setState(() {
      _pickedHomeLat = selected.latitude;
      _pickedHomeLng = selected.longitude;
      _addressResolveNote = 'Map location selected';
    });
    await _reverseGeocodeAddSelection();
  }

  Future<void> _reverseGeocodeAddSelection() async {
    final lat = _pickedHomeLat;
    final lng = _pickedHomeLng;
    if (lat == null || lng == null) return;
    if (!mounted) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = 'Saving selected coordinates in address...';
    });
    _addressCtrl.text = '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
    setState(() {
      _addressResolveNote = 'Address set to selected map coordinates';
      _isResolvingAddress = false;
    });
  }

  void _onAddAddressChanged(String value) {
    _addressDebounce?.cancel();
    final text = value.trim();
    if (text.length < 5) {
      if (!mounted) return;
      setState(() {
        _isResolvingAddress = false;
        _addressResolveNote = null;
      });
      return;
    }
    _addressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveAddAddress(text);
    });
  }

  Future<void> _autoResolveAddAddress(String address) async {
    if (!mounted) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = 'Resolving address on map...';
    });
    try {
      final hits = await locationFromAddress(address);
      if (!mounted) return;
      if (hits.isNotEmpty) {
        final loc = hits.first;
        setState(() {
          _pickedHomeLat = loc.latitude;
          _pickedHomeLng = loc.longitude;
          _addressResolveNote = 'Auto-centered from typed address';
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

  // ---------------------------------------------------------------------------
  // ADD SECTION
  // ---------------------------------------------------------------------------
  Widget _buildAddSection() {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  IconButton(
                    onPressed: () {
                      _clearForm();
                      _switchSection(DriverSection.main);
                    },
                    icon: const Icon(Icons.arrow_back_ios_new,
                        color: AppThemeColors.textPrimary, size: 18),
                    tooltip: "Back to Main",
                  ),
                  const SizedBox(width: 4),
                  Text(
                    "Add New Driver",
                    style: AppTypography.titleSmall
                        .copyWith(color: AppThemeColors.textPrimary),
                  ),
                ],
              ),
              Text(
                "All fields required • Mobile must be 10 digits",
                style: AppTypography.labelSmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlassHover,
              border: Border.all(color: AppThemeColors.border),
              borderRadius: BorderRadius.circular(AppRadius.lg),
              boxShadow: AppShadows.card,
            ),
            child: Form(
              key: _addFormKey,
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                          child: _buildField("Driver Name", _nameCtrl,
                              minLength: 2)),
                      const SizedBox(width: 12),
                      Expanded(
                          child: _buildField(
                              "Mobile No. (10 digits)", _mobileCtrl,
                              isDigits: true, exactLength: 10)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                          child: _buildField(
                              "Driving License No.", _licenseCtrl,
                              minLength: 6)),
                      const SizedBox(width: 12),
                      Expanded(
                          child: _buildField("Vehicle No.", _vehicleCtrl,
                              minLength: 6)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _buildVehicleTypeField(),
                  const SizedBox(height: 12),
                  _buildField(
                    "Home Town Address",
                    _addressCtrl,
                    minLength: 5,
                    maxLines: 3,
                    onChanged: _onAddAddressChanged,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Coordinates: ${_coordLabel()}',
                          style: AppTypography.labelSmall
                              .copyWith(color: AppThemeColors.textSecondary),
                        ),
                      ),
                      ElevatedButton.icon(
                        onPressed: _openAddMapPicker,
                        style: ElevatedButton.styleFrom(
                          backgroundColor:
                              AppThemeColors.secondary.withValues(alpha: 0.14),
                          foregroundColor: AppThemeColors.textPrimary,
                          side: BorderSide(
                            color: AppThemeColors.secondary
                                .withValues(alpha: 0.55),
                          ),
                        ),
                        icon: const Icon(Icons.map_outlined, size: 16),
                        label: const Text('Pick on Map'),
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      TextButton(
                        onPressed: (_pickedHomeLat != null &&
                                _pickedHomeLng != null &&
                                !_isResolvingAddress)
                            ? _reverseGeocodeAddSelection
                            : null,
                        child: const Text('Use Coords'),
                      ),
                    ],
                  ),
                  if (_isResolvingAddress || _addressResolveNote != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Row(
                        children: [
                          if (_isResolvingAddress)
                            const SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: AppThemeColors.secondary,
                              ),
                            ),
                          if (_isResolvingAddress)
                            const SizedBox(width: AppSpacing.xs),
                          Expanded(
                            child: Text(
                              _isResolvingAddress
                                  ? 'Resolving address...'
                                  : (_addressResolveNote ?? ''),
                              style: AppTypography.labelSmall.copyWith(
                                color: _addressResolveNote != null &&
                                        _addressResolveNote!
                                            .toLowerCase()
                                            .contains('failed')
                                    ? AppThemeColors.warning
                                    : AppThemeColors.textTertiary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 18),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: _clearForm,
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.md,
                              vertical: AppSpacing.sm),
                        ),
                        child: Text(
                          "Reset",
                          style: TextStyle(color: AppThemeColors.textPrimary),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      ElevatedButton(
                        onPressed: _isLoading ? null : _createDriver,
                        style: ElevatedButton.styleFrom(
                          backgroundColor:
                              AppThemeColors.secondary.withValues(alpha: 0.14),
                          foregroundColor: AppThemeColors.textPrimary,
                          side: BorderSide(
                              color: AppThemeColors.secondary
                                  .withValues(alpha: 0.55)),
                          padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.md,
                              vertical: AppSpacing.sm),
                          shape: RoundedRectangleBorder(
                              borderRadius:
                                  BorderRadius.circular(AppRadius.md)),
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppThemeColors.textPrimary),
                              )
                            : Text("Add Driver (Save to DB)",
                                style: AppTypography.labelSmall
                                    .copyWith(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildField(
    String label,
    TextEditingController controller, {
    int? minLength,
    bool isDigits = false,
    int? exactLength,
    int maxLines = 1,
    ValueChanged<String>? onChanged,
  }) {
    return TextFormField(
      controller: controller,
      maxLines: maxLines,
      keyboardType: isDigits ? TextInputType.number : TextInputType.text,
      onChanged: onChanged,
      style: const TextStyle(color: AppThemeColors.textPrimary),
      validator: (value) {
        final v = value?.trim() ?? "";
        if (v.isEmpty) return "$label is required";
        if (minLength != null && v.length < minLength)
          return "Min $minLength chars";
        if (isDigits && int.tryParse(v) == null) return "Digits only";
        if (exactLength != null && v.length != exactLength)
          return "Must be exactly $exactLength digits";
        return null;
      },
      decoration: InputDecoration(
        labelText: label,
        labelStyle: AppTypography.labelSmall
            .copyWith(color: AppThemeColors.textSecondary),
        filled: true,
        fillColor: AppThemeColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.secondary),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.error),
        ),
        errorStyle:
            AppTypography.labelSmall.copyWith(color: AppThemeColors.error),
        contentPadding: const EdgeInsets.all(AppSpacing.sm),
      ),
    );
  }

  double? _asDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString().trim());
  }

  String? _formatCoord(double? lat, double? lng) {
    if (lat == null || lng == null) return null;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
    return "${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}";
  }

  Future<void> _showLocationPreview({
    required String address,
    required double lat,
    required double lng,
  }) async {
    final center = LatLng(lat, lng);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        height: MediaQuery.of(context).size.height * 0.78,
        decoration: const BoxDecoration(
          color: AppThemeColors.surface,
          borderRadius:
              BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
        ),
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Requested Location",
                          style: AppTypography.titleMedium
                              .copyWith(color: AppThemeColors.textPrimary),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          address.isEmpty
                              ? "${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}"
                              : address,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AppTypography.labelSmall
                              .copyWith(color: AppThemeColors.textSecondary),
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
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: FlutterMap(
                    options: MapOptions(
                      initialCenter: center,
                      initialZoom: 14,
                      interactionOptions: const InteractionOptions(
                        flags: InteractiveFlag.pinchZoom |
                            InteractiveFlag.drag |
                            InteractiveFlag.doubleTapZoom,
                      ),
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                        subdomains: const ["a", "b", "c", "d"],
                        userAgentPackageName: "com.rgtravel.app",
                      ),
                      TileLayer(
                        urlTemplate:
                            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                        subdomains: const ["a", "b", "c"],
                        userAgentPackageName: "com.rgtravel.app",
                      ),
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: center,
                            width: 44,
                            height: 44,
                            child: const Icon(
                              Icons.location_pin,
                              color: AppThemeColors.error,
                              size: 40,
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
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      "Lat/Lng: ${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}",
                      style: AppTypography.labelSmall
                          .copyWith(color: AppThemeColors.textSecondary),
                    ),
                  ),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text("Close"),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVehicleTypeField() {
    return DropdownButtonFormField<int>(
      // Warning fix: keep controlled dropdown behavior; `initialValue` would not track later state changes safely here.
      // ignore: deprecated_member_use
      value: _selectedVehicleType,
      dropdownColor: AppThemeColors.surface,
      style: const TextStyle(color: AppThemeColors.textPrimary),
      decoration: InputDecoration(
        labelText: "Vehicle Type",
        labelStyle: AppTypography.labelSmall
            .copyWith(color: AppThemeColors.textSecondary),
        filled: true,
        fillColor: AppThemeColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.secondary),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.error),
        ),
        errorStyle:
            AppTypography.labelSmall.copyWith(color: AppThemeColors.error),
        contentPadding: const EdgeInsets.all(AppSpacing.sm),
      ),
      items: const [
        DropdownMenuItem<int>(value: 4, child: Text("4 Seater")),
        DropdownMenuItem<int>(value: 6, child: Text("6 Seater")),
      ],
      onChanged: (value) {
        if (value == null) return;
        setState(() => _selectedVehicleType = value);
      },
      validator: (value) {
        if (value == null) return "Vehicle Type is required";
        return null;
      },
    );
  }

  // ---------------------------------------------------------------------------
  // LIST SECTION
  // ---------------------------------------------------------------------------
  Widget _buildListSection() {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  IconButton(
                    onPressed: () => _switchSection(DriverSection.main),
                    icon: const Icon(Icons.arrow_back_ios_new,
                        color: AppThemeColors.textPrimary, size: 18),
                    tooltip: "Back to Main",
                  ),
                  const SizedBox(width: 4),
                  Text(
                    "All Driver List",
                    style: AppTypography.titleSmall
                        .copyWith(color: AppThemeColors.textPrimary),
                  ),
                ],
              ),
              Text(
                "${_filteredDrivers.length} driver(s)",
                style: AppTypography.labelSmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  style: const TextStyle(color: AppThemeColors.textPrimary),
                  decoration: InputDecoration(
                    hintText:
                        "Search like: 'Rahul MH12' or 'pune driver' or 'license 123'...",
                    hintStyle: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textTertiary),
                    filled: true,
                    fillColor: AppThemeColors.surface,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      borderSide:
                          const BorderSide(color: AppThemeColors.border),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      borderSide:
                          const BorderSide(color: AppThemeColors.border),
                    ),
                    contentPadding: const EdgeInsets.all(AppSpacing.sm),
                  ),
                  onSubmitted: (v) => _searchDriversBackend(v),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              ElevatedButton(
                onPressed: () => _searchDriversBackend(_searchController.text),
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      AppThemeColors.warning.withValues(alpha: 0.12),
                  foregroundColor: AppThemeColors.textPrimary,
                  side: BorderSide(
                      color: AppThemeColors.warning.withValues(alpha: 0.55)),
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md)),
                ),
                child: Text("Search",
                    style: AppTypography.labelSmall
                        .copyWith(fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: AppSpacing.xs),
              ElevatedButton(
                onPressed: () {
                  _searchController.clear();
                  _filterDrivers();
                  setState(() {});
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      AppThemeColors.background.withValues(alpha: 0.18),
                  foregroundColor: AppThemeColors.textPrimary,
                  side: const BorderSide(color: AppThemeColors.border),
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md)),
                ),
                child: Text("Clear",
                    style: AppTypography.labelSmall
                        .copyWith(fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Container(
            padding: const EdgeInsets.all(AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(AppRadius.full),
            ),
            child: Text(
              "NLP Search: matches name, vehicle, license, mobile, hometown",
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          if (_filteredDrivers.isEmpty)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Text(
                "No drivers found.",
                style: TextStyle(color: AppThemeColors.textTertiary),
              ),
            )
          else
            ..._filteredDrivers
                .map((driver) => _buildDriverCard(driver))
                .toList(),
        ],
      ),
    );
  }

  Widget _buildDriverCard(Driver driver) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlassHover,
        border: Border.all(color: AppThemeColors.border),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      driver.name,
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      "Vehicle: ${driver.vehicleNo} • Mobile: ${driver.mobile}",
                      style: AppTypography.labelSmall
                          .copyWith(color: AppThemeColors.textSecondary),
                    ),
                  ],
                ),
              ),
              ElevatedButton(
                onPressed: () => _showDriverDetails(driver),
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      AppThemeColors.secondary.withValues(alpha: 0.14),
                  foregroundColor: AppThemeColors.textPrimary,
                  side: BorderSide(
                      color: AppThemeColors.secondary.withValues(alpha: 0.55)),
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md)),
                ),
                child: Text("Show Details",
                    style: AppTypography.labelSmall
                        .copyWith(fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.xs,
            children: [
              _buildChip("License: ${driver.licenseNo}"),
              _buildChip("Home: ${_shorten(driver.hometownAddress, 32)}"),
            ],
          ),
        ],
      ),
    );
  }

  String _shorten(String text, int maxLen) {
    if (text.length <= maxLen) return text;
    return "${text.substring(0, maxLen - 1)}…";
  }
}

// =============================================================================
// EDIT MODAL WIDGET
// =============================================================================

class _EditDriverModal extends StatefulWidget {
  final Driver driver;
  final void Function(Driver) onUpdate;
  final void Function(String) onDelete;

  const _EditDriverModal({
    required this.driver,
    required this.onUpdate,
    required this.onDelete,
  });

  @override
  State<_EditDriverModal> createState() => _EditDriverModalState();
}

class _EditDriverModalState extends State<_EditDriverModal> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameCtrl;
  late TextEditingController _mobileCtrl;
  late TextEditingController _licenseCtrl;
  late TextEditingController _vehicleCtrl;
  late TextEditingController _addressCtrl;
  late int _selectedVehicleType;
  Timer? _addressDebounce;
  bool _isResolvingAddress = false;
  String? _addressResolveNote;
  double? _pickedHomeLat;
  double? _pickedHomeLng;

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.driver.name);
    _mobileCtrl = TextEditingController(text: widget.driver.mobile);
    _licenseCtrl = TextEditingController(text: widget.driver.licenseNo);
    _vehicleCtrl = TextEditingController(text: widget.driver.vehicleNo);
    _addressCtrl = TextEditingController(text: widget.driver.hometownAddress);
    _selectedVehicleType = widget.driver.vehicleType;
    _pickedHomeLat = widget.driver.homeLat;
    _pickedHomeLng = widget.driver.homeLng;
  }

  @override
  void dispose() {
    _addressDebounce?.cancel();
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _licenseCtrl.dispose();
    _vehicleCtrl.dispose();
    _addressCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      final homeTown = _addressCtrl.text.trim().isNotEmpty
          ? _addressCtrl.text.trim()
          : ((_pickedHomeLat != null && _pickedHomeLng != null)
              ? '${_pickedHomeLat!.toStringAsFixed(6)}, ${_pickedHomeLng!.toStringAsFixed(6)}'
              : '');
      final updated = Driver(
        id: widget.driver.id,
        name: _nameCtrl.text.trim(),
        mobile: _mobileCtrl.text.trim(),
        dlNo: _licenseCtrl.text.trim(),
        cabNo: _vehicleCtrl.text.trim(),
        homeTown: homeTown,
        vehicleType: _selectedVehicleType,
        homeLat: _pickedHomeLat,
        homeLng: _pickedHomeLng,
      );
      widget.onUpdate(updated);
    }
  }

  String _coordLabel() {
    if (_pickedHomeLat == null || _pickedHomeLng == null) return 'Not selected';
    return '${_pickedHomeLat!.toStringAsFixed(6)}, ${_pickedHomeLng!.toStringAsFixed(6)}';
  }

  Future<void> _openMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Update Driver Home Location',
        addressHint: _addressCtrl.text.trim(),
        initialLat: _pickedHomeLat,
        initialLng: _pickedHomeLng,
      ),
    );
    if (selected == null || !mounted) return;
    setState(() {
      _pickedHomeLat = selected.latitude;
      _pickedHomeLng = selected.longitude;
      _addressResolveNote = 'Map location selected';
    });
    await _reverseGeocodeSelection();
  }

  Future<void> _reverseGeocodeSelection() async {
    final lat = _pickedHomeLat;
    final lng = _pickedHomeLng;
    if (lat == null || lng == null) return;
    if (!mounted) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = 'Saving selected coordinates in address...';
    });
    _addressCtrl.text = '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
    setState(() {
      _addressResolveNote = 'Address set to selected map coordinates';
      _isResolvingAddress = false;
    });
  }

  void _onAddressChanged(String value) {
    _addressDebounce?.cancel();
    final text = value.trim();
    if (text.length < 5) {
      if (!mounted) return;
      setState(() {
        _isResolvingAddress = false;
        _addressResolveNote = null;
      });
      return;
    }
    _addressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveAddress(text);
    });
  }

  Future<void> _autoResolveAddress(String address) async {
    if (!mounted) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = 'Resolving address on map...';
    });
    try {
      final hits = await locationFromAddress(address);
      if (!mounted) return;
      if (hits.isNotEmpty) {
        final loc = hits.first;
        setState(() {
          _pickedHomeLat = loc.latitude;
          _pickedHomeLng = loc.longitude;
          _addressResolveNote = 'Auto-centered from typed address';
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

  void _confirmDelete() {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg)),
        title: Text("Confirm Removal",
            style: AppTypography.titleMedium
                .copyWith(color: AppThemeColors.textPrimary)),
        content: Text(
          "Are you sure you want to remove ${widget.driver.name}? (DB delete)",
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textPrimary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text("Cancel",
                style: AppTypography.labelMedium
                    .copyWith(color: AppThemeColors.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              widget.onDelete(widget.driver.id);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppThemeColors.error.withValues(alpha: 0.12),
              side: BorderSide(
                  color: AppThemeColors.error.withValues(alpha: 0.5)),
            ),
            child: Text("Delete",
                style: AppTypography.labelMedium.copyWith(
                    color: AppThemeColors.error, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
          20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20),
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.92),
        border: Border.all(color: AppThemeColors.border),
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
        boxShadow: AppShadows.elevated,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    "Driver Details: ${widget.driver.name}",
                    style: AppTypography.titleMedium.copyWith(
                      color: AppThemeColors.textPrimary,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close,
                        color: AppThemeColors.textPrimary),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              _buildField("Driver Name", _nameCtrl, minLength: 2),
              const SizedBox(height: AppSpacing.sm),
              _buildField("Mobile No. (10 digits)", _mobileCtrl,
                  isDigits: true, exactLength: 10),
              const SizedBox(height: AppSpacing.sm),
              _buildField("Driving License No.", _licenseCtrl, minLength: 6),
              const SizedBox(height: AppSpacing.sm),
              _buildField("Vehicle No.", _vehicleCtrl, minLength: 6),
              const SizedBox(height: AppSpacing.sm),
              DropdownButtonFormField<int>(
                // Warning fix: keep controlled dropdown behavior; `initialValue` would not track later state changes safely here.
                // ignore: deprecated_member_use
                value: _selectedVehicleType,
                dropdownColor: AppThemeColors.surface,
                style: const TextStyle(color: AppThemeColors.textPrimary),
                decoration: InputDecoration(
                  labelText: "Vehicle Type",
                  labelStyle: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.textSecondary),
                  filled: true,
                  fillColor: AppThemeColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    borderSide: const BorderSide(color: AppThemeColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    borderSide: const BorderSide(color: AppThemeColors.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    borderSide:
                        const BorderSide(color: AppThemeColors.secondary),
                  ),
                  errorBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    borderSide: const BorderSide(color: AppThemeColors.error),
                  ),
                  errorStyle: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.error),
                  contentPadding: const EdgeInsets.all(AppSpacing.sm),
                ),
                items: const [
                  DropdownMenuItem<int>(value: 4, child: Text("4 Seater")),
                  DropdownMenuItem<int>(value: 6, child: Text("6 Seater")),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setState(() => _selectedVehicleType = value);
                },
                validator: (value) {
                  if (value == null) return "Vehicle Type is required";
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.sm),
              _buildField(
                "Home Town Address",
                _addressCtrl,
                minLength: 5,
                maxLines: 3,
                onChanged: _onAddressChanged,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Coordinates: ${_coordLabel()}',
                      style: AppTypography.labelSmall
                          .copyWith(color: AppThemeColors.textSecondary),
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: _openMapPicker,
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.secondary.withValues(alpha: 0.14),
                      foregroundColor: AppThemeColors.textPrimary,
                      side: BorderSide(
                        color: AppThemeColors.secondary.withValues(alpha: 0.55),
                      ),
                    ),
                    icon: const Icon(Icons.map_outlined, size: 16),
                    label: const Text('Pick on Map'),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  TextButton(
                    onPressed: (_pickedHomeLat != null &&
                            _pickedHomeLng != null &&
                            !_isResolvingAddress)
                        ? _reverseGeocodeSelection
                        : null,
                    child: const Text('Use Coords'),
                  ),
                ],
              ),
              if (_isResolvingAddress || _addressResolveNote != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Row(
                    children: [
                      if (_isResolvingAddress)
                        const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: AppThemeColors.secondary,
                          ),
                        ),
                      if (_isResolvingAddress)
                        const SizedBox(width: AppSpacing.xs),
                      Expanded(
                        child: Text(
                          _isResolvingAddress
                              ? 'Resolving address...'
                              : (_addressResolveNote ?? ''),
                          style: AppTypography.labelSmall.copyWith(
                            color: _addressResolveNote != null &&
                                    _addressResolveNote!
                                        .toLowerCase()
                                        .contains('failed')
                                ? AppThemeColors.warning
                                : AppThemeColors.textTertiary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: AppSpacing.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  ElevatedButton(
                    onPressed: _confirmDelete,
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.error.withValues(alpha: 0.12),
                      foregroundColor: AppThemeColors.error,
                      side: BorderSide(
                          color: AppThemeColors.error.withValues(alpha: 0.5)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                    child: Text("Remove Driver (DB)",
                        style: AppTypography.labelSmall
                            .copyWith(fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  ElevatedButton(
                    onPressed: _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.secondary.withValues(alpha: 0.14),
                      foregroundColor: AppThemeColors.textPrimary,
                      side: BorderSide(
                          color:
                              AppThemeColors.secondary.withValues(alpha: 0.55)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                    child: Text("Update Details",
                        style: AppTypography.labelSmall
                            .copyWith(fontWeight: FontWeight.w700)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildField(
    String label,
    TextEditingController controller, {
    int? minLength,
    bool isDigits = false,
    int? exactLength,
    int maxLines = 1,
    ValueChanged<String>? onChanged,
  }) {
    return TextFormField(
      controller: controller,
      maxLines: maxLines,
      keyboardType: isDigits ? TextInputType.number : TextInputType.text,
      onChanged: onChanged,
      style: const TextStyle(color: AppThemeColors.textPrimary),
      validator: (value) {
        final v = value?.trim() ?? "";
        if (v.isEmpty) return "$label is required";
        if (minLength != null && v.length < minLength)
          return "Min $minLength chars";
        if (isDigits && int.tryParse(v) == null) return "Digits only";
        if (exactLength != null && v.length != exactLength)
          return "Must be exactly $exactLength digits";
        return null;
      },
      decoration: InputDecoration(
        labelText: label,
        labelStyle: AppTypography.labelSmall
            .copyWith(color: AppThemeColors.textSecondary),
        filled: true,
        fillColor: AppThemeColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.secondary),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppThemeColors.error),
        ),
        errorStyle:
            AppTypography.labelSmall.copyWith(color: AppThemeColors.error),
        contentPadding: const EdgeInsets.all(AppSpacing.sm),
      ),
    );
  }
}
