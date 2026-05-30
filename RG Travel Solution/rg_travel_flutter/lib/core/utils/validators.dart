// flutter/lib/core/utils/validators.dart
//
// RG Travel Solution — Validators
//
// ✅ Contains:
// - Mobile (10 digits)
// - OTP (6 digits)
// - Driver License (2 letters + 13 digits)
// - Vehicle Number (Indian formats)
// - Route Number (10 chars: first 4 = year+date, next 4 digits, last 2 month letters)
// - Time format HH:mm
// - Basic name/address/email helpers
//
// NOTE:
// - Endpoints are NOT in validators. They belong to ApiConfig.

class Validators {
  Validators._();

  // =========================
  // BASIC NORMALIZATION
  // =========================

  static String normalize(String? s) {
    if (s == null) return "";
    return s.trim().replaceAll(RegExp(r"\s+"), " ");
  }

  static bool isNotEmpty(String? s) => normalize(s).isNotEmpty;

  // =========================
  // MOBILE (India) - 10 digits
  // =========================

  static bool isMobile10(String? mobile) {
    final m = normalize(mobile).replaceAll(RegExp(r"\s+"), "");
    return RegExp(r"^\d{10}$").hasMatch(m);
  }

  static String? validateMobile10(String? mobile, {String fieldName = "Mobile"}) {
    if (!isNotEmpty(mobile)) return "$fieldName is required.";
    if (!isMobile10(mobile)) return "$fieldName must be exactly 10 digits.";
    return null;
  }

  // =========================
  // OTP - 6 digits
  // =========================

  static bool isOtp6(String? otp) {
    final o = normalize(otp);
    return RegExp(r"^\d{6}$").hasMatch(o);
  }

  static String? validateOtp6(String? otp, {String fieldName = "OTP"}) {
    if (!isNotEmpty(otp)) return "$fieldName is required.";
    if (!isOtp6(otp)) return "$fieldName must be exactly 6 digits.";
    return null;
  }

  // =========================
  // DRIVER LICENSE
  // Rule: 2 letters + 13 digits (as you asked)
  // Example: MH1234567890123
  // =========================

  static bool isDriverLicense(String? dl) {
    final v = normalize(dl).toUpperCase().replaceAll(" ", "");
    return RegExp(r"^[A-Z]{2}\d{13}$").hasMatch(v);
  }

  static String? validateDriverLicense(String? dl, {String fieldName = "DL No"}) {
    if (!isNotEmpty(dl)) return "$fieldName is required.";
    if (!isDriverLicense(dl)) {
      return "$fieldName format: 2 letters + 13 digits (e.g., MH1234567890123).";
    }
    return null;
  }

  // =========================
  // VEHICLE NUMBER (Indian)
  // Accept common formats:
  // - MH12AB1234
  // - MH 12 AB 1234
  // - MH12A1234 (older)
  // - MH12AB123 (short last)
  //
  // NOTE: India has many variants; this covers practical cases.
  // =========================

  static String normalizeVehicleNo(String? v) {
    return normalize(v).toUpperCase().replaceAll(RegExp(r"[^A-Z0-9]"), "");
  }

  static bool isVehicleNo(String? vehicleNo) {
    final v = normalizeVehicleNo(vehicleNo);

    // Common: XX00XX0000 (2 letters, 2 digits, 1-2 letters, 1-4 digits)
    final reg1 = RegExp(r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{1,4}$");

    // Some plates have 3 digits RTO code: XX000XX0000 (rare)
    final reg2 = RegExp(r"^[A-Z]{2}\d{3}[A-Z]{1,2}\d{1,4}$");

    return reg1.hasMatch(v) || reg2.hasMatch(v);
  }

  static String? validateVehicleNo(String? vehicleNo, {String fieldName = "Vehicle No"}) {
    if (!isNotEmpty(vehicleNo)) return "$fieldName is required.";
    if (!isVehicleNo(vehicleNo)) {
      return "$fieldName invalid. Example: MH12AB1234";
    }
    return null;
  }

  // =========================
  // EMPLOYEE CODE (permanent)
  // You can change rule as needed:
  // - min 4 chars, max 20, letters+digits+_-
  // =========================

  static bool isEmployeeCode(String? code) {
    final c = normalize(code);
    return RegExp(r"^[A-Za-z0-9_-]{4,20}$").hasMatch(c);
  }

  static String? validateEmployeeCode(String? code, {String fieldName = "Employee Code"}) {
    if (!isNotEmpty(code)) return "$fieldName is required.";
    if (!isEmployeeCode(code)) {
      return "$fieldName must be 4–20 chars (letters/digits/_/-).";
    }
    return null;
  }

  // =========================
  // TIME (HH:mm)
  // =========================

  static bool isTimeHHmm(String? t) {
    final v = normalize(t);
    // 00:00 to 23:59
    return RegExp(r"^([01]\d|2[0-3]):[0-5]\d$").hasMatch(v);
  }

  static String? validateTimeHHmm(String? t, {String fieldName = "Time"}) {
    if (!isNotEmpty(t)) return "$fieldName is required.";
    if (!isTimeHHmm(t)) return "$fieldName must be HH:mm (e.g., 09:30).";
    return null;
  }

  // =========================
  // NAME (basic)
  // =========================

  static bool isPersonName(String? name) {
    final n = normalize(name);
    if (n.length < 2) return false;
    // letters, spaces, dot allowed
    return RegExp(r"^[A-Za-z][A-Za-z .']{1,49}$").hasMatch(n);
  }

  static String? validateName(String? name, {String fieldName = "Name"}) {
    if (!isNotEmpty(name)) return "$fieldName is required.";
    if (!isPersonName(name)) return "$fieldName is invalid.";
    return null;
  }

  // =========================
  // EMAIL (optional)
  // =========================

  static bool isEmail(String? email) {
    final e = normalize(email);
    if (e.isEmpty) return false;
    return RegExp(r"^[^\s@]+@[^\s@]+\.[^\s@]+$").hasMatch(e);
  }

  static String? validateEmailOptional(String? email, {String fieldName = "Email"}) {
    if (!isNotEmpty(email)) return null; // optional
    if (!isEmail(email)) return "$fieldName is invalid.";
    return null;
  }

  // =========================
  // ROUTE NUMBER (your logic)
  //
  // 10 characters:
  // - first 4: year+date (you said "date and year (first 4 character)")
  //   We interpret: YY + DD (e.g., 26 + 01 for Feb 1? depends on your choice)
  // - next 4: random digits
  // - last 2: first two letters of month (JAN=JA, FEB=FE, MAR=MA, APR=AP, MAY=MY, JUN=JU, JUL=JL, AUG=AU, SEP=SE, OCT=OC, NOV=NO, DEC=DE)
  //
  // Example: "2601 4821 FE" => "26014821FE"
  //
  // Validation:
  // - Exactly 10 chars
  // - First 4 numeric
  // - Next 4 numeric
  // - Last 2 letters A-Z
  // =========================

  static bool isRouteNo(String? routeNo) {
    final r = normalize(routeNo).toUpperCase().replaceAll(" ", "");
    return RegExp(r"^\d{8}[A-Z]{2}$").hasMatch(r);
  }

  static String? validateRouteNo(String? routeNo, {String fieldName = "Route No"}) {
    if (!isNotEmpty(routeNo)) return "$fieldName is required.";
    if (!isRouteNo(routeNo)) {
      return "$fieldName invalid. Format: 8 digits + 2 month letters (e.g., 26014821FE).";
    }
    return null;
  }

  // =========================
  // PASSWORD (optional basic)
  // =========================

  static bool isPasswordStrongEnough(String? p, {int minLen = 4}) {
    final v = normalize(p);
    return v.length >= minLen;
  }

  static String? validatePassword(String? p, {String fieldName = "Password", int minLen = 4}) {
    if (!isNotEmpty(p)) return "$fieldName is required.";
    if (!isPasswordStrongEnough(p, minLen: minLen)) {
      return "$fieldName must be at least $minLen characters.";
    }
    return null;
  }

  // =========================
  // ADDRESS (basic)
  // =========================

  static String? validateAddress(String? a, {String fieldName = "Address"}) {
    if (!isNotEmpty(a)) return "$fieldName is required.";
    final v = normalize(a);
    if (v.length < 5) return "$fieldName is too short.";
    return null;
  }
}
