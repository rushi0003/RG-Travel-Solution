import 'admin_billing_pdf_types.dart';
import 'web_download_web.dart';

Future<BillingPdfResult> saveBillingPdfBytes(
  List<int> bytes,
  String fileName,
) async {
  await saveBytesAsDownload(bytes, fileName, 'application/pdf');
  return BillingPdfResult(
    fileName: fileName,
    savedPath: fileName,
    savedToDownloads: true,
  );
}
