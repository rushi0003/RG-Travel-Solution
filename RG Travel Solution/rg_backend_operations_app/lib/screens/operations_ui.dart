import 'package:flutter/material.dart';

import '../theme/ops_ui_tokens.dart';

class OpsScaffold extends StatelessWidget {
  const OpsScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.metrics,
    required this.onRefresh,
    required this.child,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final List<OpsMetric> metrics;
  final Future<void> Function() onRefresh;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          IconButton(
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: Container(
        decoration: OpsDecorations.pageBackground(),
        child: RefreshIndicator(
          onRefresh: onRefresh,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final metricWidth = context.isOpsCompact
                  ? constraints.maxWidth
                  : (constraints.maxWidth >= OpsBreakpoints.desktop
                      ? 230.0
                      : 210.0);

              return ListView(
                padding: context.opsPagePadding,
                children: [
                  OpsResponsiveContainer(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _OpsHero(
                          title: title,
                          subtitle: subtitle,
                          icon: icon,
                        ),
                        if (metrics.isNotEmpty) ...[
                          const SizedBox(height: OpsSpacing.xl),
                          Wrap(
                            spacing: OpsSpacing.lg,
                            runSpacing: OpsSpacing.lg,
                            children: metrics
                                .map(
                                  (metric) => _OpsMetricCard(
                                    metric: metric,
                                    width: metricWidth,
                                  ),
                                )
                                .toList(),
                          ),
                        ],
                        const SizedBox(height: OpsSpacing.xl),
                        child,
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class OpsResponsiveContainer extends StatelessWidget {
  const OpsResponsiveContainer({
    super.key,
    required this.child,
    this.maxWidth = 1280,
  });

  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}

class OpsPanel extends StatelessWidget {
  const OpsPanel({
    super.key,
    required this.child,
    this.padding = OpsSpacing.card,
    this.borderColor = OpsUiTokens.outline,
    this.radius = OpsRadius.xl,
    this.elevated = false,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color borderColor;
  final double radius;
  final bool elevated;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: OpsDecorations.panel(
        borderColor: borderColor,
        radius: radius,
        elevated: elevated,
      ),
      child: child,
    );
  }
}

class OpsMetric {
  const OpsMetric({
    required this.label,
    required this.value,
    required this.icon,
    required this.tone,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color tone;
}

class ErrorCard extends StatelessWidget {
  const ErrorCard({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return OpsPanel(
      padding: OpsSpacing.card,
      borderColor: OpsUiTokens.errorBorder,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline_rounded, color: OpsUiTokens.danger),
          const SizedBox(width: OpsSpacing.md),
          Expanded(
            child: Text(
              message,
              style: OpsTypography.body.copyWith(
                color: OpsUiTokens.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class OpsLoadingState extends StatelessWidget {
  const OpsLoadingState({
    super.key,
    this.message = 'Loading operations data...',
  });

  final String message;

  @override
  Widget build(BuildContext context) {
    return OpsPanel(
      padding: const EdgeInsets.symmetric(
        horizontal: OpsSpacing.xl,
        vertical: OpsSpacing.huge,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: OpsSpacing.lg),
          Text(
            message,
            textAlign: TextAlign.center,
            style: OpsTypography.body,
          ),
        ],
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({
    super.key,
    required this.title,
    required this.description,
    required this.items,
    required this.subtitleBuilder,
    this.tone = OpsUiTokens.info,
    this.emptyText = 'No records found.',
  });

  final String title;
  final String description;
  final List<Map<String, dynamic>> items;
  final String Function(Map<String, dynamic>) subtitleBuilder;
  final Color tone;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    return OpsPanel(
      borderColor: tone.withValues(alpha: 0.25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: OpsSpacing.xs),
                    Text(
                      description,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: OpsSpacing.md),
              OpsStatusBadge(
                label: '${items.length}',
                tone: tone,
                compact: true,
              ),
            ],
          ),
          const SizedBox(height: OpsSpacing.lg),
          if (items.isEmpty)
            OpsEmptyState(
              title: emptyText,
              icon: Icons.inbox_outlined,
            )
          else
            ...items.take(10).map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: OpsSpacing.md),
                    child: _OpsRecordTile(
                      title: _titleFor(item),
                      subtitle: subtitleBuilder(item),
                      accent: tone,
                    ),
                  ),
                ),
        ],
      ),
    );
  }

  String _titleFor(Map<String, dynamic> item) {
    return (item['name'] ??
            item['title'] ??
            item['route_no'] ??
            item['subject'] ??
            item['employee_name'] ??
            item['trip_id'] ??
            item['id'] ??
            'Record')
        .toString();
  }
}

class _OpsHero extends StatelessWidget {
  const _OpsHero({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < OpsBreakpoints.compact;
        final iconBox = Container(
          padding: const EdgeInsets.all(OpsSpacing.lg),
          decoration: BoxDecoration(
            color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(OpsRadius.lg),
          ),
          child: Icon(icon, size: 32, color: OpsUiTokens.primarySoft),
        );

        final textBlock = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: OpsTypography.heading),
            const SizedBox(height: OpsSpacing.sm),
            Text(
              subtitle,
              style: OpsTypography.body.copyWith(
                color: OpsUiTokens.textSecondary,
              ),
            ),
          ],
        );

        return Container(
          width: double.infinity,
          padding: EdgeInsets.all(compact ? OpsSpacing.xl : OpsSpacing.xxl),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(OpsRadius.xxl),
            gradient: OpsGradients.hero,
            border: Border.all(color: OpsUiTokens.outlineStrong),
            boxShadow: OpsShadows.glow(OpsUiTokens.primary),
          ),
          child: compact
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    iconBox,
                    const SizedBox(height: OpsSpacing.lg),
                    textBlock,
                  ],
                )
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    iconBox,
                    const SizedBox(width: OpsSpacing.lg),
                    Expanded(child: textBlock),
                  ],
                ),
        );
      },
    );
  }
}

class _OpsMetricCard extends StatelessWidget {
  const _OpsMetricCard({required this.metric, required this.width});

  final OpsMetric metric;
  final double width;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: OpsSpacing.cardCompact,
      decoration: OpsDecorations.tonalPanel(tone: metric.tone),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(metric.icon, color: metric.tone),
          const SizedBox(height: OpsSpacing.md),
          Text(
            metric.value,
            style: OpsTypography.heading,
          ),
          const SizedBox(height: OpsSpacing.xs),
          Text(metric.label, style: OpsTypography.body),
        ],
      ),
    );
  }
}

class OpsStatusBadge extends StatelessWidget {
  const OpsStatusBadge({
    super.key,
    required this.label,
    required this.tone,
    this.icon,
    this.compact = false,
  });

  final String label;
  final Color tone;
  final IconData? icon;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? OpsSpacing.md : OpsSpacing.lg,
        vertical: compact ? OpsSpacing.sm : OpsSpacing.md,
      ),
      decoration: OpsDecorations.status(tone),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: tone),
            const SizedBox(width: OpsSpacing.sm),
          ],
          Text(
            label,
            style: OpsTypography.caption.copyWith(
              color: tone,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class OpsEmptyState extends StatelessWidget {
  const OpsEmptyState({
    super.key,
    required this.title,
    this.message,
    this.icon = Icons.inbox_outlined,
  });

  final String title;
  final String? message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: OpsSpacing.cardCompact,
      decoration: OpsDecorations.mutedPanel(),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: OpsUiTokens.textTertiary),
          const SizedBox(width: OpsSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: OpsTypography.bodyStrong),
                if (message != null && message!.trim().isNotEmpty) ...[
                  const SizedBox(height: OpsSpacing.xs),
                  Text(message!, style: OpsTypography.body),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _OpsRecordTile extends StatelessWidget {
  const _OpsRecordTile({
    required this.title,
    required this.subtitle,
    required this.accent,
  });

  final String title;
  final String subtitle;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: OpsSpacing.cardCompact,
      decoration: OpsDecorations.mutedPanel(
        borderColor: accent.withValues(alpha: 0.16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 10,
            height: 10,
            margin: const EdgeInsets.only(top: 6),
            decoration: BoxDecoration(color: accent, shape: BoxShape.circle),
          ),
          const SizedBox(width: OpsSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: OpsTypography.bodyStrong,
                ),
                const SizedBox(height: OpsSpacing.xs),
                Text(
                  subtitle,
                  style: OpsTypography.body,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
