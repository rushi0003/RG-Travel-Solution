import 'package:flutter/foundation.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:rg_travel_flutter/models/admin_billing_model.dart';

import 'admin_billing_pdf_types.dart';
import 'admin_billing_pdf_saver_stub.dart'
    if (dart.library.io) 'admin_billing_pdf_saver_io.dart'
    if (dart.library.html) 'admin_billing_pdf_saver_web.dart';

class AdminBillingPdfService {
  AdminBillingPdfService._();

  static const PdfColor _brandBlue = PdfColor.fromInt(0xFF1A5276);
  static const PdfColor _borderColor = PdfColor.fromInt(0xFFD5DCE6);
  static const PdfColor _lightBlue = PdfColor.fromInt(0xFFF0F5FA);
  static const PdfColor _lightBlueAlt = PdfColor.fromInt(0xFFF8FAFC);
  static const PdfColor _advanceBg = PdfColor.fromInt(0xFFEAF7EF);
  static const PdfColor _balanceBg = PdfColor.fromInt(0xFFFBEDEE);
  static const PdfColor _textDark = PdfColor.fromInt(0xFF222222);
  static const PdfColor _textMuted = PdfColor.fromInt(0xFF555555);
  static const PdfColor _successText = PdfColor.fromInt(0xFF1E8449);
  static const PdfColor _dangerText = PdfColor.fromInt(0xFFC0392B);

  static Future<BillingPdfResult> createAndSavePdf({
    required BillingDraft draft,
  }) async {
    final assignment = draft.assignment;
    if (assignment == null) {
      throw ArgumentError('Vehicle-driver selection is required.');
    }
    if (draft.includedTrips.isEmpty) {
      throw ArgumentError('At least one completed trip is required.');
    }

    final bytes = await _buildPdfBytes(draft);
    final safeVehicleNo = assignment.vehicleNo.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final fileName = 'invoice_${safeVehicleNo}_$timestamp.pdf';

    if (kIsWeb) {
      return saveBillingPdfBytes(bytes, fileName);
    }
    return saveBillingPdfBytes(bytes, fileName);
  }

  static Future<List<int>> _buildPdfBytes(BillingDraft draft) async {
    final assignment = draft.assignment!;
    final calculation = draft.calculation;
    final pdf = pw.Document();
    final generatedAt = DateTime.now();
    final invoiceNo = _invoiceNumber(generatedAt);
    final cgstRate = draft.gstPercent / 2;
    final sgstRate = draft.gstPercent / 2;
    final cgstAmount = calculation.gstAmount / 2;
    final sgstAmount = calculation.gstAmount / 2;
    final periodLabel = draft.rangeLabel;

    pdf.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.fromLTRB(32, 30, 32, 24),
        build: (context) {
          return <pw.Widget>[
            _header(draft, invoiceNo, generatedAt),
            pw.SizedBox(height: 14),
            pw.Row(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Expanded(
                  child: _infoBox(
                    title: 'Bill To (Company / Client)',
                    child: pw.Column(
                      crossAxisAlignment: pw.CrossAxisAlignment.start,
                      children: [
                        _infoLine(
                          'Company Name',
                          _fallback(draft.companyName, assignment.driverName),
                        ),
                        _infoLine(
                          'Address',
                          _fallback(
                            draft.companyAddress,
                            'Client address not provided',
                          ),
                        ),
                        _infoLine(
                          'Contact Person',
                          _fallback(draft.contactPerson, assignment.driverName),
                        ),
                        _infoLine(
                          'Driver Mobile',
                          _fallback(
                            assignment.driverMobile,
                            draft.includedTrips.isNotEmpty
                                ? draft.includedTrips.first.driverMobile
                                : 'Not available',
                          ),
                        ),
                        _infoLine(
                          'GST No',
                          _fallback(draft.clientGstNo, 'Optional / Not provided'),
                        ),
                      ],
                    ),
                  ),
                ),
                pw.SizedBox(width: 14),
                pw.Expanded(
                  child: _infoBox(
                    title: 'Transportation Details',
                    child: pw.Column(
                      crossAxisAlignment: pw.CrossAxisAlignment.start,
                      children: [
                        _infoLine(
                          'Service Type',
                          _fallback(
                            draft.serviceType,
                            'Employee Transportation',
                          ),
                        ),
                        _infoLine(
                          'Vehicle Type',
                          (assignment.vehicleType ?? '').trim().isEmpty
                              ? 'Vehicle'
                              : assignment.vehicleType!,
                        ),
                        _infoLine('Vehicle No', assignment.vehicleNo),
                        _infoLine('Period', periodLabel),
                        _infoLine(
                          'Total Employees',
                          _fallback(draft.totalEmployees, 'Not specified'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            pw.SizedBox(height: 14),
            _tripTable(draft),
            pw.SizedBox(height: 12),
            pw.Row(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Expanded(
                  child: _notesSection(
                    draft: draft,
                    modeLabel: draft.mode == BillingMode.dateRange
                        ? 'Date range billing'
                        : 'Specific trip billing',
                    driverName: assignment.driverName,
                    vehicleNo: assignment.vehicleNo,
                    periodLabel: periodLabel,
                  ),
                ),
                pw.SizedBox(width: 18),
                pw.SizedBox(
                  width: 230,
                  child: _totalsBox(
                    totalKm: draft.totalKm,
                    subtotal: calculation.subtotal,
                    cgstRate: cgstRate,
                    cgstAmount: cgstAmount,
                    sgstRate: sgstRate,
                    sgstAmount: sgstAmount,
                    totalAmount: calculation.grandTotal,
                    advancePaid: calculation.advancePaid,
                    balanceDue: calculation.payableAmount,
                  ),
                ),
              ],
            ),
            pw.SizedBox(height: 24),
            _signatureRow(),
            pw.SizedBox(height: 14),
            _footer(),
          ];
        },
      ),
    );

    return pdf.save();
  }

  static pw.Widget _header(
    BillingDraft draft,
    String invoiceNo,
    DateTime generatedAt,
  ) {
    return pw.Container(
      padding: const pw.EdgeInsets.only(bottom: 10),
      decoration: const pw.BoxDecoration(
        border: pw.Border(
          bottom: pw.BorderSide(color: _brandBlue, width: 2.5),
        ),
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Text(
                'RG Travel Solution',
                style: pw.TextStyle(
                  fontSize: 22,
                  fontWeight: pw.FontWeight.bold,
                  color: _brandBlue,
                ),
              ),
              pw.SizedBox(height: 3),
              pw.Text(
                "Phone: 9325118627 | Email: ${_fallback(draft.companyEmail, 'rgtravelsolution@gmail.com')}",
                style: const pw.TextStyle(fontSize: 11.5, color: _textMuted),
              ),
              pw.Text(
                "GST No: ${_fallback(draft.rgGstNo, '____________________')}",
                style: const pw.TextStyle(fontSize: 11.5, color: _textMuted),
              ),
              if (draft.officeAddress.trim().isNotEmpty)
                pw.Text(
                  draft.officeAddress.trim(),
                  style: const pw.TextStyle(fontSize: 11.5, color: _textMuted),
                ),
            ],
          ),
          pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.end,
            children: [
              pw.Text(
                'INVOICE',
                style: pw.TextStyle(
                  fontSize: 28,
                  fontWeight: pw.FontWeight.bold,
                  color: _brandBlue,
                ),
              ),
              pw.SizedBox(height: 4),
              _headerMeta('Invoice No', invoiceNo),
              _headerMeta('Date', _formatDisplayDate(generatedAt)),
            ],
          ),
        ],
      ),
    );
  }

  static pw.Widget _headerMeta(String label, String value) {
    return pw.Padding(
      padding: const pw.EdgeInsets.only(bottom: 3),
      child: pw.RichText(
        text: pw.TextSpan(
          style: const pw.TextStyle(fontSize: 11.5, color: _textMuted),
          children: [
            pw.TextSpan(text: '$label: '),
            pw.TextSpan(
              text: value,
              style: pw.TextStyle(
                color: _textDark,
                fontWeight: pw.FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  static pw.Widget _infoBox({
    required String title,
    required pw.Widget child,
  }) {
    return pw.Container(
      padding: const pw.EdgeInsets.all(10),
      decoration: pw.BoxDecoration(
        color: _lightBlueAlt,
        borderRadius: pw.BorderRadius.circular(6),
        border: pw.Border.all(color: _borderColor),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(
            title,
            style: pw.TextStyle(
              fontSize: 10,
              color: PdfColors.grey700,
              fontWeight: pw.FontWeight.bold,
            ),
          ),
          pw.SizedBox(height: 6),
          child,
        ],
      ),
    );
  }

  static pw.Widget _infoLine(String label, String value) {
    return pw.Padding(
      padding: const pw.EdgeInsets.only(bottom: 4),
      child: pw.Row(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.SizedBox(
            width: 88,
            child: pw.Text(
              '$label:',
              style: const pw.TextStyle(fontSize: 11, color: PdfColors.grey700),
            ),
          ),
          pw.Expanded(
            child: pw.Text(
              value,
              style: const pw.TextStyle(fontSize: 12, color: _textDark),
            ),
          ),
        ],
      ),
    );
  }

  static pw.Widget _tripTable(BillingDraft draft) {
    final rows = draft.includedTrips.asMap().entries.map((entry) {
      final index = entry.key + 1;
      final trip = entry.value;
      final amount = trip.totalKm * draft.perKmAmount;
      return <String>[
        index.toString(),
        trip.routeNo,
        '${trip.vehicleNo} / ${trip.driverName}',
        _formatShortDate(trip.tripDate),
        trip.totalKm.toStringAsFixed(2),
        draft.perKmAmount.toStringAsFixed(2),
        amount.toStringAsFixed(2),
      ];
    }).toList();

    return pw.TableHelper.fromTextArray(
      border: pw.TableBorder.all(color: _borderColor, width: 0.6),
      headerDecoration: const pw.BoxDecoration(color: _brandBlue),
      headerStyle: pw.TextStyle(
        color: PdfColors.white,
        fontWeight: pw.FontWeight.bold,
        fontSize: 11,
      ),
      cellStyle: const pw.TextStyle(fontSize: 10.5, color: _textDark),
      cellPadding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 7),
      cellAlignments: {
        0: pw.Alignment.center,
        1: pw.Alignment.centerLeft,
        2: pw.Alignment.centerLeft,
        3: pw.Alignment.center,
        4: pw.Alignment.centerRight,
        5: pw.Alignment.centerRight,
        6: pw.Alignment.centerRight,
      },
      columnWidths: {
        0: const pw.FixedColumnWidth(28),
        1: const pw.FixedColumnWidth(68),
        2: const pw.FlexColumnWidth(2.2),
        3: const pw.FixedColumnWidth(58),
        4: const pw.FixedColumnWidth(48),
        5: const pw.FixedColumnWidth(58),
        6: const pw.FixedColumnWidth(64),
      },
      rowDecoration: pw.BoxDecoration(
        color: PdfColors.white,
      ),
      oddRowDecoration: const pw.BoxDecoration(color: _lightBlue),
      headers: const [
        'Sr.',
        'Trip Route No.',
        'Trip Location / Route',
        'Date',
        'Trip KM',
        'Rate/KM',
        'Amount',
      ],
      data: rows,
    );
  }

  static pw.Widget _notesSection({
    required BillingDraft draft,
    required String modeLabel,
    required String driverName,
    required String vehicleNo,
    required String periodLabel,
  }) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(
          'Notes / Remarks',
          style: pw.TextStyle(
            fontSize: 10,
            color: PdfColors.grey700,
            fontWeight: pw.FontWeight.bold,
          ),
        ),
        pw.SizedBox(height: 6),
        pw.Container(
          width: double.infinity,
          padding: const pw.EdgeInsets.all(10),
          decoration: pw.BoxDecoration(
            color: _lightBlueAlt,
            borderRadius: pw.BorderRadius.circular(5),
            border: pw.Border.all(color: _borderColor),
          ),
          child: pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Text(
                'Billing generated for $driverName using vehicle $vehicleNo.',
                style: const pw.TextStyle(fontSize: 11.5, color: _textDark),
              ),
              pw.SizedBox(height: 3),
              pw.Text(
                'Scope: $modeLabel | Period: $periodLabel',
                style: const pw.TextStyle(fontSize: 11.5, color: _textDark),
              ),
              pw.SizedBox(height: 3),
              pw.Text(
                _fallback(
                  draft.notes,
                  'Completed trips are included for billing. Cancelled trips are excluded automatically.',
                ),
                style: const pw.TextStyle(fontSize: 11.5, color: _textDark),
              ),
              pw.SizedBox(height: 12),
              pw.Text(
                'Payment Details:',
                style: pw.TextStyle(
                  fontSize: 11.5,
                  color: _textMuted,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
              pw.SizedBox(height: 4),
              pw.Text(
                "Bank: ${_fallback(draft.bankName, '_________________')} | A/C No: ${_fallback(draft.accountNumber, '_________________')}",
                style: const pw.TextStyle(fontSize: 11, color: _textMuted),
              ),
              pw.Text(
                "IFSC: ${_fallback(draft.ifscCode, '_________________')} | UPI: ${_fallback(draft.upiId, 'rgtravelsolution@gmail.com')}",
                style: const pw.TextStyle(fontSize: 11, color: _textMuted),
              ),
            ],
          ),
        ),
      ],
    );
  }

  static pw.Widget _totalsBox({
    required double totalKm,
    required double subtotal,
    required double cgstRate,
    required double cgstAmount,
    required double sgstRate,
    required double sgstAmount,
    required double totalAmount,
    required double advancePaid,
    required double balanceDue,
  }) {
    return pw.Container(
      decoration: pw.BoxDecoration(
        borderRadius: pw.BorderRadius.circular(6),
        border: pw.Border.all(color: _borderColor),
      ),
      child: pw.Column(
        children: [
          _totalRow(
            'Total KM',
            '${totalKm.toStringAsFixed(2)} KM',
            background: _lightBlue,
          ),
          _totalRow(
            'Subtotal',
            _money(subtotal),
            background: _lightBlue,
          ),
          _totalRow(
            'CGST (${cgstRate.toStringAsFixed(1)}%)',
            _money(cgstAmount),
          ),
          _totalRow(
            'SGST (${sgstRate.toStringAsFixed(1)}%)',
            _money(sgstAmount),
          ),
          _totalRow(
            'Total Amount',
            _money(totalAmount),
            background: _brandBlue,
            textColor: PdfColors.white,
            bold: true,
          ),
          _totalRow(
            'Advance Paid',
            _money(advancePaid),
            background: _advanceBg,
            textColor: _successText,
            bold: true,
          ),
          _totalRow(
            'Balance Due',
            _money(balanceDue),
            background: _balanceBg,
            textColor: _dangerText,
            bold: true,
            showDivider: false,
          ),
        ],
      ),
    );
  }

  static pw.Widget _totalRow(
    String label,
    String value, {
    PdfColor? background,
    PdfColor textColor = _textDark,
    bool bold = false,
    bool showDivider = true,
  }) {
    return pw.Container(
      padding: const pw.EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: pw.BoxDecoration(
        color: background,
        border: showDivider
            ? const pw.Border(
                bottom: pw.BorderSide(color: _borderColor, width: 0.6),
              )
            : null,
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text(
            label,
            style: pw.TextStyle(
              fontSize: bold ? 12.5 : 11.5,
              color: textColor,
              fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal,
            ),
          ),
          pw.Text(
            value,
            style: pw.TextStyle(
              fontSize: bold ? 12.5 : 11.5,
              color: textColor,
              fontWeight: pw.FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  static pw.Widget _signatureRow() {
    return pw.Row(
      mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
      children: [
        _signatureBox('Authorized Signature (Client)'),
        _signatureBox(
          'Authorized Signature & Stamp',
          captionStrong: 'RG Travel Solution',
        ),
      ],
    );
  }

  static pw.Widget _signatureBox(String label, {String? captionStrong}) {
    return pw.Column(
      children: [
        pw.SizedBox(width: 150, height: 30),
        pw.Container(
          width: 150,
          height: 1,
          color: _textDark,
        ),
        pw.SizedBox(height: 4),
        pw.Text(
          label,
          style: const pw.TextStyle(fontSize: 10.5, color: PdfColors.grey700),
        ),
        if (captionStrong != null)
          pw.Text(
            captionStrong,
            style: pw.TextStyle(
              fontSize: 10.5,
              color: _brandBlue,
              fontWeight: pw.FontWeight.bold,
            ),
          ),
      ],
    );
  }

  static pw.Widget _footer() {
    return pw.Container(
      padding: const pw.EdgeInsets.only(top: 8),
      decoration: const pw.BoxDecoration(
        border: pw.Border(
          top: pw.BorderSide(color: _brandBlue, width: 1.5),
        ),
      ),
      child: pw.Center(
        child: pw.Text(
          'Thank you for trusting RG Travel Solution for your Employee Transportation needs. | 9325118627 | rgtravelsolution@gmail.com',
          style: const pw.TextStyle(fontSize: 10.5, color: PdfColors.grey700),
          textAlign: pw.TextAlign.center,
        ),
      ),
    );
  }

  static String _money(double value) {
    return 'Rs. ${value.toStringAsFixed(2)}';
  }

  static String _fallback(String value, String fallback) {
    final trimmed = value.trim();
    return trimmed.isEmpty ? fallback : trimmed;
  }

  static String _invoiceNumber(DateTime value) {
    final year = value.year.toString();
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    final minuteStamp = value.hour.toString().padLeft(2, '0') +
        value.minute.toString().padLeft(2, '0');
    return 'RGT/$year$month$day/$minuteStamp';
  }

  static String _formatDisplayDate(DateTime value) {
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    final day = value.day.toString().padLeft(2, '0');
    final month = months[value.month - 1];
    return '$day $month ${value.year}';
  }

  static String _formatShortDate(String rawDate) {
    final parsed = DateTime.tryParse(rawDate);
    if (parsed == null) {
      return rawDate;
    }
    final day = parsed.day.toString().padLeft(2, '0');
    final month = parsed.month.toString().padLeft(2, '0');
    final year = parsed.year.toString().padLeft(4, '0');
    return '$day/$month/$year';
  }
}
