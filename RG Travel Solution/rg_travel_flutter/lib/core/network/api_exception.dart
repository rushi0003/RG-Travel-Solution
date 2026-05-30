// flutter/lib/core/network/api_exception.dart
//
// RG Travel Solution — API Exception
//
// ✅ Purpose:
// - Standard error model for all API calls
// - Carry statusCode, endpoint, raw payload details
// - Provide user-friendly messages for UI
//
// NOTE:
// - Endpoints constants are in ApiConfig (not here).
// - This file only represents errors (not routes).

class ApiException implements Exception {
  const ApiException(
    this.message, {
    this.statusCode,
    this.endpoint,
    this.details,
    this.type = ApiErrorType.unknown,
  });

  /// Human readable message (safe for UI)
  final String message;

  /// Optional HTTP status code (e.g., 400, 401, 500)
  final int? statusCode;

  /// Optional endpoint/path for debugging (e.g., /api/admin/trips/live)
  final String? endpoint;

  /// Optional raw response payload (decoded JSON or string)
  final dynamic details;

  /// Optional error type marker
  final ApiErrorType type;

  // =========================
  // FACTORY HELPERS
  // =========================

  /// Network/connection issue (server not reachable / CORS / offline)
  factory ApiException.network(
    String message, {
    String? endpoint,
    dynamic details,
  }) {
    return ApiException(
      message,
      endpoint: endpoint,
      details: details,
      type: ApiErrorType.network,
    );
  }

  /// Timeout issue
  factory ApiException.timeout({
    String? endpoint,
  }) {
    return const ApiException(
      'Request timeout. Please check server and internet.',
      type: ApiErrorType.timeout,
    ).copyWith(endpoint: endpoint);
  }

  /// Auth issue
  factory ApiException.unauthorized({
    String? endpoint,
    dynamic details,
  }) {
    return ApiException(
      'Unauthorized. Please login again.',
      statusCode: 401,
      endpoint: endpoint,
      details: details,
      type: ApiErrorType.unauthorized,
    );
  }

  /// Validation error (400/422)
  factory ApiException.validation(
    String message, {
    int? statusCode,
    String? endpoint,
    dynamic details,
  }) {
    return ApiException(
      message,
      statusCode: statusCode ?? 400,
      endpoint: endpoint,
      details: details,
      type: ApiErrorType.validation,
    );
  }

  /// Server error (5xx)
  factory ApiException.server(
    String message, {
    int? statusCode,
    String? endpoint,
    dynamic details,
  }) {
    return ApiException(
      message,
      statusCode: statusCode ?? 500,
      endpoint: endpoint,
      details: details,
      type: ApiErrorType.server,
    );
  }

  // =========================
  // UI HELPERS
  // =========================

  /// Friendly hint for the most common Flutter Web error: "Failed to fetch"
  bool get isFailedToFetchHint {
    final m = message.toLowerCase();
    return m.contains('failed to fetch') ||
        m.contains('xmlhttprequest') ||
        m.contains('cors');
  }

  /// A message you can directly show in SnackBar/Toast
  String get uiMessage {
    if (isFailedToFetchHint) {
      return 'Failed to fetch. Check: 1) Backend running, '
          '2) Correct baseUrl (Web=127.0.0.1, Emulator=10.0.2.2), '
          '3) CORS enabled in Flask.';
    }
    return message;
  }

  /// Useful for logs (includes status + endpoint)
  String get debugString {
    final sc = statusCode != null ? 'status=$statusCode' : 'status=?';
    final ep = endpoint != null ? ' endpoint=$endpoint' : '';
    return 'ApiException($sc$ep, type=$type, message=$message, details=$details)';
  }

  // =========================
  // COPY WITH
  // =========================

  ApiException copyWith({
    String? message,
    int? statusCode,
    String? endpoint,
    dynamic details,
    ApiErrorType? type,
  }) {
    return ApiException(
      message ?? this.message,
      statusCode: statusCode ?? this.statusCode,
      endpoint: endpoint ?? this.endpoint,
      details: details ?? this.details,
      type: type ?? this.type,
    );
  }

  @override
  String toString() => uiMessage;
}

/// Error categories for quick handling in UI/logic
enum ApiErrorType {
  network,
  timeout,
  unauthorized,
  validation,
  server,
  unknown,
}
