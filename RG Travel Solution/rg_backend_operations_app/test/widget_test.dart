import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:rg_backend_operations_app/app.dart';

void main() {
  testWidgets('shows ops login when no session is saved', (tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const RGBackendOperationsApp());
    await tester.pumpAndSettle();

    expect(find.text('RG Backend Operations Login'), findsOneWidget);
    expect(find.text('Sign In'), findsOneWidget);
    expect(find.text('Enter Ops Console'), findsOneWidget);
  });
}
