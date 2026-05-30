// flutter/lib/widgets/common/modern_button.dart
//
// RG Travel Solution — Modern Material 3 Buttons
//
// ✅ Features:
// - Primary, secondary, outline, ghost variants
// - Loading and disabled states
// - Flexible sizing
// - Icon support
// - Accessibility labels
// - Smooth animations

import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';

enum ModernButtonVariant {
  primary,
  secondary,
  outline,
  ghost,
}

enum ModernButtonSize {
  small,
  medium,
  large,
}

/// Modern Material 3 button with glassmorphism support
class ModernButton extends StatefulWidget {
  /// Button label text
  final String label;

  /// Callback when pressed
  final VoidCallback? onPressed;

  /// Button variant
  final ModernButtonVariant variant;

  /// Button size
  final ModernButtonSize size;

  /// Optional leading icon
  final IconData? leadingIcon;

  /// Optional trailing icon
  final IconData? trailingIcon;

  /// Show loading spinner and disable button
  final bool isLoading;

  /// Disable button
  final bool isDisabled;

  /// Full width
  final bool fullWidth;

  /// Custom semantic tooltip
  final String? tooltip;

  /// Semantic label for accessibility
  final String? semanticLabel;

  const ModernButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = ModernButtonVariant.primary,
    this.size = ModernButtonSize.medium,
    this.leadingIcon,
    this.trailingIcon,
    this.isLoading = false,
    this.isDisabled = false,
    this.fullWidth = false,
    this.tooltip,
    this.semanticLabel,
  });

  @override
  State<ModernButton> createState() => _ModernButtonState();
}

class _ModernButtonState extends State<ModernButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _pressController;

  @override
  void initState() {
    super.initState();
    _pressController = AnimationController(
      duration: AppAnimations.fast,
      vsync: this,
    );
  }

  @override
  void dispose() {
    _pressController.dispose();
    super.dispose();
  }

  void _onPointerDown(PointerDownEvent event) {
    if (!widget.isLoading && !widget.isDisabled) {
      _pressController.forward();
    }
  }

  void _onPointerUp(PointerUpEvent event) {
    _pressController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    final isDisabled = widget.isDisabled || widget.isLoading || widget.onPressed == null;

    return Listener(
      onPointerDown: _onPointerDown,
      onPointerUp: _onPointerUp,
      child: Tooltip(
        message: widget.tooltip ?? widget.label,
        child: Semantics(
          enabled: !isDisabled,
          button: true,
          label: widget.semanticLabel ?? widget.label,
          onTap: isDisabled ? null : widget.onPressed,
          child: ScaleTransition(
            scale: Tween<double>(begin: 1.0, end: 0.96)
                .animate(_pressController),
            child: _buildButton(isDisabled),
          ),
        ),
      ),
    );
  }

  Widget _buildButton(bool isDisabled) {
    return switch (widget.variant) {
      ModernButtonVariant.primary => _buildPrimaryButton(isDisabled),
      ModernButtonVariant.secondary => _buildSecondaryButton(isDisabled),
      ModernButtonVariant.outline => _buildOutlineButton(isDisabled),
      ModernButtonVariant.ghost => _buildGhostButton(isDisabled),
    };
  }

  Widget _buildPrimaryButton(bool isDisabled) {
    final (height, padding, textStyle, iconSize) = _getSizeValues();

    return Container(
      constraints: BoxConstraints(
        minHeight: height,
        minWidth: widget.fullWidth ? double.infinity : 0,
      ),
      decoration: BoxDecoration(
        gradient: isDisabled
            ? null
            : LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppThemeColors.primary,
                  AppThemeColors.primaryDark,
                ],
              ),
        color: isDisabled ? AppThemeColors.textDisabled : null,
        borderRadius: BorderRadius.circular(AppRadius.xs),
        boxShadow: [
          if (!isDisabled)
            BoxShadow(
              color: AppThemeColors.primary.withValues(alpha: 0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: BorderRadius.circular(AppRadius.xs),
          splashColor: AppThemeColors.background.withValues(alpha: 0.2),
          highlightColor: AppThemeColors.background.withValues(alpha: 0.1),
          child: Padding(
            padding: padding,
            child: _buildButtonContent(
              height,
              textStyle,
              iconSize,
              isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSecondaryButton(bool isDisabled) {
    final (height, padding, textStyle, iconSize) = _getSizeValues();

    return Container(
      constraints: BoxConstraints(
        minHeight: height,
        minWidth: widget.fullWidth ? double.infinity : 0,
      ),
      decoration: BoxDecoration(
        color: isDisabled
            ? AppThemeColors.textDisabled.withValues(alpha: 0.1)
            : AppThemeColors.secondary.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(AppRadius.xs),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: BorderRadius.circular(AppRadius.xs),
          splashColor: AppThemeColors.secondary.withValues(alpha: 0.2),
          highlightColor: AppThemeColors.secondary.withValues(alpha: 0.1),
          child: Padding(
            padding: padding,
            child: _buildButtonContent(
              height,
              textStyle.copyWith(
                color: isDisabled
                    ? AppThemeColors.textDisabled
                    : AppThemeColors.secondary,
              ),
              iconSize,
              isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildOutlineButton(bool isDisabled) {
    final (height, padding, textStyle, iconSize) = _getSizeValues();

    return Container(
      constraints: BoxConstraints(
        minHeight: height,
        minWidth: widget.fullWidth ? double.infinity : 0,
      ),
      decoration: BoxDecoration(
        border: Border.all(
          color: isDisabled
              ? AppThemeColors.border
              : AppThemeColors.primary,
          width: 1.5,
        ),
        borderRadius: BorderRadius.circular(AppRadius.xs),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: BorderRadius.circular(AppRadius.xs),
          splashColor: AppThemeColors.primary.withValues(alpha: 0.1),
          highlightColor: AppThemeColors.primary.withValues(alpha: 0.05),
          child: Padding(
            padding: padding,
            child: _buildButtonContent(
              height,
              textStyle.copyWith(
                color: isDisabled
                    ? AppThemeColors.textDisabled
                    : AppThemeColors.primary,
              ),
              iconSize,
              isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildGhostButton(bool isDisabled) {
    final (height, padding, textStyle, iconSize) = _getSizeValues();

    return Container(
      constraints: BoxConstraints(
        minHeight: height,
        minWidth: widget.fullWidth ? double.infinity : 0,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isDisabled ? null : widget.onPressed,
          borderRadius: BorderRadius.circular(AppRadius.xs),
          splashColor: AppThemeColors.primary.withValues(alpha: 0.1),
          highlightColor: AppThemeColors.primary.withValues(alpha: 0.05),
          child: Padding(
            padding: padding,
            child: _buildButtonContent(
              height,
              textStyle.copyWith(
                color: isDisabled
                    ? AppThemeColors.textDisabled
                    : AppThemeColors.textPrimary,
              ),
              iconSize,
              isDisabled,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildButtonContent(
    double height,
    TextStyle textStyle,
    double iconSize,
    bool isDisabled,
  ) {
    if (widget.isLoading) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: iconSize,
            height: iconSize,
            child: CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(textStyle.color!),
              strokeWidth: 2,
            ),
          ),
          SizedBox(width: widget.label.isNotEmpty ? 8 : 0),
          if (widget.label.isNotEmpty)
            Text(widget.label, style: textStyle),
        ],
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.leadingIcon != null)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Icon(
              widget.leadingIcon,
              size: iconSize,
              color: textStyle.color,
            ),
          ),
        Flexible(
          child: Text(
            widget.label,
            style: textStyle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (widget.trailingIcon != null)
          Padding(
            padding: const EdgeInsets.only(left: 8),
            child: Icon(
              widget.trailingIcon,
              size: iconSize,
              color: textStyle.color,
            ),
          ),
      ],
    );
  }

  (double, EdgeInsetsGeometry, TextStyle, double) _getSizeValues() {
    return switch (widget.size) {
      ModernButtonSize.small => (
        36,
        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        AppTypography.labelMedium,
        16,
      ),
      ModernButtonSize.medium => (
        44,
        const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        AppTypography.labelLarge,
        18,
      ),
      ModernButtonSize.large => (
        52,
        const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        AppTypography.headlineSmall,
        20,
      ),
    };
  }
}

/// Quick primary button
class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool fullWidth;
  final IconData? leadingIcon;

  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.fullWidth = true,
    this.leadingIcon,
  });

  @override
  Widget build(BuildContext context) {
    return ModernButton(
      label: label,
      onPressed: onPressed,
      variant: ModernButtonVariant.primary,
      size: ModernButtonSize.medium,
      isLoading: isLoading,
      fullWidth: fullWidth,
      leadingIcon: leadingIcon,
    );
  }
}

/// Quick secondary button
class SecondaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool fullWidth;
  final IconData? leadingIcon;

  const SecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.fullWidth = true,
    this.leadingIcon,
  });

  @override
  Widget build(BuildContext context) {
    return ModernButton(
      label: label,
      onPressed: onPressed,
      variant: ModernButtonVariant.secondary,
      size: ModernButtonSize.medium,
      fullWidth: fullWidth,
      leadingIcon: leadingIcon,
    );
  }
}

