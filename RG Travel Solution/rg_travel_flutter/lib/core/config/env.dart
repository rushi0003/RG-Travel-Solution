// flutter/lib/core/config/env.dart
//
// RG Travel Solution — Environment Config
//
// ✅ Purpose:
// - Single place to control DEV vs PROD values
// - Platform-wise host override (web/emulator)
// - Keys, feature flags, polling intervals
//
// NOTE:
// - Do NOT commit real API keys in public repos.
// - For production, use build-time secrets or server-side key protection.

import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;

enum AppEnv { dev, prod }

class Env {
  Env._();

  // =========================
  // ENV SWITCH
  // =========================

  /// Change this to AppEnv.prod when you build production.
  static const AppEnv current = AppEnv.dev;

  static bool get isDev => current == AppEnv.dev;
  static bool get isProd => current == AppEnv.prod;

  // =========================
  // BACKEND HOST SETTINGS
  // =========================

  /// Default backend port
  static const int backendPort = 5000;

  /// API prefix for backend
  static const String apiPrefix = '/api';

  /// Dev base URL overrides:
  /// Web cannot use 10.0.2.2, so use 127.0.0.1.
  static String get devBaseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:$backendPort';
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:$backendPort';
    }

    // iOS sim / Desktop
    return 'http://127.0.0.1:$backendPort';
  }

  /// Production base URL (update when you deploy)
  static const String prodBaseUrl = 'https://YOUR_PROD_DOMAIN.com';

  /// Final resolved base URL
  static String get baseUrl => isDev ? devBaseUrl : prodBaseUrl;

  /// API base URL = baseUrl + /api
  static String get apiBase => '$baseUrl$apiPrefix';

  // =========================
  // GOOGLE MAPS (Frontend use)
  // =========================
  //
  // ⚠️ Usually you should NOT expose full-power server keys in frontend.
  // Best practice:
  // - Restrict key to specific domains/apps in Google Cloud Console
  // - For Directions/Distance Matrix calls: prefer calling your backend only.
  //
  // Keep this optional (null) if not needed on Flutter side.
  // Pass with:
  // flutter run -d chrome --dart-define=GOOGLE_MAPS_API_KEY=YOUR_KEY
  static const String googleMapsApiKey = String.fromEnvironment(
    'GOOGLE_MAPS_API_KEY',
  );

  static bool get hasGoogleMapsKey => googleMapsApiKey.trim().isNotEmpty;

  // =========================
  // FEATURE FLAGS
  // =========================

  /// Enable or disable live tracking UI
  static const bool enableLiveTracking = true;

  /// Enable OTP flow
  static const bool enableOtp = true;

  /// Enable auto grouping feature
  static const bool enableAutoGrouping = true;

  /// Enable emergency swap request feature
  static const bool enableEmergencySwap = true;

  /// Enable NLP-like search (frontend only)
  static const bool enableSmartSearch = true;

  // =========================
  // POLLING / TIMERS
  // =========================

  /// Driver sends GPS update to backend every X seconds
  static const int driverGpsPushSeconds = 5;

  /// Admin/Employee fetch tracking update every X seconds
  static const int trackingPollSeconds = 5;

  /// Live trips polling interval
  static const int liveTripsPollSeconds = 10;

  /// Online drivers polling interval
  static const int onlineDriversPollSeconds = 8;

  /// Network timeout
  static const int httpTimeoutSeconds = 15;

  // =========================
  // DEBUG SETTINGS
  // =========================

  /// Print API config logs in console
  static const bool logApi = true;

  /// Print payloads (careful: may include PII)
  static const bool logPayloads = false;

  // =========================
  // HELPERS
  // =========================

  /// Returns a full URL for a path.
  /// If path starts with "/api" => attaches baseUrl
  /// else attaches apiBase + path
  static String makeUrl(String path) {
    final p = path.trim();
    if (p.startsWith('http://') || p.startsWith('https://')) return p;

    if (p.startsWith(apiPrefix)) {
      return '$baseUrl$p';
    }

    final normalized = p.startsWith('/') ? p : '/$p';
    return '$apiBase$normalized';
  }

  static String debugSummary() {
    return 'Env(current=$current, baseUrl=$baseUrl, apiBase=$apiBase)';
  }
}
