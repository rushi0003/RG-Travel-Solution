// lib/screens/admin/admin_styles.dart
//
// Backward-compatible bridge: redirects AdminColors/AdminStyles
// to canonical design tokens from app_theme.dart.
// Only admin_helpdesk_screen.dart still imports this file.

import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';

class AdminColors {
  static const Color bg = AppThemeColors.background;
  static const Color txt = AppThemeColors.textPrimary;
  static const Color muted = AppThemeColors.textSecondary;
  static const Color border = AppThemeColors.border;
  static const Color primary = AppThemeColors.primary;
  static const Color primary2 = AppThemeColors.secondary;
  static const Color danger = AppThemeColors.error;
  static const Color ok = AppThemeColors.success;
  static const Color card = AppThemeColors.cardGlass;

  static const LinearGradient brandGradient = LinearGradient(
    colors: [primary, primary2],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

class AdminStyles {
  static const double r1 = AppRadius.lg;
  static const double r2 = AppRadius.xl;

  static final List<BoxShadow> shadow = AppShadows.card;
  static final List<BoxShadow> glow = AppShadows.glow;

  static BoxDecoration glassBox({
    double radius = AppRadius.lg,
    Color? color,
    bool border = true,
  }) {
    return AppDecorations.glassmorphicCard(
      borderRadius: radius,
    );
  }

  static TextStyle get title => AppTypography.headlineSmall.copyWith(
    color: AppThemeColors.textPrimary,
    fontWeight: FontWeight.bold,
  );

  static TextStyle get subTitle => AppTypography.bodySmall.copyWith(
    color: AppThemeColors.textSecondary,
  );

  static TextStyle get label => AppTypography.labelSmall.copyWith(
    color: AppThemeColors.textSecondary,
  );

  static InputDecoration inputDeco(String label, {String? hint}) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      labelStyle: AppTypography.labelSmall.copyWith(color: AppThemeColors.textPrimary),
      hintStyle: AppTypography.labelSmall.copyWith(color: AppThemeColors.textTertiary),
      filled: true,
      fillColor: AppThemeColors.cardGlass,
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppThemeColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: BorderSide(color: AppThemeColors.border.withValues(alpha: 0.3)),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppThemeColors.error),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.md),
    );
  }
}
