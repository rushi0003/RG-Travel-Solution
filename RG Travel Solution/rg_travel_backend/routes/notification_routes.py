from flask import Blueprint, request, jsonify
from services.notification_service import NotificationService

notification_bp = Blueprint('notification', __name__, url_prefix='/api/notifications')

@notification_bp.route('/', methods=['GET'])
def get_notifications():
    """
    Get notifications for the calling admin.
    Query params: admin_id (str), limit (int, default 50), offset (int, default 0)
    """
    try:
        # In a real app the admin_id would come from the JWT token.
        # For simplicity, we accept it as a parameter for now.
        admin_id = request.args.get('admin_id')
        if not admin_id:
            return jsonify({"success": False, "message": "Admin ID required"}), 400

        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        notifications = NotificationService.get_notifications(admin_id, limit, offset)
        unread_count = NotificationService.get_unread_count(admin_id) # Optional

        return jsonify({
            "success": True,
            "data": {
                "notifications": notifications,
                "unread_count": unread_count
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@notification_bp.route('/<int:notification_id>/read', methods=['POST'])
def mark_read(notification_id):
    """
    Mark a specific notification as read.
    Body: {"admin_id": "..."}
    """
    try:
        data = request.json or {}
        admin_id = data.get('admin_id')
        if not admin_id:
            return jsonify({"success": False, "message": "Admin ID required"}), 400

        updated = NotificationService.mark_as_read(notification_id, admin_id)
        if updated:
            return jsonify({"success": True, "message": "Marked read"}), 200
        else:
            return jsonify({"success": False, "message": "Notification not found or already read"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@notification_bp.route('/read-all', methods=['POST'])
def mark_all_read():
    """
    Mark all notifications for an admin as read.
    Body: {"admin_id": "..."}
    """
    try:
        data = request.json or {}
        admin_id = data.get('admin_id')
        if not admin_id:
            return jsonify({"success": False, "message": "Admin ID required"}), 400

        success = NotificationService.mark_all_read(admin_id)
        if success:
            return jsonify({"success": True, "message": "All notifications marked read"}), 200
        else:
            return jsonify({"success": False, "message": "Failed to mark all read"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
