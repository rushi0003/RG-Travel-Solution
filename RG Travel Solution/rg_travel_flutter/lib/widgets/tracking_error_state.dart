import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

/// Reusable error state widgets for tracking screens

class TrackingErrorState extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final IconData icon;
  final Color color;

  const TrackingErrorState({
    super.key,
    required this.message,
    this.onRetry,
    this.icon = Icons.error_outline,
    this.color = AppThemeColors.error,
  });

  factory TrackingErrorState.offline({VoidCallback? onRetry}) {
    return TrackingErrorState(
      message: 'No internet connection',
      icon: Icons.wifi_off,
      color: AppThemeColors.warning,
      onRetry: onRetry,
    );
  }

  factory TrackingErrorState.staleGPS({VoidCallback? onRetry}) {
    return TrackingErrorState(
      message: 'GPS signal lost\nShowing last known location',
      icon: Icons.gps_off,
      color: AppThemeColors.warning,
      onRetry: onRetry,
    );
  }

  factory TrackingErrorState.noData({VoidCallback? onRetry}) {
    return TrackingErrorState(
      message: 'Waiting for driver location...',
      icon: Icons.location_searching,
      color: AppThemeColors.info,
      onRetry: onRetry,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 64, color: color),
          const SizedBox(height: 16),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, color: color),
          ),
          if (onRetry != null) ...[
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: color,
                foregroundColor: AppThemeColors.textPrimary,
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Offline banner widget
class OfflineBanner extends StatelessWidget {
  final DateTime? lastUpdate;

  const OfflineBanner({super.key, this.lastUpdate});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      color: AppThemeColors.warning.withValues(alpha: 0.9),
      child: Row(
        children: [
          const Icon(Icons.cloud_off,
              color: AppThemeColors.textPrimary, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              lastUpdate != null
                  ? 'Offline • Last update: ${_formatTime(lastUpdate!)}'
                  : 'Reconnecting...',
              style: const TextStyle(
                  color: AppThemeColors.textPrimary, fontSize: 12),
            ),
          ),
          const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation(AppThemeColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }
}

/// Stale GPS indicator overlay
class StaleGPSIndicator extends StatelessWidget {
  final DateTime lastUpdate;

  const StaleGPSIndicator({super.key, required this.lastUpdate});

  @override
  Widget build(BuildContext context) {
    final secondsSinceUpdate = DateTime.now().difference(lastUpdate).inSeconds;

    if (secondsSinceUpdate < 60) {
      return const SizedBox.shrink(); // No indicator if fresh
    }

    return Positioned(
      top: 100,
      left: 16,
      right: 16,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: AppThemeColors.warning.withValues(alpha: 0.95),
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(
              color: AppThemeColors.background.withValues(alpha: 0.2),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            const Icon(Icons.warning,
                color: AppThemeColors.textPrimary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'GPS signal weak • Last update ${secondsSinceUpdate}s ago',
                style: const TextStyle(
                    color: AppThemeColors.textPrimary, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
