// flutter/lib/widgets/layout/side_profile_drawer.dart
//
// RG Travel Solution — Side Profile Drawer (Left Sidebar)
//
// Supports roles:
// - Admin: profile + (Update profile, Logout) + 6 center buttons
// - Driver: profile + (Update profile, Trip history, Logout)
// - Employee: profile + (Update profile, Absent, Trip history, Help desk, Logout)
//
// IMPORTANT:
// This widget does NOT call backend directly.
// It uses callbacks to integrate with services/endpoints.
//
// Recommended backend endpoints (to be used in services/screens):
// Admin profile:
//   GET  /api/admin/{adminId}
//   PUT  /api/admin/{adminId}
// Driver profile:
//   GET  /api/driver/{driverId}
//   PUT  /api/driver/{driverId}   (or request-change flow)
// Employee profile:
//   GET  /api/employee/{employeeId}
//   PUT  /api/employee/{employeeId} (or request-change flow)

import 'package:flutter/material.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_logo.dart';

enum RGRole { admin, driver, employee }

class SideProfileDrawer extends StatelessWidget {
  final RGRole role;

  /// Display data
  final String name;
  final String mobile;

  /// Optional role-specific fields
  final String? officeName;
  final String? officeAddress;

  final String? cabNo;
  final String? dlNo;
  final String? homeTown;

  final String? employeeCode;
  final String? loginTime;
  final String? logoutTime;
  final String? homeAddress;

  /// Navigation callbacks (menu)
  final VoidCallback? onOpenUpdateProfile;
  final VoidCallback? onLogout;

  // Admin menu (6 buttons)
  final VoidCallback? onAdminCreateGroupAssign;
  final VoidCallback? onAdminLiveTrips;
  final VoidCallback? onAdminDrivers;
  final VoidCallback? onAdminEmployees;
  final VoidCallback? onAdminTripHistory;
  final VoidCallback? onAdminLiveTracking;

  // Driver menu
  final VoidCallback? onDriverTripHistory;

  // Employee menu
  final VoidCallback? onEmployeeAbsent;
  final VoidCallback? onEmployeeTripHistory;
  final VoidCallback? onEmployeeHelpDesk;

  /// UI
  final bool isBusy;
  final String appTitle;

  const SideProfileDrawer({
    super.key,
    required this.role,
    required this.name,
    required this.mobile,
    this.officeName,
    this.officeAddress,
    this.cabNo,
    this.dlNo,
    this.homeTown,
    this.employeeCode,
    this.loginTime,
    this.logoutTime,
    this.homeAddress,
    this.onOpenUpdateProfile,
    this.onLogout,
    this.onAdminCreateGroupAssign,
    this.onAdminLiveTrips,
    this.onAdminDrivers,
    this.onAdminEmployees,
    this.onAdminTripHistory,
    this.onAdminLiveTracking,
    this.onDriverTripHistory,
    this.onEmployeeAbsent,
    this.onEmployeeTripHistory,
    this.onEmployeeHelpDesk,
    this.isBusy = false,
    this.appTitle = "RG Travel Solution",
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final roleLabel = switch (role) {
      RGRole.admin => "ADMIN",
      RGRole.driver => "DRIVER",
      RGRole.employee => "EMPLOYEE",
    };

    return Drawer(
      width: 330,
      backgroundColor: theme.colorScheme.surface.withValues(alpha: 0.92),
      child: SafeArea(
        child: Column(
          children: [
            _Header(
              appTitle: appTitle,
              roleLabel: roleLabel,
              name: name,
              mobile: mobile,
            ),
            const SizedBox(height: 10),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
                children: [
                  _ProfileCard(
                    role: role,
                    name: name,
                    mobile: mobile,
                    officeName: officeName,
                    officeAddress: officeAddress,
                    cabNo: cabNo,
                    dlNo: dlNo,
                    homeTown: homeTown,
                    employeeCode: employeeCode,
                    loginTime: loginTime,
                    logoutTime: logoutTime,
                    homeAddress: homeAddress,
                  ),
                  const SizedBox(height: 14),

                  // Primary actions
                  RGButton(
                    text: "Update Profile",
                    icon: Icons.edit_rounded,
                    variant: RGButtonVariant.primary,
                    isLoading: isBusy,
                    onPressed: isBusy ? null : onOpenUpdateProfile,
                  ),
                  const SizedBox(height: 10),

                  ..._buildRoleMenu(context),

                  const SizedBox(height: 16),
                  RGButton(
                    text: "Logout",
                    icon: Icons.logout_rounded,
                    variant: RGButtonVariant.danger,
                    isLoading: false,
                    onPressed: onLogout,
                  ),
                ],
              ),
            ),
            _FooterNote(role: role),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildRoleMenu(BuildContext context) {
    final items = <Widget>[];

    switch (role) {
      case RGRole.admin:
        items.addAll([
          _SectionTitle(text: "Admin Modules"),
          const SizedBox(height: 10),
          _MenuGrid(items: [
            _MenuItem(
              title: "Create Group\n& Assign Trip",
              icon: Icons.groups_rounded,
              onTap: onAdminCreateGroupAssign,
            ),
            _MenuItem(
              title: "View\nLive Trips",
              icon: Icons.route_rounded,
              onTap: onAdminLiveTrips,
            ),
            _MenuItem(
              title: "Drivers",
              icon: Icons.directions_car_filled_rounded,
              onTap: onAdminDrivers,
            ),
            _MenuItem(
              title: "Employees",
              icon: Icons.badge_rounded,
              onTap: onAdminEmployees,
            ),
            _MenuItem(
              title: "Trip\nHistory",
              icon: Icons.history_rounded,
              onTap: onAdminTripHistory,
            ),
            _MenuItem(
              title: "Live Driver\nTracking",
              icon: Icons.location_searching_rounded,
              onTap: onAdminLiveTracking,
            ),
          ]),
        ]);
        break;

      case RGRole.driver:
        items.addAll([
          _SectionTitle(text: "Driver"),
          const SizedBox(height: 10),
          _MenuGrid(items: [
            _MenuItem(
              title: "Trip History",
              icon: Icons.history_rounded,
              onTap: onDriverTripHistory,
            ),
          ]),
        ]);
        break;

      case RGRole.employee:
        items.addAll([
          _SectionTitle(text: "Employee"),
          const SizedBox(height: 10),
          _MenuGrid(items: [
            _MenuItem(
              title: "Absent\nRequest",
              icon: Icons.event_busy_rounded,
              onTap: onEmployeeAbsent,
            ),
            _MenuItem(
              title: "Trip\nHistory",
              icon: Icons.history_rounded,
              onTap: onEmployeeTripHistory,
            ),
            _MenuItem(
              title: "Help\nDesk",
              icon: Icons.support_agent_rounded,
              onTap: onEmployeeHelpDesk,
            ),
          ]),
        ]);
        break;
    }

    return items.expand((w) => [w, const SizedBox(height: 10)]).toList()
      ..removeLast(); // remove last extra gap
  }
}

// =============================================================
// Header
// =============================================================

class _Header extends StatelessWidget {
  final String appTitle;
  final String roleLabel;
  final String name;
  final String mobile;

  const _Header({
    required this.appTitle,
    required this.roleLabel,
    required this.name,
    required this.mobile,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: theme.dividerColor.withValues(alpha: 0.5),
          ),
        ),
      ),
      child: Row(
        children: [
          _Avatar(name: name),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const RGLogo(
                      variant: RGLogoVariant.mark,
                      width: 28,
                      height: 28,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        appTitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w900,
                          letterSpacing: 0,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    _RoleChip(text: roleLabel),
                    const SizedBox(width: 8),
                    Text(
                      mobile,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.72),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_left_rounded),
        ],
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  final String name;
  const _Avatar({required this.name});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final initials = _initials(name);

    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primary.withValues(alpha: 0.95),
            theme.colorScheme.primary.withValues(alpha: 0.35),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withValues(alpha: 0.18),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Center(
        child: Text(
          initials,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w900,
            letterSpacing: 0,
            color: theme.colorScheme.onPrimary,
          ),
        ),
      ),
    );
  }

  String _initials(String input) {
    final parts = input.trim().split(RegExp(r"\s+"));
    if (parts.isEmpty) return "RG";
    final a = parts.first.isNotEmpty ? parts.first[0].toUpperCase() : "R";
    final b = parts.length > 1 && parts[1].isNotEmpty
        ? parts[1][0].toUpperCase()
        : "G";
    return "$a$b";
  }
}

class _RoleChip extends StatelessWidget {
  final String text;
  const _RoleChip({required this.text});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: theme.dividerColor.withValues(alpha: 0.45),
        ),
      ),
      child: Text(
        text,
        style: theme.textTheme.labelSmall?.copyWith(
          fontWeight: FontWeight.w900,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

// =============================================================
// Profile Card
// =============================================================

class _ProfileCard extends StatelessWidget {
  final RGRole role;
  final String name;
  final String mobile;

  final String? officeName;
  final String? officeAddress;

  final String? cabNo;
  final String? dlNo;
  final String? homeTown;

  final String? employeeCode;
  final String? loginTime;
  final String? logoutTime;
  final String? homeAddress;

  const _ProfileCard({
    required this.role,
    required this.name,
    required this.mobile,
    this.officeName,
    this.officeAddress,
    this.cabNo,
    this.dlNo,
    this.homeTown,
    this.employeeCode,
    this.loginTime,
    this.logoutTime,
    this.homeAddress,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    List<_KV> rows = [];

    rows.add(_KV("Name", name));
    rows.add(_KV("Mobile", mobile));

    if (role == RGRole.admin) {
      rows.add(_KV("Office Name", officeName ?? "-"));
      rows.add(_KV("Office Address", officeAddress ?? "-"));
    }

    if (role == RGRole.driver) {
      rows.add(_KV("Cab No", cabNo ?? "-"));
      rows.add(_KV("DL No", dlNo ?? "-"));
      rows.add(_KV("Home Town", homeTown ?? "-"));
    }

    if (role == RGRole.employee) {
      rows.add(_KV("Employee Code", employeeCode ?? "-"));
      rows.add(_KV("Login Time", loginTime ?? "-"));
      rows.add(_KV("Logout Time", logoutTime ?? "-"));
      rows.add(_KV("Home Address", homeAddress ?? "-"));
    }

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.26),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.40)),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withValues(alpha: 0.10),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Profile",
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 10),
          ...rows.map((kv) => _ProfileRow(k: kv.k, v: kv.v)).toList(),
        ],
      ),
    );
  }
}

class _ProfileRow extends StatelessWidget {
  final String k;
  final String v;
  const _ProfileRow({required this.k, required this.v});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              k,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.70),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Text(
              v,
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _KV {
  final String k;
  final String v;
  _KV(this.k, this.v);
}

// =============================================================
// Menu grid
// =============================================================

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle({required this.text});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Text(
      text,
      style: theme.textTheme.titleSmall?.copyWith(
        fontWeight: FontWeight.w900,
        letterSpacing: 0,
      ),
    );
  }
}

class _MenuGrid extends StatelessWidget {
  final List<_MenuItem> items;
  const _MenuGrid({required this.items});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (_, c) {
        // 2-column grid (fixed)
        final itemWidth = (c.maxWidth - 12) / 2;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: items
              .map(
                (it) => SizedBox(
                  width: itemWidth,
                  child: _MenuTile(item: it),
                ),
              )
              .toList(),
        );
      },
    );
  }
}

class _MenuItem {
  final String title;
  final IconData icon;
  final VoidCallback? onTap;
  _MenuItem({required this.title, required this.icon, required this.onTap});
}

class _MenuTile extends StatelessWidget {
  final _MenuItem item;
  const _MenuTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: theme.colorScheme.surface.withValues(alpha: 0.22),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: item.onTap == null
            ? null
            : () {
                Navigator.pop(context); // close drawer
                item.onTap!.call();
              },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: theme.dividerColor.withValues(alpha: 0.38)),
          ),
          child: Row(
            children: [
              Icon(item.icon,
                  size: 18,
                  color: theme.colorScheme.primary.withValues(alpha: 0.95)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  item.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w900,
                    height: 1.2,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// =============================================================
// Footer
// =============================================================

class _FooterNote extends StatelessWidget {
  final RGRole role;
  const _FooterNote({required this.role});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final note = switch (role) {
      RGRole.admin =>
        "Tip: Use Create Group to auto-group 4/6 employees and assign a route.",
      RGRole.driver =>
        "Tip: Verify OTP to start/end trip. Mark No-Show if employee absent.",
      RGRole.employee =>
        "Tip: Get OTP for trip start/end and track driver live on map.",
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
      decoration: BoxDecoration(
        border: Border(
            top: BorderSide(color: theme.dividerColor.withValues(alpha: 0.5))),
      ),
      child: Text(
        note,
        style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.onSurface.withValues(alpha: 0.65),
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
