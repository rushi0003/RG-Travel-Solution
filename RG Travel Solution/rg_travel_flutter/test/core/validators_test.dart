// test/core/validators_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:rg_travel_flutter/core/utils/validators.dart';

void main() {
  group('Validators', () {
    test('Mobile 10 digits', () {
      expect(Validators.isMobile10('9999999999'), true);
      expect(Validators.isMobile10('99999'), false);
      expect(Validators.validateMobile10(''), isNotNull);
      expect(Validators.validateMobile10('1234567890'), isNull);
    });

    test('OTP 6 digits', () {
      expect(Validators.isOtp6('123456'), true);
      expect(Validators.isOtp6('12345'), false);
    });

    test('Driver License: 2 letters + 13 digits', () {
      expect(Validators.isDriverLicense('MH1234567890123'), true);
      expect(Validators.isDriverLicense('M1234567890123'), false);
    });

    test('Vehicle number common formats', () {
      expect(Validators.isVehicleNo('MH12AB1234'), true);
      expect(Validators.isVehicleNo('mh 12 ab 1234'), true);
      expect(Validators.isVehicleNo('MH12A1234'), true);
      expect(Validators.isVehicleNo('INVALID'), false);
    });

    test('Route No: 10 chars (8 digits + 2 letters)', () {
      expect(Validators.isRouteNo('26014821FE'), true);
      expect(Validators.isRouteNo('26014821F'), false);
      expect(Validators.isRouteNo('26014821FEB'), false);
      expect(Validators.isRouteNo('ABCD4821FE'), false);
    });

    test('Time HH:mm', () {
      expect(Validators.isTimeHHmm('09:30'), true);
      expect(Validators.isTimeHHmm('23:59'), true);
      expect(Validators.isTimeHHmm('24:00'), false);
      expect(Validators.isTimeHHmm('9:30'), false);
    });
  });
}
