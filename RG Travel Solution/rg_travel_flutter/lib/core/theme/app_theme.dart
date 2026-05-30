// flutter/lib/core/theme/app_theme.dart
//
// RG Travel Solution — Material 3 Glassmorphism Theme
//
// ✅ Design System:
// - Material 3 with dark glassmorphism aesthetic
// - Consistent 8px grid spacing system
// - Accessibility-first colors (WCAG AA compliant)
// - Responsive typography
// - Smooth animations and transitions

import 'package:flutter/material.dart';

/// Modern glassmorphism color palette
/// All colors must meet WCAG AA accessibility standards (minimum 4.5:1 contrast)
abstract class AppThemeColors {
  AppThemeColors._();

  // ═══════════════════════ PRIMARY ═══════════════════════
  /// Vibrant cyan - primary action, highlights, active states
  static const Color primary = Color(0xFF00D1FF);
  static const Color primaryLight = Color(0xFF8BE9FD);
  static const Color primaryDark = Color(0xFF009CBD);

  // ═══════════════════════ SECONDARY ═══════════════════════
  /// Elegant violet - emphasis, secondary actions
  static const Color secondary = Color(0xFF34D399);
  static const Color secondaryLight = Color(0xFF6EE7B7);
  static const Color secondaryDark = Color(0xFF059669);

  // ═══════════════════════ BACKGROUNDS & SURFACES ═══════════════════════
  /// Deep navy-black - main background
  static const Color background = Color(0xFF08111F);

  /// Slightly lighter for secondary areas
  static const Color backgroundLight = Color(0xFF091726);

  /// Sheet/surface background with opacity
  static const Color surface = Color(0xFF0F172A);
  static const Color surfaceLight = Color(0xFF111827);
  static const Color surfaceLighter = Color(0xFF1E293B);

  /// Glassmorphism frosted effect (semi-transparent layers)
  static const Color cardGlass = Color(0x0DFFFFFF); // 5% white overlay
  static const Color cardGlassHover = Color(0x12FFFFFF); // 7% white overlay
  static const Color cardGlassActive = Color(0x1AFFFFFF); // 10% white overlay

  // ═══════════════════════ TEXT ═══════════════════════
  /// Primary text - high contrast
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFFCBD5E1);
  static const Color textTertiary = Color(0xFF94A3B8);
  static const Color textDisabled = Color(0xFF64748B);

  // ═══════════════════════ SEMANTIC COLORS ═══════════════════════
  static const Color success = Color(0xFF34D399);
  static const Color successLight = Color(0xFF34D399);
  static const Color successDark = Color(0xFF059669);

  static const Color warning = Color(0xFFFBBF24);
  static const Color warningLight = Color(0xFFFBBF24);
  static const Color warningDark = Color(0xFFF59E0B);

  static const Color error = Color(0xFFFB7185);
  static const Color errorLight = Color(0xFFFDA4AF);
  static const Color errorDark = Color(0xFFE11D48);

  static const Color info = Color(0xFF67E8F9);
  static const Color infoLight = Color(0xFF60A5FA);
  static const Color infoDark = Color(0xFF1D4ED8);

  // ═══════════════════════ BORDERS & DIVIDERS ═══════════════════════
  static const Color border = Color(0xFF1F2937);
  static const Color borderLight = Color(0xFF1D415A);
  static const Color divider = Color(0xFF172033);

  // ═══════════════════════ STATE LAYERS ═══════════════════════
  /// Hover/focus state overlay
  static const Color stateLayerOnTertiary = Color(0x12FFFFFF);

  /// Pressed/activated state
  static const Color stateLayerOnTertiaryActive = Color(0x1AFFFFFF);

  /// Disabled state
  static const Color stateLayerOnTertiaryDisabled = Color(0x0AFFFFFF);
}

/// Spacing system - 8px grid base unit
abstract class AppSpacing {
  AppSpacing._();

  static const double xs = 4; // 0.5x grid
  static const double sm = 8; // 1x grid
  static const double md = 16; // 2x grid
  static const double lg = 24; // 3x grid
  static const double xl = 32; // 4x grid
  static const double xxl = 48; // 6x grid
  static const double xxxl = 64; // 8x grid

  // Edge insets for common patterns
  static const EdgeInsets pagePadding = EdgeInsets.all(md);
  static const EdgeInsets pageHorizontalPadding =
      EdgeInsets.symmetric(horizontal: lg);
  static const EdgeInsets cardPadding = EdgeInsets.all(md);
  static const EdgeInsets buttonPadding =
      EdgeInsets.symmetric(horizontal: md, vertical: sm);
}

/// Border radius system - smooth curves
abstract class AppRadius {
  AppRadius._();

  static const double xs = 8; // Buttons, small elements
  static const double sm = 12; // Form inputs
  static const double md = 16; // Cards, medium elements
  static const double lg = 20; // Modals, large cards
  static const double xl = 24; // Large containers
  static const double xxl = 32; // Extra large components
  static const double full = 9999; // Pill shapes, FABs
}

/// Typography scale with Material 3 compliance
abstract class AppTypography {
  AppTypography._();

  static const String fontFamily = 'Inter';
  static const List<String> fontFallback = <String>[
    'Segoe UI',
    'Roboto',
    'Arial',
    'sans-serif',
  ];

  // Display styles - large prominent text
  static const TextStyle displayLarge = TextStyle(
    fontSize: 28,
    fontWeight: FontWeight.w700,
    height: 1.3,
    letterSpacing: 0,
  );

  static const TextStyle displayMedium = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w700,
    height: 1.35,
    letterSpacing: 0,
  );

  static const TextStyle displaySmall = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 1.4,
    letterSpacing: 0,
  );

  // Headline styles - section headers
  static const TextStyle headlineLarge = TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    height: 1.45,
    letterSpacing: 0,
  );

  static const TextStyle headlineMedium = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    height: 1.5,
    letterSpacing: 0,
  );

  static const TextStyle headlineSmall = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.57,
    letterSpacing: 0,
  );

  // Title styles - medium emphasis text
  static const TextStyle titleLarge = TextStyle(
    fontSize: 22,
    fontWeight: FontWeight.w600,
    height: 1.27,
    letterSpacing: 0,
  );

  static const TextStyle titleMedium = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w500,
    height: 1.5,
    letterSpacing: 0,
  );

  static const TextStyle titleSmall = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w500,
    height: 1.43,
    letterSpacing: 0,
  );

  // Body styles - main content
  static const TextStyle bodyLarge = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.5,
    letterSpacing: 0,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.57,
    letterSpacing: 0,
  );

  static const TextStyle bodySmall = TextStyle(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.66,
    letterSpacing: 0,
  );

  // Label styles - buttons, labels, tags
  static const TextStyle labelLarge = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.43,
    letterSpacing: 0,
  );

  static const TextStyle labelMedium = TextStyle(
    fontSize: 12,
    fontWeight: FontWeight.w600,
    height: 1.33,
    letterSpacing: 0,
  );

  static const TextStyle labelSmall = TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 1.45,
    letterSpacing: 0,
  );
}

/// Animation durations for smooth transitions
abstract class AppAnimations {
  AppAnimations._();

  static const Duration instant = Duration(milliseconds: 100);
  static const Duration fast = Duration(milliseconds: 200);
  static const Duration normal = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 450);
  static const Duration slower = Duration(milliseconds: 600);

  static const Curve defaultCurve = Curves.easeInOut;
  static const Curve snappyCurve = Curves.easeOutCubic;
  static const Curve gentleCurve = Curves.easeInOutCubic;
}

/// Reusable gradient presets for backgrounds and accent elements
abstract class AppGradients {
  AppGradients._();

  /// Main screen background gradient — deep navy to near-black
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF07101C),
      Color(0xFF091726),
      Color(0xFF0D1E30),
    ],
    stops: [0.0, 0.5, 1.0],
  );

  /// Accent glow gradient — cyan to violet
  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      AppThemeColors.primary,
      AppThemeColors.secondary,
    ],
  );

  /// Subtle card gradient — barely visible surface shift
  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF101B2F),
      AppThemeColors.surface,
    ],
  );

  /// Sidebar gradient — slightly lighter than background
  static const LinearGradient sidebarGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [
      AppThemeColors.surface,
      AppThemeColors.background,
    ],
  );

  /// Shimmer loading gradient
  static const LinearGradient shimmerGradient = LinearGradient(
    begin: Alignment(-1.0, -0.3),
    end: Alignment(1.0, 0.3),
    colors: [
      Color(0xFF1A1F2E),
      AppThemeColors.surfaceLighter,
      Color(0xFF1A1F2E),
    ],
    stops: [0.0, 0.5, 1.0],
  );

  /// Primary button gradient
  static const LinearGradient primaryButtonGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      AppThemeColors.primary,
      AppThemeColors.primaryDark,
    ],
  );
}

/// Consistent shadow tokens for depth hierarchy
abstract class AppShadows {
  AppShadows._();

  /// Subtle glow — cards, list items
  static List<BoxShadow> get subtle => [
        BoxShadow(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: AppThemeColors.primary.withValues(alpha: 0.04),
          blurRadius: 8,
          offset: const Offset(0, 2),
        ),
      ];

  /// Card shadow — elevated cards, modals
  static List<BoxShadow> get card => [
        BoxShadow(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: Colors.black.withValues(alpha: 0.3),
          blurRadius: 16,
          offset: const Offset(0, 4),
        ),
        BoxShadow(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: AppThemeColors.primary.withValues(alpha: 0.06),
          blurRadius: 24,
          offset: const Offset(0, 8),
        ),
      ];

  /// Elevated shadow — dialogs, bottom sheets
  static List<BoxShadow> get elevated => [
        BoxShadow(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: Colors.black.withValues(alpha: 0.4),
          blurRadius: 32,
          offset: const Offset(0, 8),
        ),
        BoxShadow(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: AppThemeColors.primary.withValues(alpha: 0.08),
          blurRadius: 40,
          offset: const Offset(0, 12),
        ),
      ];

  /// Glow effect — active/focused elements
  static List<BoxShadow> get glow => [
        BoxShadow(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: AppThemeColors.primary.withValues(alpha: 0.15),
          blurRadius: 20,
          spreadRadius: 2,
        ),
      ];
}

/// Pre-built BoxDecoration helpers for glassmorphic surfaces
abstract class AppDecorations {
  AppDecorations._();

  /// Frosted glass card with subtle border and blur effect
  static BoxDecoration glassmorphicCard({
    double borderRadius = AppRadius.md,
    double borderOpacity = 0.08,
  }) =>
      BoxDecoration(
        gradient: AppGradients.cardGradient,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: Colors.white.withValues(alpha: borderOpacity),
        ),
        boxShadow: AppShadows.card,
      );

  /// Sidebar container decoration
  // Warning fix: make the static sidebar decoration const; UI output remains unchanged.
  static BoxDecoration get sidebar => const BoxDecoration(
        gradient: AppGradients.sidebarGradient,
        border: Border(
          right: BorderSide(
            color: AppThemeColors.border,
            width: 1,
          ),
        ),
      );

  /// Surface container (forms, sections)
  static BoxDecoration surface({
    double borderRadius = AppRadius.md,
  }) =>
      BoxDecoration(
        color: AppThemeColors.surface,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(color: AppThemeColors.border),
      );

  /// Accent-bordered card (highlighted)
  static BoxDecoration accentCard({
    double borderRadius = AppRadius.md,
  }) =>
      BoxDecoration(
        gradient: AppGradients.cardGradient,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: AppThemeColors.primary.withValues(alpha: 0.25),
        ),
        boxShadow: AppShadows.glow,
      );

  /// Input field decoration
  static BoxDecoration get inputField => BoxDecoration(
        color: AppThemeColors.surfaceLight,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: AppThemeColors.border),
      );

  /// Status chip decoration
  static BoxDecoration statusChip(Color color) => BoxDecoration(
        // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: color.withValues(alpha: 0.25),
        ),
      );
}

/// Standardized icon sizes
abstract class AppIconSizes {
  AppIconSizes._();

  static const double xs = 14;
  static const double sm = 18;
  static const double md = 22;
  static const double lg = 28;
  static const double xl = 36;
  static const double xxl = 48;
}

/// Build Material 3 theme with glassmorphism aesthetic
class AppThemeBuilder {
  static ThemeData buildDarkTheme() {
    const colorScheme = ColorScheme.dark(
      primary: AppThemeColors.primary,
      onPrimary: AppThemeColors.background,
      primaryContainer: AppThemeColors.primaryDark,
      onPrimaryContainer: AppThemeColors.primaryLight,
      secondary: AppThemeColors.secondary,
      onSecondary: AppThemeColors.background,
      tertiary: AppThemeColors.info,
      onTertiary: AppThemeColors.background,
      error: AppThemeColors.error,
      onError: AppThemeColors.background,
      // Warning fix: keep legacy background mapping to preserve current UI palette.
      // ignore: deprecated_member_use
      background: AppThemeColors.background,
      // Warning fix: keep legacy onBackground mapping to preserve current UI palette.
      // ignore: deprecated_member_use
      onBackground: AppThemeColors.textPrimary,
      surface: AppThemeColors.surface,
      onSurface: AppThemeColors.textPrimary,
    );

    return ThemeData(
      // ═══════════════════════ CORE PROPERTIES ═══════════════════════
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: AppTypography.fontFamily,
      fontFamilyFallback: AppTypography.fontFallback,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppThemeColors.background,
      textTheme: const TextTheme(
        displayLarge: AppTypography.displayLarge,
        displayMedium: AppTypography.displayMedium,
        displaySmall: AppTypography.displaySmall,
        headlineLarge: AppTypography.headlineLarge,
        headlineMedium: AppTypography.headlineMedium,
        headlineSmall: AppTypography.headlineSmall,
        titleLarge: AppTypography.titleLarge,
        titleMedium: AppTypography.titleMedium,
        titleSmall: AppTypography.titleSmall,
        bodyLarge: AppTypography.bodyLarge,
        bodyMedium: AppTypography.bodyMedium,
        bodySmall: AppTypography.bodySmall,
        labelLarge: AppTypography.labelLarge,
        labelMedium: AppTypography.labelMedium,
        labelSmall: AppTypography.labelSmall,
      ).apply(
        fontFamily: AppTypography.fontFamily,
        bodyColor: AppThemeColors.textPrimary,
        displayColor: AppThemeColors.textPrimary,
      ),

      // ═══════════════════════ APP BAR ═══════════════════════
      appBarTheme: AppBarTheme(
        backgroundColor: AppThemeColors.background,
        foregroundColor: AppThemeColors.textPrimary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: AppTypography.headlineLarge.copyWith(
          color: AppThemeColors.textPrimary,
        ),
        surfaceTintColor: Colors.transparent,
      ),

      // ═══════════════════════ CARD ═══════════════════════
      cardTheme: CardThemeData(
        color: AppThemeColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          side: const BorderSide(
            color: AppThemeColors.border,
          ),
        ),
        surfaceTintColor: Colors.transparent,
      ),

      // ═══════════════════════ INPUT FIELDS ═══════════════════════
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppThemeColors.surfaceLight,
        contentPadding: AppSpacing.buttonPadding,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(color: AppThemeColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(
            color: AppThemeColors.border,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(
            color: AppThemeColors.primary,
            width: 2,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(
            color: AppThemeColors.error,
          ),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(
            color: AppThemeColors.error,
            width: 2,
          ),
        ),
        labelStyle: AppTypography.bodyMedium.copyWith(
          color: AppThemeColors.textSecondary,
        ),
        hintStyle: AppTypography.bodyMedium.copyWith(
          color: AppThemeColors.textTertiary,
        ),
        helperStyle: AppTypography.labelSmall.copyWith(
          color: AppThemeColors.textTertiary,
        ),
        errorStyle: AppTypography.labelSmall.copyWith(
          color: AppThemeColors.error,
        ),
        prefixIconColor: AppThemeColors.textSecondary,
        suffixIconColor: AppThemeColors.textSecondary,
        floatingLabelStyle: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.primary,
        ),
      ),

      // ═══════════════════════ BUTTONS ═══════════════════════
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppThemeColors.primary,
          foregroundColor: AppThemeColors.background,
          elevation: 0,
          padding: AppSpacing.buttonPadding,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.xs),
          ),
          textStyle: AppTypography.labelLarge,
          minimumSize: const Size(0, 44),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppThemeColors.primary,
          side: const BorderSide(color: AppThemeColors.primary, width: 1.5),
          padding: AppSpacing.buttonPadding,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.xs),
          ),
          textStyle: AppTypography.labelLarge,
          minimumSize: const Size(0, 44),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppThemeColors.primary,
          padding: AppSpacing.buttonPadding,
          textStyle: AppTypography.labelLarge,
          minimumSize: const Size(0, 44),
        ),
      ),

      // ═══════════════════════ FLOATING ACTION BUTTON ═══════════════════════
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppThemeColors.primary,
        foregroundColor: AppThemeColors.background,
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.full),
        ),
      ),

      // ═══════════════════════ DIALOGS & BOTTOM SHEETS ═══════════════════════
      dialogTheme: DialogThemeData(
        backgroundColor: AppThemeColors.surface,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        surfaceTintColor: Colors.transparent,
      ),

      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppThemeColors.surface,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(AppRadius.lg),
            topRight: Radius.circular(AppRadius.lg),
          ),
        ),
        surfaceTintColor: Colors.transparent,
      ),

      // ═══════════════════════ CHIPS & TAGS ═══════════════════════
      chipTheme: ChipThemeData(
        backgroundColor: AppThemeColors.surfaceLight,
        selectedColor: AppThemeColors.primary,
        disabledColor: AppThemeColors.textDisabled,
        labelStyle: AppTypography.labelMedium.copyWith(
          color: AppThemeColors.textPrimary,
        ),
        secondaryLabelStyle: AppTypography.labelMedium.copyWith(
          color: AppThemeColors.background,
        ),
        side: const BorderSide(color: AppThemeColors.border),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.full),
        ),
      ),

      // ═══════════════════════ LISTS ═══════════════════════
      listTileTheme: ListTileThemeData(
        tileColor: AppThemeColors.surface,
        selectedColor: AppThemeColors.primary,
        textColor: AppThemeColors.textPrimary,
        iconColor: AppThemeColors.textSecondary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
      ),

      // ═══════════════════════ PROGRESS INDICATORS ═══════════════════════
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppThemeColors.primary,
        linearTrackColor: AppThemeColors.border,
        linearMinHeight: 4,
      ),

      // ═══════════════════════ SLIDERS ═══════════════════════
      sliderTheme: SliderThemeData(
        activeTrackColor: AppThemeColors.primary,
        inactiveTrackColor: AppThemeColors.border,
        thumbColor: AppThemeColors.primary,
        // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
        overlayColor: AppThemeColors.primary.withValues(alpha: 0.2),
        valueIndicatorColor: AppThemeColors.primary,
      ),

      // ═══════════════════════ SWITCH & CHECKBOX ═══════════════════════
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppThemeColors.primary;
          }
          return AppThemeColors.textTertiary;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
            return AppThemeColors.primary.withValues(alpha: 0.3);
          }
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          return AppThemeColors.border.withValues(alpha: 0.3);
        }),
      ),

      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppThemeColors.primary;
          }
          return AppThemeColors.surface;
        }),
        side: const BorderSide(color: AppThemeColors.border),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.xs),
        ),
      ),

      // ═══════════════════════ NAVIGATION ═══════════════════════
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppThemeColors.surfaceLight,
        // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
        indicatorColor: AppThemeColors.primary.withValues(alpha: 0.15),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const IconThemeData(color: AppThemeColors.primary);
          }
          return const IconThemeData(color: AppThemeColors.textSecondary);
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppTypography.labelSmall.copyWith(
              color: AppThemeColors.primary,
            );
          }
          return AppTypography.labelSmall.copyWith(
            color: AppThemeColors.textSecondary,
          );
        }),
      ),

      tabBarTheme: const TabBarThemeData(
        indicatorSize: TabBarIndicatorSize.tab,
        indicator: UnderlineTabIndicator(
          borderSide: BorderSide(
            color: AppThemeColors.primary,
            width: 3,
          ),
        ),
        labelColor: AppThemeColors.primary,
        unselectedLabelColor: AppThemeColors.textSecondary,
        labelStyle: AppTypography.labelLarge,
        unselectedLabelStyle: AppTypography.labelMedium,
      ),

      // ═══════════════════════ DIVIDERS & SNACKBARS ═══════════════════════
      dividerTheme: const DividerThemeData(
        color: AppThemeColors.border,
        thickness: 1,
        space: AppSpacing.md,
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppThemeColors.surfaceLight,
        contentTextStyle: AppTypography.bodyMedium.copyWith(
          color: AppThemeColors.textPrimary,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          side: const BorderSide(color: AppThemeColors.border),
        ),
        elevation: 4,
      ),

      // ═══════════════════════ TOOLTIPS ═══════════════════════
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: AppThemeColors.surface.withValues(alpha: 0.95),
          borderRadius: BorderRadius.circular(AppRadius.xs),
          border: Border.all(color: AppThemeColors.border),
        ),
        textStyle: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
        ),
      ),

      // ═══════════════════════ VISUAL DENSITY ═══════════════════════
      visualDensity: VisualDensity.standard,
    );
  }
}
