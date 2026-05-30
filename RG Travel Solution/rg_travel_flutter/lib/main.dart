// flutter/lib/main.dart
//
// RG Travel Solution — Entry point
//
// ✅ Responsibilities:
// ✅ Responsibilities:
// - Ensure Flutter binding initialized
// - Decide initial screen based on saved session (role/userId)
// - Launch App widget (app.dart)
//
// This file should stay small & stable.

import 'package:flutter/material.dart';

import 'app.dart';
import 'core/config/env.dart';
import 'core/storage/session_store.dart';

// Export a minimal test widget so widget tests that import `main.dart` can
// access `MyApp` without tightly coupling to the full app shell.
export 'widget.dart';

void main() async {
  final binding = WidgetsFlutterBinding.ensureInitialized();

  // ✅ SAFE LIFECYCLE HANDLING (Flutter Web Fix)
  // Instead of force unwrapping (binding.lifecycleState!), check for null
  final state = binding.lifecycleState;
  if (state != null) {
      debugPrint("App Lifecycle State: $state");
  }

  // Optional debug log (helps fix Failed to fetch / wrong baseUrl)
  if (Env.logApi) {
    // ignore: avoid_print
    print(Env.debugSummary());
  }

  // Determine initial route based on saved session
  final initialRoute = await _resolveInitialRoute();

  runApp(RGTravelApp(initialRoute: initialRoute));
}

Future<String> _resolveInitialRoute() async {
  final loggedIn = await SessionStore.isLoggedIn();
  if (!loggedIn) return "/login";

  final role = await SessionStore.getRole();
  final userId = await SessionStore.getUserId();

  // If something missing -> back to login
  if (role == null || userId == null) return "/login";

  switch (role) {
    case UserRole.admin:
      return "/admin/dashboard";
    case UserRole.driver:
      return "/driver/dashboard";
    case UserRole.employee:
      return "/employee/dashboard";
  }
}
