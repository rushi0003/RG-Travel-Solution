// flutter/lib/core/theme/responsive.dart
//
// RG Travel Solution — Responsive Layout Utilities
//
// ✅ Features:
// - Mobile-first breakpoints for responsive design
// - Helper methods to detect screen size
// - Adaptive widgets for different screen sizes
// - Padding/margin adjustments based on device type

import 'package:flutter/material.dart';

/// Responsive breakpoints following Material 3 guidelines
class ResponsiveBreakpoints {
  // Mobile: 360dp - 599dp
  static const double mobileStart = 360;
  static const double mobile = 480;
  static const double mobileEnd = 599;

  // Tablet: 600dp - 839dp
  static const double tabletStart = 600;
  static const double tablet = 720;
  static const double tabletEnd = 839;

  // Desktop: 840dp+
  static const double desktopStart = 840;
  static const double desktop = 1280;
  static const double desktopFhd = 1920;
}

/// Device type detection
enum DeviceType {
  mobile,
  tablet,
  desktop,
}

/// Responsive helper extension on BuildContext
extension ResponsiveContext on BuildContext {
  /// Get current device width
  double get screenWidth => MediaQuery.of(this).size.width;

  /// Get current device height
  double get screenHeight => MediaQuery.of(this).size.height;

  /// Get device type based on screen width
  DeviceType get deviceType {
    if (screenWidth >= ResponsiveBreakpoints.desktopStart) {
      return DeviceType.desktop;
    } else if (screenWidth >= ResponsiveBreakpoints.tabletStart) {
      return DeviceType.tablet;
    }
    return DeviceType.mobile;
  }

  /// Is mobile device?
  bool get isMobile => deviceType == DeviceType.mobile;

  /// Is tablet device?
  bool get isTablet => deviceType == DeviceType.tablet;

  /// Is desktop device?
  bool get isDesktop => deviceType == DeviceType.desktop;

  /// Is mobile or tablet (not desktop)
  bool get isMobileOrTablet => !isDesktop;

  /// Get safe area (avoid notches and safe edges)
  EdgeInsets get safeAreaPadding => MediaQuery.of(this).padding;

  /// Get safe area view insets
  EdgeInsets get viewInsets => MediaQuery.of(this).viewInsets;

  /// Get device orientation
  Orientation get orientation => MediaQuery.of(this).orientation;

  /// Is portrait orientation?
  bool get isPortrait => orientation == Orientation.portrait;

  /// Is landscape orientation?
  bool get isLandscape => orientation == Orientation.landscape;

  /// Get device pixel ratio for crisp graphics
  double get devicePixelRatio => MediaQuery.of(this).devicePixelRatio;
}

/// Adaptive value based on device type
T responsive<T>({
  required BuildContext context,
  required T mobile,
  T? tablet,
  T? desktop,
}) {
  final deviceType = (context.width >= ResponsiveBreakpoints.desktopStart)
      ? DeviceType.desktop
      : (context.width >= ResponsiveBreakpoints.tabletStart)
          ? DeviceType.tablet
          : DeviceType.mobile;

  return switch (deviceType) {
    DeviceType.desktop => desktop ?? tablet ?? mobile,
    DeviceType.tablet => tablet ?? mobile,
    DeviceType.mobile => mobile,
  };
}

/// Simpler getter for width
extension _WidthHelper on BuildContext {
  double get width => MediaQuery.of(this).size.width;
}

/// Adaptive widget that changes layout based on screen size
class AdaptiveLayout extends StatelessWidget {
  const AdaptiveLayout({
    super.key,
    required this.mobileBuilder,
    this.tabletBuilder,
    this.desktopBuilder,
  });

  final Widget Function(BuildContext context) mobileBuilder;
  final Widget Function(BuildContext context)? tabletBuilder;
  final Widget Function(BuildContext context)? desktopBuilder;

  @override
  Widget build(BuildContext context) {
    return responsive(
      context: context,
      mobile: mobileBuilder(context),
      tablet: tabletBuilder?.call(context) ?? mobileBuilder(context),
      desktop: desktopBuilder?.call(context) ??
          tabletBuilder?.call(context) ??
          mobileBuilder(context),
    );
  }
}

/// Responsive padding widget
class ResponsivePadding extends StatelessWidget {
  const ResponsivePadding({
    super.key,
    required this.child,
    this.mobilePadding,
    this.tabletPadding,
    this.desktopPadding,
  });

  final Widget child;
  final EdgeInsets? mobilePadding;
  final EdgeInsets? tabletPadding;
  final EdgeInsets? desktopPadding;

  @override
  Widget build(BuildContext context) {
    final padding = responsive(
      context: context,
      mobile: mobilePadding ?? const EdgeInsets.all(16),
      tablet: tabletPadding ?? const EdgeInsets.all(20),
      desktop: desktopPadding ?? const EdgeInsets.all(24),
    );

    return Padding(padding: padding, child: child);
  }
}

/// Responsive max width container for desktop layouts
class ResponsiveContainer extends StatelessWidget {
  const ResponsiveContainer({
    super.key,
    required this.child,
    this.desktopMaxWidth = 1280,
    this.tabletMaxWidth = 720,
  });

  final Widget child;
  final double desktopMaxWidth;
  final double tabletMaxWidth;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: switch (context.deviceType) {
            DeviceType.desktop => desktopMaxWidth,
            DeviceType.tablet => tabletMaxWidth,
            DeviceType.mobile => double.infinity,
          },
        ),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: switch (context.deviceType) {
              DeviceType.desktop => 24,
              DeviceType.tablet => 16,
              DeviceType.mobile => 16,
            },
          ),
          child: child,
        ),
      ),
    );
  }
}
