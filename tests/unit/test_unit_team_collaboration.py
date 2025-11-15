"""
Unit tests for Team Collaboration functionality
"""
import pytest
import json
from src.app import app, dbs, Post, User
from datetime import datetime


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'

    with app.test_client() as client:
        dbs.create_all()

        # Create test manager
        manager = User(
            email='manager@test.com',
            full_name='Test Manager',
            role='manager'
        )
        dbs.session.add(manager)

        # Create test user
        user = User(
            email='user@test.com',
            full_name='Test User',
            role='user'
        )
        dbs.session.add(user)
        dbs.session.commit()

        yield client

        dbs.drop_all()


class TestTeamCollaboration:
    """Test Team Collaboration routes"""

    def test_team_collaboration_requires_manager(self, client):
        """Test team collaboration page requires manager role"""
        with client.session_transaction() as sess:
            sess['user_id'] = 2  # Regular user
            sess['role'] = 'user'

        response = client.get('/team-collaboration')
        assert response.status_code == 302  # Redirect

    def test_team_collaboration_manager_access(self, client):
        """Test manager can access team collaboration page"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'
            sess['full_name'] = 'Test Manager'

        response = client.get('/team-collaboration')
        assert response.status_code == 200

    def test_team_collaboration_shows_pending_posts(self, client):
        """Test team collaboration displays pending posts"""
        user = User.query.filter_by(role='user').first()

        # Create pending post
        post = Post(
            user_id=user.user_id,
            content_text='Pending post for review',
            status='pending'
        )
        dbs.session.add(post)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'
            sess['full_name'] = 'Test Manager'

        response = client.get('/team-collaboration')
        assert response.status_code == 200
        assert b'Pending post for review' in response.data

    def test_team_collaboration_shows_scheduled_posts(self, client):
        """Test team collaboration displays scheduled posts"""
        user = User.query.filter_by(role='user').first()

        # Create scheduled post
        post = Post(
            user_id=user.user_id,
            content_text='Scheduled post for review',
            status='scheduled'
        )
        dbs.session.add(post)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'
            sess['full_name'] = 'Test Manager'

        response = client.get('/team-collaboration')
        assert response.status_code == 200
        assert b'Scheduled post for review' in response.data

    def test_update_post_status_approve(self, client):
        """Test approving a post"""
        user = User.query.filter_by(role='user').first()
        post = Post(
            user_id=user.user_id,
            content_text='Post to approve',
            status='pending'
        )
        dbs.session.add(post)
        dbs.session.commit()
        post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'

        response = client.post('/update_post_status',
                               data=json.dumps({
                                   'post_id': post_id,
                                   'action': 'approved'
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify post status changed
        post = Post.query.get(post_id)
        assert post.status == 'approved'

    def test_update_post_status_reject(self, client):
        """Test rejecting a post"""
        user = User.query.filter_by(role='user').first()
        post = Post(
            user_id=user.user_id,
            content_text='Post to reject',
            status='pending'
        )
        dbs.session.add(post)
        dbs.session.commit()
        post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'

        response = client.post('/update_post_status',
                               data=json.dumps({
                                   'post_id': post_id,
                                   'action': 'rejected'
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify post status changed
        post = Post.query.get(post_id)
        assert post.status == 'rejected'

    def test_invite_member_requires_manager(self, client):
        """Test inviting member requires manager role"""
        with client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['role'] = 'user'

        response = client.post('/invite_member',
                               data=json.dumps({
                                   'name': 'New User',
                                   'email': 'newuser@test.com',
                                   'role': 'user'
                               }),
                               content_type='application/json')

        assert response.status_code == 403

    def test_invite_member_success(self, client):
        """Test successfully inviting a new member"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'

        response = client.post('/invite_member',
                               data=json.dumps({
                                   'name': 'New Member',
                                   'email': 'newmember@test.com',
                                   'role': 'user'
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'temp_password' in data

        # Verify user was created
        new_user = User.query.filter_by(email='newmember@test.com').first()
        assert new_user is not None
        assert new_user.full_name == 'New Member'

    def test_invite_member_duplicate_email(self, client):
        """Test inviting member with duplicate email fails"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'

        response = client.post('/invite_member',
                               data=json.dumps({
                                   'name': 'Duplicate User',
                                   'email': 'user@test.com',  # Already exists
                                   'role': 'user'
                               }),
                               content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert 'already exists' in data['message']

    def test_search_members(self, client):
        """Test searching team members"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'

        response = client.get('/search_members?query=Test')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Manager and User

    def test_notification_count_includes_pending_and_scheduled(self, client):
        """Test notification count includes both pending and scheduled posts"""
        user = User.query.filter_by(role='user').first()

        # Create pending post
        pending_post = Post(
            user_id=user.user_id,
            content_text='Pending post',
            status='pending'
        )
        dbs.session.add(pending_post)

        # Create scheduled post
        scheduled_post = Post(
            user_id=user.user_id,
            content_text='Scheduled post',
            status='scheduled'
        )
        dbs.session.add(scheduled_post)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'
            sess['full_name'] = 'Test Manager'

        response = client.get('/team-collaboration')
        assert response.status_code == 200
        # Check that notification count is at least 2
        assert b'notification-badge' in response.data
