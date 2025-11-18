"""
Notification Helper - Sends events to the notification microservice
"""
import requests

NOTIFICATION_SERVICE_URL = "http://127.0.0.1:5001"

def _send_notification(payload):
    """Send notification to the notification microservice"""
    print(f"🔔 SENDING NOTIFICATION: {payload}")
    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/api/events/publish",
            json=payload,
            timeout=5
        )
        if response.status_code == 201:
            print(f"✅ Notification sent successfully: {payload.get('status', 'unknown')}")
            return True
        else:
            print(f"⚠️ Notification service returned {response.status_code}: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"⚠️ Cannot connect to notification service at {NOTIFICATION_SERVICE_URL}")
        return False
    except Exception as e:
        print(f"⚠️ Error sending notification: {e}")
        return False


def notify_post_created(user_id, post_id, status="draft"):
    """Notify when a post is created"""
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": status,
        "notification_type": "system"
    })


def notify_post_published(user_id, post_id, platform, success=True, error_msg=""):
    """Notify when a post is published or fails"""
    status = "published" if success else "failed"
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": status,
        "platform": platform,
        "error_message": error_msg if not success else "",
        "notification_type": "system"
    })


def send_publish_notification(user_id, platform, post_id, published_at=None):
    """
    Send a publish notification with timestamp support.
    This is the new format that includes proper timestamp handling.
    """
    payload = {
        "user_id": user_id,
        "post_id": post_id,
        "status": "published",
        "platform": platform,
        "notification_type": "system"
    }
    
    # Add timestamp if provided
    if published_at:
        payload["published_at"] = str(published_at)
    
    return _send_notification(payload)


def notify_post_scheduled(user_id, post_id, scheduled_time):
    """Notify when a post is scheduled"""
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": "scheduled",
        "scheduled_time": str(scheduled_time),
        "notification_type": "system"
    })


def notify_post_deleted(user_id, post_id):
    """Notify when a post is deleted"""
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": "deleted",
        "notification_type": "system"
    })


def notify_post_edited(user_id, post_id):
    """Notify when a post is edited"""
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": "edited",
        "notification_type": "system"
    })


def notify_account_linked(user_id, platform_name):
    """Notify when a social account is linked"""
    return _send_notification({
        "user_id": user_id,
        "status": "account_linked",
        "platform": platform_name,
        "notification_type": "system"
    })


def notify_account_unlinked(user_id, platform_name):
    """Notify when a social account is unlinked"""
    return _send_notification({
        "user_id": user_id,
        "status": "account_unlinked",
        "platform": platform_name,
        "notification_type": "system"
    })


def notify_approval_request(manager_user_id, post_id, requester_name):
    """Notify manager of new approval request"""
    return _send_notification({
        "user_id": manager_user_id,
        "post_id": post_id,
        "status": "approval_request",
        "requester_name": requester_name,
        "notification_type": "team"
    })


def notify_post_approved(user_id, post_id, approver_name="Manager"):
    """Notify user their post was approved"""
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": "approved",
        "approver_name": approver_name,
        "notification_type": "team"
    })


def notify_post_rejected(user_id, post_id, reason="", approver_name="Manager"):
    """Notify user their post was rejected"""
    return _send_notification({
        "user_id": user_id,
        "post_id": post_id,
        "status": "rejected",
        "reason": reason,
        "approver_name": approver_name,
        "notification_type": "team"
    })
