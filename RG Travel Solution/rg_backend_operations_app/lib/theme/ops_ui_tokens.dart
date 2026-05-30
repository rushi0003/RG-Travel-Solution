import 'package:flutter/material.dart';

class OpsUiTokens {
  const OpsUiTokens._();

  // Enterprise transport-tech palette.
  static const background = Color(0xFF08111F);
  static const backgroundAlt = Color(0xFF07101C);
  static const backgroundMid = Color(0xFF091726);
  static const backgroundDeep = Color(0xFF0D1E30);

  static const surface = Color(0xFF0B1220);
  static const panel = Color(0xFF0F172A);
  static const panelMuted = Color(0xFF111827);
  static const panelStrong = Color(0xFF0B1320);
  static const panelInfo = Color(0xFF111E31);
  static const panelInfoBorder = Color(0xFF203047);
  static const panelOverlay = Color(0xFF111C2D);
  static const panelOverlayAlt = Color(0xFF0E1726);
  static const panelChip = Color(0xFF0C2435);
  static const panelChipBorder = Color(0xFF1F3B53);
  static const panelBadge = Color(0xFF102438);
  static const panelBadgeBorder = Color(0xFF21344B);
  static const panelSidebarActive = Color(0xFF10263B);
  static const panelSidebarAccent = Color(0xFF10304A);
  static const panelIcon = Color(0xFF0B2233);

  static const outline = Color(0xFF1F2937);
  static const outlineStrong = Color(0xFF1D415A);
  static const divider = Color(0xFF172033);

  static const textPrimary = Color(0xFFF8FAFC);
  static const textSecondary = Color(0xFFCBD5E1);
  static const textTertiary = Color(0xFF94A3B8);
  static const textDisabled = Color(0xFF64748B);

  static const primary = Color(0xFF00D1FF);
  static const primarySoft = Color(0xFF8BE9FD);
  static const secondary = Color(0xFF34D399);
  static const accent = Color(0xFFA78BFA);
  static const success = Color(0xFF34D399);
  static const warning = Color(0xFFFBBF24);
  static const warningDeep = Color(0xFFF59E0B);
  static const danger = Color(0xFFFB7185);
  static const info = Color(0xFF67E8F9);
  static const blue = Color(0xFF60A5FA);
  static const purple = Color(0xFFA78BFA);

  static const heroGradient = [
    Color(0xFF102033),
    Color(0xFF0A3144),
    Color(0xFF134E4A),
  ];

  static const backgroundGradient = [
    backgroundAlt,
    backgroundMid,
    backgroundDeep,
  ];

  static const loginBackgroundGradient = [
    backgroundAlt,
    Color(0xFF0A1B2E),
    Color(0xFF0E2A38),
  ];

  static const accessHeroGradient = [
    Color(0xFF0F1E32),
    Color(0xFF0A3144),
    Color(0xFF134E4A),
  ];

  static const errorSurface = Color(0xFF2A1010);
  static const errorBorder = Color(0xFF7F1D1D);

  static const buttonForeground = Color(0xFF04131D);
  static const buttonDisabled = Color(0xFF16465A);
}

class OpsSpacing {
  const OpsSpacing._();

  static const double xxs = 2;
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;
  static const double huge = 40;
  static const double section = 48;

  static const EdgeInsets page = EdgeInsets.all(xxl);
  static const EdgeInsets pageCompact = EdgeInsets.all(lg);
  static const EdgeInsets card = EdgeInsets.all(xl);
  static const EdgeInsets cardCompact = EdgeInsets.all(lg);
  static const EdgeInsets field = EdgeInsets.symmetric(
    horizontal: lg,
    vertical: lg,
  );
  static const EdgeInsets button = EdgeInsets.symmetric(
    horizontal: xl,
    vertical: lg,
  );
}

class OpsRadius {
  const OpsRadius._();

  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 20;
  static const double xl = 24;
  static const double xxl = 28;
  static const double full = 999;
}

class OpsBreakpoints {
  const OpsBreakpoints._();

  static const double compact = 600;
  static const double tablet = 840;
  static const double desktop = 1180;
  static const double wide = 1440;
}

class OpsTypography {
  const OpsTypography._();

  static const String fontFamily = 'Inter';
  static const List<String> fontFallback = <String>[
    'Segoe UI',
    'Roboto',
    'Arial',
    'sans-serif',
  ];

  static const display = TextStyle(
    fontSize: 32,
    height: 1.16,
    fontWeight: FontWeight.w800,
    letterSpacing: 0,
    color: OpsUiTokens.textPrimary,
  );

  static const heading = TextStyle(
    fontSize: 24,
    height: 1.22,
    fontWeight: FontWeight.w700,
    letterSpacing: 0,
    color: OpsUiTokens.textPrimary,
  );

  static const title = TextStyle(
    fontSize: 20,
    height: 1.28,
    fontWeight: FontWeight.w700,
    letterSpacing: 0,
    color: OpsUiTokens.textPrimary,
  );

  static const subtitle = TextStyle(
    fontSize: 16,
    height: 1.45,
    fontWeight: FontWeight.w600,
    letterSpacing: 0,
    color: OpsUiTokens.textSecondary,
  );

  static const body = TextStyle(
    fontSize: 14,
    height: 1.5,
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    color: OpsUiTokens.textSecondary,
  );

  static const bodyStrong = TextStyle(
    fontSize: 14,
    height: 1.45,
    fontWeight: FontWeight.w700,
    letterSpacing: 0,
    color: OpsUiTokens.textPrimary,
  );

  static const caption = TextStyle(
    fontSize: 12,
    height: 1.4,
    fontWeight: FontWeight.w500,
    letterSpacing: 0,
    color: OpsUiTokens.textTertiary,
  );

  static const button = TextStyle(
    fontSize: 14,
    height: 1.2,
    fontWeight: FontWeight.w700,
    letterSpacing: 0,
  );
}

class OpsGradients {
  const OpsGradients._();

  static const background = LinearGradient(
    colors: OpsUiTokens.backgroundGradient,
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const hero = LinearGradient(
    colors: OpsUiTokens.heroGradient,
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const accessHero = LinearGradient(
    colors: OpsUiTokens.accessHeroGradient,
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const panel = LinearGradient(
    colors: [
      Color(0xFF101B2F),
      OpsUiTokens.panel,
    ],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const danger = LinearGradient(
    colors: [
      Color(0xFF1A1830),
      Color(0xFF231629),
      Color(0xFF2B1520),
    ],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

class OpsShadows {
  const OpsShadows._();

  static List<BoxShadow> get card => [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.22),
          blurRadius: 24,
          offset: const Offset(0, 14),
        ),
      ];

  static List<BoxShadow> glow(Color color) => [
        BoxShadow(
          color: color.withValues(alpha: 0.16),
          blurRadius: 22,
          offset: const Offset(0, 10),
        ),
      ];
}

class OpsDecorations {
  const OpsDecorations._();

  static BoxDecoration pageBackground() => const BoxDecoration(
        gradient: OpsGradients.background,
      );

  static BoxDecoration panel({
    Color borderColor = OpsUiTokens.outline,
    double radius = OpsRadius.xl,
    bool elevated = false,
  }) {
    return BoxDecoration(
      color: OpsUiTokens.panel,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: borderColor),
      boxShadow: elevated ? OpsShadows.card : null,
    );
  }

  static BoxDecoration mutedPanel({
    Color borderColor = OpsUiTokens.outline,
    double radius = OpsRadius.lg,
  }) {
    return BoxDecoration(
      color: OpsUiTokens.panelMuted,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: borderColor),
    );
  }

  static BoxDecoration tonalPanel({
    required Color tone,
    double radius = OpsRadius.xl,
    double alpha = 0.25,
  }) {
    return BoxDecoration(
      color: OpsUiTokens.panel,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: tone.withValues(alpha: alpha)),
    );
  }

  static BoxDecoration status(Color tone) {
    return BoxDecoration(
      color: tone.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(OpsRadius.full),
      border: Border.all(color: tone.withValues(alpha: 0.32)),
    );
  }
}

extension OpsResponsiveContext on BuildContext {
  double get opsWidth => MediaQuery.sizeOf(this).width;
  bool get isOpsCompact => opsWidth < OpsBreakpoints.compact;
  bool get isOpsTablet =>
      opsWidth >= OpsBreakpoints.compact && opsWidth < OpsBreakpoints.desktop;
  bool get isOpsDesktop => opsWidth >= OpsBreakpoints.desktop;

  EdgeInsets get opsPagePadding =>
      isOpsCompact ? OpsSpacing.pageCompact : OpsSpacing.page;
}
