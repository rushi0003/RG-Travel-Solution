// lib/screens/admin/admin_dashboard.dart
//
// RG Travel Solution â€” Admin Dashboard (single file)
// ================================================
//
// âœ… Fixes your current runtime issues:
// 1) "Failed to fetch http://10.0.2.2:5000/... on Edge/Web"
//    -> Web/Edge cannot reach 10.0.2.2 (that is Android emulator-only).
//    -> This file auto-switches baseUrl:
//       - Web:  http://127.0.0.1:5000
//       - Mobile/Emulator: http://10.0.2.2:5000
//    (You can override from UI too)
//
// 2) "setState() called after dispose()"
//    -> This file uses safeSetState() + cancels Timers in dispose().
//
// âœ… Admin dashboard features included (as per your logic):
// - Left sidebar profile (avatar, name, mobile, office name, office address)
// - Update profile + Logout
// - Center modules:
//   1) Create group & assign trip (pickup/drop, time, vehicle type 4/6, drivers list, employees list, manual override selection)
//   2) View live trips (with members + cancel/complete)
//   3) Drivers (list + driver requests approve/reject)
//   4) Employees (list + employee requests approve/reject)
//   5) Trip history (basic list + search)
//   6) Live driver tracking (online drivers + location)
//
// âœ… Uses backend APIs (recommended paths):
// - GET/PUT  /api/admin/profile/<adminId>
// - GET      /api/admin/employees
// - GET      /api/admin/drivers
// - GET      /api/admin/driver-requests
// - POST     /api/admin/driver-requests/<id>/approve
// - POST     /api/admin/driver-requests/<id>/reject
// - GET      /api/admin/employee-requests
// - POST     /api/admin/employee-requests/<id>/approve
// - POST     /api/admin/employee-requests/<id>/reject
// - POST     /api/admin/groups/create-and-assign
// - GET      /api/admin/trips/live
// - GET      /api/admin/trips
// - POST     /api/admin/trips/<id>/cancel
// - POST     /api/admin/trips/<id>/complete
// - GET      /api/admin/drivers/online
// - GET      /api/admin/routes/<route_no>/driver-location
//
// Dependencies (pubspec.yaml):
//   http: ^1.2.2
//
// ------------------------------------------------------------

import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/storage/session_store.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/core/utils/constants.dart';
import 'package:rg_travel_flutter/core/services/api_service.dart';
import 'package:rg_travel_flutter/screens/admin/drivers_screen.dart';
import 'package:rg_travel_flutter/screens/admin/employees_screen.dart';
import 'package:rg_travel_flutter/screens/admin/create_group_assign_screen.dart';
import 'package:rg_travel_flutter/screens/admin/live_trips_screen.dart';
import 'package:rg_travel_flutter/screens/admin/live_tracking_screen.dart';
import 'package:rg_travel_flutter/screens/admin/trip_history_screen.dart';
import 'package:rg_travel_flutter/screens/admin/admin_billing_screen.dart';
import 'package:rg_travel_flutter/screens/admin/admin_sos_screen.dart';
import 'package:rg_travel_flutter/screens/admin/admin_notifications_screen.dart';
import 'package:rg_travel_flutter/screens/admin/admin_helpdesk_screen.dart';
import 'package:rg_travel_flutter/widgets/common/map_coordinate_picker_sheet.dart';
import 'package:latlong2/latlong.dart';
// ... (existing imports)

class AdminDashboard extends StatefulWidget {
  final String adminId;

  const AdminDashboard({super.key, required this.adminId});

  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

enum AdminSection {
  createGroupAssign,
  liveTrips,
  drivers,
  employees,
  tripHistory,
  billing,
  liveTracking,
  helpdesk,
  sos, // SOS Alerts
}

class _AdminDashboardState extends State<AdminDashboard> {
  // -----------------------
  // Base URL handling
  // -----------------------
  late String _baseUrl;
  final _baseUrlCtrl = TextEditingController();

  // -----------------------
  // UI state
  // -----------------------
  AdminSection _section = AdminSection.createGroupAssign;
  bool _loading = false;
  String? _error;

  // Sidebar profile
  Map<String, dynamic>? _adminProfile;

  // Legacy inline dashboard state was removed after these sections were split
  // into dedicated screens. This shell keeps only actively used state.

  // Simple â€œNLP-likeâ€ search (fuzzy contains)
  final _driverSearchCtrl = TextEditingController();
  final _employeeSearchCtrl = TextEditingController();
  final _tripSearchCtrl = TextEditingController();

  // Admin profile update controllers
  final _adminNameCtrl = TextEditingController();
  final _adminMobileCtrl = TextEditingController();
  final _officeNameCtrl = TextEditingController();
  final _officeAddrCtrl = TextEditingController();
  final _officeLatCtrl = TextEditingController();
  final _officeLngCtrl = TextEditingController();

  // Driver form controllers
  final _driverNameCtrl = TextEditingController();
  final _driverMobileCtrl = TextEditingController();
  final _driverLicenseCtrl = TextEditingController();
  final _driverVehicleCtrl = TextEditingController();
  final _driverHometownCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();

    _baseUrl = kIsWeb ? "http://127.0.0.1:5000" : "http://10.0.2.2:5000";
    _baseUrlCtrl.text = _baseUrl;

    _bootstrap();
  }

  @override
  void dispose() {
    _baseUrlCtrl.dispose();
    _driverSearchCtrl.dispose();
    _employeeSearchCtrl.dispose();
    _tripSearchCtrl.dispose();

    _adminNameCtrl.dispose();
    _adminMobileCtrl.dispose();
    _officeNameCtrl.dispose();
    _officeAddrCtrl.dispose();
    _officeLatCtrl.dispose();
    _officeLngCtrl.dispose();

    _driverNameCtrl.dispose();
    _driverMobileCtrl.dispose();
    _driverLicenseCtrl.dispose();
    _driverVehicleCtrl.dispose();
    _driverHometownCtrl.dispose();

    super.dispose();
  }

  // =========================
  // Safe setState
  // =========================
  void safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  // =========================
  // Bootstrap load
  // =========================
  Future<void> _bootstrap() async {
    safeSetState(() {
      _loading = true;
      _error = null;
    });

    try {
      await _fetchAdminProfile();
    } catch (e) {
      safeSetState(() => _error = "Bootstrap failed: $e");
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  // =========================
  // HTTP client helpers
  // =========================
  // Delegate HTTP calls to ApiService for logging and status mapping centrally.
  Future<Map<String, dynamic>> _getJson(String path) async {
    return await ApiService.getJson(path);
  }

  Future<Map<String, dynamic>> _putJson(
      String path, Map<String, dynamic> payload) async {
    return await ApiService.putJson(path, payload);
  }

  Future<Map<String, dynamic>> _getAdminProfileJson() async {
    final numericAdminId = _normalizeAdminIdToIntString(widget.adminId);
    final paths = (numericAdminId != null)
        ? [
            "/api/admin/${widget.adminId}",
            "/api/admin/$numericAdminId/profile",
            "/api/admin/profile/$numericAdminId",
          ]
        : [
            "/api/admin/${widget.adminId}",
          ];
    Object? lastError;
    for (final p in paths) {
      try {
        return await _getJson(p);
      } catch (e) {
        lastError = e;
      }
    }
    throw Exception("Failed to load admin profile: $lastError");
  }

  Future<Map<String, dynamic>> _putAdminProfileJson(
      Map<String, dynamic> payload) async {
    final numericAdminId = _normalizeAdminIdToIntString(widget.adminId);
    final paths = (numericAdminId != null)
        ? [
            "/api/admin/${widget.adminId}",
            "/api/admin/$numericAdminId/profile",
            "/api/admin/profile/$numericAdminId",
          ]
        : [
            "/api/admin/${widget.adminId}",
          ];
    Object? lastError;
    for (final p in paths) {
      try {
        return await _putJson(p, payload);
      } catch (e) {
        lastError = e;
      }
    }
    throw Exception("Failed to update admin profile: $lastError");
  }

  String? _normalizeAdminIdToIntString(String raw) {
    final direct = int.tryParse(raw);
    if (direct != null) return direct.toString();
    final tailDigits = RegExp(r'(\d+)$').firstMatch(raw)?.group(1);
    if (tailDigits == null) return null;
    final parsed = int.tryParse(tailDigits);
    return parsed?.toString();
  }

  // =========================
  // Fetch functions
  // =========================
  Future<void> _fetchAdminProfile() async {
    // If your backend uses /admin/profile instead, switch here.
    // Call backend path: /api/admin/<id> as implemented on server
    final res = await _getAdminProfileJson();
    final data = (res["data"] as Map?)?.cast<String, dynamic>() ?? {};

    safeSetState(() {
      _adminProfile = data;

      _adminNameCtrl.text = (data["name"] ?? "").toString();
      _adminMobileCtrl.text = (data["mobile"] ?? "").toString();
      _officeNameCtrl.text = (data["office_name"] ?? "").toString();
      _officeAddrCtrl.text =
          (data["office_address"] ?? data["office_location"] ?? "").toString();
      _officeLatCtrl.text = (data["office_lat"] ?? "").toString();
      _officeLngCtrl.text = (data["office_lng"] ?? "").toString();
    });
  }

  // =========================
  // Actions
  // =========================
  Future<void> _saveAdminProfile() async {
    final officeLat = double.tryParse(_officeLatCtrl.text.trim());
    final officeLng = double.tryParse(_officeLngCtrl.text.trim());
    final officeAddress = _officeAddrCtrl.text.trim();
    final officeLocation = (officeLat != null && officeLng != null)
        ? "${officeLat.toStringAsFixed(6)},${officeLng.toStringAsFixed(6)}"
        : officeAddress;
    final payload = {
      "name": _adminNameCtrl.text.trim(),
      "mobile": _adminMobileCtrl.text.trim(),
      "office_name": _officeNameCtrl.text.trim(),
      "office_address": officeAddress,
      "office_location": officeLocation,
      if (officeLat != null) "office_lat": officeLat,
      if (officeLng != null) "office_lng": officeLng,
    };

    try {
      safeSetState(() => _loading = true);
      await _putAdminProfileJson(payload);
      await _fetchAdminProfile();
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text("Profile updated")));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text("Update failed: $e")));
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  String _officeCoordLabel() {
    final lat = double.tryParse(_officeLatCtrl.text.trim());
    final lng = double.tryParse(_officeLngCtrl.text.trim());
    if (lat == null || lng == null) return "Not selected";
    return "${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}";
  }

  Future<void> _pickOfficeLocationOnMap() async {
    final initialLat = double.tryParse(_officeLatCtrl.text.trim());
    final initialLng = double.tryParse(_officeLngCtrl.text.trim());

    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: "Set Office Location",
        addressHint: _officeAddrCtrl.text.trim(),
        initialLat: initialLat,
        initialLng: initialLng,
      ),
    );

    if (selected == null || !mounted) return;
    final lat = selected.latitude;
    final lng = selected.longitude;
    if (!mounted) return;
    safeSetState(() {
      _officeAddrCtrl.text = "${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}";
      _officeLatCtrl.text = selected.latitude.toStringAsFixed(6);
      _officeLngCtrl.text = selected.longitude.toStringAsFixed(6);
    });
  }

  // =========================
  // UI helpers
  // =========================
  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  // =========================
  // BUILD
  // =========================
  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isDesktop = width >= 1100;
    final isCompact = width < 900;

    if (isDesktop) {
      return Scaffold(
        backgroundColor: AppThemeColors.background,
        body: SafeArea(
          child: Row(
            children: [
              SizedBox(
                width: 320,
                child: _buildSidebar(context),
              ),
              Expanded(
                child: Column(
                  children: [
                    _buildTopBar(context, compact: false),
                    Expanded(
                      child: _buildBody(context),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      drawer: Drawer(
        width: isCompact ? width * 0.88 : 340,
        backgroundColor: Colors.transparent,
        child: SafeArea(child: _buildSidebar(context)),
      ),
      body: SafeArea(
        child: Column(
          children: [
            _buildTopBar(context, compact: true),
            _buildMobileQuickNav(),
            Expanded(child: _buildBody(context)),
          ],
        ),
      ),
    );
  }

  Widget _buildMobileQuickNav() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, 10, AppSpacing.md, 8),
      decoration: BoxDecoration(
        color: AppThemeColors.background,
        border: Border(
          bottom: BorderSide(color: AppThemeColors.border),
        ),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            _mobileNavChip(
                AdminSection.createGroupAssign, Icons.groups, "Groups"),
            _mobileNavChip(
                AdminSection.liveTrips, Icons.local_taxi, "Live Trips"),
            _mobileNavChip(AdminSection.drivers, Icons.badge, "Drivers"),
            _mobileNavChip(AdminSection.employees, Icons.people, "Employees"),
            _mobileNavChip(AdminSection.tripHistory, Icons.history, "History"),
            _mobileNavChip(AdminSection.billing, Icons.receipt_long, "Billing"),
            _mobileNavChip(
                AdminSection.liveTracking, Icons.location_on, "Tracking"),
            _mobileNavChip(AdminSection.helpdesk, Icons.support_agent, "Help"),
          ],
        ),
      ),
    );
  }

  Widget _mobileNavChip(AdminSection section, IconData icon, String label) {
    final active = _section == section;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.full),
        onTap: () async => _changeSection(section),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: active
                ? AppThemeColors.cardGlassActive
                : AppThemeColors.cardGlass,
            borderRadius: BorderRadius.circular(AppRadius.full),
            border: Border.all(
              color: active
                  ? AppThemeColors.cardGlassActive
                  : AppThemeColors.border,
            ),
          ),
          child: Row(
            children: [
              Icon(icon, size: 15, color: AppThemeColors.textPrimary),
              const SizedBox(width: 6),
              Text(
                label,
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textPrimary,
                  fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSidebar(BuildContext context) {
    final prof = _adminProfile ?? {};
    final name = (prof["name"] ?? "Admin").toString();
    final mobile = (prof["mobile"] ?? "").toString();
    final office = (prof["office_name"] ?? "").toString();
    final addr = (prof["office_address"] ?? "").toString();

    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.surface,
        border: Border(
          right: BorderSide(color: AppThemeColors.border),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Avatar + name
            Row(
              children: [
                CircleAvatar(
                  radius: 26,
                  backgroundColor: AppThemeColors.cardGlassActive,
                  child: const Icon(Icons.admin_panel_settings,
                      color: AppThemeColors.textPrimary),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyLarge.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            _miniInfo("Mobile", mobile.isEmpty ? "â€”" : mobile),
            _miniInfo("Office", office.isEmpty ? "â€”" : office),
            _miniInfo("Address", addr.isEmpty ? "â€”" : addr),

            const SizedBox(height: AppSpacing.md),

            // Update profile + logout
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _openProfileSheet(context),
                    icon: const Icon(Icons.edit, size: AppIconSizes.sm),
                    label: const Text("Update Profile"),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                IconButton(
                  onPressed: _logout,
                  icon: const Icon(Icons.logout,
                      color: AppThemeColors.textPrimary),
                  tooltip: "Logout",
                ),
              ],
            ),

            const SizedBox(height: AppSpacing.md),
            Text(
              "Modules",
              style: AppTypography.labelLarge.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),

            Expanded(
              child: ListView(
                children: [
                  _navItem(AdminSection.createGroupAssign, Icons.groups,
                      "Create Group & Assign Trip"),
                  _navItem(AdminSection.liveTrips, Icons.local_taxi,
                      "View Live Trip"),
                  _navItem(AdminSection.drivers, Icons.badge, "Driver"),
                  _navItem(AdminSection.employees, Icons.people, "Employee"),
                  _navItem(
                      AdminSection.tripHistory, Icons.history, "Trip History"),
                  _navItem(AdminSection.billing, Icons.receipt_long, "Billing"),
                  _navItem(AdminSection.liveTracking, Icons.location_on,
                      "Live Driver Tracking"),
                  _navItem(
                      AdminSection.helpdesk, Icons.support_agent, "Help Desk"),
                ],
              ),
            ),

            const SizedBox(height: AppSpacing.sm),
            Text(
              "Backend Base URL",
              style: AppTypography.labelSmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _baseUrlCtrl,
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textPrimary),
              decoration: InputDecoration(
                filled: true,
                fillColor: AppThemeColors.cardGlass,
                hintText: "http://127.0.0.1:5000",
                hintStyle: AppTypography.labelSmall
                    .copyWith(color: AppThemeColors.textTertiary),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                    borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm, vertical: AppSpacing.sm),
              ),
              onSubmitted: (v) async {
                final nv = v.trim();
                if (nv.isEmpty) return;
                safeSetState(() {
                  _baseUrl = nv;
                });
                _toast("Base URL set to: $_baseUrl");
                await _bootstrap();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _miniInfo(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 64,
            child: Text(
              "$k:",
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textTertiary),
            ),
          ),
          Expanded(
            child: Text(
              v,
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _changeSection(AdminSection s) async {
    safeSetState(() {
      _section = s;
      _error = null;
    });
  }

  Future<void> _logout() async {
    await SessionStore.clear();
    if (!mounted) return;
    unawaited(Navigator.of(context).pushReplacementNamed(AppRoutes.login));
  }

  Widget _navItem(AdminSection s, IconData icon, String label) {
    final active = _section == s;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: () async => _changeSection(s),
        child: AnimatedContainer(
          duration: AppAnimations.fast,
          curve: AppAnimations.defaultCurve,
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md, vertical: AppSpacing.md),
          decoration: BoxDecoration(
            color: active
                ? AppThemeColors.cardGlassActive
                : AppThemeColors.cardGlass,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(
                color: active
                    ? AppThemeColors.cardGlassActive
                    : AppThemeColors.border),
          ),
          child: Row(
            children: [
              Icon(icon,
                  color: AppThemeColors.textPrimary, size: AppIconSizes.sm),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  label,
                  style: AppTypography.labelSmall.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: active ? FontWeight.w700 : FontWeight.w600,
                  ),
                ),
              ),
              if (active)
                Icon(Icons.chevron_right,
                    color: AppThemeColors.textSecondary, size: AppIconSizes.sm),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context, {required bool compact}) {
    return Container(
      height: compact ? 60 : 56,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.background,
        border: Border(
          bottom: BorderSide(color: AppThemeColors.border),
        ),
      ),
      child: Row(
        children: [
          if (compact)
            Builder(
              builder: (ctx) => IconButton(
                onPressed: () => Scaffold.of(ctx).openDrawer(),
                tooltip: "Menu",
                icon: const Icon(Icons.menu, color: AppThemeColors.textPrimary),
              ),
            ),
          Expanded(
            child: Text(
              "RG Travel Solution Admin",
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.bodyLarge.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          if (_loading)
            const SizedBox(
              width: AppIconSizes.sm,
              height: AppIconSizes.sm,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          const SizedBox(width: AppSpacing.md),
          IconButton(
            onPressed: () => Navigator.push(
              context,
              // Warning fix: add explicit route type to satisfy strict inference.
              MaterialPageRoute<void>(
                  builder: (_) => const AdminNotificationsScreen()),
            ),
            tooltip: "Notifications",
            icon: const Icon(Icons.notifications,
                color: AppThemeColors.textPrimary),
          ),
          const SizedBox(width: AppSpacing.sm),
          IconButton(
            onPressed: _bootstrap,
            tooltip: "Refresh",
            icon: const Icon(Icons.refresh, color: AppThemeColors.textPrimary),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Text(
            _error!,
            style:
                AppTypography.bodyMedium.copyWith(color: AppThemeColors.error),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    switch (_section) {
      case AdminSection.createGroupAssign:
        return _buildCreateGroupAssign(context);
      case AdminSection.liveTrips:
        return _buildLiveTrips(context);
      case AdminSection.drivers:
        return _buildDrivers(context);
      case AdminSection.employees:
        return _buildEmployees(context);
      case AdminSection.tripHistory:
        return _buildTripHistory(context);
      case AdminSection.billing:
        return _buildBilling(context);
      case AdminSection.liveTracking:
        return _buildLiveTracking(context);
      case AdminSection.helpdesk:
        return _buildHelpdesk(context);
      case AdminSection.sos:
        return const AdminSOSScreen();
    }
  }

  // =========================================================
  // Section 1: Create group & assign trip
  // =========================================================
  // =========================================================
  // Section 1: Create group & assign trip
  // =========================================================
  Widget _buildCreateGroupAssign(BuildContext context) {
    return CreateGroupAssignScreen(adminId: widget.adminId);
  }

  // =========================================================
  // Section 2: Live Trips
  // =========================================================
  Widget _buildLiveTrips(BuildContext context) {
    return LiveTripsScreen(adminId: widget.adminId);
  }

  // =========================================================
  // Section 3: Drivers (3-Button Interface with Premium Design)
  // =========================================================
  Widget _buildDrivers(BuildContext context) {
    // Use the dedicated DriversScreen widget for all driver management
    return const DriversScreen();
  }

  // =========================================================
  // Section 4: Employees
  // =========================================================
  Widget _buildEmployees(BuildContext context) {
    return EmployeesScreen(adminId: widget.adminId);
  }

  // =========================================================
  // Section 5: Trip History
  // =========================================================
  Widget _buildTripHistory(BuildContext context) {
    return TripHistoryScreen(
      adminId: widget.adminId,
      embedded: true,
    );
  }

  Widget _buildBilling(BuildContext context) {
    return AdminBillingScreen(
      adminId: widget.adminId,
      embedded: true,
    );
  }

  // =========================================================
  // Section 6: Live Driver Tracking
  // =========================================================
  // =========================================================
  // Section 6: Live Driver Tracking
  // =========================================================
  Widget _buildLiveTracking(BuildContext context) {
    return LiveTrackingScreen(adminId: widget.adminId);
  }

  Widget _buildHelpdesk(BuildContext context) {
    return const AdminHelpDeskScreen();
  }

  // =========================================================
  // Profile sheet
  // =========================================================
  void _openProfileSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppThemeColors.surface,
      isScrollControlled: true,
      builder: (_) {
        return Padding(
          padding: EdgeInsets.only(
            left: AppSpacing.md,
            right: AppSpacing.md,
            top: AppSpacing.md,
            bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.md,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                  width: 46,
                  height: 5,
                  decoration: BoxDecoration(
                      color: AppThemeColors.border,
                      borderRadius: BorderRadius.circular(AppRadius.full))),
              const SizedBox(height: AppSpacing.md),
              Text("Update Admin Profile",
                  style: AppTypography.bodyLarge.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  )),
              const SizedBox(height: AppSpacing.md),
              _field(_adminNameCtrl, "Name"),
              const SizedBox(height: AppSpacing.sm),
              _field(_adminMobileCtrl, "Mobile (10 digits)",
                  keyboard: TextInputType.phone),
              const SizedBox(height: AppSpacing.sm),
              _field(_officeNameCtrl, "Office Name"),
              const SizedBox(height: AppSpacing.sm),
              _field(_officeAddrCtrl, "Office Address", maxLines: 2),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _pickOfficeLocationOnMap,
                      icon: const Icon(Icons.map_outlined),
                      label: const Text("Set on Map"),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  "Office Coordinates: ${_officeCoordLabel()}",
                  style: AppTypography.bodySmall
                      .copyWith(color: AppThemeColors.textSecondary),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text("Close"),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: FilledButton(
                      onPressed: () async {
                        Navigator.pop(context);
                        await _saveAdminProfile();
                      },
                      child: const Text("Save"),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
          ),
        );
      },
    );
  }

  // =========================================================
  // Widgets
  // =========================================================
  Widget _field(TextEditingController ctrl, String label,
      {TextInputType? keyboard, int maxLines = 1}) {
    return TextField(
      controller: ctrl,
      maxLines: maxLines,
      keyboardType: keyboard,
      style:
          AppTypography.bodyMedium.copyWith(color: AppThemeColors.textPrimary),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: AppTypography.labelMedium
            .copyWith(color: AppThemeColors.textSecondary),
        filled: true,
        fillColor: AppThemeColors.cardGlass,
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            borderSide: BorderSide.none),
      ),
    );
  }

}

// A tiny widget to track driver location for a route number.
// (You can later replace this with Google Map widget + marker animation.)
class _RouteTrackWidget extends StatefulWidget {
  final String baseUrl;
  final Future<Map<String, dynamic>> Function(String path) getJson;

  const _RouteTrackWidget({required this.baseUrl, required this.getJson});

  @override
  State<_RouteTrackWidget> createState() => _RouteTrackWidgetState();
}

class _RouteTrackWidgetState extends State<_RouteTrackWidget> {
  final _routeCtrl = TextEditingController();
  bool _loading = false;
  String? _msg;
  Map<String, dynamic>? _loc;

  @override
  void dispose() {
    _routeCtrl.dispose();
    super.dispose();
  }

  Future<void> _track() async {
    final rn = _routeCtrl.text.trim();
    if (rn.isEmpty) return;

    setState(() {
      _loading = true;
      _msg = null;
      _loc = null;
    });

    try {
      final res = await widget.getJson("/api/admin/routes/$rn/driver-location");
      final data = (res["data"] as Map?)?.cast<String, dynamic>() ?? {};
      setState(() {
        _loc = data;
        _msg = "OK";
      });
    } catch (e) {
      setState(() {
        _msg = "Failed: $e";
      });
    } finally {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final lat = _loc?["lat"];
    final lng = _loc?["lng"];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _routeCtrl,
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textPrimary),
          decoration: InputDecoration(
            hintText: "Enter route number (10 chars)",
            hintStyle: AppTypography.bodySmall
                .copyWith(color: AppThemeColors.textTertiary),
            filled: true,
            fillColor: AppThemeColors.cardGlass,
            border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: BorderSide.none),
            prefixIcon: Icon(Icons.numbers, color: AppThemeColors.textTertiary),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            FilledButton.icon(
              onPressed: _loading ? null : _track,
              icon: const Icon(Icons.my_location),
              label: const Text("Track"),
            ),
            const SizedBox(width: AppSpacing.sm),
            if (_loading)
              const SizedBox(
                  width: AppIconSizes.sm,
                  height: AppIconSizes.sm,
                  child: CircularProgressIndicator(strokeWidth: 2)),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        if (_msg != null)
          Text(_msg!,
              style: AppTypography.bodySmall.copyWith(
                color: _msg == "OK"
                    ? AppThemeColors.success
                    : AppThemeColors.error,
              )),
        const SizedBox(height: 6),
        if (_loc != null)
          Text(
            lat != null ? "Driver Location: Lat=$lat, Lng=$lng" : "No data",
            style: AppTypography.bodySmall
                .copyWith(color: AppThemeColors.textSecondary),
          ),
      ],
    );
  }

}

// Small spacer widget used in Wrap where Spacer() doesn't work
class SpacerWidget extends StatelessWidget {
  const SpacerWidget({super.key});

  @override
  Widget build(BuildContext context) => const SizedBox(width: 1);
}



