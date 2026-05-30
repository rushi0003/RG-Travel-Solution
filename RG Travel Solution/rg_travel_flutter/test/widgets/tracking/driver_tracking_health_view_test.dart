import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rg_travel_flutter/widgets/tracking/driver_tracking_health_view.dart';

void main() {
  Widget wrap(Widget child) {
    return MaterialApp(
      home: Scaffold(body: child),
    );
  }

  testWidgets('shows waiting message when online and no sync yet',
      (tester) async {
    await tester.pumpWidget(
      wrap(
        const DriverTrackingHealthView(
          isOnline: true,
          socketConnected: true,
          trackingHealthError: false,
          onRetryNow: _noop,
        ),
      ),
    );

    expect(find.text('Waiting for first location sync...'), findsOneWidget);
    expect(find.text('Retry now'), findsOneWidget);
  });

  testWidgets('shows server code and triggers retry callback', (tester) async {
    var tapped = 0;

    await tester.pumpWidget(
      wrap(
        DriverTrackingHealthView(
          isOnline: true,
          socketConnected: true,
          trackingHealthError: true,
          trackingHealthMessage: 'Upload failed with HTTP 429',
          lastUploadServerCode: 429,
          onRetryNow: () {
            tapped += 1;
          },
        ),
      ),
    );

    expect(find.text('Upload failed with HTTP 429'), findsOneWidget);
    expect(find.text('HTTP 429'), findsOneWidget);

    await tester.tap(find.text('Retry now'));
    await tester.pump();
    expect(tapped, 1);
  });

  testWidgets('returns empty widget when offline', (tester) async {
    await tester.pumpWidget(
      wrap(
        const DriverTrackingHealthView(
          isOnline: false,
          socketConnected: false,
          trackingHealthError: false,
          onRetryNow: _noop,
        ),
      ),
    );

    expect(find.text('Retry now'), findsNothing);
    expect(find.text('Waiting for first location sync...'), findsNothing);
  });
}

void _noop() {}
