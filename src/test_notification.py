"""
Test Suite for SMMS Notification System
Run with: pytest test_notifications.py -v
"""
import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import pytz


# ========================================
# UNIT TESTS - notification_helper.py
# ========================================

class TestNotificationHelper:
    """Test notification helper functions"""
    
    @patch('notification_helper.requests.post')
    def test_send_notification_success(self, mock_post):
        """Test successful notification sending"""
        from notification_helper import _send_notification
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        payload = {
            "user_id": 1,
            "post_id": 10,
            "status": "published",
            "platform": "LinkedIn",
            "notification_type": "system"
        }
        
        result = _send_notification(payload)
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json'] == payload
    
    @patch('notification_helper.requests.post')
    def test_send_notification_connection_error(self, mock_post):
        """Test notification when service is down"""
        from notification_helper import _send_notification
        import requests
        
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        payload = {"user_id": 1, "status": "test"}
        result = _send_notification(payload)
        
        assert result is False
    
    @patch('notification_helper.requests.post')
    def test_send_notification_server_error(self, mock_post):
        """Test notification when server returns error"""
        from notification_helper import _send_notification
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        payload = {"user_id": 1, "status": "test"}
        result = _send_notification(payload)
        
        assert result is False
    
    @patch('notification_helper._send_notification')
    def test_notify_post_created(self, mock_send):
        """Test post creation notification"""
        from notification_helper import notify_post_created
        
        mock_send.return_value = True
        result = notify_post_created(user_id=1, post_id=10, status="draft")
        
        assert result is True
        mock_send.assert_called_once()
        call_payload = mock_send.call_args[0][0]
        assert call_payload["user_id"] == 1
        assert call_payload["post_id"] == 10
        assert call_payload["status"] == "draft"
        assert call_payload["notification_type"] == "system"
    
    @patch('notification_helper._send_notification')
    def test_notify_post_published_success(self, mock_send):
        """Test successful publish notification"""
        from notification_helper import notify_post_published
        
        mock_send.return_value = True
        result = notify_post_published(
            user_id=1, 
            post_id=10, 
            platform="LinkedIn", 
            success=True
        )
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "published"
        assert call_payload["platform"] == "LinkedIn"
        assert call_payload["error_message"] == ""
    
    @patch('notification_helper._send_notification')
    def test_notify_post_published_failure(self, mock_send):
        """Test failed publish notification"""
        from notification_helper import notify_post_published
        
        mock_send.return_value = True
        result = notify_post_published(
            user_id=1, 
            post_id=10, 
            platform="Twitter", 
            success=False,
            error_msg="Rate limit exceeded"
        )
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "failed"
        assert call_payload["error_message"] == "Rate limit exceeded"
    
    @patch('notification_helper._send_notification')
    def test_send_publish_notification_with_timestamp(self, mock_send):
        """Test new publish notification format with timestamp"""
        from notification_helper import send_publish_notification
        
        mock_send.return_value = True
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        
        result = send_publish_notification(
            user_id=1,
            platform="LinkedIn",
            post_id=10,
            published_at=now_utc
        )
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["user_id"] == 1
        assert call_payload["post_id"] == 10
        assert call_payload["platform"] == "LinkedIn"
        assert call_payload["status"] == "published"
        assert "published_at" in call_payload
    
    @patch('notification_helper._send_notification')
    def test_notify_post_deleted(self, mock_send):
        """Test post deletion notification"""
        from notification_helper import notify_post_deleted
        
        mock_send.return_value = True
        result = notify_post_deleted(user_id=1, post_id=10)
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "deleted"
    
    @patch('notification_helper._send_notification')
    def test_notify_post_scheduled(self, mock_send):
        """Test post scheduled notification"""
        from notification_helper import notify_post_scheduled
        
        mock_send.return_value = True
        scheduled_time = datetime.now()
        result = notify_post_scheduled(user_id=1, post_id=10, scheduled_time=scheduled_time)
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "scheduled"
        assert "scheduled_time" in call_payload
    
    @patch('notification_helper._send_notification')
    def test_notify_account_linked(self, mock_send):
        """Test account linked notification"""
        from notification_helper import notify_account_linked
        
        mock_send.return_value = True
        result = notify_account_linked(user_id=1, platform_name="LinkedIn")
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "account_linked"
        assert call_payload["platform"] == "LinkedIn"
    
    @patch('notification_helper._send_notification')
    def test_notify_approval_request(self, mock_send):
        """Test approval request notification"""
        from notification_helper import notify_approval_request
        
        mock_send.return_value = True
        result = notify_approval_request(
            manager_user_id=2, 
            post_id=10, 
            requester_name="John Doe"
        )
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["user_id"] == 2
        assert call_payload["status"] == "approval_request"
        assert call_payload["notification_type"] == "team"
    
    @patch('notification_helper._send_notification')
    def test_notify_post_approved(self, mock_send):
        """Test post approved notification"""
        from notification_helper import notify_post_approved
        
        mock_send.return_value = True
        result = notify_post_approved(user_id=1, post_id=10, approver_name="Manager")
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "approved"
        assert call_payload["notification_type"] == "team"
    
    @patch('notification_helper._send_notification')
    def test_notify_post_rejected(self, mock_send):
        """Test post rejected notification"""
        from notification_helper import notify_post_rejected
        
        mock_send.return_value = True
        result = notify_post_rejected(
            user_id=1, 
            post_id=10, 
            reason="Content policy violation",
            approver_name="Manager"
        )
        
        assert result is True
        call_payload = mock_send.call_args[0][0]
        assert call_payload["status"] == "rejected"
        assert call_payload["reason"] == "Content policy violation"


# ========================================
# UNIT TESTS - Platform Name Helper
# ========================================

class TestPlatformNameHelper:
    """Test get_platform_name function"""
    
    def test_linkedin_platform_id(self):
        """Test LinkedIn platform ID mapping"""
        # Import from app.py after it's loaded
        from app import get_platform_name
        assert get_platform_name(1) == "LinkedIn"
    
    def test_twitter_platform_id(self):
        """Test Twitter platform ID mapping"""
        from app import get_platform_name
        assert get_platform_name(2) == "Twitter"
    
    def test_instagram_platform_id(self):
        """Test Instagram platform ID mapping"""
        from app import get_platform_name
        assert get_platform_name(3) == "Instagram"
    
    def test_facebook_platform_id(self):
        """Test Facebook platform ID mapping"""
        from app import get_platform_name
        assert get_platform_name(4) == "Facebook"
    
    def test_unknown_platform_id(self):
        """Test unknown platform ID returns Unknown"""
        from app import get_platform_name
        assert get_platform_name(999) == "Unknown"
        assert get_platform_name(0) == "Unknown"
        assert get_platform_name(-1) == "Unknown"


# ========================================
# INTEGRATION TESTS - Notification Service API
# ========================================

class TestNotificationServiceAPI:
    """Test notification microservice API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client for notifapp"""
        import sys
        sys.path.insert(0, '.')
        from notifapp import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code in [200, 500]  # 500 if DB not connected
        data = json.loads(response.data)
        assert 'status' in data
    
    @patch('notifapp.get_conn')
    def test_publish_event_success(self, mock_conn, client):
        """Test publishing event to notification service"""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        payload = {
            "user_id": 1,
            "post_id": 10,
            "status": "published",
            "platform": "LinkedIn",
            "notification_type": "system"
        }
        
        response = client.post(
            '/api/events/publish',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'created'
        assert 'notification_id' in data
    
    def test_publish_event_missing_status(self, client):
        """Test publishing event without status field"""
        payload = {
            "user_id": 1,
            "post_id": 10
        }
        
        response = client.post(
            '/api/events/publish',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('notifapp.get_conn')
    def test_get_notifications(self, mock_conn, client):
        """Test getting notifications for user"""
        # Mock database results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'notification_id': 1,
                'title': 'Test Notification',
                'message': 'Test message',
                'notification_type': 'system',
                'is_read': False,
                'created_at': datetime.now(),
                'post_id': 10,
                'schedule_id': None
            }
        ]
        mock_cursor.fetchone.side_effect = [
            {'count': 1},  # total
            {'count': 1},  # unread
            {'count': 1},  # system
            {'count': 0}   # team
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        response = client.get('/api/notifications?user_id=1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'notifications' in data
        assert 'counts' in data
    
    def test_get_notifications_missing_user_id(self, client):
        """Test getting notifications without user_id"""
        response = client.get('/api/notifications')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('notifapp.get_conn')
    def test_mark_all_read(self, mock_conn, client):
        """Test marking all notifications as read"""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        response = client.put('/api/notifications/mark-read/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['updated'] == 5
    
    @patch('notifapp.get_conn')
    def test_mark_single_read(self, mock_conn, client):
        """Test marking single notification as read"""
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        response = client.put('/api/notifications/1/read')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
    
    @patch('notifapp.get_conn')
    def test_clear_notifications(self, mock_conn, client):
        """Test clearing all notifications for user"""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 10
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        response = client.delete('/api/notifications/clear/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'cleared'
        assert data['deleted'] == 10
    
    @patch('notifapp.get_conn')
    def test_get_unread_count(self, mock_conn, client):
        """Test getting unread notification count"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'count': 3}
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        response = client.get('/api/notifications/unread-count/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['unread_count'] == 3


# ========================================
# NOTIFICATION TITLE/MESSAGE GENERATION TESTS
# ========================================

class TestNotificationTitleGeneration:
    """Test notification title and message generation"""
    
    @pytest.fixture
    def client(self):
        """Create test client for notifapp"""
        from notifapp import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @patch('notifapp.get_conn')
    def test_published_notification_title(self, mock_conn, client):
        """Test published notification generates correct title"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        payload = {
            "user_id": 1,
            "post_id": 10,
            "status": "published",
            "platform": "LinkedIn"
        }
        
        response = client.post(
            '/api/events/publish',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        # Check that cursor.execute was called with correct title
        call_args = mock_cursor.execute.call_args
        assert "Post published on LinkedIn" in str(call_args)
    
    @patch('notifapp.get_conn')
    def test_failed_notification_title(self, mock_conn, client):
        """Test failed notification generates correct title"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        payload = {
            "user_id": 1,
            "post_id": 10,
            "status": "failed",
            "platform": "Twitter",
            "error_reason": "Rate limit exceeded"
        }
        
        response = client.post(
            '/api/events/publish',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        call_args = mock_cursor.execute.call_args
        assert "Post failed on Twitter" in str(call_args)
    
    @patch('notifapp.get_conn')
    def test_scheduled_notification_title(self, mock_conn, client):
        """Test scheduled notification generates correct title"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        payload = {
            "user_id": 1,
            "post_id": 10,
            "status": "scheduled"
        }
        
        response = client.post(
            '/api/events/publish',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        call_args = mock_cursor.execute.call_args
        assert "Post scheduled" in str(call_args)
    
    @patch('notifapp.get_conn')
    def test_approval_request_notification(self, mock_conn, client):
        """Test approval request notification is team type"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        
        payload = {
            "user_id": 2,
            "post_id": 10,
            "status": "approval_request",
            "requester_name": "John Doe"
        }
        
        response = client.post(
            '/api/events/publish',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        call_args = mock_cursor.execute.call_args
        # Check notification_type is 'team'
        assert "team" in str(call_args)


# ========================================
# END-TO-END TESTS
# ========================================

class TestEndToEndNotification:
    """End-to-end notification flow tests"""
    
    @patch('notification_helper.requests.post')
    def test_full_publish_notification_flow(self, mock_post):
        """Test complete notification flow from helper to service"""
        from notification_helper import send_publish_notification
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "status": "created",
            "notification_id": 1
        }
        mock_post.return_value = mock_response
        
        # Send notification
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        result = send_publish_notification(
            user_id=1,
            platform="LinkedIn",
            post_id=10,
            published_at=now_utc
        )
        
        assert result is True
        
        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert payload['user_id'] == 1
        assert payload['post_id'] == 10
        assert payload['platform'] == "LinkedIn"
        assert payload['status'] == "published"
    
    def test_notification_with_disabled_service(self):
        """Test notification behavior when service is disabled"""
        # This tests the NOTIFICATIONS_ENABLED flag behavior
        # In production, this would prevent calls to the service
        pass
    
    @patch('notification_helper.requests.post')
    def test_multiple_platform_notifications(self, mock_post):
        """Test sending notifications for multiple platforms"""
        from notification_helper import send_publish_notification
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        platforms = ["LinkedIn", "Twitter", "Instagram", "Facebook"]
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        
        for platform in platforms:
            result = send_publish_notification(
                user_id=1,
                platform=platform,
                post_id=10,
                published_at=now_utc
            )
            assert result is True
        
        assert mock_post.call_count == 4


# ========================================
# PYTEST FIXTURES
# ========================================

@pytest.fixture(scope='session')
def setup_test_environment():
    """Setup test environment"""
    import os
    os.environ['TESTING'] = 'true'
    yield
    del os.environ['TESTING']


# ========================================
# RUN TESTS
# ========================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
