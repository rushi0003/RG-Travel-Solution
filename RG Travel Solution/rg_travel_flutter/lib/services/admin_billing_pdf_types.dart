class BillingPdfResult {
  final String fileName;
  final String? savedPath;
  final bool savedToDownloads;

  const BillingPdfResult({
    required this.fileName,
    required this.savedPath,
    required this.savedToDownloads,
  });
}
