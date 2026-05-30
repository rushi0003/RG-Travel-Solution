// lib/widgets/auth/sub_tabs.dart
//
// RG Travel Solution — Sub Tabs
//
// Login / Registration toggle for Driver and Employee modes

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

enum AuthMode { login, register }

class SubTabs extends StatelessWidget {
  const SubTabs({
    super.key,
    required this.selectedMode,
    required this.onModeChanged,
    this.enabled = true,
    this.loginLabel = 'Login',
    this.registerLabel = 'New Registration',
  });

  final AuthMode selectedMode;
  final ValueChanged<AuthMode> onModeChanged;
  final bool enabled;
  final String loginLabel;
  final String registerLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: AppThemeColors.border,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _SubTab(
              label: loginLabel,
              isActive: selectedMode == AuthMode.login,
              enabled: enabled,
              onTap: () => onModeChanged(AuthMode.login),
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: _SubTab(
              label: registerLabel,
              isActive: selectedMode == AuthMode.register,
              enabled: enabled,
              onTap: () => onModeChanged(AuthMode.register),
            ),
          ),
        ],
      ),
    );
  }
}

class _SubTab extends StatelessWidget {
  const _SubTab({
    required this.label,
    required this.isActive,
    required this.enabled,
    required this.onTap,
  });

  final String label;
  final bool isActive;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: AnimatedContainer(
        duration: AppAnimations.fast,
        curve: AppAnimations.defaultCurve,
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: AppSpacing.md),
        decoration: BoxDecoration(
          color: isActive
              ? AppThemeColors.primary.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: Border.all(
            color: isActive
                ? AppThemeColors.primary.withValues(alpha: 0.3)
                : Colors.transparent,
            width: 1,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: AppTypography.labelSmall.copyWith(
              color: isActive
                  ? AppThemeColors.textPrimary
                  : AppThemeColors.textSecondary,
              fontWeight: isActive ? FontWeight.w700 : FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
