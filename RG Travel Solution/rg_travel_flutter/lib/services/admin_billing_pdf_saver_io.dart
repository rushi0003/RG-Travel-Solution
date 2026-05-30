import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'admin_billing_pdf_types.dart';

Future<BillingPdfResult> saveBillingPdfBytes(
  List<int> bytes,
  String fileName,
) async {
  final downloadsDir = await _resolvePreferredDirectory();
  final file = File('${downloadsDir.path}${Platform.pathSeparator}$fileName');
  await file.writeAsBytes(bytes, flush: true);
  final normalizedPath = file.path.replaceAll('\\', '/');
  final savedToDownloads = normalizedPath.toLowerCase().contains('/download');

  return BillingPdfResult(
    fileName: fileName,
    savedPath: file.path,
    savedToDownloads: savedToDownloads,
  );
}

Future<Directory> _resolvePreferredDirectory() async {
  final candidates = <Directory>[
    Directory('/storage/emulated/0/Download'),
    Directory('/sdcard/Download'),
  ];
  for (final dir in candidates) {
    try {
      if (await dir.exists()) {
        return dir;
      }
    } catch (_) {}
  }

  final externalDir = await getExternalStorageDirectory();
  if (externalDir != null) {
    return externalDir;
  }

  return getApplicationDocumentsDirectory();
}
