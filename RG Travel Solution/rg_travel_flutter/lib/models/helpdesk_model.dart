class HelpdeskTicket {
  final int id;
  final String userId;
  final String userType;
  final String userName; // enriched by backend join
  final String subject;
  final String message;
  final String priority;
  final String status;
  final String? adminNotes;
  final String? resolvedBy;
  final String? resolvedAt;
  final String createdAt;

  HelpdeskTicket({
    required this.id,
    required this.userId,
    required this.userType,
    required this.userName,
    required this.subject,
    required this.message,
    required this.priority,
    required this.status,
    this.adminNotes,
    this.resolvedBy,
    this.resolvedAt,
    required this.createdAt,
  });

  factory HelpdeskTicket.fromJson(Map<String, dynamic> json) {
    return HelpdeskTicket(
      id: (json['id'] is int ? json['id'] : int.tryParse(json['id'].toString())) as int? ?? 0,
      // Warning fix: `toString()` is never null, so removing the dead fallback preserves behavior.
      userId: (json['user_id'] as dynamic).toString(),
      userType: (json['user_type'] as String?) ?? '',
      userName: (json['user_name'] as String?) ?? 'Unknown',
      subject: (json['subject'] as String?) ?? '',
      message: (json['message'] as String?) ?? '',
      priority: (json['priority'] as String?) ?? 'normal',
      status: (json['status'] as String?) ?? 'open',
      adminNotes: json['admin_notes'] as String?,
      resolvedBy: json['resolved_by'] as String?,
      resolvedAt: json['resolved_at'] as String?,
      createdAt: (json['created_at'] as String?) ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'user_type': userType,
    'user_name': userName,
    'subject': subject,
    'message': message,
    'priority': priority,
    'status': status,
    'admin_notes': adminNotes,
    'resolved_by': resolvedBy,
    'resolved_at': resolvedAt,
    'created_at': createdAt,
  };
}
