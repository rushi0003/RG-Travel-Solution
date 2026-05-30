// flutter/lib/widgets/common/glassmorphic_card.dart
//
// RG Travel Solution — Modern Glassmorphism Card
//
// ✅ Features:
// - Frosted glass effect with backdrop blur
// - Smooth gradient backgrounds
// - Subtle shadows and borders
// - Hover and tap animations
// - Accessibility support

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';

class GlassmorphicCard extends StatefulWidget {
  /// Card content
  final Widget child;

  /// Optional card title
  final String? title;

  /// Optional title icon
  final IconData? titleIcon;

  /// Optional subtitle
  final String? subtitle;

  /// Optional card header action (e.g., more menu, settings)
  final Widget? headerAction;

  /// Tap callback
  final VoidCallback? onTap;

  /// Padding inside card
  final EdgeInsetsGeometry padding;

  /// Border radius
  final double radius;

  /// Backdrop blur amount (0 = no blur)
  final double blurAmount;

  /// Enable hover effect
  final bool enableHover;

  /// Custom border color override
  final Color? borderColor;

  /// Custom background color override
  final Color? backgroundColor;

  /// Minimum height
  final double? minHeight;

  /// Shadow elevation (0 = no shadow)
  final double elevation;

  /// Loading state
  final bool isLoading;

  /// Gradient background for accent
  final Gradient? gradient;

  const GlassmorphicCard({
    super.key,
    required this.child,
    this.title,
    this.titleIcon,
    this.subtitle,
    this.headerAction,
    this.onTap,
    this.padding = const EdgeInsets.all(16),
    this.radius = 16,
    this.blurAmount = 8,
    this.enableHover = true,
    this.borderColor,
    this.backgroundColor,
    this.minHeight,
    this.elevation = 0,
    this.isLoading = false,
    this.gradient,
  });

  @override
  State<GlassmorphicCard> createState() => _GlassmorphicCardState();
}

class _GlassmorphicCardState extends State<GlassmorphicCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _hoverController;
  late Animation<double> _hoverAnimation;

  @override
  void initState() {
    super.initState();
    _hoverController = AnimationController(
      duration: AppAnimations.fast,
      vsync: this,
    );
    _hoverAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _hoverController, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _hoverController.dispose();
    super.dispose();
  }

  void _onHoverChange(bool isHovering) {
    if (!widget.enableHover) return;
    if (isHovering) {
      _hoverController.forward();
    } else {
      _hoverController.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    final borderRadius = BorderRadius.circular(widget.radius);

    return MouseRegion(
      onEnter: (_) => _onHoverChange(true),
      onExit: (_) => _onHoverChange(false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedBuilder(
          animation: _hoverAnimation,
          builder: (context, child) {
            return Container(
              constraints: widget.minHeight != null
                  ? BoxConstraints(minHeight: widget.minHeight!)
                  : null,
              decoration: BoxDecoration(
                borderRadius: borderRadius,
                boxShadow: [
                  BoxShadow(
                    color: AppThemeColors.background
                        .withValues(alpha: 0.1 + _hoverAnimation.value * 0.1),
                    blurRadius: 8 + _hoverAnimation.value * 4,
                    offset: Offset(0, 2 + _hoverAnimation.value * 2),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: borderRadius,
                child: Stack(
                  children: [
                    /// Backdrop blur effect
                    if (widget.blurAmount > 0)
                      BackdropFilter(
                        filter: ImageFilter.blur(
                          sigmaX: widget.blurAmount,
                          sigmaY: widget.blurAmount,
                        ),
                        child: Container(),
                      ),

                    /// Glassmorphic background
                    Container(
                      decoration: BoxDecoration(
                        gradient: widget.gradient ??
                            LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                (widget.backgroundColor ??
                                        AppThemeColors.surface)
                                    .withValues(
                                        alpha:
                                            0.7 + _hoverAnimation.value * 0.1),
                                (widget.backgroundColor ??
                                        AppThemeColors.surfaceLight)
                                    .withValues(
                                        alpha:
                                            0.5 + _hoverAnimation.value * 0.1),
                              ],
                            ),
                        border: Border.all(
                          color: (widget.borderColor ?? AppThemeColors.border)
                              .withValues(
                                  alpha: 0.4 + _hoverAnimation.value * 0.2),
                          width: 1.5,
                        ),
                      ),
                    ),

                    /// Content
                    SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          /// Header (title + action)
                          if (widget.title != null ||
                              widget.headerAction != null)
                            Padding(
                              padding: EdgeInsets.fromLTRB(
                                widget.padding.resolve(TextDirection.ltr).left,
                                widget.padding.resolve(TextDirection.ltr).top,
                                widget.padding.resolve(TextDirection.ltr).right,
                                widget.subtitle != null ? 8 : 12,
                              ),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  if (widget.titleIcon != null)
                                    Padding(
                                      padding: const EdgeInsets.only(right: 8),
                                      child: Icon(
                                        widget.titleIcon,
                                        color: AppThemeColors.primary,
                                        size: 22,
                                      ),
                                    ),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          widget.title ?? '',
                                          style: AppTypography.headlineMedium
                                              .copyWith(
                                            color: AppThemeColors.textPrimary,
                                          ),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        if (widget.subtitle != null)
                                          Padding(
                                            padding:
                                                const EdgeInsets.only(top: 4),
                                            child: Text(
                                              widget.subtitle!,
                                              style: AppTypography.bodySmall
                                                  .copyWith(
                                                color:
                                                    AppThemeColors.textTertiary,
                                              ),
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                  if (widget.headerAction != null)
                                    Padding(
                                      padding: const EdgeInsets.only(left: 12),
                                      child: widget.headerAction,
                                    ),
                                ],
                              ),
                            ),

                          /// Divider
                          if (widget.title != null ||
                              widget.headerAction != null)
                            Padding(
                              padding: EdgeInsets.symmetric(
                                horizontal: widget.padding
                                    .resolve(TextDirection.ltr)
                                    .left,
                              ),
                              child: Divider(
                                color: AppThemeColors.border
                                    .withValues(alpha: 0.3),
                                thickness: 1,
                                height: 16,
                              ),
                            ),

                          /// Body content
                          if (widget.isLoading)
                            Padding(
                              padding: widget.padding,
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const SizedBox(height: 24),
                                  CircularProgressIndicator(
                                    color: AppThemeColors.primary,
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    'Loading...',
                                    style: AppTypography.bodyMedium.copyWith(
                                      color: AppThemeColors.textSecondary,
                                    ),
                                  ),
                                  const SizedBox(height: 24),
                                ],
                              ),
                            )
                          else
                            Padding(
                              padding: widget.padding,
                              child: widget.child,
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Compact glassmorphic card (minimal padding, no header)
class CompactGlassmorphicCard extends StatelessWidget {
  final Widget child;
  final VoidCallback? onTap;
  final double radius;
  final double blurAmount;
  final Color? borderColor;
  final Color? backgroundColor;
  final double? minHeight;

  const CompactGlassmorphicCard({
    super.key,
    required this.child,
    this.onTap,
    this.radius = 12,
    this.blurAmount = 6,
    this.borderColor,
    this.backgroundColor,
    this.minHeight,
  });

  @override
  Widget build(BuildContext context) {
    return GlassmorphicCard(
      child: child,
      onTap: onTap,
      radius: radius,
      blurAmount: blurAmount,
      borderColor: borderColor,
      backgroundColor: backgroundColor,
      minHeight: minHeight,
      padding: const EdgeInsets.all(12),
      elevation: 0,
      enableHover: true,
    );
  }
}
