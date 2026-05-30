// flutter/lib/widgets/common/rg_error_view.dart
//
// RG Travel Solution — Error View Widget
//
// ✅ Features:
// - Error icon + message
// - Retry button
// - Glassmorphism card styling
// - Fade-in animation

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Error state with message and retry button.
///
/// Usage:
/// ```dart
/// RGErrorView(
///   message: 'Failed to load trips',
///   onRetry: () => _fetchTrips(),
/// )
/// ```
class RGErrorView extends StatefulWidget {
  final String message;
  final String? details;
  final VoidCallback? onRetry;
  final IconData icon;
  final bool compact;

  const RGErrorView({
    super.key,
    this.message = 'Something went wrong',
    this.details,
    this.onRetry,
    this.icon = Icons.error_outline_rounded,
    this.compact = false,
  });

  @override
  State<RGErrorView> createState() => _RGErrorViewState();
}

class _RGErrorViewState extends State<RGErrorView>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AppAnimations.normal,
    )..forward();
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: AppAnimations.defaultCurve,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.compact) return _buildCompact();
    return _buildFull();
  }

  Widget _buildFull() {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: Center(
        child: Padding(
          padding: AppSpacing.pagePadding,
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.lg),
            decoration: AppDecorations.glassmorphicCard(
              borderRadius: AppRadius.lg,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Error icon
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: AppThemeColors.error.withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppThemeColors.error.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Icon(
                    widget.icon,
                    size: 32,
                    color: AppThemeColors.error,
                  ),
                ),

                const SizedBox(height: AppSpacing.md),

                // Error message
                Text(
                  widget.message,
                  textAlign: TextAlign.center,
                  style: AppTypography.headlineMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                  ),
                ),

                // Details
                if (widget.details != null &&
                    widget.details!.trim().isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    widget.details!,
                    textAlign: TextAlign.center,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textTertiary,
                    ),
                  ),
                ],

                // Retry button
                if (widget.onRetry != null) ...[
                  const SizedBox(height: AppSpacing.lg),
                  ElevatedButton.icon(
                    onPressed: widget.onRetry,
                    icon: const Icon(Icons.refresh_rounded,
                        size: AppIconSizes.sm),
                    label: const Text('Retry'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppThemeColors.primary,
                      foregroundColor: AppThemeColors.background,
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.lg,
                        vertical: AppSpacing.sm + 2,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.xs),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Compact inline error (for use inside lists/cards)
  Widget _buildCompact() {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        child: Row(
          children: [
            Icon(
              widget.icon,
              size: AppIconSizes.sm,
              color: AppThemeColors.error,
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                widget.message,
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.error,
                ),
              ),
            ),
            if (widget.onRetry != null)
              TextButton(
                onPressed: widget.onRetry,
                style: TextButton.styleFrom(
                  foregroundColor: AppThemeColors.primary,
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm,
                  ),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text('Retry'),
              ),
          ],
        ),
      ),
    );
  }
}

