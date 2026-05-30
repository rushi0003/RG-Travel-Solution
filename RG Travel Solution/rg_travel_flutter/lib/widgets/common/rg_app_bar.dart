// flutter/lib/widgets/common/rg_app_bar.dart
//
// RG Travel Solution — Glassmorphic App Bar
//
// ✅ Features:
// - Frosted glass effect background
// - Gradient accent bottom line
// - Consistent styling across all screens
// - Back button support
// - Actions support

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import 'rg_logo.dart';

/// Modern glassmorphic AppBar with frosted background and accent line.
///
/// Usage:
/// ```dart
/// Scaffold(
///   appBar: RGAppBar(title: 'Dashboard'),
///   ...
/// )
/// ```
class RGAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final String? subtitle;
  final List<Widget>? actions;
  final Widget? leading;
  final bool showBackButton;
  final VoidCallback? onBack;
  final double height;
  final bool centerTitle;

  const RGAppBar({
    super.key,
    required this.title,
    this.subtitle,
    this.actions,
    this.leading,
    this.showBackButton = false,
    this.onBack,
    this.height = 64,
    this.centerTitle = false,
  });

  @override
  Size get preferredSize => Size.fromHeight(height);

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height + MediaQuery.of(context).padding.top,
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.85),
        border: const Border(
          bottom: BorderSide(
            color: AppThemeColors.border,
            width: 1,
          ),
        ),
        boxShadow: AppShadows.subtle,
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: Row(
            children: [
              // Leading / Back button
              if (leading != null)
                leading!
              else if (showBackButton)
                _BackButton(onTap: onBack ?? () => Navigator.of(context).pop()),

              if (leading != null || showBackButton)
                const SizedBox(width: AppSpacing.sm),

              // Title section
              Expanded(
                child: Row(
                  children: [
                    const RGLogo(
                      variant: RGLogoVariant.mark,
                      width: 36,
                      height: 36,
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: centerTitle
                          ? Center(
                              child: _TitleSection(
                                title: title,
                                subtitle: subtitle,
                              ),
                            )
                          : _TitleSection(title: title, subtitle: subtitle),
                    ),
                  ],
                ),
              ),

              // Actions
              if (actions != null) ...[
                const SizedBox(width: AppSpacing.sm),
                ...actions!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _BackButton extends StatelessWidget {
  final VoidCallback onTap;
  const _BackButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.xs),
        onTap: onTap,
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: AppThemeColors.cardGlass,
            borderRadius: BorderRadius.circular(AppRadius.xs),
            border: Border.all(
              color: AppThemeColors.border,
            ),
          ),
          child: const Icon(
            Icons.arrow_back_ios_new_rounded,
            size: AppIconSizes.sm,
            color: AppThemeColors.textPrimary,
          ),
        ),
      ),
    );
  }
}

class _TitleSection extends StatelessWidget {
  final String title;
  final String? subtitle;
  const _TitleSection({required this.title, this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.headlineLarge.copyWith(
            color: AppThemeColors.textPrimary,
          ),
        ),
        if (subtitle != null && subtitle!.trim().isNotEmpty) ...[
          const SizedBox(height: 2),
          Text(
            subtitle!,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
        ],
      ],
    );
  }
}

