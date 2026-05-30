import 'package:flutter/material.dart';

import 'screens/backend_operations_dashboard.dart';
import 'screens/ops_login_screen.dart';
import 'services/admin_service.dart';
import 'services/ops_session_store.dart';
import 'theme/ops_theme.dart';

class RGBackendOperationsApp extends StatelessWidget {
  const RGBackendOperationsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'RG Backend Operations',
      theme: OpsTheme.dark(),
      home: const _OpsBootstrap(),
    );
  }
}

class _OpsBootstrap extends StatefulWidget {
  const _OpsBootstrap();

  @override
  State<_OpsBootstrap> createState() => _OpsBootstrapState();
}

class _OpsBootstrapState extends State<_OpsBootstrap> {
  late final Future<bool> _bootstrapFuture = _bootstrap();

  Future<bool> _bootstrap() async {
    final savedBaseUrl = await OpsSessionStore.getBaseUrl();
    if (savedBaseUrl != null && savedBaseUrl.trim().isNotEmpty) {
      AdminService.setBaseUrl(savedBaseUrl);
    }
    return OpsSessionStore.isLoggedIn();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _bootstrapFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (snapshot.data == true) {
          return const BackendOperationsDashboard();
        }
        return const OpsLoginScreen();
      },
    );
  }
}
