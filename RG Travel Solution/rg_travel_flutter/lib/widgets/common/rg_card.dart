// flutter/lib/widgets/common/rg_card.dart
//
// RG Travel Solution — Common Card Widget
// Used across Admin/Driver/Employee dashboards.
//
// Features:
// - Soft glass-like / futuristic look
// - Optional onTap
// - Optional header row (title, subtitle, trailing)
// - Optional padding + radius + border
// - Optional "loading" placeholder state

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class RGCard extends StatelessWidget {
  final Widget child;

  /// Optional header
  final String? title;
  final String? subtitle;
  final Widget? trailing;

  /// Tap support
  final VoidCallback? onTap;

  /// Styling
  final EdgeInsetsGeometry padding;
  final double radius;
  final double borderWidth;

  /// When true, show a simple loading placeholder
  final bool isLoading;
  final double? minHeight;
  final EdgeInsetsGeometry? margin;

  const RGCard({
    super.key,
    required this.child,
    this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.padding = AppSpacing.cardPadding,
    this.radius = AppRadius.lg,
    this.borderWidth = 1.0,
    this.isLoading = false,
    this.minHeight,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final surface = theme.colorScheme.surface;
    final onSurface = theme.colorScheme.onSurface;
    final primary = theme.colorScheme.primary;

    final cardBg = surface.withValues(alpha: 0.28);
    final borderColor = theme.dividerColor.withValues(alpha: 0.5);

    Widget body = Container(
      margin: margin,
      constraints:
          minHeight == null ? null : BoxConstraints(minHeight: minHeight!),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        color: cardBg,
        border: Border.all(color: borderColor, width: borderWidth),
        boxShadow: [
          // Soft glow
          BoxShadow(
            color: primary.withValues(alpha: 0.10),
            blurRadius: 18,
            spreadRadius: 0,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: Padding(
          padding: padding,
          child:
              isLoading ? _LoadingBody(theme) : _ContentBody(theme, onSurface),
        ),
      ),
    );

    if (onTap == null) return body;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(radius),
        onTap: onTap,
        child: body,
      ),
    );
  }

  Widget _ContentBody(ThemeData theme, Color onSurface) {
    final hasHeader = (title != null && title!.trim().isNotEmpty) ||
        (subtitle != null && subtitle!.trim().isNotEmpty) ||
        trailing != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (hasHeader)
          _Header(title: title, subtitle: subtitle, trailing: trailing),
        if (hasHeader) const SizedBox(height: 12),
        child,
      ],
    );
  }
}

// ------------------------------------------------------------
// Header widget
// ------------------------------------------------------------
class _Header extends StatelessWidget {
  final String? title;
  final String? subtitle;
  final Widget? trailing;

  const _Header({
    required this.title,
    required this.subtitle,
    required this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final titleText = (title ?? "").trim();
    final subtitleText = (subtitle ?? "").trim();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (titleText.isNotEmpty)
                Text(
                  titleText,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              if (subtitleText.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  subtitleText,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
                  ),
                ),
              ],
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: 10),
          trailing!,
        ],
      ],
    );
  }
}

// ------------------------------------------------------------
// Simple Loading placeholder
// ------------------------------------------------------------
class _LoadingBody extends StatefulWidget {
  final ThemeData theme;
  const _LoadingBody(this.theme);

  @override
  State<_LoadingBody> createState() => _LoadingBodyState();
}

class _LoadingBodyState extends State<_LoadingBody>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _a;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1100))
      ..repeat(reverse: true);
    _a = Tween<double>(begin: 0.35, end: 0.75)
        .animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final base = widget.theme.dividerColor.withValues(alpha: 0.35);

    return AnimatedBuilder(
      animation: _a,
      builder: (_, __) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _bar(base.withValues(alpha: _a.value), widthFactor: 0.65),
            const SizedBox(height: 10),
            _bar(base.withValues(alpha: _a.value), widthFactor: 0.45),
            const SizedBox(height: 16),
            _bar(base.withValues(alpha: _a.value),
                height: 14, widthFactor: 0.92),
            const SizedBox(height: 8),
            _bar(base.withValues(alpha: _a.value),
                height: 14, widthFactor: 0.88),
            const SizedBox(height: 8),
            _bar(base.withValues(alpha: _a.value),
                height: 14, widthFactor: 0.75),
          ],
        );
      },
    );
  }

  Widget _bar(Color c, {double height = 12, double widthFactor = 1.0}) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      child: Container(
        height: height,
        decoration: BoxDecoration(
          color: c,
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }
}
