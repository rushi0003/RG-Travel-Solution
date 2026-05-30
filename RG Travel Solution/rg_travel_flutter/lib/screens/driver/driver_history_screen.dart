import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/services/driver_service.dart';

class DriverHistoryScreen extends StatefulWidget {
  final String driverId;

  const DriverHistoryScreen({super.key, required this.driverId});

  @override
  State<DriverHistoryScreen> createState() => _DriverHistoryScreenState();
}

class _DriverHistoryScreenState extends State<DriverHistoryScreen> {
  bool _isLoading = false;
  List<Map<String, dynamic>> _trips = [];
  DateTime? _fromDate;
  DateTime? _toDate;
  final _dateFormat = DateFormat('yyyy-MM-dd');

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    try {
      final from = _fromDate != null ? _dateFormat.format(_fromDate!) : null;
      final to = _toDate != null ? _dateFormat.format(_toDate!) : null;
      final data = await DriverService.getDriverTripHistory(
        widget.driverId,
        fromDate: from,
        toDate: to,
      );
      if (!mounted) return;
      setState(() => _trips = data);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _pickDate(bool isFrom) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: isFrom ? (_fromDate ?? now) : (_toDate ?? now),
      firstDate: DateTime(2023),
      lastDate: DateTime(2028),
    );
    if (picked == null) return;
    setState(() {
      if (isFrom) {
        _fromDate = picked;
      } else {
        _toDate = picked;
      }
    });
    _loadHistory();
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return AppThemeColors.success;
      case 'cancelled':
        return AppThemeColors.error;
      default:
        return AppThemeColors.warningDark;
    }
  }

  String _tripDateTime(Map<String, dynamic> trip) {
    final date = (trip['trip_date'] ?? trip['trip_day'] ?? '').toString();
    final time = (trip['schedule_time'] ?? '').toString();
    if (date.isEmpty && time.isEmpty) return '-';
    if (date.isEmpty) return time;
    if (time.isEmpty) return date;
    return '$date  $time';
  }

  String _driverSwapLabel(Map<String, dynamic> trip) {
    final original = (trip['original_driver'] as Map?)?.cast<String, dynamic>();
    final current = (trip['current_driver'] as Map?)?.cast<String, dynamic>();
    final originalName = (original?['name'] ?? '').toString().trim();
    final currentName = (current?['name'] ?? '').toString().trim();
    if (originalName.isEmpty) return '';
    if (originalName == currentName || currentName.isEmpty) return originalName;
    return '$originalName -> $currentName';
  }

  Widget _infoChip(String label, {Color? color}) {
    final chipColor = color ?? AppThemeColors.textTertiary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: chipColor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: chipColor.withValues(alpha: 0.20)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: chipColor,
        ),
      ),
    );
  }

  Widget _dateBtn(String text, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
        decoration: BoxDecoration(
          border: Border.all(color: AppThemeColors.border),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(text, style: AppTypography.bodySmall),
            const Icon(
              Icons.calendar_today,
              size: 14,
              color: AppThemeColors.textTertiary,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTripCard(Map<String, dynamic> trip) {
    final status = (trip['status'] ?? 'unknown').toString();
    final color = _statusColor(status);
    final showKm = trip['show_total_km'] == true && trip['total_km'] != null;
    final km = showKm ? '${trip['total_km']} km' : '';
    final hasSwap = trip['has_emergency_swap'] == true;
    final noShowCount = (trip['no_show_count'] as num?)?.toInt() ?? 0;
    final currentVehicle =
        (trip['current_vehicle_no'] ?? trip['cab_no'] ?? '-').toString();
    final originalVehicle =
        (trip['original_vehicle_no'] ?? currentVehicle).toString();
    final swapLabel = _driverSwapLabel(trip);
    final noShowMembers = (trip['no_show_members'] is List)
        ? (trip['no_show_members'] as List)
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => ((e['name'] ?? '').toString()))
            .where((e) => e.trim().isNotEmpty)
            .toList()
        : <String>[];
    final cancelReason = (trip['cancel_reason'] ?? '').toString().trim();

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Route #${trip['route_no'] ?? '?'}',
                    style: AppTypography.titleSmall.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    status.toUpperCase(),
                    style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              _tripDateTime(trip),
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Type: ${(trip['trip_type'] ?? '-').toString()}',
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textTertiary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              hasSwap
                  ? 'Driver swap: $swapLabel'
                  : 'Driver: ${(trip['current_driver']?['name'] ?? trip['driver_name'] ?? '-').toString()}',
              style: TextStyle(
                fontSize: 13,
                color: hasSwap
                    ? AppThemeColors.warningDark
                    : AppThemeColors.textSecondary,
                fontWeight: hasSwap ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              hasSwap
                  ? 'Vehicle: $originalVehicle -> $currentVehicle'
                  : 'Vehicle: $currentVehicle',
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
            if (cancelReason.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'Cancel reason: $cancelReason',
                style: AppTypography.bodySmall.copyWith(
                  fontSize: 12,
                  color: AppThemeColors.error,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (showKm) _infoChip(km, color: AppThemeColors.success),
                _infoChip(
                  '${trip['employee_count'] ?? 0} employees',
                  color: AppThemeColors.infoLight,
                ),
                if (noShowCount > 0)
                  _infoChip(
                    '$noShowCount no-show',
                    color: AppThemeColors.error,
                  ),
                if (hasSwap)
                  _infoChip(
                    'Emergency swap',
                    color: AppThemeColors.warningDark,
                  ),
              ],
            ),
            if (noShowMembers.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'No-show: ${noShowMembers.join(', ')}',
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.error,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Trip History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadHistory,
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: Column(
          children: [
            Container(
              color: AppThemeColors.surface,
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Row(
                children: [
                  Expanded(
                    child: _dateBtn(
                      "From: ${_fromDate != null ? _dateFormat.format(_fromDate!) : 'Any'}",
                      () => _pickDate(true),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _dateBtn(
                      "To: ${_toDate != null ? _dateFormat.format(_toDate!) : 'Any'}",
                      () => _pickDate(false),
                    ),
                  ),
                  if (_fromDate != null || _toDate != null)
                    IconButton(
                      icon: const Icon(Icons.clear, size: 20),
                      onPressed: () {
                        setState(() {
                          _fromDate = null;
                          _toDate = null;
                        });
                        _loadHistory();
                      },
                    ),
                ],
              ),
            ),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _trips.isEmpty
                      ? Center(
                          child: Text(
                            'No trips found',
                            style: AppTypography.bodyMedium.copyWith(
                              color: AppThemeColors.textTertiary,
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          itemCount: _trips.length,
                          itemBuilder: (ctx, i) => _buildTripCard(_trips[i]),
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
