// flutter/lib/app.dart
//
// RG Travel Solution â€” App Shell
//
// âœ… Responsibilities:
// - MaterialApp config (theme, routes, navigation)
// - Initial route comes from main.dart
// - Central routing for Admin/Driver/Employee modules
//
// NOTE:
// - Endpoints are in ApiConfig (core/config/api_config.dart)
// - This file handles UI routing, not backend routing.

import 'package:flutter/material.dart';

import 'core/config/env.dart';
import 'core/storage/session_store.dart';
import 'core/theme/app_theme.dart';
import 'core/utils/constants.dart';

import 'screens/admin/admin_dashboard.dart';
import 'screens/admin/admin_helpdesk_screen.dart';
import 'screens/admin/admin_notifications_screen.dart';
import 'screens/admin/admin_sos_screen.dart';
import 'screens/admin/create_group_assign_screen.dart';
import 'screens/admin/drivers_screen.dart';
import 'screens/admin/employees_screen.dart';
import 'screens/admin/live_trips_screen.dart';
import 'screens/admin/live_tracking_screen.dart';
import 'screens/admin/trip_history_screen.dart';
import 'screens/driver/assigned_trip_screen.dart';
import 'screens/driver/driver_dashboard.dart';
import 'screens/driver/driver_profile_screen.dart';
import 'screens/driver/otp_screen.dart';
import 'screens/employee/employee_dashboard.dart';
import 'screens/employee/driver_tracking_screen.dart';
import 'screens/employee/my_trip_screen.dart';
import 'screens/login/login_screen.dart';

class RGTravelApp extends StatelessWidget {
  const RGTravelApp({
    super.key,
    required this.initialRoute,
  });

  final String initialRoute;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: AppNavigator.navigatorKey,
      debugShowCheckedModeBanner: false,
      title: AppInfo.appName,
      theme: AppThemeBuilder.buildDarkTheme(),
      initialRoute: initialRoute,
      onGenerateRoute: _onGenerateRoute,
      onUnknownRoute: (settings) {
        return MaterialPageRoute(
          builder: (_) => _UnknownRouteScreen(routeName: settings.name),
        );
      },
    );
  }

  Route<dynamic>? _onGenerateRoute(RouteSettings settings) {
    final args = (settings.arguments is Map) ? settings.arguments as Map : <dynamic, dynamic>{};

    WidgetBuilder? builder;

    switch (settings.name) {
      // Login (no args expected)
      case AppRoutes.login:
        builder = (_) => const _AppBg(child: LoginScreen());
        break;

      // Admin routes (require adminId)
      case AppRoutes.adminDashboard:
        final rawAdminId = args['adminId'];
        builder = (_) => _AppBg(
              child: _AdminRouteResolver(
                explicitAdminId: rawAdminId?.toString(),
                childBuilder: (adminId) => AdminDashboard(adminId: adminId),
              ),
            );
        break;
      case AppRoutes.adminCreateGroup:
        final rawAdminId = args['adminId'];
        builder = (_) => _AppBg(
              child: _AdminRouteResolver(
                explicitAdminId: rawAdminId?.toString(),
                childBuilder: (adminId) =>
                    CreateGroupAssignScreen(adminId: adminId),
              ),
            );
        break;
      case AppRoutes.adminLiveTrips:
        builder = (_) => _AppBg(
              child: _AdminRouteResolver(
                explicitAdminId: args['adminId']?.toString(),
                childBuilder: (adminId) => LiveTripsScreen(adminId: adminId),
              ),
            );
        break;
      case AppRoutes.adminDrivers:
        builder = (_) => const _AppBg(child: DriversScreen());
        break;
      case AppRoutes.adminEmployees:
        builder = (_) => _AppBg(
              child: _AdminRouteResolver(
                explicitAdminId: args['adminId']?.toString(),
                childBuilder: (adminId) => EmployeesScreen(adminId: adminId),
              ),
            );
        break;
      case AppRoutes.adminTripHistory:
        builder = (_) => _AppBg(
              child: _AdminRouteResolver(
                explicitAdminId: args['adminId']?.toString(),
                childBuilder: (adminId) => TripHistoryScreen(adminId: adminId),
              ),
            );
        break;
      case AppRoutes.adminLiveTracking:
        final initialQuery = (args['q'] ?? '').toString();
        builder = (_) => _AppBg(
              child: _AdminRouteResolver(
                explicitAdminId: args['adminId']?.toString(),
                childBuilder: (adminId) => LiveTrackingScreen(
                  adminId: adminId,
                  initialQuery: initialQuery,
                ),
              ),
            );
        break;
      case AppRoutes.adminSos:
        builder = (_) => const _AppBg(child: AdminSOSScreen());
        break;
      case AppRoutes.adminHelpdesk:
        builder = (_) => const _AppBg(child: AdminHelpDeskScreen());
        break;
      case AppRoutes.adminNotifications:
        builder = (_) => const _AppBg(child: AdminNotificationsScreen());
        break;

      // Driver routes
      case AppRoutes.driverDashboard:
        final rawDriverId = args['driverId'];
        final driverId = (rawDriverId ?? '').toString();
        builder = (_) => _AppBg(child: DriverDashboard(driverId: driverId));
        break;
      case AppRoutes.driverProfile:
        final rawDriverId = args['driverId'];
        final driverId = (rawDriverId ?? '').toString();
        builder = (_) => _AppBg(child: DriverProfileScreen(driverId: driverId));
        break;
      case AppRoutes.driverAssignedTrip:
        final rawDriverId = args['driverId'];
        final driverId = (rawDriverId ?? '').toString();
        builder = (_) => _AppBg(child: AssignedTripScreen(driverId: driverId));
        break;
      case AppRoutes.driverOtp:
        final rawDriverId = args['driverId'];
        final driverId = (rawDriverId ?? '').toString();
        final rawTripId = args['tripId'];
        final tripId = (rawTripId is int)
            ? rawTripId
            : int.tryParse((rawTripId ?? '').toString()) ?? 0;
        final otpType = (args['otpType'] ?? '').toString();
        final tripType = (args['tripType'] ?? '').toString();
        builder = (_) => _AppBg(child: OtpScreen(driverId: driverId, tripId: tripId, otpType: otpType, tripType: tripType));
        break;

      // Employee routes
      case AppRoutes.employeeDashboard:
        final rawEmployeeId = args['employeeId'];
        final employeeId = (rawEmployeeId ?? '').toString();
        builder = (_) => _AppBg(child: EmployeeDashboard(employeeId: employeeId));
        break;
      case AppRoutes.employeeMyTrip:
        final rawEmployeeId = args['employeeId'];
        final employeeId = (rawEmployeeId ?? '').toString();
        builder = (_) => _AppBg(child: MyTripScreen(employeeId: employeeId));
        break;
      case AppRoutes.employeeTrackingView:
        final routeNo = (args['routeNo'] ?? '').toString();
        final employeeId = (args['employeeId'] ?? '').toString();
        builder = (_) => _AppBg(
              child: DriverTrackingScreen(
                routeNo: routeNo,
                employeeId: employeeId,
              ),
            );
        break;

      default:
        // Return null so that onUnknownRoute is used by MaterialApp
        return null;
    }

    return MaterialPageRoute(builder: builder, settings: settings);
  }
}

class _AdminRouteResolver extends StatelessWidget {
  const _AdminRouteResolver({
    required this.explicitAdminId,
    required this.childBuilder,
  });

  final String? explicitAdminId;
  final Widget Function(String adminId) childBuilder;

  @override
  Widget build(BuildContext context) {
    final direct = (explicitAdminId ?? '').trim();
    if (direct.isNotEmpty) {
      return childBuilder(direct);
    }

    return FutureBuilder<String?>(
      future: SessionStore.getUserId(),
      builder: (context, snapshot) {
        final sessionAdminId = (snapshot.data ?? '').trim();
        if (sessionAdminId.isEmpty) {
          return const Scaffold(
            body: Center(
              child: Text('Missing admin session'),
            ),
          );
        }
        return childBuilder(sessionAdminId);
      },
    );
  }
}

/// Common background wrapper
/// Uses gradient background from the design system for all screens.
class _AppBg extends StatelessWidget {
  const _AppBg({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: AppGradients.backgroundGradient,
      ),
      child: child,
    );
  }
}

class AppNavigator {
  AppNavigator._();
  static final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
}

/// Unknown route screen (prevents crash)
class _UnknownRouteScreen extends StatelessWidget {
  const _UnknownRouteScreen({this.routeName});

  final String? routeName;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(title: const Text('Route Not Found')),
      body: Padding(
        padding: AppSpacing.pagePadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Unknown route: ${routeName ?? 'null'}',
              style: AppTypography.bodyLarge.copyWith(
                color: AppThemeColors.textPrimary,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Env: ${Env.debugSummary()}',
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
            const SizedBox(height: 18),
            ElevatedButton(
              onPressed: () => Navigator.pushNamedAndRemoveUntil(
                context,
                AppRoutes.login,
                (_) => false,
              ),
              child: const Text('Go to Login'),
            ),
          ],
        ),
      ),
    );
  }
}
