// flutter/lib/widgets/common/rg_empty_state.dart
//
// RG Travel Solution — Empty State Widget
//
// ✅ Features:
// - Icon + message + optional description
// - Optional action button
// - Consistent glassmorphism styling
// - Fade-in animation

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Empty list/data placeholder with icon, message, and optional action.
///
/// Usage:
/// ```dart
/// RGEmptyState(
///   icon: Icons.inbox_rounded,
///   title: 'No trips found',
///   subtitle: 'Create a new trip to get started',
///   actionLabel: 'Create Trip',
///   onAction: () => _createTrip(),
/// )
/// ```
class RGEmptyState extends StatefulWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final String? actionLabel;
  final VoidCallback? onAction;
  final double iconSize;

  const RGEmptyState({
    super.key,
    this.icon = Icons.inbox_rounded,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onAction,
    this.iconSize = 56,
  });

  @override
  State<RGEmptyState> createState() => _RGEmptyStateState();
}

class _RGEmptyStateState extends State<RGEmptyState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AppAnimations.slow,
    )..forward();
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: AppAnimations.gentleCurve,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: Center(
        child: Padding(
          padding: AppSpacing.pagePadding,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Icon container with subtle glow
              Container(
                width: widget.iconSize + 32,
                height: widget.iconSize + 32,
                decoration: BoxDecoration(
                  color: AppThemeColors.surfaceLight,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: AppThemeColors.border,
                  ),
                ),
                child: Icon(
                  widget.icon,
                  size: widget.iconSize,
                  color: AppThemeColors.textTertiary,
                ),
              ),

              const SizedBox(height: AppSpacing.lg),

              // Title
              Text(
                widget.title,
                textAlign: TextAlign.center,
                style: AppTypography.headlineMedium.copyWith(
                  color: AppThemeColors.textPrimary,
                ),
              ),

              // Subtitle
              if (widget.subtitle != null && widget.subtitle!.trim().isNotEmpty) ...[
                const SizedBox(height: AppSpacing.sm),
                Text(
                  widget.subtitle!,
                  textAlign: TextAlign.center,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
              ],

              // Action button
              if (widget.actionLabel != null && widget.onAction != null) ...[
                const SizedBox(height: AppSpacing.lg),
                OutlinedButton.icon(
                  onPressed: widget.onAction,
                  icon: const Icon(Icons.add_rounded, size: AppIconSizes.sm),
                  label: Text(widget.actionLabel!),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppThemeColors.primary,
                    side: BorderSide(
                      color: AppThemeColors.primary.withValues(alpha: 0.4),
                    ),
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.lg,
                      vertical: AppSpacing.sm + 4,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

