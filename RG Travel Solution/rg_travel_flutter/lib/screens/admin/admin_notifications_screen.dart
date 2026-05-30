import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/storage/session_store.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/services/admin_service.dart';

class AdminNotificationsScreen extends StatefulWidget {
  const AdminNotificationsScreen({super.key});

  @override
  State<AdminNotificationsScreen> createState() =>
      _AdminNotificationsScreenState();
}

class _AdminNotificationsScreenState extends State<AdminNotificationsScreen> {
  bool _isLoading = false;
  List<Map<String, dynamic>> _notifications = [];
  int _unreadCount = 0;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() => _isLoading = true);
    try {
      final adminId = await SessionStore.getUserId();
      if (adminId == null) return;

      final res = await AdminService.getNotifications(adminId: adminId);
      final rawList = (res['notifications'] ?? res['notification']) as List?;
      final list =
          rawList?.map((e) => e as Map<String, dynamic>).toList() ?? [];
      final count = res['unread_count'] as int? ?? 0;

      if (mounted) {
        setState(() {
          _notifications = list;
          _unreadCount = count;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading notifications: $e')),
        );
      }
    }
  }

  Future<void> _markRead(dynamic id) async {
    final nid = int.tryParse(id?.toString() ?? '') ?? 0;
    if (nid == 0) return;
    try {
      final adminId = await SessionStore.getUserId();
      if (adminId == null) return;
      await AdminService.markNotificationRead(nid, adminId);
      setState(() {
        final index = _notifications
            .indexWhere((n) => (n['id']?.toString() ?? '') == nid.toString());
        if (index != -1) {
          _notifications[index]['is_read'] = true;
          if (_unreadCount > 0) _unreadCount--;
        }
      });
    } catch (e) {
      // ignore error
    }
  }

  Future<void> _markAllRead() async {
    try {
      final adminId = await SessionStore.getUserId();
      if (adminId == null) return;
      await AdminService.markAllNotificationsRead(adminId);
      setState(() {
        for (var n in _notifications) {
          n['is_read'] = true;
        }
        _unreadCount = 0;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('All marked as read')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (_notifications.isNotEmpty)
            TextButton(
              onPressed: _markAllRead,
              child: const Text('Mark all read'),
            )
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _loadNotifications,
                child: _notifications.isEmpty
                    ? _buildEmptyState()
                    : ListView.builder(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        itemCount: _notifications.length,
                        itemBuilder: (context, index) {
                          final n = _notifications[index];
                          return _buildNotificationCard(n);
                        },
                      ),
              ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.notifications_off_outlined,
            size: 64,
            color: AppThemeColors.textTertiary,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No notifications',
            style: AppTypography.bodyLarge.copyWith(
              color: AppThemeColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNotificationCard(Map<String, dynamic> n) {
    final isRead = n['is_read'] == true;
    final type = n['type'] ?? 'info';

    Color iconColor;
    IconData iconData;

    switch (type) {
      case 'warning':
        iconColor = AppThemeColors.warning;
        iconData = Icons.warning_amber_rounded;
        break;
      case 'error':
        iconColor = AppThemeColors.error;
        iconData = Icons.error_outline;
        break;
      case 'success':
        iconColor = AppThemeColors.success;
        iconData = Icons.check_circle_outline;
        break;
      case 'info':
      default:
        iconColor = AppThemeColors.primary;
        iconData = Icons.info_outline;
        break;
    }

    return Card(
      color: isRead ? AppThemeColors.surface : AppThemeColors.surfaceLight,
      elevation: 0,
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: BorderSide(
          // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
          color: isRead
              ? AppThemeColors.border.withValues(alpha: 0)
              : AppThemeColors.primary.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: InkWell(
        onTap: () {
          if (!isRead) _markRead(n['id']);
        },
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
                  color: iconColor.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(iconData, size: 20, color: iconColor),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            (n['title'] ?? 'No Title').toString(),
                            style: AppTypography.bodyLarge.copyWith(
                              fontWeight:
                                  isRead ? FontWeight.normal : FontWeight.bold,
                            ),
                          ),
                        ),
                        if (!isRead)
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: AppThemeColors.primary,
                              shape: BoxShape.circle,
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      (n['message'] ?? '').toString(),
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      (n['created_at'] ?? '').toString(),
                      style: AppTypography.bodySmall.copyWith(
                        color: AppThemeColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
