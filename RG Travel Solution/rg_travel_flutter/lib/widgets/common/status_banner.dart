// lib/widgets/common/status_banner.dart
//
// RG Travel Solution — Status Banner
//
// Displays success/error messages with appropriate styling

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

enum StatusType { success, error }

class StatusBanner extends StatelessWidget {
  const StatusBanner({
    super.key,
    required this.message,
    required this.type,
    this.onDismiss,
  });

  final String message;
  final StatusType type;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final isSuccess = type == StatusType.success;
    final color = isSuccess ? AppThemeColors.success : AppThemeColors.error;
    final icon = isSuccess ? Icons.check_circle_outline : Icons.error_outline;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withValues(alpha: 0.35),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: color,
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (onDismiss != null) ...[
            const SizedBox(width: 8),
            InkWell(
              onTap: onDismiss,
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: Icon(
                  Icons.close,
                  color: AppThemeColors.textSecondary,
                  size: 18,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
