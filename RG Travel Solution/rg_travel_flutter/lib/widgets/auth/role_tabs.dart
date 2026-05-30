// lib/widgets/auth/role_tabs.dart
//
// RG Travel Solution — Role Tabs
//
// Role selection tabs (Admin, Driver, Employee) with glassmorphism effect

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

enum UserRole { admin, driver, employee }

class RoleTabs extends StatelessWidget {
  const RoleTabs({
    super.key,
    required this.selectedRole,
    required this.onRoleChanged,
    this.enabled = true,
  });

  final UserRole selectedRole;
  final ValueChanged<UserRole> onRoleChanged;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(
          color: AppThemeColors.border,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _RoleTab(
              label: 'Admin',
              icon: Icons.admin_panel_settings,
              emoji: '👑',
              isActive: selectedRole == UserRole.admin,
              enabled: enabled,
              onTap: () => onRoleChanged(UserRole.admin),
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _RoleTab(
              label: 'Driver',
              icon: Icons.local_taxi,
              emoji: '🚖',
              isActive: selectedRole == UserRole.driver,
              enabled: enabled,
              onTap: () => onRoleChanged(UserRole.driver),
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _RoleTab(
              label: 'Employee',
              icon: Icons.badge,
              emoji: '🧑‍💼',
              isActive: selectedRole == UserRole.employee,
              enabled: enabled,
              onTap: () => onRoleChanged(UserRole.employee),
            ),
          ),
        ],
      ),
    );
  }
}

class _RoleTab extends StatelessWidget {
  const _RoleTab({
    required this.label,
    required this.icon,
    required this.emoji,
    required this.isActive,
    required this.enabled,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final String emoji;
  final bool isActive;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: AnimatedContainer(
        duration: AppAnimations.fast,
        curve: AppAnimations.defaultCurve,
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: AppSpacing.sm),
        decoration: BoxDecoration(
          color: isActive
              ? AppThemeColors.cardGlassActive
              : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
            color: isActive
                ? AppThemeColors.primary.withValues(alpha: 0.25)
                : Colors.transparent,
            width: 1,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              emoji,
              style: TextStyle(
                fontSize: 24,
                color: enabled
                    ? AppThemeColors.textPrimary
                    : AppThemeColors.textTertiary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: AppTypography.labelSmall.copyWith(
                color: isActive
                    ? AppThemeColors.textPrimary
                    : AppThemeColors.textSecondary,
                fontWeight: isActive ? FontWeight.w700 : FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
