// flutter/lib/widgets/common/rg_button.dart
//
// RG Travel Solution — Common Button Widget
// Reusable across Admin/Driver/Employee screens.
//
// Features:
// - Variants: primary, secondary, outline, danger
// - Loading state with spinner
// - Disabled state
// - Optional icon
// - Full width option
// - Clean, modern style (works in dark theme)

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

enum RGButtonVariant { primary, secondary, outline, danger }

class RGButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;

  /// Show loading spinner and disable button
  final bool isLoading;

  /// Explicit disabled state
  final bool isDisabled;

  /// Button variant
  final RGButtonVariant variant;

  /// Optional leading icon
  final IconData? icon;

  /// Full width button
  final bool fullWidth;

  /// Custom height
  final double height;

  /// Border radius
  final double radius;

  /// Text style override (optional)
  final TextStyle? textStyle;

  /// Padding override (optional)
  final EdgeInsetsGeometry? padding;

  const RGButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.isLoading = false,
    this.isDisabled = false,
    this.variant = RGButtonVariant.primary,
    this.icon,
    this.fullWidth = true,
    this.height = 48,
    this.radius = AppRadius.md,
    this.textStyle,
    this.padding,
  });

  bool get _effectiveDisabled => isDisabled || isLoading || onPressed == null;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final colors = _resolveColors(theme, variant);
    final bgColor = _effectiveDisabled ? colors.disabledBg : colors.bg;
    final fgColor = _effectiveDisabled ? colors.disabledFg : colors.fg;
    final borderColor =
        _effectiveDisabled ? colors.disabledBorder : colors.border;

    final child = _buildChild(theme, fgColor);

    final btnStyle = ButtonStyle(
      minimumSize: WidgetStateProperty.all(
        Size(fullWidth ? double.infinity : 0, height),
      ),
      padding: WidgetStateProperty.all(
        padding ?? AppSpacing.buttonPadding,
      ),
      elevation: WidgetStateProperty.all(0),
      backgroundColor: WidgetStateProperty.all(
        variant == RGButtonVariant.outline ? Colors.transparent : bgColor,
      ),
      foregroundColor: WidgetStateProperty.all(fgColor),
      overlayColor: WidgetStateProperty.all(
        fgColor.withValues(alpha: 0.08),
      ),
      shape: WidgetStateProperty.all(
        RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radius),
          side: BorderSide(
            color: variant == RGButtonVariant.outline
                ? borderColor
                : Colors.transparent,
            width: 1.2,
          ),
        ),
      ),
    );

    return AnimatedOpacity(
      duration: const Duration(milliseconds: 160),
      opacity: _effectiveDisabled ? 0.72 : 1.0,
      child: variant == RGButtonVariant.outline
          ? OutlinedButton(
              onPressed: _effectiveDisabled ? null : onPressed,
              style: btnStyle,
              child: child,
            )
          : ElevatedButton(
              onPressed: _effectiveDisabled ? null : onPressed,
              style: btnStyle,
              child: child,
            ),
    );
  }

  Widget _buildChild(ThemeData theme, Color fgColor) {
    final textWidget = Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: textStyle ??
          theme.textTheme.labelLarge?.copyWith(
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
            color: fgColor,
          ),
    );

    if (isLoading) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(
              strokeWidth: 2.2,
              valueColor: AlwaysStoppedAnimation<Color>(fgColor),
            ),
          ),
          const SizedBox(width: 10),
          textWidget,
        ],
      );
    }

    if (icon != null) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 18, color: fgColor),
          const SizedBox(width: 10),
          textWidget,
        ],
      );
    }

    return Center(child: textWidget);
  }

  _RGButtonColors _resolveColors(ThemeData theme, RGButtonVariant v) {
    // Base colors (dark theme friendly)
    final primary = theme.colorScheme.primary;
    final onPrimary = theme.colorScheme.onPrimary;
    final surface = theme.colorScheme.surface;
    final onSurface = theme.colorScheme.onSurface;

    switch (v) {
      case RGButtonVariant.primary:
        return _RGButtonColors(
          bg: primary,
          fg: onPrimary,
          border: primary,
          disabledBg: primary.withValues(alpha: 0.35),
          disabledFg: onPrimary.withValues(alpha: 0.65),
          disabledBorder: primary.withValues(alpha: 0.25),
        );

      case RGButtonVariant.secondary:
        // Slightly muted surface button
        return _RGButtonColors(
          bg: surface.withValues(alpha: 0.35),
          fg: onSurface,
          border: surface.withValues(alpha: 0.4),
          disabledBg: surface.withValues(alpha: 0.2),
          disabledFg: onSurface.withValues(alpha: 0.5),
          disabledBorder: surface.withValues(alpha: 0.2),
        );

      case RGButtonVariant.outline:
        return _RGButtonColors(
          bg: Colors.transparent,
          fg: onSurface,
          border: theme.dividerColor.withValues(alpha: 0.7),
          disabledBg: Colors.transparent,
          disabledFg: onSurface.withValues(alpha: 0.5),
          disabledBorder: theme.dividerColor.withValues(alpha: 0.3),
        );

      case RGButtonVariant.danger:
        final danger = theme.colorScheme.error;
        final onDanger = theme.colorScheme.onError;
        return _RGButtonColors(
          bg: danger,
          fg: onDanger,
          border: danger,
          disabledBg: danger.withValues(alpha: 0.35),
          disabledFg: onDanger.withValues(alpha: 0.7),
          disabledBorder: danger.withValues(alpha: 0.25),
        );
    }
  }
}

class _RGButtonColors {
  final Color bg;
  final Color fg;
  final Color border;

  final Color disabledBg;
  final Color disabledFg;
  final Color disabledBorder;

  const _RGButtonColors({
    required this.bg,
    required this.fg,
    required this.border,
    required this.disabledBg,
    required this.disabledFg,
    required this.disabledBorder,
  });
}
