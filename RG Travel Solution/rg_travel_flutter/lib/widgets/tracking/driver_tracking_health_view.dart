import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class DriverTrackingHealthView extends StatelessWidget {
  const DriverTrackingHealthView({
    super.key,
    required this.isOnline,
    required this.socketConnected,
    required this.trackingHealthError,
    required this.onRetryNow,
    this.trackingHealthMessage,
    this.lastLocationUploadAt,
    this.lastUploadServerCode,
    this.now,
  });

  final bool isOnline;
  final bool socketConnected;
  final bool trackingHealthError;
  final VoidCallback onRetryNow;
  final String? trackingHealthMessage;
  final DateTime? lastLocationUploadAt;
  final int? lastUploadServerCode;
  final DateTime? now;

  @override
  Widget build(BuildContext context) {
    if (!isOnline) {
      return const SizedBox.shrink();
    }

    final message = trackingHealthMessage ??
        (lastLocationUploadAt != null
            ? 'Last sync ${_timeAgo(lastLocationUploadAt!)}'
            : (socketConnected
                ? 'Waiting for first location sync...'
                : 'Socket connecting...'));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 4),
        Text(
          message,
          style: AppTypography.labelSmall.copyWith(
            color: trackingHealthError
                ? AppThemeColors.warning
                : AppThemeColors.textTertiary,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            if (lastUploadServerCode != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppThemeColors.cardGlass,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppThemeColors.border),
                ),
                child: Text(
                  'HTTP $lastUploadServerCode',
                  style: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.textSecondary),
                ),
              ),
            const Spacer(),
            TextButton(
              onPressed: onRetryNow,
              style: TextButton.styleFrom(
                foregroundColor: AppThemeColors.primary,
                minimumSize: const Size(10, 28),
                padding: const EdgeInsets.symmetric(horizontal: 8),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text(
                'Retry now',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
      ],
    );
  }

  String _timeAgo(DateTime dt) {
    final baseline = now ?? DateTime.now();
    final seconds = baseline.difference(dt).inSeconds;
    if (seconds < 60) {
      return '${seconds}s ago';
    }
    return '${seconds ~/ 60}m ago';
  }
}
