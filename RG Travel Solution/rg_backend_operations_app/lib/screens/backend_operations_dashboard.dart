import 'dart:async';

import 'package:flutter/material.dart';

import '../models/admin_operations_snapshot.dart';
import '../services/admin_operations_service.dart';
import '../services/admin_service.dart';
import '../services/ops_session_store.dart';
import '../theme/ops_ui_tokens.dart';
import 'admin_access_screen.dart';
import 'fleet_operations_screen.dart';
import 'operations_ui.dart';
import 'ops_login_screen.dart';
import 'request_queue_screen.dart';
import 'support_operations_screen.dart';
import 'trip_operations_screen.dart';

enum OpsSection {
  overview,
  adminAccess,
  trips,
  requests,
  fleet,
  support,
}

class BackendOperationsDashboard extends StatefulWidget {
  const BackendOperationsDashboard({super.key});

  @override
  State<BackendOperationsDashboard> createState() =>
      _BackendOperationsDashboardState();
}

class _BackendOperationsDashboardState
    extends State<BackendOperationsDashboard> {
  final TextEditingController _baseUrlController =
      TextEditingController(text: AdminService.baseUrl);
  AdminOperationsSnapshot _snapshot = const AdminOperationsSnapshot();
  OpsSection _section = OpsSection.overview;
  Timer? _pollTimer;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
    _pollTimer = Timer.periodic(const Duration(seconds: 20), (_) => _load());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _baseUrlController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final snapshot = await AdminOperationsService.loadSnapshot();
      if (!mounted) return;
      setState(() {
        _snapshot = snapshot;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _applyBaseUrl() async {
    AdminService.setBaseUrl(_baseUrlController.text);
    await _load();
  }

  void _openScreen(Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  Future<void> _logout() async {
    await OpsSessionStore.clear();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const OpsLoginScreen()),
      (_) => false,
    );
  }

  List<_OpsNavItem> get _navItems => [
        const _OpsNavItem(
          section: OpsSection.overview,
          title: 'Overview',
          subtitle: 'Live control room',
          icon: Icons.dashboard_customize_rounded,
        ),
        const _OpsNavItem(
          section: OpsSection.adminAccess,
          title: 'Admin Access',
          subtitle: 'Credential control',
          icon: Icons.admin_panel_settings_rounded,
        ),
        const _OpsNavItem(
          section: OpsSection.trips,
          title: 'Trip Operations',
          subtitle: 'Routes and trip changes',
          icon: Icons.alt_route_rounded,
        ),
        const _OpsNavItem(
          section: OpsSection.requests,
          title: 'Request Queue',
          subtitle: 'Pending approvals',
          icon: Icons.inventory_2_rounded,
        ),
        const _OpsNavItem(
          section: OpsSection.fleet,
          title: 'Fleet and Drivers',
          subtitle: 'Driver readiness',
          icon: Icons.local_taxi_rounded,
        ),
        const _OpsNavItem(
          section: OpsSection.support,
          title: 'Safety and Support',
          subtitle: 'SOS and helpdesk',
          icon: Icons.support_agent_rounded,
        ),
      ];

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= OpsBreakpoints.desktop;
    final sectionMeta = _sectionMeta(_section);

    return Scaffold(
      appBar: AppBar(
        title: const Text('RG Backend Operations'),
        actions: [
          IconButton(
            onPressed: _load,
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh',
          ),
          IconButton(
            onPressed: _logout,
            icon: const Icon(Icons.logout_rounded),
            tooltip: 'Logout',
          ),
        ],
      ),
      drawer: isWide ? null : Drawer(child: _buildSidebar()),
      body: Container(
        decoration: OpsDecorations.pageBackground(),
        child: Row(
          children: [
            if (isWide) SizedBox(width: 310, child: _buildSidebar()),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  padding: context.opsPagePadding,
                  children: [
                    OpsResponsiveContainer(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildHero(sectionMeta),
                          const SizedBox(height: OpsSpacing.xl),
                          _buildConnectionCard(),
                          const SizedBox(height: OpsSpacing.xl),
                          _buildStatusBar(),
                          const SizedBox(height: OpsSpacing.xxl),
                          if (_loading)
                            const OpsLoadingState(
                              message: 'Refreshing operations snapshot...',
                            )
                          else if (_error != null)
                            _buildErrorCard()
                          else
                            _buildSectionContent(),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSidebar() {
    return Container(
      color: OpsUiTokens.background,
      padding: const EdgeInsets.fromLTRB(
        OpsSpacing.xl,
        OpsSpacing.xl,
        OpsSpacing.xl,
        OpsSpacing.xxl,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: OpsSpacing.cardCompact,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(OpsRadius.xl),
              gradient: OpsGradients.hero,
              border: Border.all(color: OpsUiTokens.outlineStrong),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 20,
                      backgroundColor:
                          OpsUiTokens.primary.withValues(alpha: 0.14),
                      child: const Icon(
                        Icons.hub_rounded,
                        color: OpsUiTokens.primarySoft,
                      ),
                    ),
                    const SizedBox(width: OpsSpacing.md),
                    const Expanded(
                      child: Text(
                        'Ops Control',
                        style: OpsTypography.title,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: OpsSpacing.lg),
                const Text(
                  'Dedicated admin console for backend travel operations.',
                  style: OpsTypography.body,
                ),
              ],
            ),
          ),
          const SizedBox(height: OpsSpacing.xl),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: _navItems.map((item) {
                final selected = _section == item.section;
                return Padding(
                  padding: const EdgeInsets.only(bottom: OpsSpacing.md),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () {
                        setState(() => _section = item.section);
                        Navigator.maybePop(context);
                      },
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        padding: OpsSpacing.cardCompact,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(OpsRadius.lg),
                          color: selected
                              ? OpsUiTokens.panelSidebarActive
                              : OpsUiTokens.panel,
                          border: Border.all(
                            color: selected
                                ? OpsUiTokens.primary
                                : OpsUiTokens.outline,
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(OpsSpacing.md),
                              decoration: BoxDecoration(
                                color: selected
                                    ? OpsUiTokens.primary
                                        .withValues(alpha: 0.14)
                                    : OpsUiTokens.panelMuted,
                                borderRadius:
                                    BorderRadius.circular(OpsRadius.md),
                              ),
                              child: Icon(
                                item.icon,
                                color: selected
                                    ? OpsUiTokens.primarySoft
                                    : OpsUiTokens.textSecondary,
                              ),
                            ),
                            const SizedBox(width: OpsSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    item.title,
                                    style: OpsTypography.bodyStrong,
                                  ),
                                  const SizedBox(height: OpsSpacing.xs),
                                  Text(
                                    item.subtitle,
                                    style: OpsTypography.caption,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: OpsSpacing.md),
          const OpsPanel(
            padding: OpsSpacing.cardCompact,
            radius: OpsRadius.lg,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Auto refresh',
                  style: OpsTypography.bodyStrong,
                ),
                SizedBox(height: OpsSpacing.xs),
                Text(
                  'Snapshot updates every 20 seconds while the dashboard stays open.',
                  style: OpsTypography.body,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHero(_OpsSectionMeta meta) {
    return Container(
      padding: const EdgeInsets.all(OpsSpacing.xxl),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(OpsRadius.xxl),
        gradient: OpsGradients.hero,
        border: Border.all(color: OpsUiTokens.outlineStrong),
        boxShadow: OpsShadows.glow(OpsUiTokens.primary),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: OpsSpacing.xl,
            runSpacing: OpsSpacing.xl,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(OpsSpacing.lg),
                decoration: BoxDecoration(
                  color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(OpsRadius.lg),
                ),
                child:
                    Icon(meta.icon, size: 34, color: OpsUiTokens.primarySoft),
              ),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 620),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      meta.title,
                      style: OpsTypography.display,
                    ),
                    const SizedBox(height: OpsSpacing.sm),
                    Text(
                      meta.subtitle,
                      style: OpsTypography.body,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: OpsSpacing.xl),
          Wrap(
            spacing: OpsSpacing.md,
            runSpacing: OpsSpacing.md,
            children: [
              _heroChip('Live Trips', _snapshot.liveTrips),
              _heroChip('Pending Approvals', _snapshot.pendingApprovals),
              _heroChip('Online Drivers', _snapshot.onlineDrivers),
              _heroChip('SOS', _snapshot.sos),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildConnectionCard() {
    return _panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.settings_ethernet_rounded,
                color: OpsUiTokens.primarySoft,
              ),
              SizedBox(width: OpsSpacing.md),
              Text(
                'Backend Connection',
                style: OpsTypography.title,
              ),
            ],
          ),
          const SizedBox(height: OpsSpacing.sm),
          const Text(
            'Use this console only for backend operations. It talks directly to the Flask backend used by the admin workflows.',
            style: OpsTypography.body,
          ),
          const SizedBox(height: OpsSpacing.lg),
          Wrap(
            spacing: OpsSpacing.md,
            runSpacing: OpsSpacing.md,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [
              SizedBox(
                width: 520,
                child: TextField(
                  controller: _baseUrlController,
                  decoration: const InputDecoration(
                    labelText: 'Backend Base URL',
                    hintText: 'http://127.0.0.1:5000',
                    prefixIcon: Icon(Icons.link_rounded),
                  ),
                ),
              ),
              FilledButton.icon(
                onPressed: _applyBaseUrl,
                icon: const Icon(Icons.check_rounded),
                label: const Text('Apply Connection'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBar() {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _pill('Live Trips', _snapshot.liveTrips, OpsUiTokens.info),
        _pill('Pending', _snapshot.pendingApprovals, OpsUiTokens.warning),
        _pill(
          'Online Drivers',
          _snapshot.onlineDrivers,
          OpsUiTokens.blue,
        ),
        _pill('SOS', _snapshot.sos, OpsUiTokens.danger),
        _pill('Helpdesk', _snapshot.helpdesk, OpsUiTokens.secondary),
      ],
    );
  }

  Widget _buildSectionContent() {
    switch (_section) {
      case OpsSection.overview:
        return _buildOverview();
      case OpsSection.adminAccess:
        return _buildAdminAccess();
      case OpsSection.trips:
        return _buildTrips();
      case OpsSection.requests:
        return _buildRequests();
      case OpsSection.fleet:
        return _buildFleet();
      case OpsSection.support:
        return _buildSupport();
    }
  }

  Widget _buildOverview() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(
          'Operations Snapshot',
          'High-signal overview of trips, approvals, fleet readiness, and support pressure.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 280,
              child: _statCard(
                'Live Trips',
                _snapshot.liveTrips,
                Icons.alt_route_rounded,
                tone: OpsUiTokens.info,
              ),
            ),
            SizedBox(
              width: 280,
              child: _statCard(
                'Pending Approvals',
                _snapshot.pendingApprovals,
                Icons.rule_rounded,
                tone: OpsUiTokens.warning,
              ),
            ),
            SizedBox(
              width: 280,
              child: _statCard(
                'Drivers',
                _snapshot.drivers,
                Icons.badge_rounded,
                tone: OpsUiTokens.blue,
              ),
            ),
            SizedBox(
              width: 280,
              child: _statCard(
                'Employees',
                _snapshot.employees,
                Icons.groups_rounded,
                tone: OpsUiTokens.secondary,
              ),
            ),
            SizedBox(
              width: 280,
              child: _statCard(
                'Online Drivers',
                _snapshot.onlineDrivers,
                Icons.local_taxi_rounded,
                tone: OpsUiTokens.purple,
              ),
            ),
            SizedBox(
              width: 280,
              child: _statCard(
                'Support Load',
                _snapshot.helpdesk + _snapshot.sos,
                Icons.support_agent_rounded,
                tone: OpsUiTokens.danger,
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 360,
              child: _actionCard(
                title: 'Admin Access',
                description:
                    'Provision and remove backend admins from the dedicated access workspace.',
                icon: Icons.admin_panel_settings_rounded,
                tone: OpsUiTokens.info,
                actionLabel: 'Open Admin Access',
                onTap: () => _openScreen(const AdminAccessScreen()),
              ),
            ),
            SizedBox(
              width: 360,
              child: _actionCard(
                title: 'Trip Operations',
                description:
                    'Review live trips, swap pressure, and cancellation workload.',
                icon: Icons.alt_route_rounded,
                tone: OpsUiTokens.warning,
                actionLabel: 'Open Trip Operations',
                onTap: () => _openScreen(const TripOperationsScreen()),
              ),
            ),
            SizedBox(
              width: 360,
              child: _actionCard(
                title: 'Safety and Support',
                description:
                    'Track SOS alerts and helpdesk volume from one response view.',
                icon: Icons.support_agent_rounded,
                tone: OpsUiTokens.secondary,
                actionLabel: 'Open Support Detail',
                onTap: () => _openScreen(const SupportOperationsScreen()),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTrips() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(
          'Trip Operations',
          'Core trip activity, live demand, and intervention load.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 300,
              child: _statCard(
                'Live Trips',
                _snapshot.liveTrips,
                Icons.timeline_rounded,
                tone: OpsUiTokens.info,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Swap Requests',
                _snapshot.swapRequests,
                Icons.swap_horiz_rounded,
                tone: OpsUiTokens.warning,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Trip Cancel Requests',
                _snapshot.tripCancels,
                Icons.cancel_schedule_send_rounded,
                tone: OpsUiTokens.danger,
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _actionCard(
          title: 'Trip intervention board',
          description:
              'Open the trip detail screen to inspect active trips, swaps, and cancel requests.',
          icon: Icons.open_in_new_rounded,
          tone: OpsUiTokens.info,
          actionLabel: 'Open Trip Operations Detail',
          onTap: () => _openScreen(const TripOperationsScreen()),
        ),
      ],
    );
  }

  Widget _buildAdminAccess() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(
          'Admin Access',
          'Admin login data stays in the backend database. Manage who can enter the operations console.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 300,
              child: _statCard(
                'Access Workspace',
                1,
                Icons.admin_panel_settings_rounded,
                tone: OpsUiTokens.info,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Login Backend',
                1,
                Icons.storage_rounded,
                tone: OpsUiTokens.secondary,
              ),
            ),
            SizedBox(
              width: 300,
              child: _panel(
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Access policy',
                      style: OpsTypography.title,
                    ),
                    SizedBox(height: OpsSpacing.md),
                    Text(
                      'Use the Admin Access screen to create new credentials, review admin readiness, and remove stale accounts.',
                      style: OpsTypography.body,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _actionCard(
          title: 'Open admin access workspace',
          description:
              'Go to the dedicated admin control screen for searchable admin management and create/remove actions.',
          icon: Icons.manage_accounts_rounded,
          tone: OpsUiTokens.info,
          actionLabel: 'Open Admin Access Detail',
          onTap: () => _openScreen(const AdminAccessScreen()),
        ),
      ],
    );
  }

  Widget _buildRequests() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(
          'Request Queue',
          'All approval-heavy operational flows in one place.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 300,
              child: _statCard(
                'Driver Requests',
                _snapshot.driverRequests,
                Icons.badge_rounded,
                tone: OpsUiTokens.blue,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Employee Requests',
                _snapshot.employeeRequests,
                Icons.people_alt_rounded,
                tone: OpsUiTokens.secondary,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Driver Changes',
                _snapshot.driverChanges,
                Icons.manage_accounts_rounded,
                tone: OpsUiTokens.warning,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Employee Changes',
                _snapshot.employeeChanges,
                Icons.edit_note_rounded,
                tone: OpsUiTokens.purple,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Absence Requests',
                _snapshot.absenceRequests,
                Icons.event_busy_rounded,
                tone: OpsUiTokens.danger,
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _actionCard(
          title: 'Open approval queue',
          description:
              'Inspect pending driver, employee, change, and absence requests from the full queue screen.',
          icon: Icons.open_in_new_rounded,
          tone: OpsUiTokens.warning,
          actionLabel: 'Open Request Queue Detail',
          onTap: () => _openScreen(const RequestQueueScreen()),
        ),
      ],
    );
  }

  Widget _buildFleet() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(
          'Fleet and Drivers',
          'Operational fleet readiness and active workforce visibility.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 300,
              child: _statCard(
                'Drivers',
                _snapshot.drivers,
                Icons.local_taxi_rounded,
                tone: OpsUiTokens.blue,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Online Drivers',
                _snapshot.onlineDrivers,
                Icons.location_searching_rounded,
                tone: OpsUiTokens.info,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Employees',
                _snapshot.employees,
                Icons.groups_rounded,
                tone: OpsUiTokens.secondary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _actionCard(
          title: 'Open fleet detail',
          description:
              'Drill into the fleet screen for more detailed driver and employee visibility.',
          icon: Icons.open_in_new_rounded,
          tone: OpsUiTokens.blue,
          actionLabel: 'Open Fleet Detail',
          onTap: () => _openScreen(const FleetOperationsScreen()),
        ),
      ],
    );
  }

  Widget _buildSupport() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(
          'Safety and Support',
          'Emergency signals and support workload from one response layer.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 300,
              child: _statCard(
                'SOS Alerts',
                _snapshot.sos,
                Icons.warning_amber_rounded,
                tone: OpsUiTokens.danger,
              ),
            ),
            SizedBox(
              width: 300,
              child: _statCard(
                'Helpdesk Tickets',
                _snapshot.helpdesk,
                Icons.support_agent_rounded,
                tone: OpsUiTokens.secondary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _actionCard(
          title: 'Open support detail',
          description:
              'Review emergency alerts and helpdesk queue items in the dedicated support screen.',
          icon: Icons.open_in_new_rounded,
          tone: OpsUiTokens.secondary,
          actionLabel: 'Open Support Detail',
          onTap: () => _openScreen(const SupportOperationsScreen()),
        ),
      ],
    );
  }

  Widget _buildErrorCard() {
    return ErrorCard(message: _error!);
  }

  Widget _sectionHeader(String title, String subtitle) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: OpsTypography.heading,
        ),
        const SizedBox(height: OpsSpacing.xs),
        Text(
          subtitle,
          style: OpsTypography.body,
        ),
      ],
    );
  }

  Widget _statCard(
    String title,
    int value,
    IconData icon, {
    required Color tone,
  }) {
    return _panel(
      borderColor: tone.withValues(alpha: 0.28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(OpsSpacing.md),
            decoration: BoxDecoration(
              color: tone.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(OpsRadius.md),
            ),
            child: Icon(icon, color: tone, size: 24),
          ),
          const SizedBox(height: OpsSpacing.lg),
          Text(
            '$value',
            style: OpsTypography.display,
          ),
          const SizedBox(height: OpsSpacing.sm),
          Text(
            title,
            style: OpsTypography.subtitle,
          ),
        ],
      ),
    );
  }

  Widget _actionCard({
    required String title,
    required String description,
    required IconData icon,
    required Color tone,
    required String actionLabel,
    required VoidCallback onTap,
  }) {
    return _panel(
      borderColor: tone.withValues(alpha: 0.25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(OpsSpacing.md),
            decoration: BoxDecoration(
              color: tone.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(OpsRadius.md),
            ),
            child: Icon(icon, color: tone),
          ),
          const SizedBox(height: OpsSpacing.lg),
          Text(
            title,
            style: OpsTypography.title,
          ),
          const SizedBox(height: OpsSpacing.sm),
          Text(
            description,
            style: OpsTypography.body,
          ),
          const SizedBox(height: OpsSpacing.xl),
          FilledButton.icon(
            onPressed: onTap,
            icon: const Icon(Icons.open_in_new_rounded),
            label: Text(actionLabel),
          ),
        ],
      ),
    );
  }

  Widget _pill(String label, int value, Color color) {
    return OpsStatusBadge(
      label: '$label: $value',
      tone: color,
      compact: true,
    );
  }

  Widget _heroChip(String label, int value) {
    return OpsStatusBadge(
      label: '$label: $value',
      tone: OpsUiTokens.primarySoft,
      compact: true,
    );
  }

  Widget _panel({
    required Widget child,
    Color borderColor = OpsUiTokens.outline,
  }) {
    return OpsPanel(
      borderColor: borderColor,
      child: child,
    );
  }

  _OpsSectionMeta _sectionMeta(OpsSection section) {
    switch (section) {
      case OpsSection.overview:
        return const _OpsSectionMeta(
          title: 'Operations Overview',
          subtitle:
              'Monitor the full backend operations landscape from one dashboard before drilling into detail screens.',
          icon: Icons.dashboard_customize_rounded,
        );
      case OpsSection.adminAccess:
        return const _OpsSectionMeta(
          title: 'Admin Access Control',
          subtitle:
              'Manage backend admin credentials and keep console access aligned with your current operations team.',
          icon: Icons.admin_panel_settings_rounded,
        );
      case OpsSection.trips:
        return const _OpsSectionMeta(
          title: 'Trip Operations Control',
          subtitle:
              'Track live trip load, swaps, and cancellations that require intervention from operations.',
          icon: Icons.alt_route_rounded,
        );
      case OpsSection.requests:
        return const _OpsSectionMeta(
          title: 'Request Queue Management',
          subtitle:
              'Stay on top of pending approvals across driver, employee, and absence workflows.',
          icon: Icons.inventory_2_rounded,
        );
      case OpsSection.fleet:
        return const _OpsSectionMeta(
          title: 'Fleet Readiness',
          subtitle:
              'Watch driver availability and workforce numbers that shape daily execution capacity.',
          icon: Icons.local_taxi_rounded,
        );
      case OpsSection.support:
        return const _OpsSectionMeta(
          title: 'Safety and Support Response',
          subtitle:
              'Review SOS pressure and helpdesk workload from a single support-facing command layer.',
          icon: Icons.support_agent_rounded,
        );
    }
  }
}

class _OpsNavItem {
  const _OpsNavItem({
    required this.section,
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final OpsSection section;
  final String title;
  final String subtitle;
  final IconData icon;
}

class _OpsSectionMeta {
  const _OpsSectionMeta({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;
}
