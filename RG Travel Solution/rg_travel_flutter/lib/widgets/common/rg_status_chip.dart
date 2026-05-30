// flutter/lib/widgets/common/rg_status_chip.dart
//
// RG Travel Solution — Status Chip Widget
//
// ✅ Features:
// - Semantic color mapping for trip/request statuses
// - Dot indicator + label
// - Consistent glassmorphism styling

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Status badge with semantic colors for various states.
///
/// Usage:
/// ```dart
/// RGStatusChip(label: 'Active', type: RGStatusType.active)
/// RGStatusChip.fromString('completed')
/// ```
enum RGStatusType {
  active,
  pending,
  completed,
  cancelled,
  error,
  info,
  warning,
}

class RGStatusChip extends StatelessWidget {
  final String label;
  final RGStatusType type;
  final bool showDot;
  final double? fontSize;

  const RGStatusChip({
    super.key,
    required this.label,
    this.type = RGStatusType.info,
    this.showDot = true,
    this.fontSize,
  });

  /// Create a status chip from a string status value.
  /// Maps common status strings to [RGStatusType].
  factory RGStatusChip.fromString(String status) {
    final normalized = status.trim().toLowerCase().replaceAll('_', '');
    final RGStatusType type;
    switch (normalized) {
      case 'active':
      case 'started':
      case 'inprogress':
      case 'online':
      case 'approved':
        type = RGStatusType.active;
        break;
      case 'pending':
      case 'assigned':
      case 'waiting':
        type = RGStatusType.pending;
        break;
      case 'completed':
      case 'done':
      case 'finished':
        type = RGStatusType.completed;
        break;
      case 'cancelled':
      case 'rejected':
      case 'failed':
        type = RGStatusType.cancelled;
        break;
      case 'error':
        type = RGStatusType.error;
        break;
      case 'warning':
        type = RGStatusType.warning;
        break;
      default:
        type = RGStatusType.info;
    }

    // Capitalize first letter for display
    final label = status.isNotEmpty
        ? '${status[0].toUpperCase()}${status.substring(1).replaceAll('_', ' ')}'
        : status;

    return RGStatusChip(label: label, type: type);
  }

  Color get _color {
    switch (type) {
      case RGStatusType.active:
        return AppThemeColors.success;
      case RGStatusType.pending:
        return AppThemeColors.warning;
      case RGStatusType.completed:
        return AppThemeColors.info;
      case RGStatusType.cancelled:
        return AppThemeColors.error;
      case RGStatusType.error:
        return AppThemeColors.error;
      case RGStatusType.warning:
        return AppThemeColors.warning;
      case RGStatusType.info:
        return AppThemeColors.info;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm + 2,
        vertical: AppSpacing.xs,
      ),
      decoration: AppDecorations.statusChip(_color),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: _color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
          ],
          Text(
            label,
            style: AppTypography.labelSmall.copyWith(
              color: _color,
              fontSize: fontSize,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
