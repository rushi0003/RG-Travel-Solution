# RG Travel Solution - Flutter Integration Guide

## 📱 Flutter App Setup & Configuration

### 1. Project Structure

```
rg_travel_flutter/
├── lib/
│   ├── main.dart                 # Entry point
│   ├── app.dart                  # App shell & routing
│   │
│   ├── core/
│   │   ├── config/
│   │   │   ├── env.dart          # API config & base URL
│   │   │   ├── api_config.dart   # Endpoint constants
│   │   │   └── app_constants.dart# App-wide constants
│   │   │
│   │   ├── network/
│   │   │   ├── api_client.dart   # HTTP client wrapper
│   │   │   ├── api_exception.dart# Custom exceptions
│   │   │   └── interceptors.dart # Request/response interceptors
│   │   │
│   │   ├── storage/
│   │   │   └── session_store.dart# SharedPreferences wrapper
│   │   │
│   │   └── utils/
│   │       ├── constants.dart    # UI constants
│   │       ├── validators.dart   # Input validation
│   │       └── helpers.dart      # Utility functions
│   │
│   ├── models/
│   │   ├── admin_model.dart
│   │   ├── driver_model.dart
│   │   ├── employee_model.dart
│   │   ├── trip_model.dart
│   │   ├── auth_models.dart
│   │   └── location_model.dart
│   │
│   ├── services/
│   │   ├── auth_service.dart     # Authentication logic
│   │   ├── admin_service.dart    # Admin API calls
│   │   ├── driver_service.dart   # Driver API calls
│   │   ├── employee_service.dart # Employee API calls
│   │   ├── trip_service.dart     # Trip API calls
│   │   └── location_service.dart # Location & tracking
│   │
│   ├── state/
│   │   ├── admin_provider.dart
│   │   ├── driver_provider.dart
│   │   ├── employee_provider.dart
│   │   ├── auth_provider.dart
│   │   └── trip_provider.dart
│   │
│   ├── screens/
│   │   ├── login/
│   │   │   └── login_screen.dart
│   │   ├── admin/
│   │   │   ├── admin_dashboard.dart
│   │   │   ├── create_group_assign_screen.dart
│   │   │   ├── live_trips_screen.dart
│   │   │   ├── drivers_screen.dart
│   │   │   ├── employees_screen.dart
│   │   │   ├── trip_history_screen.dart
│   │   │   └── live_tracking_screen.dart
│   │   ├── driver/
│   │   │   ├── driver_dashboard.dart
│   │   │   ├── driver_profile_screen.dart
│   │   │   ├── assigned_trip_screen.dart
│   │   │   └── otp_screen.dart
│   │   └── employee/
│   │       ├── employee_dashboard.dart
│   │       ├── my_trip_screen.dart
│   │       └── live_tracking_view.dart
│   │
│   └── widgets/
│       ├── common/
│       │   ├── custom_app_bar.dart
│       │   ├── custom_button.dart
│       │   ├── custom_text_field.dart
│       │   ├── custom_card.dart
│       │   └── loading_spinner.dart
│       ├── layout/
│       │   ├── safe_area_layout.dart
│       │   └── responsive_grid.dart
│       └── trip/
│           ├── trip_card.dart
│           ├── driver_location_card.dart
│           └── otp_input_widget.dart
│
└── pubspec.yaml                  # Dependencies
```

---

## 🔧 Setup Instructions

### 1. Install Dependencies

```bash
cd rg_travel_flutter
flutter pub get
```

### 2. Configure Backend URL

Edit [lib/core/config/env.dart](lib/core/config/env.dart):

```dart
class Env {
  // API Configuration
  static const String baseUrl = "http://10.0.2.2:5000";  // Android Emulator
  // static const String baseUrl = "http://192.168.1.100:5000";  // Your Machine IP
  // static const String baseUrl = "http://api.example.com";  // Production
  
  static const String apiPrefix = "/api";
  
  // Feature Flags
  static const bool logApi = true;     // Enable API logging
  static const bool logState = true;   // Enable state logs
  
  static String debugSummary() {
    return '''
    ╔═══════════════════════════════════════════════════════╗
    ║        RG Travel Solution - Configuration             ║
    ╠═══════════════════════════════════════════════════════╣
    ║ Backend URL: $baseUrl
    ║ API Prefix: $apiPrefix
    ║ Full API URL: $baseUrl$apiPrefix
    ║ API Logging: $logApi
    ║ State Logging: $logState
    ╚═══════════════════════════════════════════════════════╝
    ''';
  }
}
```

### 3. Run Flutter App

**Android Emulator:**
```bash
flutter run -d emulator-5554
```

**Physical Device:**
```bash
flutter run
```

**Web:**
```bash
flutter run -d chrome
```

---

## 📡 Core API Integration

### API Client Setup

The API client is in [lib/core/network/api_client.dart](lib/core/network/api_client.dart):

```dart
class ApiClient {
  static const _connectTimeout = Duration(seconds: 30);
  static const _receiveTimeout = Duration(seconds: 30);
  
  final http.Client _httpClient;
  final SessionStore _sessionStore;
  
  ApiClient({
    http.Client? httpClient,
    SessionStore? sessionStore,
  })  : _httpClient = httpClient ?? http.Client(),
        _sessionStore = sessionStore ?? SessionStore();

  Future<T> get<T>(
    String endpoint, {
    Map<String, String>? headers,
    required T Function(dynamic) parser,
  }) async {
    try {
      final token = await _sessionStore.getToken();
      final finalHeaders = _buildHeaders(token, headers);
      
      final response = await _httpClient.get(
        Uri.parse('${Env.baseUrl}${Env.apiPrefix}$endpoint'),
        headers: finalHeaders,
      ).timeout(_receiveTimeout);
      
      return _handleResponse(response, parser);
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error: ${e.message}',
        statusCode: 0,
      );
    }
  }

  Future<T> post<T>(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    required T Function(dynamic) parser,
  }) async {
    try {
      final token = await _sessionStore.getToken();
      final finalHeaders = _buildHeaders(token, headers);
      
      final response = await _httpClient.post(
        Uri.parse('${Env.baseUrl}${Env.apiPrefix}$endpoint'),
        headers: finalHeaders,
        body: jsonEncode(body ?? {}),
      ).timeout(_receiveTimeout);
      
      return _handleResponse(response, parser);
    } catch (e) {
      throw ApiException(message: e.toString(), statusCode: -1);
    }
  }

  Map<String, String> _buildHeaders(
    String? token,
    Map<String, String>? customHeaders,
  ) {
    final headers = {
      'Content-Type': 'application/json',
      ...?customHeaders,
    };
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  T _handleResponse<T>(
    http.Response response,
    T Function(dynamic) parser,
  ) {
    if (response.statusCode == 200 || response.statusCode == 201) {
      final jsonData = jsonDecode(response.body);
      return parser(jsonData['data']);
    } else if (response.statusCode == 401) {
      throw ApiException(
        message: 'Unauthorized - Please login again',
        statusCode: 401,
      );
    } else {
      final jsonData = jsonDecode(response.body);
      throw ApiException(
        message: jsonData['message'] ?? 'Unknown error',
        statusCode: response.statusCode,
      );
    }
  }
}
```

---

## 🔐 Authentication Flow

### Login Process

```dart
// In AuthService
class AuthService {
  final ApiClient _apiClient;
  final SessionStore _sessionStore;

  Future<LoginResponse> loginAdmin({
    required String mobile,
    required String password,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/auth/admin/login',
        body: {
          'mobile': mobile,
          'password': password,
        },
        parser: (data) => data as Map<String, dynamic>,
      );

      // Extract token and save
      final token = response['token'] as String;
      final expiresAt = response['expires_at'] as String;
      final profile = response['profile'] as Map<String, dynamic>;

      // Save to persistent storage
      await _sessionStore.saveToken(token);
      await _sessionStore.saveRole('admin');
      await _sessionStore.saveUserId(profile['id']);
      await _sessionStore.saveExpiryTime(expiresAt);

      return LoginResponse(
        success: true,
        token: token,
        profile: AdminModel.fromJson(profile),
      );
    } on ApiException catch (e) {
      return LoginResponse(
        success: false,
        error: e.message,
      );
    }
  }

  Future<void> logout() async {
    try {
      await _apiClient.post(
        '/auth/logout',
        parser: (_) => null,
      );
    } catch (e) {
      // Continue logout even if API fails
    }
    await _sessionStore.clearAll();
  }
}
```

### Protected Requests

```dart
// Login screen integration
class LoginScreen extends StatefulWidget {
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _mobileController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('RG Travel - Login')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _mobileController,
              decoration: InputDecoration(
                labelText: 'Mobile (10 digits)',
                prefixIcon: Icon(Icons.phone),
              ),
              keyboardType: TextInputType.phone,
            ),
            SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: Icon(Icons.lock),
              ),
              obscureText: true,
            ),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleLogin,
                child: _isLoading
                    ? CircularProgressIndicator()
                    : Text('Login'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleLogin() async {
    setState(() => _isLoading = true);

    final authService = AuthService();
    final result = await authService.loginAdmin(
      mobile: _mobileController.text,
      password: _passwordController.text,
    );

    setState(() => _isLoading = false);

    if (result.success) {
      // Navigate to dashboard
      Navigator.of(context).pushReplacementNamed(
        '/admin/dashboard',
        arguments: result.profile,
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result.error ?? 'Login failed')),
      );
    }
  }

  @override
  void dispose() {
    _mobileController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}
```

---

## 📊 State Management (Provider/GetX)

### Using Riverpod/GetX

```dart
// lib/state/admin_provider.dart
final adminTripsProvider = StateNotifierProvider<AdminTripsNotifier, AsyncValue<List<TripModel>>>((ref) {
  return AdminTripsNotifier();
});

class AdminTripsNotifier extends StateNotifier<AsyncValue<List<TripModel>>> {
  AdminTripsNotifier() : super(const AsyncValue.loading());

  Future<void> fetchLiveTrips() async {
    state = const AsyncValue.loading();
    try {
      final adminService = AdminService();
      final trips = await adminService.getLiveTrips();
      state = AsyncValue.data(trips);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }

  Future<void> createTrip(CreateTripRequest request) async {
    try {
      final adminService = AdminService();
      final trip = await adminService.createTrip(request);
      final currentTrips = state.maybeWhen(
        data: (trips) => trips,
        orElse: () => <TripModel>[],
      );
      state = AsyncValue.data([...currentTrips, trip]);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }
}
```

### Using Consumer Widgets

```dart
class AdminDashboard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tripsAsync = ref.watch(adminTripsProvider);

    return Scaffold(
      appBar: AppBar(title: Text('Admin Dashboard')),
      body: tripsAsync.when(
        data: (trips) => ListView.builder(
          itemCount: trips.length,
          itemBuilder: (context, index) => TripCard(trip: trips[index]),
        ),
        loading: () => Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => ref.read(adminTripsProvider.notifier).createTrip(
          CreateTripRequest(
            tripType: 'pickup',
            scheduleTime: '09:00',
            vehicleType: '4',
          ),
        ),
        child: Icon(Icons.add),
      ),
    );
  }
}
```

---

## 🗺️ Location & Maps Integration

### Location Service

```dart
class LocationService {
  final Geolocator _geolocator = Geolocator();
  final DriverService _driverService = DriverService();

  Stream<Position> getLocationStream({
    Duration interval = const Duration(seconds: 5),
  }) {
    return _geolocator.getPositionStream(
      locationSettings: LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 10, // meters
      ),
    );
  }

  Future<void> startLocationTracking(int tripId) async {
    getLocationStream().listen((position) async {
      try {
        await _driverService.updateTripLocation(
          tripId: tripId,
          latitude: position.latitude,
          longitude: position.longitude,
          accuracy: position.accuracy,
        );
      } catch (e) {
        print('Failed to update location: $e');
      }
    });
  }
}
```

### Google Maps Integration

```dart
class LiveTrackingMap extends StatefulWidget {
  final String routeNo;
  final EmployeeService employeeService;

  @override
  State<LiveTrackingMap> createState() => _LiveTrackingMapState();
}

class _LiveTrackingMapState extends State<LiveTrackingMap> {
  late GoogleMapController _mapController;
  final Set<Marker> _markers = {};
  final Set<Polyline> _polylines = {};

  @override
  void initState() {
    super.initState();
    _startTrackingUpdates();
  }

  Future<void> _startTrackingUpdates() async {
    while (mounted) {
      try {
        final location = await widget.employeeService
            .getDriverLocation(widget.routeNo);
        
        setState(() {
          _markers.add(
            Marker(
              markerId: MarkerId('driver'),
              position: LatLng(location.latitude, location.longitude),
              infoWindow: InfoWindow(title: 'Driver Location'),
            ),
          );
        });

        await Future.delayed(Duration(seconds: 10));
      } catch (e) {
        print('Error updating location: $e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return GoogleMap(
      onMapCreated: (controller) => _mapController = controller,
      initialCameraPosition: CameraPosition(
        target: LatLng(12.9352, 77.6245),
        zoom: 15,
      ),
      markers: _markers,
      polylines: _polylines,
    );
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }
}
```

---

## 🧪 Testing

### Unit Tests

```dart
// test/services/auth_service_test.dart
void main() {
  group('AuthService', () {
    late MockApiClient mockApiClient;
    late MockSessionStore mockSessionStore;
    late AuthService authService;

    setUp(() {
      mockApiClient = MockApiClient();
      mockSessionStore = MockSessionStore();
      authService = AuthService(
        apiClient: mockApiClient,
        sessionStore: mockSessionStore,
      );
    });

    test('Admin login returns LoginResponse with token', () async {
      final mockResponse = {
        'token': 'test_token_123',
        'expires_at': '2026-02-01T14:30:00',
        'profile': {'id': 'admin_1', 'name': 'Admin'},
      };

      when(mockApiClient.post(
        '/auth/admin/login',
        body: anyNamed('body'),
        parser: anyNamed('parser'),
      )).thenAnswer((_) async => mockResponse);

      final result = await authService.loginAdmin(
        mobile: '9876543210',
        password: 'admin@123',
      );

      expect(result.success, isTrue);
      expect(result.token, 'test_token_123');
      verify(mockSessionStore.saveToken('test_token_123')).called(1);
    });

    test('Failed login returns error', () async {
      when(mockApiClient.post(
        any,
        body: anyNamed('body'),
        parser: anyNamed('parser'),
      )).thenThrow(
        ApiException(
          message: 'Invalid credentials',
          statusCode: 401,
        ),
      );

      final result = await authService.loginAdmin(
        mobile: '9876543210',
        password: 'wrong',
      );

      expect(result.success, isFalse);
      expect(result.error, contains('Invalid credentials'));
    });
  });
}
```

### Widget Tests

```dart
// test/screens/login_screen_test.dart
void main() {
  group('LoginScreen', () {
    testWidgets('Shows error on failed login', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(home: LoginScreen()),
      );

      await tester.enterText(find.byType(TextField).at(0), '9876543210');
      await tester.enterText(find.byType(TextField).at(1), 'wrong');
      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();

      expect(find.byType(SnackBar), findsOneWidget);
    });
  });
}
```

---

## 📲 Available Models

### AdminModel
```dart
class AdminModel {
  final String id;
  final String name;
  final String mobile;
  final String email;
  final String officeLocation;
  final DateTime createdAt;
}
```

### DriverModel
```dart
class DriverModel {
  final String id;
  final String name;
  final String mobile;
  final String dlNo;
  final String vehicleNo;
  final String vehicleType;
  final bool isApproved;
  final DateTime dlExpiry;
  final DateTime rcExpiry;
}
```

### EmployeeModel
```dart
class EmployeeModel {
  final String id;
  final String name;
  final String mobile;
  final String email;
  final String loginTime;
  final String logoutTime;
  final String dropLocation;
  final double dropLat;
  final double dropLng;
}
```

### TripModel
```dart
class TripModel {
  final int id;
  final String routeNo;
  final String tripType;
  final String status;
  final int employeeCount;
  final List<EmployeeInTrip> members;
  final String? startOtp;
  final String? endOtp;
  final DateTime? startTime;
  final DateTime? endTime;
  final double? totalKm;
}
```

---

## 🚀 Deployment

### Build APK (Android)
```bash
flutter build apk --release
# Output: build/app/outputs/apk/release/app-release.apk
```

### Build iOS App
```bash
flutter build ios --release
```

### Build Web App
```bash
flutter build web --release
# Output: build/web/
```

---

## 📚 Useful Links

- [Flutter Documentation](https://flutter.dev/docs)
- [Riverpod State Management](https://riverpod.dev)
- [Google Maps for Flutter](https://pub.dev/packages/google_maps_flutter)
- [Geolocator Package](https://pub.dev/packages/geolocator)
- [HTTP Package](https://pub.dev/packages/http)
- [SharedPreferences](https://pub.dev/packages/shared_preferences)

---

**Last Updated**: 2026-02-01  
**Flutter Version**: 3.4+  
**Dart Version**: 3.0+
