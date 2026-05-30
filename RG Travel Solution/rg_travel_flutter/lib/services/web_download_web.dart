// Warning note: keeping `dart:html` here for web download compatibility in the current project setup.
// ignore_for_file: deprecated_member_use
import 'dart:html' as html;

Future<void> saveBytesAsDownload(
  List<int> bytes,
  String fileName,
  String mimeType,
) async {
  final blob = html.Blob(<dynamic>[bytes], mimeType);
  final url = html.Url.createObjectUrlFromBlob(blob);
  final anchor = html.AnchorElement(href: url)
    ..download = fileName
    ..style.display = 'none';
  html.document.body?.children.add(anchor);
  anchor.click();
  anchor.remove();
  html.Url.revokeObjectUrl(url);
}
