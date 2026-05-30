import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../core/theme/app_theme.dart';

class MapCoordinatePickerSheet extends StatefulWidget {
  final String title;
  final String addressHint;
  final double? initialLat;
  final double? initialLng;

  const MapCoordinatePickerSheet({
    super.key,
    required this.title,
    required this.addressHint,
    this.initialLat,
    this.initialLng,
  });

  @override
  State<MapCoordinatePickerSheet> createState() =>
      _MapCoordinatePickerSheetState();
}

class _MapCoordinatePickerSheetState extends State<MapCoordinatePickerSheet> {
  static const LatLng _defaultCenter = LatLng(18.5204, 73.8567);
  late final MapController _mapController;
  late LatLng _selected;
  double _zoom = 13.0;

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
    final compact = size.width < 600;
    final height = size.height * (compact ? 0.9 : 0.82);
    return Container(
      height: height,
      decoration: const BoxDecoration(
        color: AppThemeColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.sm,
              AppSpacing.md,
              AppSpacing.sm,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: AppTypography.displayMedium.copyWith(
                          color: AppThemeColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        widget.addressHint.isEmpty
                            ? 'Tap map to select coordinates'
                            : widget.addressHint,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppThemeColors.textSecondary,
                        ),
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
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.md),
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
                      userAgentPackageName: 'com.rgtravel.app',
                    ),
                    TileLayer(
                      urlTemplate:
                          'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                      subdomains: const ['a', 'b', 'c'],
                      userAgentPackageName: 'com.rgtravel.app',
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: _selected,
                          width: 48,
                          height: 48,
                          child: const Icon(
                            Icons.location_pin,
                            color: AppThemeColors.error,
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
              AppSpacing.md,
              AppSpacing.sm,
              AppSpacing.md,
              AppSpacing.md,
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final footerCompact = constraints.maxWidth < 600;
                final selectedText = Text(
                  'Selected: ${_selected.latitude.toStringAsFixed(6)}, ${_selected.longitude.toStringAsFixed(6)}',
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                );
                final actions = Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
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
                      const SizedBox(height: AppSpacing.sm),
                      actions,
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: selectedText),
                    const SizedBox(width: AppSpacing.sm),
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
