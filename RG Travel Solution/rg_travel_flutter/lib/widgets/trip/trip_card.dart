// flutter/lib/widgets/trip/trip_card.dart
//
// RG Travel Solution — Trip Card Widget
//
// Displays a TripModel (routeNo-based) for Admin / Driver / Employee screens.
//
// Depends on:
// - flutter/lib/models/trip_model.dart
// - flutter/lib/widgets/common/rg_card.dart
// - flutter/lib/widgets/common/rg_button.dart
//
// IMPORTANT:
// This widget does NOT call APIs directly.
// Screen passes callbacks which will call services/endpoints.

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../models/trip_model.dart';
import '../common/rg_card.dart';
import '../common/rg_button.dart';

enum TripCardRole { admin, driver, employee }

class TripCard extends StatelessWidget {
  final TripModel trip;
  final TripCardRole role;

  /// For list tap (open details)
  final VoidCallback? onTap;

  /// Optional actions (screen should implement API calls)
  final VoidCallback? onViewMap;
  final VoidCallback? onViewTracking;
  final VoidCallback? onMarkCompleted;
  final VoidCallback? onCancel;
  final VoidCallback? onStartTrip;
  final VoidCallback? onVerifyStartOtp;
  final VoidCallback? onVerifyEndOtp;

  /// If you want card to show action row
  final bool showActions;

  /// Loading state for buttons (screen-level)
  final bool isBusy;

  const TripCard({
    super.key,
    required this.trip,
    this.role = TripCardRole.admin,
    this.onTap,
    this.onViewMap,
    this.onViewTracking,
    this.onMarkCompleted,
    this.onCancel,
    this.onStartTrip,
    this.onVerifyStartOtp,
    this.onVerifyEndOtp,
    this.showActions = true,
    this.isBusy = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final typeText = trip.isPickup
        ? "Pickup"
        : trip.isDrop
            ? "Drop"
            : "Trip";
    final timeText =
        (trip.scheduledTime ?? "").trim().isEmpty ? "-" : trip.scheduledTime!;
    final dateText = (trip.tripDate ?? "").trim().isEmpty ? "" : trip.tripDate!;

    final kmText =
        trip.totalKm == null ? "-" : trip.totalKm!.toStringAsFixed(1);

    final driverText = trip.driver == null
        ? "-"
        : "${trip.driver!.name} • ${trip.cabNo ?? trip.driver!.cabNo ?? "-"}";

    final empCount = trip.employees.length;
    final stopCount = trip.stops.isNotEmpty ? trip.stops.length : empCount;

    final badge = _StatusBadge(status: trip.status);

    final subtitle = [
      "$typeText • $timeText",
      if (dateText.isNotEmpty) dateText,
      "Stops: $stopCount",
      "KM: $kmText",
    ].join("  |  ");

    return RGCard(
      onTap: onTap,
      title: "Route No: ${trip.routeNo}",
      subtitle: subtitle,
      trailing: badge,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _InfoRow(
            icon: Icons.local_taxi,
            label: "Cab / Driver",
            value: driverText,
          ),
          const SizedBox(height: 10),
          _InfoRow(
            icon: Icons.groups_rounded,
            label: "Employees",
            value: "$empCount",
            trailing: _NoShowChip(
              noShowCount: trip.noShowEmployeeIds.length,
              absentCount: trip.absentEmployeeIds.length,
            ),
          ),
          if (trip.cancelReason != null &&
              trip.cancelReason!.trim().isNotEmpty) ...[
            const SizedBox(height: 10),
            _CancelBox(reason: trip.cancelReason!.trim()),
          ],
          if (showActions) ...[
            const SizedBox(height: 14),
            _buildActions(context, theme),
          ],
        ],
      ),
    );
  }

  Widget _buildActions(BuildContext context, ThemeData theme) {
    final canTrack = onViewTracking != null;
    final canMap = onViewMap != null;

    // Role-specific logic hints
    final showAdminActions = role == TripCardRole.admin;
    final showDriverActions = role == TripCardRole.driver;
    final showEmployeeActions = role == TripCardRole.employee;

    // OTP rules (as per your spec)
    final showStartOtp = trip.requiresStartOtp && (onVerifyStartOtp != null);
    final showEndOtp = trip.requiresEndOtp && (onVerifyEndOtp != null);

    // Start trip button for driver:
    // - pickup: require verify start otp first (backend should enforce)
    // - drop: start trip without OTP (your spec)
    final showStartTripBtn = showDriverActions && onStartTrip != null;

    final showCompleteBtn = (showAdminActions || showDriverActions) &&
        onMarkCompleted != null &&
        !trip.isCancelled;

    final showCancelBtn =
        showAdminActions && onCancel != null && !trip.isCompleted;

    // Compose action buttons
    final buttons = <Widget>[];

    if (canTrack && (trip.isLive || showEmployeeActions)) {
      buttons.add(
        RGButton(
          text: "Live Track",
          icon: Icons.location_searching,
          variant: RGButtonVariant.outline,
          isLoading: isBusy,
          onPressed: isBusy ? null : onViewTracking,
        ),
      );
    }

    if (canMap) {
      buttons.add(
        RGButton(
          text: "Open Map",
          icon: Icons.map_outlined,
          variant: RGButtonVariant.outline,
          isLoading: isBusy,
          onPressed: isBusy ? null : onViewMap,
        ),
      );
    }

    if (showStartOtp) {
      buttons.add(
        RGButton(
          text: "Verify Start OTP",
          icon: Icons.lock_open_rounded,
          variant: RGButtonVariant.secondary,
          isLoading: isBusy,
          onPressed: isBusy ? null : onVerifyStartOtp,
        ),
      );
    }

    if (showStartTripBtn) {
      buttons.add(
        RGButton(
          text: trip.isDrop ? "Start Trip" : "Start Trip",
          icon: Icons.play_arrow_rounded,
          variant: RGButtonVariant.primary,
          isLoading: isBusy,
          onPressed: isBusy ? null : onStartTrip,
        ),
      );
    }

    if (showEndOtp) {
      buttons.add(
        RGButton(
          text: "Verify End OTP",
          icon: Icons.verified_rounded,
          variant: RGButtonVariant.secondary,
          isLoading: isBusy,
          onPressed: isBusy ? null : onVerifyEndOtp,
        ),
      );
    }

    if (showCompleteBtn) {
      buttons.add(
        RGButton(
          text: "Mark Completed",
          icon: Icons.check_circle_outline,
          variant: RGButtonVariant.primary,
          isLoading: isBusy,
          onPressed: isBusy ? null : onMarkCompleted,
        ),
      );
    }

    if (showCancelBtn) {
      buttons.add(
        RGButton(
          text: "Cancel Trip",
          icon: Icons.cancel_outlined,
          variant: RGButtonVariant.danger,
          isLoading: isBusy,
          onPressed: isBusy ? null : onCancel,
        ),
      );
    }

    if (buttons.isEmpty) {
      return const SizedBox.shrink();
    }

    // Show in grid-like wrap
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: buttons.map((w) => SizedBox(width: 170, child: w)).toList(),
    );
  }
}

// =============================================================
// UI helpers
// =============================================================

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Widget? trailing;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon,
            size: 18, color: theme.colorScheme.primary.withValues(alpha: 0.9)),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.65),
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                value,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: 10),
          trailing!,
        ]
      ],
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final TripStatus status;
  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    String text;
    Color bg;

    switch (status) {
      case TripStatus.pending:
        text = "Pending";
        bg = theme.colorScheme.surface.withValues(alpha: 0.35);
        break;
      case TripStatus.assigned:
        text = "Assigned";
        bg = theme.colorScheme.primary.withValues(alpha: 0.18);
        break;
      case TripStatus.inProgress:
        text = "Live";
        bg = AppThemeColors.info.withValues(alpha: 0.20);
        break;
      case TripStatus.completed:
        text = "Completed";
        bg = AppThemeColors.success.withValues(alpha: 0.20);
        break;
      case TripStatus.cancelled:
        text = "Cancelled";
        bg = AppThemeColors.error.withValues(alpha: 0.18);
        break;
      case TripStatus.unknown:
        text = "Unknown";
        bg = theme.colorScheme.surface.withValues(alpha: 0.25);
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: theme.dividerColor.withValues(alpha: 0.55),
          width: 1,
        ),
      ),
      child: Text(
        text,
        style: theme.textTheme.labelSmall?.copyWith(
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _NoShowChip extends StatelessWidget {
  final int noShowCount;
  final int absentCount;

  const _NoShowChip({
    required this.noShowCount,
    required this.absentCount,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (noShowCount == 0 && absentCount == 0) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface.withValues(alpha: 0.22),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: theme.dividerColor.withValues(alpha: 0.35)),
        ),
        child: Text(
          "All Present",
          style:
              theme.textTheme.labelSmall?.copyWith(fontWeight: FontWeight.w700),
        ),
      );
    }

    final parts = <String>[];
    if (noShowCount > 0) parts.add("No-show: $noShowCount");
    if (absentCount > 0) parts.add("Absent: $absentCount");

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppThemeColors.warningDark.withValues(alpha: 0.20),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.35)),
      ),
      child: Text(
        parts.join("  "),
        style: theme.textTheme.labelSmall?.copyWith(
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _CancelBox extends StatelessWidget {
  final String reason;
  const _CancelBox({required this.reason});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppThemeColors.error.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: AppThemeColors.error.withValues(alpha: 0.22),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.info_outline,
            size: 18,
            color: AppThemeColors.error,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              reason,
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
