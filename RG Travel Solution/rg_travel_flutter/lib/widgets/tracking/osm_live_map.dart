import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class OsmLiveMap extends StatelessWidget {
  const OsmLiveMap({
    super.key,
    required this.mapController,
    required this.initialCenter,
    required this.routeHistory,
    required this.markers,
    required this.polylineColor,
  });

  final MapController mapController;
  final LatLng initialCenter;
  final List<LatLng> routeHistory;
  final List<Marker> markers;
  final Color polylineColor;

  @override
  Widget build(BuildContext context) {
    return FlutterMap(
      mapController: mapController,
      options: MapOptions(
        initialCenter: initialCenter,
        initialZoom: 16,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.rgtravel.app',
        ),
        if (routeHistory.length >= 2)
          PolylineLayer(
            polylines: [
              Polyline(
                points: List<LatLng>.from(routeHistory),
                color: polylineColor,
                strokeWidth: 4,
              ),
            ],
          ),
        MarkerLayer(markers: List<Marker>.from(markers)),
      ],
    );
  }
}
