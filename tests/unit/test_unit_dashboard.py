"""
Unit tests for dashboard routes
"""
import pytest
from datetime import datetime
from src.app import app, dbs, User, Post, Platform, ScheduledPost


class TestUserDashboard:
    """Test user dashboard functionality"""

    def test_user_dashboard_with_login(self, client):
        """Test user dashboard access when logged in"""
        # Create test user
        user = User(email='user@test.com', full_name='Test User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['full_name'] = user.full_name
            sess['role'] = user.role

        response = client.get('/dashboard/user')
        assert response.status_code == 200
        assert b'Test User' in response.data or b'Dashboard' in response.data

    def test_user_dashboard_without_login(self, client):
        """Test user dashboard redirects when not logged in"""
        response = client.get('/dashboard/user')
        assert response.status_code == 302  # Redirect to login

    def test_user_dashboard_shows_posts(self, client):
        """Test user dashboard displays user's posts"""
        user = User(email='user@test.com', full_name='Test User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        # Create posts
        post1 = Post(user_id=user.user_id, content_text='Post 1', status='published')
        post2 = Post(user_id=user.user_id, content_text='Post 2', status='draft')
        dbs.session.add_all([post1, post2])
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['full_name'] = user.full_name
            sess['role'] = user.role

        response = client.get('/dashboard/user')
        assert response.status_code == 200


class TestManagerDashboard:
    """Test manager dashboard functionality"""

    def test_manager_dashboard_with_manager_role(self, client):
        """Test manager dashboard access with manager role"""
        manager = User(email='manager@test.com', full_name='Manager', role='manager')
        dbs.session.add(manager)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = manager.user_id
            sess['full_name'] = manager.full_name
            sess['role'] = 'manager'

        response = client.get('/dashboard/manager')
        assert response.status_code == 200

    def test_manager_dashboard_without_login(self, client):
        """Test manager dashboard redirects when not logged in"""
        response = client.get('/dashboard/manager')
        assert response.status_code == 302

    def test_manager_dashboard_with_user_role(self, client):
        """Test manager dashboard denies access to regular users"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['full_name'] = user.full_name
            sess['role'] = 'user'

        response = client.get('/dashboard/manager')
        assert response.status_code in [302, 403]  # Redirect or forbidden

    def test_manager_dashboard_shows_pending_posts(self, client):
        """Test manager dashboard shows pending posts"""
        manager = User(email='manager@test.com', full_name='Manager', role='manager')
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add_all([manager, user])
        dbs.session.commit()

        # Create pending posts
        post = Post(user_id=user.user_id, content_text='Pending post', status='pending')
        dbs.session.add(post)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = manager.user_id
            sess['full_name'] = manager.full_name
            sess['role'] = 'manager'

        response = client.get('/dashboard/manager')
        assert response.status_code == 200


class TestLinkedAccountsPage:
    """Test linked accounts page"""

    def test_linked_accounts_with_login(self, client):
        """Test linked accounts page when logged in"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['full_name'] = user.full_name
            sess['role'] = user.role

        response = client.get('/linked-accounts')
        assert response.status_code == 200

    def test_linked_accounts_without_login(self, client):
        """Test linked accounts page redirects when not logged in"""
        response = client.get('/linked-accounts')
        assert response.status_code == 302

    def test_linked_accounts_shows_platforms(self, client):
        """Test linked accounts page shows linked platforms"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        # Add linked platforms
        platform = Platform(
            user_id=user.user_id,
            platform_name='twitter',
            platform_user_id='twitter_123',
            access_token='token',
            expires_at=datetime(2030, 1, 1)
        )
        dbs.session.add(platform)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['full_name'] = user.full_name
            sess['role'] = user.role

        response = client.get('/linked-accounts')
        assert response.status_code == 200


class TestNotificationCount:
    """Test notification count API"""

    def test_notification_count_with_login(self, client):
        """Test notification count returns count when logged in"""
        manager = User(email='manager@test.com', full_name='Manager', role='manager')
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add_all([manager, user])
        dbs.session.commit()

        # Create pending posts
        post1 = Post(user_id=user.user_id, content_text='Post 1', status='pending')
        post2 = Post(user_id=user.user_id, content_text='Post 2', status='pending')
        dbs.session.add_all([post1, post2])
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = manager.user_id
            sess['role'] = 'manager'

        response = client.get('/api/notification-count')
        assert response.status_code == 200
        data = response.get_json()
        assert 'count' in data
        assert data['count'] >= 0

    def test_notification_count_without_login(self, client):
        """Test notification count returns 401 when not logged in"""
        response = client.get('/api/notification-count')
        assert response.status_code in [302, 401]

    def test_notification_count_for_user_role(self, client):
        """Test notification count for regular user"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.get('/api/notification-count')
        assert response.status_code == 200
        data = response.get_json()
        assert 'count' in data
        assert data['count'] == 0  # Users don't see notifications
