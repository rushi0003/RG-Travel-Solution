// lib/utils/validators.dart
//
// RG Travel Solution — Validation Utilities
//
// Centralized validation functions for all form fields
// Returns null if valid, error message string if invalid

class Validators {
  Validators._();

  /// Validates mobile number - exactly 10 digits
  static String? validateMobile(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Mobile number is required';
    }
    final cleaned = value.trim();
    if (!RegExp(r'^\d{10}$').hasMatch(cleaned)) {
      return 'Mobile must be exactly 10 digits';
    }
    return null;
  }

  /// Validates DL Number - 2 letters + 13 digits
  /// Example: MH1234567890123
  static String? validateDLNo(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'DL Number is required';
    }
    final cleaned = value.trim().toUpperCase();
    if (!RegExp(r'^[A-Z]{2}\d{13}$').hasMatch(cleaned)) {
      return 'DL must be 2 letters + 13 digits (e.g., MH1234567890123)';
    }
    return null;
  }

  /// Validates Cab/Vehicle Number - plate format
  /// Regex: ^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$
  /// Example: MH12AB1234
  static String? validateCabNo(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Cab number is required';
    }
    final cleaned = value.trim().toUpperCase().replaceAll(' ', '');
    if (!RegExp(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$').hasMatch(cleaned)) {
      return 'Cab number must be like MH12AB1234';
    }
    return null;
  }

  /// Validates password with configurable minimum length
  static String? validatePassword(String? value, {int minLength = 4}) {
    if (value == null || value.isEmpty) {
      return 'Password is required';
    }
    if (value.length < minLength) {
      return 'Password must be at least $minLength characters';
    }
    return null;
  }

  /// Validates name with configurable minimum length
  static String? validateName(String? value, {int minLength = 2}) {
    if (value == null || value.trim().isEmpty) {
      return 'Name is required';
    }
    if (value.trim().length < minLength) {
      return 'Name must be at least $minLength characters';
    }
    return null;
  }

  /// Validates employee ID - minimum 3 characters
  static String? validateEmployeeId(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Employee ID is required';
    }
    if (value.trim().length < 3) {
      return 'Employee ID must be at least 3 characters';
    }
    return null;
  }

  /// Validates address - minimum 5 characters
  static String? validateAddress(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Address is required';
    }
    if (value.trim().length < 5) {
      return 'Address must be at least 5 characters';
    }
    return null;
  }

  /// Validates time in HH:mm format
  static String? validateTime(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Time is required';
    }
    final cleaned = value.trim();
    // Simple HH:mm format check
    if (!RegExp(r'^\d{1,2}:\d{2}$').hasMatch(cleaned)) {
      return 'Time must be in HH:mm format';
    }
    
    // Parse and validate ranges
    final parts = cleaned.split(':');
    if (parts.length != 2) return 'Invalid time format';
    
    final hour = int.tryParse(parts[0]);
    final minute = int.tryParse(parts[1]);
    
    if (hour == null || minute == null) return 'Invalid time values';
    if (hour < 0 || hour > 23) return 'Hour must be between 0 and 23';
    if (minute < 0 || minute > 59) return 'Minute must be between 0 and 59';
    
    return null;
  }

  /// Normalizes cab number (uppercase, removes spaces)
  static String normalizeCabNo(String value) {
    return value.trim().toUpperCase().replaceAll(' ', '');
  }

  /// Normalizes DL number (uppercase)
  static String normalizeDLNo(String value) {
    return value.trim().toUpperCase();
  }

  /// Formats time from TimeOfDay to HH:mm string
  static String formatTime(int hour, int minute) {
    return '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';
  }
}
