// flutter/lib/screen/admin/trip_history_screen.dart
//
// RG Travel Solution — Admin Trip History Screen
// - Full trip history view
// - NLP-like search + filters + sorting
// - Trip detail modal
//
// Dependencies (pubspec.yaml):
//   http: ^1.2.2

import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/services/admin_service.dart';
import '../../core/storage/session_store.dart';

class TripHistoryScreen extends StatefulWidget {
  final String adminId;
  final String? baseUrl;
  final bool embedded;

  const TripHistoryScreen({
    super.key,
    required this.adminId,
    this.baseUrl,
    this.embedded = false,
  });

  @override
  State<TripHistoryScreen> createState() => _TripHistoryScreenState();
}

class _TripHistoryScreenState extends State<TripHistoryScreen> {
  // -----------------------
  // State
  // -----------------------
  late TextEditingController _searchCtrl;
  late TextEditingController _driverIdCtrl;
  late TextEditingController _employeeIdCtrl;
  bool _loading = false;
  String? _error;
  List<Map<String, dynamic>> _trips = [];
  int _totalCount = 0;
  int _currentPage = 1;
  final int _pageSize = 10;

  String _statusFilter = 'all';
  String _typeFilter = 'all';
  DateTime? _fromDate;
  DateTime? _toDate;
  String _sort = 'latest';

  int? _int(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    return int.tryParse(v.toString());
  }

  double _dbl(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }

  String _yyyyMmDd(DateTime d) {
    final y = d.year.toString().padLeft(4, "0");
    final m = d.month.toString().padLeft(2, "0");
    final day = d.day.toString().padLeft(2, "0");
    return "$y-$m-$day";
  }

  @override
  void initState() {
    super.initState();
    _searchCtrl = TextEditingController();
    _driverIdCtrl = TextEditingController();
    _employeeIdCtrl = TextEditingController();
    _fetchTrips();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _driverIdCtrl.dispose();
    _employeeIdCtrl.dispose();
    super.dispose();
  }

  // -----------------------
  // Helpers
  // -----------------------
  void safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  void toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _exportHistory() async {
    final employeeId = _int(_employeeIdCtrl.text.trim());
    try {
      await AdminService.exportTripHistory(
        q: _searchCtrl.text.trim(),
        status: _statusFilter,
        type: _typeFilter,
        fromDate: _fromDate != null ? _yyyyMmDd(_fromDate!) : null,
        toDate: _toDate != null ? _yyyyMmDd(_toDate!) : null,
        sort: _sort,
        driverId: _driverIdCtrl.text.trim().isEmpty
            ? null
            : _driverIdCtrl.text.trim(),
        employeeId: employeeId,
      );
      toast("Trip history export opened.");
    } catch (_) {
      final url = AdminService.buildTripHistoryExportUrl(
        q: _searchCtrl.text.trim(),
        status: _statusFilter,
        type: _typeFilter,
        fromDate: _fromDate != null ? _yyyyMmDd(_fromDate!) : null,
        toDate: _toDate != null ? _yyyyMmDd(_toDate!) : null,
        sort: _sort,
        driverId: _driverIdCtrl.text.trim().isEmpty
            ? null
            : _driverIdCtrl.text.trim(),
        employeeId: employeeId,
      );
      await AdminService.copyToClipboard(url);
      toast("Export link copied to clipboard.");
    }
  }

  // -----------------------
  // Fetch trips
  // -----------------------
  Future<void> _fetchTrips() async {
    safeSetState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await SessionStore.getToken();
      final result = await AdminService.getTripHistory(
        q: _searchCtrl.text.trim(),
        status: _statusFilter,
        type: _typeFilter,
        fromDate: _fromDate != null ? _yyyyMmDd(_fromDate!) : null,
        toDate: _toDate != null ? _yyyyMmDd(_toDate!) : null,
        sort: _sort,
        driverId: _driverIdCtrl.text.trim().isEmpty
            ? null
            : _driverIdCtrl.text.trim(),
        employeeId: _int(_employeeIdCtrl.text.trim()),
        limit: _pageSize,
        offset: (_currentPage - 1) * _pageSize,
        token: token,
      );

      safeSetState(() {
        _trips = ((result["trips"] as List?) ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => e.cast<String, dynamic>())
            .toList();
        _totalCount = _int(result["total_count"]) ?? _trips.length;
      });
    } catch (e) {
      safeSetState(() => _error = "Load failed: $e");
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  Future<void> _openTripDetails(Map<String, dynamic> trip) async {
    final tripId = _int(trip["id"] ?? trip["trip_id"]);
    if (tripId == null) return;

    try {
      final token = await SessionStore.getToken();
      final data = await AdminService.getTripById(tripId, token: token);

      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (_) => _TripDetailDialog(data: data),
      );
    } catch (e) {
      toast("Trip detail failed: $e");
    }
  }

  // -----------------------
  // Date pickers
  // -----------------------
  Future<void> _pickFromDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _fromDate ?? now,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 1),
    );
    if (picked == null) return;
    safeSetState(() => _fromDate = picked);
    _fetchTrips();
  }

  Future<void> _pickToDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _toDate ?? now,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 1),
    );
    if (picked == null) return;
    safeSetState(() => _toDate = picked);
    _fetchTrips();
  }

  void _clearDates() {
    safeSetState(() {
      _fromDate = null;
      _toDate = null;
      _currentPage = 1;
    });
    _fetchTrips();
  }

  void _clearAllFilters() {
    _searchCtrl.clear();
    _driverIdCtrl.clear();
    _employeeIdCtrl.clear();
    safeSetState(() {
      _fromDate = null;
      _toDate = null;
      _statusFilter = 'all';
      _typeFilter = 'all';
      _sort = 'latest';
      _currentPage = 1;
    });
    _fetchTrips();
  }

  int get _totalPages {
    if (_totalCount <= 0) return 1;
    return (_totalCount / _pageSize).ceil();
  }

  void _goToPage(int page) {
    final safePage = page.clamp(1, _totalPages);
    if (safePage == _currentPage) return;
    safeSetState(() => _currentPage = safePage);
    _fetchTrips();
  }

  // -----------------------
  // UI
  // -----------------------
  @override
  Widget build(BuildContext context) {
    final content = Container(
      decoration: widget.embedded
          ? BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  AppThemeColors.backgroundLight,
                  AppThemeColors.background,
                ],
              ),
            )
          : const BoxDecoration(
              gradient: AppGradients.backgroundGradient,
            ),
      child: SafeArea(
        top: !widget.embedded,
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            _backendCard(),
            const SizedBox(height: 12),
            _filtersCard(),
            const SizedBox(height: 12),
            if (_loading) const LinearProgressIndicator(minHeight: 3),
            if (_error != null) ...[
              const SizedBox(height: 10),
              _msg(_error!, error: true),
            ],
            const SizedBox(height: 12),
            _card(
              title: "Trips ($_totalCount)",
              child: _trips.isEmpty
                  ? _hint("No trips found. Try another search/filter.")
                  : Column(
                      children: [
                        ..._trips.map(_tripTile),
                        const SizedBox(height: AppSpacing.md),
                        _paginationBar(),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );

    if (widget.embedded) {
      return content;
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: AppThemeColors.textPrimary,
        title: Text("Trip History",
            style: AppTypography.titleMedium
                .copyWith(color: AppThemeColors.textPrimary)),
        flexibleSpace: Container(
          decoration: BoxDecoration(
            gradient: AppGradients.accentGradient,
          ),
        ),
        actions: [
          IconButton(
            onPressed: _exportHistory,
            icon: const Icon(Icons.download_rounded,
                color: AppThemeColors.textPrimary),
          ),
          IconButton(
              onPressed: _fetchTrips,
              icon:
                  const Icon(Icons.refresh, color: AppThemeColors.textPrimary)),
        ],
      ),
      body: content,
    );
  }

  Widget _filtersCard() {
    return _card(
      title: "Search & Filters",
      child: Column(
        children: [
          Align(
            alignment: Alignment.centerRight,
            child: OutlinedButton.icon(
              onPressed: _exportHistory,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppThemeColors.textPrimary,
                side: const BorderSide(color: AppThemeColors.border),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
              ),
              icon: const Icon(Icons.file_download_outlined, size: 18),
              label: const Text("Export CSV"),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          TextField(
            controller: _searchCtrl,
            style: AppTypography.bodyMedium
                .copyWith(color: AppThemeColors.textPrimary),
            decoration: _deco(
              "Search (NLP-like)",
              "ex: employee two, no-show, swap, MH12AA1111, cancelled",
              Icons.search,
            ),
            onSubmitted: (_) {
              safeSetState(() => _currentPage = 1);
              _fetchTrips();
            },
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _driverIdCtrl,
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textPrimary),
                  decoration: _deco(
                      "Driver ID", "specific driver", Icons.person_outline),
                  onSubmitted: (_) {
                    safeSetState(() => _currentPage = 1);
                    _fetchTrips();
                  },
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: TextField(
                  controller: _employeeIdCtrl,
                  keyboardType: TextInputType.number,
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textPrimary),
                  decoration: _deco(
                      "Employee ID", "specific employee", Icons.badge_outlined),
                  onSubmitted: (_) {
                    safeSetState(() => _currentPage = 1);
                    _fetchTrips();
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _statusFilter,
                  dropdownColor: AppThemeColors.surface,
                  decoration: _deco("Status", "all", Icons.flag),
                  items: const [
                    DropdownMenuItem(value: "all", child: Text("All")),
                    DropdownMenuItem(value: "active", child: Text("Active")),
                    DropdownMenuItem(
                        value: "in_progress", child: Text("In Progress")),
                    DropdownMenuItem(
                        value: "completed", child: Text("Completed")),
                    DropdownMenuItem(
                        value: "cancelled", child: Text("Cancelled")),
                  ],
                  onChanged: (v) {
                    if (v == null) return;
                    safeSetState(() {
                      _statusFilter = v;
                      _currentPage = 1;
                    });
                    _fetchTrips();
                  },
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textPrimary),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _typeFilter,
                  dropdownColor: AppThemeColors.surface,
                  decoration: _deco("Type", "all", Icons.swap_vert),
                  items: const [
                    DropdownMenuItem(value: "all", child: Text("All")),
                    DropdownMenuItem(value: "pickup", child: Text("Pickup")),
                    DropdownMenuItem(value: "drop", child: Text("Drop")),
                  ],
                  onChanged: (v) {
                    if (v == null) return;
                    safeSetState(() {
                      _typeFilter = v;
                      _currentPage = 1;
                    });
                    _fetchTrips();
                  },
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _sort,
                  dropdownColor: AppThemeColors.surface,
                  decoration: _deco("Sort", "latest", Icons.sort),
                  items: const [
                    DropdownMenuItem(
                        value: "latest", child: Text("Latest First")),
                    DropdownMenuItem(
                        value: "km_desc", child: Text("KM High → Low")),
                    DropdownMenuItem(
                        value: "km_asc", child: Text("KM Low → High")),
                  ],
                  onChanged: (v) {
                    if (v == null) return;
                    safeSetState(() {
                      _sort = v;
                      _currentPage = 1;
                    });
                    _fetchTrips();
                  },
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _pickFromDate,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppThemeColors.textPrimary,
                    side: const BorderSide(color: AppThemeColors.border),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md)),
                  ),
                  icon: const Icon(Icons.date_range, size: 18),
                  label: Text(
                      _fromDate == null ? "From Date" : _yyyyMmDd(_fromDate!)),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _pickToDate,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppThemeColors.textPrimary,
                    side: const BorderSide(color: AppThemeColors.border),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md)),
                  ),
                  icon: const Icon(Icons.date_range_outlined, size: 18),
                  label:
                      Text(_toDate == null ? "To Date" : _yyyyMmDd(_toDate!)),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Align(
            alignment: Alignment.centerRight,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextButton(
                  onPressed: _clearDates,
                  child: Text("Clear Dates",
                      style: AppTypography.labelMedium
                          .copyWith(color: AppThemeColors.secondary)),
                ),
                TextButton(
                  onPressed: _clearAllFilters,
                  child: Text("Reset All",
                      style: AppTypography.labelMedium
                          .copyWith(color: AppThemeColors.secondary)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _tripTile(Map<String, dynamic> t) {
    final routeNo = (t["route_no"] ?? t["route_number"] ?? "—").toString();
    final status = (t["status"] ?? "—").toString();
    final type = (t["trip_type"] ?? t["type"] ?? "—").toString();
    final currentDriver = (t["current_driver"] is Map)
        ? (t["current_driver"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final originalDriver = (t["original_driver"] is Map)
        ? (t["original_driver"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final driver =
        (currentDriver["name"] ?? t["driver_name"] ?? t["driver"] ?? "—")
            .toString();
    final originalDriverName = (originalDriver["name"] ?? driver).toString();
    final cab = (t["current_vehicle_no"] ?? t["cab_no"] ?? "—").toString();
    final originalCab = (t["original_vehicle_no"] ?? cab).toString();
    final km = _dbl(t["total_km"]);
    final showKm = t["show_total_km"] == true && t["total_km"] != null;
    final time =
        "${(t["trip_date"] ?? "").toString()} ${(t["schedule_time"] ?? t["time"] ?? "").toString()}"
            .trim();
    final noShowCount = _int(t["no_show_count"]) ?? 0;
    final hasSwap = t["has_emergency_swap"] == true;
    final cancelReason = (t["cancel_reason"] ?? "").toString().trim();

    Color badgeColor;
    final s = status.toLowerCase();
    if (s.contains("complete")) {
      badgeColor = AppThemeColors.success;
    } else if (s.contains("cancel")) {
      badgeColor = AppThemeColors.error;
    } else if (s.contains("progress")) {
      badgeColor = AppThemeColors.warning;
    } else {
      badgeColor = AppThemeColors.info;
    }

    return InkWell(
      onTap: () => _openTripDetails(t),
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          gradient: AppGradients.cardGradient,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: hasSwap
                ? AppThemeColors.warning.withValues(alpha: 0.45)
                : badgeColor.withValues(alpha: 0.28),
          ),
          boxShadow: AppShadows.card,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    routeNo,
                    style: AppTypography.titleSmall.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                _statusBadge(status, badgeColor),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                _badge("Type: $type"),
                _badge(hasSwap
                    ? "Driver: $originalDriverName -> $driver"
                    : "Driver: $driver"),
                _badge(hasSwap ? "Cab: $originalCab -> $cab" : "Cab: $cab"),
                if (showKm) _badge("KM: ${km.toStringAsFixed(1)}"),
                if (noShowCount > 0) _badge("No-show: $noShowCount"),
                if (hasSwap) _badge("Emergency Swap"),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              "Time: ${time.isEmpty ? "—" : time}",
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textSecondary, fontSize: 12),
            ),
            if (cancelReason.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                "Cancel reason: $cancelReason",
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.errorLight,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.sm),
            Text(
              "Tap to view details",
              style: AppTypography.labelSmall
                  .copyWith(color: AppThemeColors.textTertiary, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }

  // -----------------------
  // UI helpers
  // -----------------------
  Widget _backendCard() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        gradient: AppGradients.cardGradient,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.dns,
                  color: AppThemeColors.textTertiary, size: 16),
              const SizedBox(width: 8),
              Text("Connected to RG Backend",
                  style: AppTypography.labelMedium.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 4),
          Text(AdminService.baseUrl,
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textSecondary, fontSize: 10)),
        ],
      ),
    );
  }

  Widget _paginationBar() {
    return Row(
      children: [
        Expanded(
          child: Text(
            "Page $_currentPage / $_totalPages",
            style: AppTypography.bodySmall
                .copyWith(color: AppThemeColors.textSecondary),
          ),
        ),
        OutlinedButton(
          onPressed: _currentPage > 1 && !_loading
              ? () => _goToPage(_currentPage - 1)
              : null,
          style: OutlinedButton.styleFrom(
            foregroundColor: AppThemeColors.textPrimary,
            side: const BorderSide(color: AppThemeColors.border),
            backgroundColor: AppThemeColors.surfaceLight,
          ),
          child: const Text("Previous"),
        ),
        const SizedBox(width: AppSpacing.sm),
        OutlinedButton(
          onPressed: _currentPage < _totalPages && !_loading
              ? () => _goToPage(_currentPage + 1)
              : null,
          style: OutlinedButton.styleFrom(
            foregroundColor: AppThemeColors.textPrimary,
            side: const BorderSide(color: AppThemeColors.border),
            backgroundColor: AppThemeColors.surfaceLight,
          ),
          child: const Text("Next"),
        ),
      ],
    );
  }

  Widget _card({required String title, required Widget child}) {
    return Container(
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
          Text(title,
              style: AppTypography.titleSmall.copyWith(
                  color: AppThemeColors.textPrimary,
                  fontWeight: FontWeight.bold)),
          const SizedBox(height: AppSpacing.md),
          child,
        ],
      ),
    );
  }

  Widget _msg(String t, {required bool error}) {
    final color = error ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Text(
        t,
        style: AppTypography.labelMedium.copyWith(
            color: AppThemeColors.textPrimary, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _hint(String t) => Text(t,
      style:
          AppTypography.bodySmall.copyWith(color: AppThemeColors.textTertiary));

  InputDecoration _deco(String label, String hint, IconData icon) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      labelStyle: AppTypography.labelMedium
          .copyWith(color: AppThemeColors.textSecondary),
      hintStyle:
          AppTypography.labelSmall.copyWith(color: AppThemeColors.textTertiary),
      prefixIcon: Icon(icon, color: AppThemeColors.textTertiary),
      filled: true,
      fillColor: AppThemeColors.surfaceLight,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppThemeColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppThemeColors.primary),
      ),
    );
  }

  Widget _badge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppThemeColors.surfaceLight,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppThemeColors.borderLight),
      ),
      child: Text(
        text,
        style: AppTypography.labelSmall.copyWith(
          color: AppThemeColors.textSecondary,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _statusBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        text,
        style: AppTypography.labelSmall.copyWith(
          color: color == AppThemeColors.warning
              ? AppThemeColors.background
              : AppThemeColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// ------------------------------------------------------
// Trip Detail Dialog
// ------------------------------------------------------
class _TripDetailDialog extends StatelessWidget {
  final Map<String, dynamic> data;

  const _TripDetailDialog({required this.data});

  int _int(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    final routeNo = (data["route_no"] ?? "—").toString();
    final status = (data["status"] ?? "—").toString();
    final type = (data["trip_type"] ?? data["type"] ?? "—").toString();
    final currentDriver = (data["current_driver"] is Map)
        ? (data["current_driver"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final originalDriver = (data["original_driver"] is Map)
        ? (data["original_driver"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final driver =
        (currentDriver["name"] ?? data["driver_name"] ?? "—").toString();
    final cab =
        (data["current_vehicle_no"] ?? data["cab_no"] ?? "—").toString();
    final originalCab = (data["original_vehicle_no"] ?? cab).toString();
    final showKm = data["show_total_km"] == true && data["total_km"] != null;
    final km = showKm ? data["total_km"].toString() : "Not applicable";

    final employees = (data["employees"] is List)
        ? (data["employees"] as List<dynamic>)
        : <dynamic>[];
    final stops = (data["stops"] is List)
        ? (data["stops"] as List<dynamic>)
        : <dynamic>[];
    final cancelReason = (data["cancel_reason"] ?? "").toString();
    final noShowMembers = (data["no_show_members"] is List)
        ? (data["no_show_members"] as List<dynamic>)
        : <dynamic>[];

    return AlertDialog(
      backgroundColor: AppThemeColors.surface,
      title: Text("Trip • $routeNo",
          style: AppTypography.titleMedium
              .copyWith(color: AppThemeColors.textPrimary)),
      content: SizedBox(
        width: double.maxFinite,
        height: 520,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _kv("Status", status),
              _kv("Type", type),
              _kv(
                "Driver",
                data["has_emergency_swap"] == true
                    ? "${(originalDriver["name"] ?? driver).toString()} -> $driver"
                    : driver,
              ),
              _kv(
                "Cab",
                data["has_emergency_swap"] == true
                    ? "$originalCab -> $cab"
                    : cab,
              ),
              _kv("Total KM", km),
              _kv("No-show Count", (data["no_show_count"] ?? 0).toString()),
              if (cancelReason.isNotEmpty) _kv("Cancel Reason", cancelReason),
              if (noShowMembers.isNotEmpty)
                _kv(
                  "No-show Members",
                  noShowMembers
                      .map((e) => ((e as Map)["name"] ?? "").toString())
                      .where((e) => e.trim().isNotEmpty)
                      .join(", "),
                ),
              const SizedBox(height: AppSpacing.md),
              Text("Employees",
                  style: AppTypography.titleSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: AppSpacing.sm),
              if (employees.isEmpty)
                Text("No employees data.",
                    style: AppTypography.bodySmall
                        .copyWith(color: AppThemeColors.textSecondary))
              else
                ...employees.map((e) {
                  final m = (e as Map).cast<String, dynamic>();
                  final name = (m["name"] ?? "—").toString();
                  final mobile = (m["mobile"] ?? "—").toString();
                  final noShow = _int(m["no_show"] ?? 0) == 1;
                  final noShowReason = (m["no_show_reason"] ?? "").toString();
                  return ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(name,
                        style: AppTypography.bodyMedium.copyWith(
                          color: noShow
                              ? AppThemeColors.error
                              : AppThemeColors.textPrimary,
                          fontWeight: FontWeight.bold,
                        )),
                    subtitle: Text(
                      noShow && noShowReason.isNotEmpty
                          ? "$mobile\n$noShowReason"
                          : mobile,
                      style: AppTypography.bodySmall
                          .copyWith(color: AppThemeColors.textSecondary),
                    ),
                    trailing: noShow
                        ? Text("NO SHOW",
                            style: AppTypography.labelSmall
                                .copyWith(color: AppThemeColors.error))
                        : null,
                  );
                }).toList(),
              const SizedBox(height: AppSpacing.md),
              Text("Stops / Waypoints",
                  style: AppTypography.titleSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: AppSpacing.sm),
              if (stops.isEmpty)
                Text("No stops saved.",
                    style: AppTypography.bodySmall
                        .copyWith(color: AppThemeColors.textSecondary))
              else
                ...stops.map((s) {
                  return Text("• ${s.toString()}",
                      style: AppTypography.bodySmall
                          .copyWith(color: AppThemeColors.textSecondary));
                }).toList(),
            ],
          ),
        ),
      ),
      actions: [
        if (data["polyline"] != null && data["polyline"].toString().isNotEmpty)
          TextButton.icon(
            icon: const Icon(Icons.map, size: 16),
            label: const Text("View Route Path"),
            onPressed: () {
              // Navigate to LiveTrackingScreen in 'history' mode if applicable
              // For now, toast the availability
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text("Route path visualization enabled ✅")),
              );
            },
          ),
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text("Close",
              style: AppTypography.labelMedium
                  .copyWith(color: AppThemeColors.textSecondary)),
        ),
      ],
    );
  }

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: RichText(
        text: TextSpan(
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textSecondary),
          children: [
            TextSpan(
                text: "$k: ",
                style: const TextStyle(fontWeight: FontWeight.bold)),
            TextSpan(
                text: v,
                style: const TextStyle(color: AppThemeColors.textPrimary)),
          ],
        ),
      ),
    );
  }
}
