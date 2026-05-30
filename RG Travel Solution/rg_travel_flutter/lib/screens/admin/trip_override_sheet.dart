import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../services/admin_service.dart';

class TripOverrideSheet extends StatefulWidget {
  final Map<String, dynamic> trip;
  final String adminId;
  final VoidCallback onUpdate;

  const TripOverrideSheet({
    super.key,
    required this.trip,
    required this.adminId,
    required this.onUpdate,
  });

  @override
  State<TripOverrideSheet> createState() => _TripOverrideSheetState();
}

class _TripOverrideSheetState extends State<TripOverrideSheet>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;

  int? _selectedEmployeeId;
  int? _targetTripId;
  List<Map<String, dynamic>> _activeTrips = [];

  String? _selectedNewDriverId;
  List<Map<String, dynamic>> _availableDrivers = [];

  final _cancelReasonController = TextEditingController();

  int? _int(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    return int.tryParse(v.toString());
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final trips = await AdminService.getLiveTrips();
      _activeTrips = trips
          .where((t) => _int(t['id']) != _int(widget.trip['trip_id']))
          .toList();

      final tripType = (widget.trip['trip_type'] ?? 'pickup').toString();
      final time = (widget.trip['schedule_time'] ?? '00:00').toString();
      final vType = widget.trip['vehicle_type'];

      _availableDrivers = await AdminService.getAvailableDrivers(
        tripType: tripType,
        scheduledTime: time,
        vehicleType: vType is int ? vType : int.tryParse(vType.toString()),
        adminId: widget.adminId,
      );
    } catch (e) {
      debugPrint('Error loading override data: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _cancelReasonController.dispose();
    super.dispose();
  }

  Future<void> _handleMoveEmployee() async {
    if (_selectedEmployeeId == null || _targetTripId == null) return;

    setState(() => _isLoading = true);
    try {
      await AdminService.moveEmployee(
        fromTripId: _int(widget.trip['trip_id'] ?? widget.trip['id']) ?? 0,
        employeeId: _selectedEmployeeId!,
        toTripId: _targetTripId!,
        adminId: widget.adminId,
      );
      Navigator.pop(context);
      widget.onUpdate();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Employee moved successfully')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to move employee: $e')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleSwapDriver() async {
    if (_selectedNewDriverId == null) return;

    setState(() => _isLoading = true);
    try {
      await AdminService.swapDriver(
        tripId: _int(widget.trip['trip_id'] ?? widget.trip['id']) ?? 0,
        newDriverId: _selectedNewDriverId!,
        adminId: widget.adminId,
      );
      Navigator.pop(context);
      widget.onUpdate();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Driver swapped successfully')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to swap driver: $e')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleCancelTrip() async {
    if (_cancelReasonController.text.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please provide a valid reason')),
      );
      return;
    }

    setState(() => _isLoading = true);
    try {
      await AdminService.cancelTrip(
        _int(widget.trip['trip_id'] ?? widget.trip['id']) ?? 0,
        reason: _cancelReasonController.text,
      );
      Navigator.pop(context);
      widget.onUpdate();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Trip cancelled successfully')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to cancel trip: $e')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final employees = (widget.trip['employees'] as List?) ?? [];

    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      decoration: BoxDecoration(
        color: AppThemeColors.surface,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppRadius.lg),
        ),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.35),
        ),
      ),
      child: Column(
        children: [
          const SizedBox(height: AppSpacing.md),
          Container(
            width: 42,
            height: 4,
            decoration: BoxDecoration(
              color: AppThemeColors.borderLight,
              borderRadius: BorderRadius.circular(AppRadius.full),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Trip Override Actions',
            style: AppTypography.headlineLarge.copyWith(fontSize: 18),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            "Trip #${widget.trip['trip_id']} - Route ${widget.trip['route_no']}",
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          TabBar(
            controller: _tabController,
            labelColor: AppThemeColors.primary,
            unselectedLabelColor: AppThemeColors.textTertiary,
            indicatorColor: AppThemeColors.primary,
            tabs: const [
              Tab(text: 'Move Emp'),
              Tab(text: 'Swap Driver'),
              Tab(text: 'Cancel'),
            ],
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(
                    controller: _tabController,
                    children: [
                      _MoveEmployeeTab(
                        employees: employees,
                        activeTrips: _activeTrips,
                        selectedEmployeeId: _selectedEmployeeId,
                        targetTripId: _targetTripId,
                        onEmployeeChanged: (val) =>
                            setState(() => _selectedEmployeeId = val),
                        onTripChanged: (val) =>
                            setState(() => _targetTripId = val),
                        onSubmit: _handleMoveEmployee,
                      ),
                      _SwapDriverTab(
                        trip: widget.trip,
                        availableDrivers: _availableDrivers,
                        selectedNewDriverId: _selectedNewDriverId,
                        onDriverChanged: (val) =>
                            setState(() => _selectedNewDriverId = val),
                        onSubmit: _handleSwapDriver,
                      ),
                      _CancelTripTab(
                        controller: _cancelReasonController,
                        onSubmit: _handleCancelTrip,
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _MoveEmployeeTab extends StatelessWidget {
  const _MoveEmployeeTab({
    required this.employees,
    required this.activeTrips,
    required this.selectedEmployeeId,
    required this.targetTripId,
    required this.onEmployeeChanged,
    required this.onTripChanged,
    required this.onSubmit,
  });

  final List<dynamic> employees;
  final List<Map<String, dynamic>> activeTrips;
  final int? selectedEmployeeId;
  final int? targetTripId;
  final ValueChanged<int?> onEmployeeChanged;
  final ValueChanged<int?> onTripChanged;
  final VoidCallback onSubmit;

  int? _int(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    return int.tryParse(v.toString());
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        children: [
          DropdownButtonFormField<int>(
            initialValue: selectedEmployeeId,
            decoration: const InputDecoration(
              labelText: 'Select Employee to Move',
            ),
            items: employees.map<DropdownMenuItem<int>>((e) {
              final eId = _int(e['id']);
              return DropdownMenuItem<int>(
                value: eId,
                child: Text(
                  "${(e['name'] ?? 'Unknown').toString()} (${(e['mobile'] ?? '').toString()})",
                ),
              );
            }).toList(),
            onChanged: onEmployeeChanged,
          ),
          const SizedBox(height: AppSpacing.md),
          DropdownButtonFormField<int>(
            initialValue: targetTripId,
            decoration: const InputDecoration(labelText: 'Select Target Trip'),
            items: activeTrips.map<DropdownMenuItem<int>>((t) {
              final tId = _int(t['id']);
              final vType = _int(t['vehicle_type']) ?? 4;
              return DropdownMenuItem<int>(
                value: tId,
                child: Text(
                  "Trip #$tId (${(t['route_no'] ?? 'N/A').toString()}) - $vType seater",
                ),
              );
            }).toList(),
            onChanged: onTripChanged,
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onSubmit,
              child: const Text('Move Employee'),
            ),
          ),
        ],
      ),
    );
  }
}

class _SwapDriverTab extends StatelessWidget {
  const _SwapDriverTab({
    required this.trip,
    required this.availableDrivers,
    required this.selectedNewDriverId,
    required this.onDriverChanged,
    required this.onSubmit,
  });

  final Map<String, dynamic> trip;
  final List<Map<String, dynamic>> availableDrivers;
  final String? selectedNewDriverId;
  final ValueChanged<String?> onDriverChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.person_outline_rounded),
            title: Text(
              'Current Driver',
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
            subtitle: Text(
              "${trip['driver_name'] ?? 'Unknown'} (${trip['vehicle_no']})",
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const Divider(color: AppThemeColors.divider),
          const SizedBox(height: AppSpacing.md),
          DropdownButtonFormField<String>(
            initialValue: selectedNewDriverId,
            decoration: const InputDecoration(labelText: 'Select New Driver'),
            items: availableDrivers.map<DropdownMenuItem<String>>((d) {
              final dId = d['id'] is int
                  ? d['id']
                  : int.tryParse(d['id']?.toString() ?? '');
              return DropdownMenuItem<String>(
                value: dId?.toString() ?? '',
                child: Text(
                  "${(d['name'] ?? 'Unknown').toString()} - ${(d['cab_no'] ?? 'N/A').toString()}",
                ),
              );
            }).toList(),
            onChanged: onDriverChanged,
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onSubmit,
              child: const Text('Swap Driver'),
            ),
          ),
        ],
      ),
    );
  }
}

class _CancelTripTab extends StatelessWidget {
  const _CancelTripTab({
    required this.controller,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppThemeColors.error.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(AppRadius.sm),
              border: Border.all(
                color: AppThemeColors.error.withValues(alpha: 0.30),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  color: AppThemeColors.error,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'This action cannot be undone. All employees will be unassigned.',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.error,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          TextFormField(
            controller: controller,
            decoration: const InputDecoration(labelText: 'Cancellation Reason'),
            maxLines: 3,
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onSubmit,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppThemeColors.error,
                foregroundColor: AppThemeColors.textPrimary,
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                ),
              ),
              child: const Text('Cancel Trip'),
            ),
          ),
        ],
      ),
    );
  }
}
