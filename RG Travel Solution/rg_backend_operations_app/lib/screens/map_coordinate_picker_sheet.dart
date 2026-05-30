import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../theme/ops_ui_tokens.dart';

class MapCoordinatePickerSheet extends StatefulWidget {
  const MapCoordinatePickerSheet({
    super.key,
    required this.title,
    required this.addressHint,
    this.initialLat,
    this.initialLng,
  });

  final String title;
  final String addressHint;
  final double? initialLat;
  final double? initialLng;

  @override
  State<MapCoordinatePickerSheet> createState() =>
      _MapCoordinatePickerSheetState();
}

class _MapCoordinatePickerSheetState extends State<MapCoordinatePickerSheet> {
  static const LatLng _defaultCenter = LatLng(18.5204, 73.8567);

  late final MapController _mapController;
  late LatLng _selected;
  double _zoom = 13;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _selected = (widget.initialLat != null && widget.initialLng != null)
        ? LatLng(widget.initialLat!, widget.initialLng!)
        : _defaultCenter;
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final compact = size.width < OpsBreakpoints.compact;
    final height = size.height * (compact ? 0.9 : 0.82);
    return Container(
      height: height,
      decoration: const BoxDecoration(
        color: OpsUiTokens.panel,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(OpsRadius.xl),
        ),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              OpsSpacing.lg,
              OpsSpacing.md,
              OpsSpacing.lg,
              OpsSpacing.sm,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: OpsTypography.heading,
                      ),
                      const SizedBox(height: OpsSpacing.xs),
                      Text(
                        widget.addressHint.isEmpty
                            ? 'Tap map to select coordinates'
                            : widget.addressHint,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: OpsTypography.body,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close_rounded),
                  tooltip: 'Close',
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: OpsSpacing.lg),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(OpsRadius.lg),
                child: FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: _selected,
                    initialZoom: _zoom,
                    onTap: (_, point) {
                      setState(() {
                        _selected = point;
                      });
                    },
                    onPositionChanged: (position, _) {
                      _zoom = position.zoom;
                    },
                  ),
                  children: [
                    TileLayer(
                      urlTemplate:
                          'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                      subdomains: const ['a', 'b', 'c', 'd'],
                      userAgentPackageName: 'com.rgtravel.backendops',
                    ),
                    TileLayer(
                      urlTemplate:
                          'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                      subdomains: const ['a', 'b', 'c'],
                      userAgentPackageName: 'com.rgtravel.backendops',
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: _selected,
                          width: 48,
                          height: 48,
                          child: const Icon(
                            Icons.location_pin,
                            color: OpsUiTokens.danger,
                            size: 42,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              OpsSpacing.lg,
              OpsSpacing.md,
              OpsSpacing.lg,
              OpsSpacing.lg,
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final footerCompact =
                    constraints.maxWidth < OpsBreakpoints.compact;
                final selectedText = Text(
                  'Selected: ${_selected.latitude.toStringAsFixed(6)}, ${_selected.longitude.toStringAsFixed(6)}',
                  overflow: TextOverflow.ellipsis,
                  style: OpsTypography.body,
                );
                final actions = Wrap(
                  spacing: OpsSpacing.sm,
                  runSpacing: OpsSpacing.sm,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () {
                        _mapController.move(_selected, _zoom);
                      },
                      icon: const Icon(Icons.my_location_rounded, size: 16),
                      label: const Text('Center'),
                    ),
                    ElevatedButton.icon(
                      onPressed: () => Navigator.pop(context, _selected),
                      icon: const Icon(Icons.check_rounded, size: 16),
                      label: const Text('Use Location'),
                    ),
                  ],
                );

                if (footerCompact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      selectedText,
                      const SizedBox(height: OpsSpacing.md),
                      actions,
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: selectedText),
                    const SizedBox(width: OpsSpacing.md),
                    actions,
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
