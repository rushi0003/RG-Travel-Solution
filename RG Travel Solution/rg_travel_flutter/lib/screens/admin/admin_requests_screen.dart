import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../services/admin_service.dart';
import '../../widgets/common/rg_card.dart';

class AdminRequestsScreen extends StatefulWidget {
  const AdminRequestsScreen({super.key});

  @override
  State<AdminRequestsScreen> createState() => _AdminRequestsScreenState();
}

class _AdminRequestsScreenState extends State<AdminRequestsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _loading = false;
  List<Map<String, dynamic>> _absenceList = [];
  List<Map<String, dynamic>> _hometownList = [];
  List<Map<String, dynamic>> _swapList = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _refreshAll();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _refreshAll() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        AdminService.getAbsenceRequests(),
        AdminService.getDriverChangeRequests(),
        AdminService.getSwapRequests(),
      ]);

      if (!mounted) return;
      setState(() {
        _absenceList = results[0];
        _hometownList = results[1];
        _swapList = results[2];
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _approveAbsence(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      await AdminService.approveAbsenceRequest(nid);
      await _refreshAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed: $e')),
      );
    }
  }

  Future<void> _rejectAbsence(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      await AdminService.rejectAbsenceRequest(nid);
      await _refreshAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed: $e')),
      );
    }
  }

  Future<void> _approveHometown(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      await AdminService.approveDriverChange(nid);
      await _refreshAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed: $e')),
      );
    }
  }

  Future<void> _rejectHometown(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      await AdminService.rejectDriverChange(nid);
      await _refreshAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed: $e')),
      );
    }
  }

  Future<void> _approveSwap(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      await AdminService.approveSwapRequest(nid);
      await _refreshAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed: $e')),
      );
    }
  }

  Future<void> _rejectSwap(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      await AdminService.rejectSwapRequest(nid);
      await _refreshAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Pending Requests'),
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppThemeColors.primary,
          unselectedLabelColor: AppThemeColors.textTertiary,
          indicatorColor: AppThemeColors.primary,
          tabs: const [
            Tab(text: 'Absence'),
            Tab(text: 'Profile/Home'),
            Tab(text: 'Swaps'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _loading ? null : _refreshAll,
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(
                controller: _tabController,
                children: [
                  _buildAbsenceList(),
                  _buildHometownList(),
                  _buildSwapList(),
                ],
              ),
      ),
    );
  }

  Widget _buildAbsenceList() {
    final pendingItems = _absenceList.where((item) {
      return (item['status'] ?? 'pending').toString().toLowerCase() ==
          'pending';
    }).toList();
    if (pendingItems.isEmpty) return _emptyState('No absence requests');
    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: pendingItems.length,
      itemBuilder: (ctx, i) {
        final item = pendingItems[i];
        final id = item['id'];
        final name = item['employee_name'] ?? 'Unknown';
        final from =
            (item['from_date'] ?? item['absent_date'] ?? '').toString();
        final to = (item['to_date'] ?? item['absent_date'] ?? '').toString();
        final totalDays = (item['total_days'] ?? 1).toString();
        final reason = item['reason'] ?? '-';
        final kind =
            (item['request_kind'] ?? 'absence').toString().toLowerCase();

        return _requestCard(
          title:
              kind == 'cancel' ? '$name (Cancel Absence)' : '$name (Absence)',
          subtitle: 'From: $from\nTo: $to\nDays: $totalDays\nReason: $reason',
          onApprove: () => _approveAbsence(id),
          onReject: () => _rejectAbsence(id),
        );
      },
    );
  }

  Widget _buildHometownList() {
    if (_hometownList.isEmpty) {
      return _emptyState('No profile/hometown requests');
    }
    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: _hometownList.length,
      itemBuilder: (ctx, i) {
        final item = _hometownList[i];
        final id = item['id'];
        final name = item['driver_name'] ?? 'Driver';
        final changes = item['changes'] ?? <String, dynamic>{};

        var changeText = '';
        if (changes is Map) {
          changes.forEach((k, v) => changeText += '$k: $v\n');
        } else {
          changeText = changes.toString();
        }

        return _requestCard(
          title: '$name (Profile Change)',
          subtitle: changeText.trim(),
          onApprove: () => _approveHometown(id),
          onReject: () => _rejectHometown(id),
        );
      },
    );
  }

  Widget _buildSwapList() {
    if (_swapList.isEmpty) return _emptyState('No swap requests');
    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: _swapList.length,
      itemBuilder: (ctx, i) {
        final item = _swapList[i];
        final id = item['id'];
        final dName = item['driver_name'] ?? 'Driver';
        final reason = item['reason'] ?? '';
        final newDriver = item['new_driver_name'] ?? 'N/A';
        final newCab = item['new_cab_no'] ?? 'N/A';

        return _requestCard(
          title: '$dName (Emergency Swap)',
          subtitle: 'Reason: $reason\nTarget: $newDriver / $newCab',
          onApprove: () => _approveSwap(id),
          onReject: () => _rejectSwap(id),
        );
      },
    );
  }

  Widget _requestCard({
    required String title,
    required String subtitle,
    required VoidCallback onApprove,
    required VoidCallback onReject,
  }) {
    return RGCard(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      title: title,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            subtitle,
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            alignment: WrapAlignment.end,
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              OutlinedButton(
                onPressed: onReject,
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppThemeColors.error,
                  side: const BorderSide(color: AppThemeColors.error),
                ),
                child: const Text('Reject'),
              ),
              ElevatedButton(
                onPressed: onApprove,
                child: const Text('Approve'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _emptyState(String msg) {
    return Center(
      child: RGCard(
        child: Text(
          msg,
          textAlign: TextAlign.center,
          style: AppTypography.bodyMedium.copyWith(
            color: AppThemeColors.textSecondary,
          ),
        ),
      ),
    );
  }
}
