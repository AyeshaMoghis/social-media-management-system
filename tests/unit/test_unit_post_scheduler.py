"""
Unit tests for Post Scheduler functionality
"""
import pytest
from datetime import datetime, timedelta
from src.app import app, dbs, Post, PostPlatform, ScheduledPost, Platform, User
from werkzeug.datastructures import FileStorage
import io
import os


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['UPLOAD_FOLDER'] = 'test_uploads'

    with app.test_client() as client:
        dbs.create_all()

        # Create test user
        test_user = User(
            email='testuser@example.com',
            full_name='Test User',
            role='user'
        )
        dbs.session.add(test_user)

        # Create test platform
        test_platform = Platform(
            platform_name='Twitter',
            is_active=True
        )
        dbs.session.add(test_platform)

        dbs.session.commit()

        yield client

        dbs.drop_all()

    # Cleanup test uploads folder
    if os.path.exists('test_uploads'):
        import shutil
        shutil.rmtree('test_uploads')


class TestPostModel:
    """Test Post model"""

    def test_post_creation(self, client):
        """Test creating a post"""
        user = User.query.first()
        post = Post(
            user_id=user.user_id,
            content_text='Test post content',
            status='draft'
        )
        dbs.session.add(post)
        dbs.session.commit()

        assert post.post_id is not None
        assert post.content_text == 'Test post content'
        assert post.status == 'draft'
        assert post.created_at is not None

    def test_post_default_status(self, client):
        """Test post default status is draft"""
        user = User.query.first()
        post = Post(
            user_id=user.user_id,
            content_text='Test post'
        )
        dbs.session.add(post)
        dbs.session.commit()

        assert post.status == 'draft'


class TestPostPlatformModel:
    """Test PostPlatform model"""

    def test_post_platform_creation(self, client):
        """Test linking post to platform"""
        user = User.query.first()
        platform = Platform.query.first()

        post = Post(
            user_id=user.user_id,
            content_text='Test post',
            status='draft'
        )
        dbs.session.add(post)
        dbs.session.flush()

        post_platform = PostPlatform(
            post_id=post.post_id,
            platform_id=platform.platform_id
        )
        dbs.session.add(post_platform)
        dbs.session.commit()

        assert post_platform.post_id == post.post_id
        assert post_platform.platform_id == platform.platform_id
        assert post_platform.published is False


class TestScheduledPostModel:
    """Test ScheduledPost model"""

    def test_scheduled_post_creation(self, client):
        """Test creating a scheduled post"""
        user = User.query.first()
        platform = Platform.query.first()

        post = Post(
            user_id=user.user_id,
            content_text='Scheduled post',
            status='scheduled'
        )
        dbs.session.add(post)
        dbs.session.flush()

        future_time = datetime.now() + timedelta(hours=2)
        scheduled_post = ScheduledPost(
            post_id=post.post_id,
            platform_id=platform.platform_id,
            scheduled_time=future_time
        )
        dbs.session.add(scheduled_post)
        dbs.session.commit()

        assert scheduled_post.scheduled_time == future_time
        assert scheduled_post.status == 'scheduled'


class TestPostSchedulerRoutes:
    """Test Post Scheduler routes"""

    def test_post_scheduler_page_requires_login(self, client):
        """Test post scheduler page requires login"""
        response = client.get('/post-scheduler')
        assert response.status_code == 302  # Redirect to login

    def test_post_scheduler_page_with_login(self, client):
        """Test post scheduler page with logged in user"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'

        response = client.get('/post-scheduler')
        assert response.status_code == 200

    def test_get_posts_requires_login(self, client):
        """Test GET /api/posts requires login"""
        response = client.get('/api/posts')
        assert response.status_code == 401
        assert b'Unauthorized' in response.data

    def test_get_posts_with_login(self, client):
        """Test GET /api/posts with logged in user"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1

        response = client.get('/api/posts')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_create_post_requires_login(self, client):
        """Test POST /api/posts requires login"""
        response = client.post('/api/posts', data={'text': 'Test post'})
        assert response.status_code == 401

    def test_create_post_missing_content(self, client):
        """Test creating post without text or media fails"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1

        response = client.post('/api/posts', data={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_draft_post(self, client):
        """Test creating a draft post"""
        platform = Platform.query.first()

        with client.session_transaction() as sess:
            sess['user_id'] = 1

        response = client.post('/api/posts', data={
            'text': 'Test draft post',
            'account_ids[]': [platform.platform_id],
            'status': 'draft'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'post_id' in data
        assert data['message'] == 'Post created successfully'

        # Verify in database
        post = Post.query.get(data['post_id'])
        assert post.content_text == 'Test draft post'
        assert post.status == 'draft'

    def test_create_scheduled_post(self, client):
        """Test creating a scheduled post"""
        platform = Platform.query.first()
        future_time = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')

        with client.session_transaction() as sess:
            sess['user_id'] = 1

        response = client.post('/api/posts', data={
            'text': 'Test scheduled post',
            'account_ids[]': [platform.platform_id],
            'status': 'scheduled',
            'scheduled_time': future_time
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'post_id' in data

        # Verify in database
        post = Post.query.get(data['post_id'])
        assert post.status == 'scheduled'

        scheduled = ScheduledPost.query.filter_by(post_id=post.post_id).first()
        assert scheduled is not None

    def test_update_post_requires_login(self, client):
        """Test PUT /api/posts/<id> requires login"""
        response = client.put('/api/posts/1', data={'text': 'Updated'})
        assert response.status_code == 401

    def test_update_nonexistent_post(self, client):
        """Test updating nonexistent post returns 404"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1

        response = client.put('/api/posts/9999', data={'text': 'Updated'})
        assert response.status_code == 404

    def test_delete_post_requires_login(self, client):
        """Test DELETE /api/posts/<id> requires login"""
        response = client.delete('/api/posts/1')
        assert response.status_code == 401

    def test_delete_nonexistent_post(self, client):
        """Test deleting nonexistent post returns 404"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1

        response = client.delete('/api/posts/9999')
        assert response.status_code == 404


class TestHelperFunctions:
    """Test helper functions"""

    def test_allowed_file_valid_extensions(self, client):
        """Test allowed_file with valid extensions"""
        from src.app import allowed_file

        assert allowed_file('image.png') is True
        assert allowed_file('photo.jpg') is True
        assert allowed_file('video.mp4') is True
        assert allowed_file('test.jpeg') is True

    def test_allowed_file_invalid_extensions(self, client):
        """Test allowed_file with invalid extensions"""
        from src.app import allowed_file

        assert allowed_file('document.pdf') is False
        assert allowed_file('script.exe') is False
        assert allowed_file('noextension') is False

    def test_get_file_type(self, client):
        """Test get_file_type function"""
        from src.app import get_file_type

        assert get_file_type('image.png') == 'image'
        assert get_file_type('photo.jpg') == 'image'
        assert get_file_type('video.mp4') == 'video'
        assert get_file_type('movie.avi') == 'video'
        assert get_file_type('unknown.txt') == 'unknown'
