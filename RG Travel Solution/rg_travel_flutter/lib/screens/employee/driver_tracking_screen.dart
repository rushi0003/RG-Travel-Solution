import 'dart:async';

import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/services/employee_service.dart';

import '../../core/theme/app_theme.dart';

class DriverTrackingScreen extends StatefulWidget {
  final String routeNo;
  final String employeeId;

  const DriverTrackingScreen({
    super.key,
    required this.routeNo,
    required this.employeeId,
  });

  @override
  State<DriverTrackingScreen> createState() => _DriverTrackingScreenState();
}

class _DriverTrackingScreenState extends State<DriverTrackingScreen> {
  bool _loading = true;
  Timer? _pollTimer;

  Map<String, dynamic>? _trackingData;
  Map<String, dynamic>? _tripDetails;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _safeSetState(VoidCallback fn) {
    if (mounted) setState(fn);
  }

  Future<void> _loadInitialData() async {
    try {
      final trip = await EmployeeService.getTripDetailsByRoute(widget.routeNo);
      _safeSetState(() {
        _tripDetails = trip;
      });
      await _fetchTracking();
    } catch (e) {
      debugPrint('Failed to load trip details: $e');
    } finally {
      _safeSetState(() => _loading = false);
    }
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _fetchTracking();
    });
  }

  Future<void> _fetchTracking() async {
    try {
      final res =
          await EmployeeService.getLatestTrackingByRoute(widget.routeNo);
      _safeSetState(() {
        _trackingData = res;
      });
    } catch (e) {
      debugPrint('Tracking poll failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final driverName = (_tripDetails?['driver_name'] ?? 'Driver').toString();
    final cabNo = (_tripDetails?['cab_no'] ?? '-').toString();

    final lat = _trackingData?['lat']?.toString() ?? '-';
    final lng = _trackingData?['lng']?.toString() ?? '-';
    final lastUpdate =
        (_trackingData?['updated_at'] as String?) ?? 'Waiting for update...';

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Live Tracking'),
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    Expanded(
                      child: Container(
                        width: double.infinity,
                        margin: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          gradient: AppGradients.cardGradient,
                          borderRadius: BorderRadius.circular(AppRadius.xl),
                          border: Border.all(
                            color: AppThemeColors.borderLight.withValues(
                              alpha: 0.48,
                            ),
                          ),
                          boxShadow: AppShadows.card,
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(AppRadius.xl),
                          child: Stack(
                            children: [
                              Positioned.fill(
                                child: CustomPaint(
                                  painter: GridPainter(),
                                ),
                              ),
                              Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.map_outlined,
                                      size: 64,
                                      color: AppThemeColors.textPrimary
                                          .withValues(alpha: 0.10),
                                    ),
                                    const SizedBox(height: AppSpacing.md),
                                    Text(
                                      'SIMULATED MAP VIEW',
                                      style: AppTypography.titleSmall.copyWith(
                                        color: AppThemeColors.textPrimary
                                            .withValues(alpha: 0.35),
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                      padding:
                                          const EdgeInsets.all(AppSpacing.xs),
                                      decoration: BoxDecoration(
                                        color: AppThemeColors.textPrimary,
                                        shape: BoxShape.circle,
                                        boxShadow: [
                                          BoxShadow(
                                            color: AppThemeColors.primary
                                                .withValues(alpha: 0.45),
                                            blurRadius: 22,
                                            spreadRadius: 5,
                                          ),
                                        ],
                                      ),
                                      child: const Icon(
                                        Icons.directions_car,
                                        color: AppThemeColors.primaryDark,
                                        size: 32,
                                      ),
                                    ),
                                    const SizedBox(height: AppSpacing.sm),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: AppSpacing.sm,
                                        vertical: AppSpacing.xs,
                                      ),
                                      decoration: BoxDecoration(
                                        color: AppThemeColors.background
                                            .withValues(alpha: 0.78),
                                        borderRadius: BorderRadius.circular(
                                          AppRadius.xs,
                                        ),
                                      ),
                                      child: Text(
                                        cabNo,
                                        style: AppTypography.bodySmall.copyWith(
                                          color: AppThemeColors.textPrimary,
                                          fontWeight: FontWeight.w800,
                                        ),
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
                    _TrackingInfoPanel(
                      driverName: driverName,
                      cabNo: cabNo,
                      lat: lat,
                      lng: lng,
                      updated: _formatTime(lastUpdate),
                    ),
                  ],
                ),
        ),
      ),
    );
  }

  String _formatTime(String raw) {
    if (raw.contains('Waiting')) return raw;
    try {
      final dt = DateTime.parse(raw).toLocal();
      final hour = dt.hour.toString().padLeft(2, '0');
      final minute = dt.minute.toString().padLeft(2, '0');
      final second = dt.second.toString().padLeft(2, '0');
      return '$hour:$minute:$second';
    } catch (_) {
      return raw;
    }
  }
}

class _TrackingInfoPanel extends StatelessWidget {
  const _TrackingInfoPanel({
    required this.driverName,
    required this.cabNo,
    required this.lat,
    required this.lng,
    required this.updated,
  });

  final String driverName;
  final String cabNo;
  final String lat;
  final String lng;
  final String updated;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.96),
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppRadius.xl),
        ),
        border: Border(
          top: BorderSide(
            color: AppThemeColors.borderLight.withValues(alpha: 0.45),
          ),
        ),
        boxShadow: AppShadows.elevated,
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: AppThemeColors.primary.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                ),
                child: const Icon(
                  Icons.person_outline_rounded,
                  color: AppThemeColors.primary,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      driverName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.titleMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'Cab: $cabNo',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppThemeColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const _LiveBadge(),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Divider(
            height: 1,
            color: AppThemeColors.divider.withValues(alpha: 0.8),
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(child: _StatItem(label: 'LATITUDE', value: lat)),
              Expanded(child: _StatItem(label: 'LONGITUDE', value: lng)),
              Expanded(child: _StatItem(label: 'UPDATED', value: updated)),
            ],
          ),
        ],
      ),
    );
  }
}

class _LiveBadge extends StatelessWidget {
  const _LiveBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: AppThemeColors.success.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(
          color: AppThemeColors.success.withValues(alpha: 0.35),
        ),
      ),
      child: Text(
        'LIVE',
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.success,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  const _StatItem({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.bodySmall.copyWith(
            color: AppThemeColors.textTertiary,
            fontWeight: FontWeight.w800,
            fontSize: 10,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.bodySmall.copyWith(
            color: AppThemeColors.textPrimary,
            fontWeight: FontWeight.w700,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}

class GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppThemeColors.textPrimary.withValues(alpha: 0.05)
      ..strokeWidth = 1;

    const step = 40.0;
    for (double i = 0; i < size.width; i += step) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), paint);
    }
    for (double i = 0; i < size.height; i += step) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
