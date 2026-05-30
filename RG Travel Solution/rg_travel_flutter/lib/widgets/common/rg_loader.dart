// flutter/lib/widgets/common/rg_loader.dart
//
// RG Travel Solution — Common Loader Widgets
//
// Includes:
// - RGLoader (inline spinner + optional message)
// - RGFullScreenLoader (overlay-style loading)
// - RGSkeleton (simple shimmer-like placeholder)
// No external dependencies required.

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class RGLoader extends StatelessWidget {
  final String? message;
  final double size;
  final double strokeWidth;
  final bool center;

  const RGLoader({
    super.key,
    this.message,
    this.size = 22,
    this.strokeWidth = 2.6,
    this.center = true,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final indicator = SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: strokeWidth,
        valueColor: AlwaysStoppedAnimation<Color>(theme.colorScheme.primary),
      ),
    );

    final msg = (message ?? "").trim();

    Widget body = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        indicator,
        if (msg.isNotEmpty) ...[
          const SizedBox(width: 12),
          Text(
            msg,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.85),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ],
    );

    if (center) {
      body = Center(child: body);
    }

    return body;
  }
}

class RGFullScreenLoader extends StatelessWidget {
  final String? message;
  final bool dismissible;

  const RGFullScreenLoader({
    super.key,
    this.message,
    this.dismissible = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final msg = (message ?? "Loading...").trim();

    return PopScope(
      canPop: dismissible,
      child: Scaffold(
        backgroundColor: AppThemeColors.background.withValues(alpha: 0.75),
        body: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface.withValues(alpha: 0.24),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: theme.dividerColor.withValues(alpha: 0.45),
              ),
              boxShadow: [
                BoxShadow(
                  color: theme.colorScheme.primary.withValues(alpha: 0.12),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                )
              ],
            ),
            child: RGLoader(
              message: msg,
              size: 26,
              strokeWidth: 2.8,
              center: false,
            ),
          ),
        ),
      ),
    );
  }
}

/// Simple skeleton block (shimmer-like using animated opacity)
class RGSkeleton extends StatefulWidget {
  final double height;
  final double width;
  final double radius;

  const RGSkeleton({
    super.key,
    required this.height,
    required this.width,
    this.radius = 12,
  });

  @override
  State<RGSkeleton> createState() => _RGSkeletonState();
}

class _RGSkeletonState extends State<RGSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _a;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1050))
      ..repeat(reverse: true);
    _a = Tween<double>(begin: 0.30, end: 0.75).animate(
      CurvedAnimation(parent: _c, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final base = theme.dividerColor.withValues(alpha: 0.55);

    return AnimatedBuilder(
      animation: _a,
      builder: (_, __) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            color: base.withValues(alpha: _a.value),
            borderRadius: BorderRadius.circular(widget.radius),
          ),
        );
      },
    );
  }
}

/// Helper widget to show a skeleton list quickly
class RGSkeletonList extends StatelessWidget {
  final int count;
  final double itemHeight;
  final EdgeInsetsGeometry padding;

  const RGSkeletonList({
    super.key,
    this.count = 6,
    this.itemHeight = 64,
    this.padding = const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
  });

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: padding,
      itemCount: count,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        return Row(
          children: [
            const RGSkeleton(height: 44, width: 44, radius: 12),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  RGSkeleton(height: 14, width: 220, radius: 10),
                  SizedBox(height: 10),
                  RGSkeleton(height: 12, width: 170, radius: 10),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
