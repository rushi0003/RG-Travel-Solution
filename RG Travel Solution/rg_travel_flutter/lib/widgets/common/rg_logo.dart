import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/core/utils/constants.dart';

enum RGLogoVariant { full, mark }

class RGLogo extends StatelessWidget {
  const RGLogo({
    super.key,
    this.variant = RGLogoVariant.full,
    this.width,
    this.height,
    this.fit = BoxFit.contain,
    this.showGlow = false,
  });

  final RGLogoVariant variant;
  final double? width;
  final double? height;
  final BoxFit fit;
  final bool showGlow;

  @override
  Widget build(BuildContext context) {
    final borderRadius = BorderRadius.circular(
      variant == RGLogoVariant.mark ? AppRadius.lg : AppRadius.xl,
    );
    final fallback = _FallbackLogo(
      variant: variant,
      width: width,
      height: height,
    );

    return SizedBox(
      width: width,
      height: height,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: borderRadius,
          boxShadow: showGlow ? AppShadows.glow : null,
        ),
        child: ClipRRect(
          borderRadius: borderRadius,
          child: AppAssets.hasBundledLogo
              ? Image.asset(
                  AppAssets.logo,
                  fit: fit,
                  errorBuilder: (_, __, ___) => fallback,
                )
              : fallback,
        ),
      ),
    );
  }
}

class _FallbackLogo extends StatelessWidget {
  const _FallbackLogo({
    required this.variant,
    this.width,
    this.height,
  });

  final RGLogoVariant variant;
  final double? width;
  final double? height;

  @override
  Widget build(BuildContext context) {
    switch (variant) {
      case RGLogoVariant.mark:
        return Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                AppThemeColors.primary,
                AppThemeColors.info,
                AppThemeColors.secondary,
              ],
            ),
            border: Border.all(
              color: AppThemeColors.textPrimary.withValues(alpha: 0.14),
            ),
          ),
          child: const Center(
            child: Text(
              AppInfo.companyShort,
              style: TextStyle(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
        );
      case RGLogoVariant.full:
        return Container(
          width: width,
          height: height,
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.xl),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                AppThemeColors.backgroundLight,
                AppThemeColors.surface,
                AppThemeColors.background,
              ],
            ),
            border: Border.all(
              color: AppThemeColors.primary.withValues(alpha: 0.28),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      AppThemeColors.primary,
                      AppThemeColors.info,
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppThemeColors.primary.withValues(alpha: 0.25),
                      blurRadius: 20,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.flight_takeoff_rounded,
                  color: AppThemeColors.textPrimary,
                  size: 30,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppInfo.companyShort,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.displayMedium.copyWith(
                        color: AppThemeColors.textPrimary,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                    Text(
                      'TRAVEL SOLUTION',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.titleMedium.copyWith(
                        color: AppThemeColors.warningLight,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
    }
  }
}
