import 'package:flutter/material.dart';

import 'ops_ui_tokens.dart';

class OpsTheme {
  const OpsTheme._();

  static ThemeData dark() {
    final base = ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
      fontFamily: OpsTypography.fontFamily,
      fontFamilyFallback: OpsTypography.fontFallback,
      colorScheme: const ColorScheme.dark(
        primary: OpsUiTokens.primary,
        onPrimary: OpsUiTokens.buttonForeground,
        secondary: OpsUiTokens.secondary,
        onSecondary: OpsUiTokens.buttonForeground,
        tertiary: OpsUiTokens.accent,
        error: OpsUiTokens.danger,
        onError: OpsUiTokens.textPrimary,
        surface: OpsUiTokens.panel,
        onSurface: OpsUiTokens.textPrimary,
      ),
      scaffoldBackgroundColor: OpsUiTokens.background,
    );

    final textTheme = base.textTheme.apply(
      fontFamily: OpsTypography.fontFamily,
      fontFamilyFallback: OpsTypography.fontFallback,
      bodyColor: OpsUiTokens.textPrimary,
      displayColor: OpsUiTokens.textPrimary,
    );

    return base.copyWith(
      textTheme: textTheme.copyWith(
        displayLarge: OpsTypography.display.copyWith(fontSize: 36),
        displayMedium: OpsTypography.display,
        displaySmall: OpsTypography.heading,
        headlineLarge: OpsTypography.heading,
        headlineMedium: OpsTypography.title,
        headlineSmall: OpsTypography.title.copyWith(fontSize: 18),
        titleLarge: OpsTypography.title,
        titleMedium: OpsTypography.subtitle.copyWith(
          color: OpsUiTokens.textPrimary,
        ),
        titleSmall: OpsTypography.bodyStrong,
        bodyLarge: OpsTypography.subtitle,
        bodyMedium: OpsTypography.body,
        bodySmall: OpsTypography.caption,
        labelLarge: OpsTypography.button,
        labelMedium: OpsTypography.caption.copyWith(
          fontWeight: FontWeight.w700,
        ),
        labelSmall: OpsTypography.caption,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: OpsUiTokens.background,
        foregroundColor: OpsUiTokens.textPrimary,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: OpsTypography.title,
      ),
      cardTheme: CardThemeData(
        color: OpsUiTokens.panel,
        elevation: 0,
        margin: EdgeInsets.zero,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(OpsRadius.xl),
          side: const BorderSide(color: OpsUiTokens.outline),
        ),
      ),
      dividerColor: OpsUiTokens.divider,
      dividerTheme: const DividerThemeData(
        color: OpsUiTokens.divider,
        thickness: 1,
        space: OpsSpacing.xxl,
      ),
      iconTheme: const IconThemeData(color: OpsUiTokens.textPrimary),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: OpsUiTokens.panelMuted,
        contentTextStyle: OpsTypography.body.copyWith(
          color: OpsUiTokens.textPrimary,
        ),
        behavior: SnackBarBehavior.floating,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(OpsRadius.md),
          side: const BorderSide(color: OpsUiTokens.outline),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: OpsUiTokens.panelMuted,
        labelStyle: OpsTypography.body.copyWith(
          color: OpsUiTokens.textSecondary,
        ),
        hintStyle: OpsTypography.body.copyWith(
          color: OpsUiTokens.textTertiary,
        ),
        helperStyle: OpsTypography.caption,
        errorStyle: OpsTypography.caption.copyWith(color: OpsUiTokens.danger),
        prefixIconColor: OpsUiTokens.textTertiary,
        suffixIconColor: OpsUiTokens.textTertiary,
        contentPadding: OpsSpacing.field,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(OpsRadius.md),
          borderSide: const BorderSide(color: OpsUiTokens.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(OpsRadius.md),
          borderSide: const BorderSide(color: OpsUiTokens.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(OpsRadius.md),
          borderSide: const BorderSide(
            color: OpsUiTokens.primary,
            width: 1.4,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(OpsRadius.md),
          borderSide: const BorderSide(color: OpsUiTokens.danger),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(OpsRadius.md),
          borderSide: const BorderSide(
            color: OpsUiTokens.danger,
            width: 1.4,
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: OpsUiTokens.primary,
          foregroundColor: OpsUiTokens.buttonForeground,
          disabledBackgroundColor: OpsUiTokens.buttonDisabled,
          disabledForegroundColor: OpsUiTokens.textTertiary,
          textStyle: OpsTypography.button,
          padding: OpsSpacing.button,
          minimumSize: const Size(0, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(OpsRadius.md),
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: OpsUiTokens.primary,
          foregroundColor: OpsUiTokens.buttonForeground,
          disabledBackgroundColor: OpsUiTokens.buttonDisabled,
          disabledForegroundColor: OpsUiTokens.textTertiary,
          elevation: 0,
          textStyle: OpsTypography.button,
          padding: OpsSpacing.button,
          minimumSize: const Size(0, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(OpsRadius.md),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: OpsUiTokens.textPrimary,
          side: const BorderSide(color: OpsUiTokens.outlineStrong),
          textStyle: OpsTypography.button,
          padding: OpsSpacing.button,
          minimumSize: const Size(0, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(OpsRadius.md),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: OpsUiTokens.primarySoft,
          textStyle: OpsTypography.button,
          padding: const EdgeInsets.symmetric(
            horizontal: OpsSpacing.lg,
            vertical: OpsSpacing.md,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(OpsRadius.sm),
          ),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: OpsUiTokens.textPrimary,
          backgroundColor: OpsUiTokens.textPrimary.withValues(alpha: 0.03),
          hoverColor: OpsUiTokens.textPrimary.withValues(alpha: 0.06),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(OpsRadius.sm),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: OpsUiTokens.panelChip,
        disabledColor: OpsUiTokens.panelMuted,
        selectedColor: OpsUiTokens.primary.withValues(alpha: 0.16),
        labelStyle: OpsTypography.caption.copyWith(
          color: OpsUiTokens.textSecondary,
          fontWeight: FontWeight.w700,
        ),
        side: const BorderSide(color: OpsUiTokens.panelChipBorder),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(OpsRadius.full),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: OpsUiTokens.panel,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(OpsRadius.xl),
          side: const BorderSide(color: OpsUiTokens.outline),
        ),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: OpsUiTokens.panel,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(OpsRadius.xl),
          ),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: OpsUiTokens.primary,
        circularTrackColor: OpsUiTokens.outline,
        linearTrackColor: OpsUiTokens.outline,
        linearMinHeight: 4,
      ),
      drawerTheme: const DrawerThemeData(
        backgroundColor: OpsUiTokens.background,
        surfaceTintColor: Colors.transparent,
      ),
      visualDensity: VisualDensity.standard,
    );
  }
}
