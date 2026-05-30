import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../services/admin_service.dart';
import '../../widgets/common/rg_card.dart';

class AdminSOSScreen extends StatefulWidget {
  const AdminSOSScreen({super.key});

  @override
  State<AdminSOSScreen> createState() => _AdminSOSScreenState();
}

class _AdminSOSScreenState extends State<AdminSOSScreen> {
  List<Map<String, dynamic>> _alerts = [];

  @override
  void initState() {
    super.initState();
    _fetchSOS();
  }

  Future<void> _fetchSOS() async {
    try {
      final data = await AdminService.getSOSAlerts();
      if (mounted) {
        setState(() => _alerts = data);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  Future<void> _resolve(int id) async {
    final noteCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Resolve SOS'),
        content: TextField(
          controller: noteCtrl,
          decoration: const InputDecoration(labelText: 'Resolution Note'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Resolve'),
          ),
        ],
      ),
    );

    if (ok == true) {
      try {
        await AdminService.resolveSOS(id, note: noteCtrl.text.trim());
        await _fetchSOS();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed: $e')),
          );
        }
      }
    }
    noteCtrl.dispose();
  }

  Future<void> _openMap(double lat, double lng) async {
    final url =
        Uri.parse('https://www.google.com/maps/search/?api=1&query=$lat,$lng');
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Live SOS Alerts'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _fetchSOS,
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: _alerts.isEmpty
              ? const _EmptySOSState()
              : ListView.builder(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  itemCount: _alerts.length,
                  itemBuilder: (ctx, i) {
                    final item = _alerts[i];
                    final id = item['id'];
                    final empName = item['employee_name'] ?? 'Unknown';
                    final time = item['created_at'] ?? '';
                    final lat = (item['lat'] as num?)?.toDouble() ?? 0.0;
                    final lng = (item['lng'] as num?)?.toDouble() ?? 0.0;
                    final tripId = item['trip_id'];

                    return RGCard(
                      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 42,
                                height: 42,
                                decoration: BoxDecoration(
                                  color: AppThemeColors.error.withValues(
                                    alpha: 0.12,
                                  ),
                                  borderRadius:
                                      BorderRadius.circular(AppRadius.sm),
                                ),
                                child: const Icon(
                                  Icons.emergency_share_outlined,
                                  color: AppThemeColors.error,
                                ),
                              ),
                              const SizedBox(width: AppSpacing.sm),
                              Expanded(
                                child: Text(
                                  'Emergency: $empName',
                                  style: AppTypography.titleSmall.copyWith(
                                    color: AppThemeColors.error,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            'Time: $time | Trip: ${tripId ?? 'N/A'}',
                            style: AppTypography.bodySmall.copyWith(
                              color: AppThemeColors.textSecondary,
                            ),
                          ),
                          if (lat != 0 && lng != 0) ...[
                            const SizedBox(height: AppSpacing.sm),
                            TextButton.icon(
                              onPressed: () => _openMap(lat, lng),
                              icon: const Icon(Icons.map_outlined, size: 18),
                              label: const Text('Open Location in Maps'),
                            ),
                          ],
                          const SizedBox(height: AppSpacing.sm),
                          Align(
                            alignment: Alignment.centerRight,
                            child: ElevatedButton.icon(
                              onPressed: () =>
                                  _resolve(int.tryParse(id.toString()) ?? 0),
                              icon: const Icon(Icons.check_circle_outline),
                              label: const Text('Resolve'),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}

class _EmptySOSState extends StatelessWidget {
  const _EmptySOSState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: RGCard(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.check_circle_outline,
              size: 64,
              color: AppThemeColors.success,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'No Active SOS Alerts',
              style: AppTypography.titleMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
