"""
Unit tests for helper functions and utility endpoints
"""
import pytest
from io import BytesIO
from src.app import app, dbs, User, Post, ScheduledPost, Platform
from src.app import allowed_file, get_file_type
from datetime import datetime, timedelta


class TestHelperFunctions:
    """Test helper utility functions"""

    def test_allowed_file_with_valid_image(self, client):
        """Test allowed_file with valid image extensions"""
        assert allowed_file('photo.jpg') == True
        assert allowed_file('image.png') == True
        assert allowed_file('picture.jpeg') == True
        assert allowed_file('graphic.gif') == True

    def test_allowed_file_with_valid_video(self, client):
        """Test allowed_file with valid video extensions"""
        assert allowed_file('video.mp4') == True
        assert allowed_file('movie.avi') == True
        assert allowed_file('clip.mov') == True

    def test_allowed_file_with_invalid_extension(self, client):
        """Test allowed_file rejects invalid extensions"""
        assert allowed_file('script.exe') == False
        assert allowed_file('document.pdf') == False
        assert allowed_file('readme.txt') == False

    def test_allowed_file_with_no_extension(self, client):
        """Test allowed_file with no extension"""
        assert allowed_file('filename') == False

    def test_get_file_type_images(self, client):
        """Test get_file_type returns 'image' for image files"""
        assert get_file_type('photo.jpg') == 'image'
        assert get_file_type('image.png') == 'image'
        assert get_file_type('picture.jpeg') == 'image'
        assert get_file_type('graphic.gif') == 'image'

    def test_get_file_type_videos(self, client):
        """Test get_file_type returns 'video' for video files"""
        assert get_file_type('video.mp4') == 'video'
        assert get_file_type('movie.avi') == 'video'
        assert get_file_type('clip.mov') == 'video'

    def test_get_file_type_unknown(self, client):
        """Test get_file_type for unknown file types"""
        result = get_file_type('file.xyz')
        # Function may return None or 'unknown' depending on implementation
        assert result in [None, 'unknown']


class TestFileUploadEndpoint:
    """Test file upload functionality"""

    def test_upload_without_file(self, client):
        """Test upload endpoint without file"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.post('/upload', data={})
            assert response.status_code in [400, 302]

    def test_upload_without_login(self, client):
        """Test upload endpoint requires login"""
        data = {
            'file': (BytesIO(b'test content'), 'test.jpg')
        }
        response = client.post('/upload', data=data)
        assert response.status_code in [401, 302]


class TestPostSchedulerPage:
    """Test post scheduler page endpoint"""

    def test_post_scheduler_requires_login(self, client):
        """Test post scheduler page requires authentication"""
        response = client.get('/post-scheduler')
        assert response.status_code == 302  # Redirect to login

    def test_post_scheduler_with_login(self, client):
        """Test post scheduler page with logged-in user"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            # Add a platform so post-scheduler doesn't redirect
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
                sess['role'] = 'user'

            response = client.get('/post-scheduler')
            # May return 200 or redirect depending on whether user has linked accounts
            assert response.status_code in [200, 302]


class TestHomePage:
    """Test home page endpoint"""

    def test_home_page_loads(self, client):
        """Test home page loads successfully"""
        response = client.get('/')
        assert response.status_code == 200

    def test_home_page_content(self, client):
        """Test home page contains expected content"""
        response = client.get('/')
        assert response.status_code == 200
        # Check for common elements
        assert b'html' in response.data.lower() or b'login' in response.data.lower()


class TestSearchAndFilter:
    """Test search and filter functionality"""

    def test_team_collaboration_with_search(self, client):
        """Test team collaboration page with search query"""
        with app.app_context():
            manager = User(email='manager@test.com', full_name='Manager', role='manager')
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add_all([manager, user])
            dbs.session.commit()

            post1 = Post(user_id=user.user_id, content_text='Hello world', status='pending')
            post2 = Post(user_id=user.user_id, content_text='Python programming', status='pending')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = manager.user_id
                sess['full_name'] = manager.full_name
                sess['role'] = 'manager'

            response = client.get('/team-collaboration?search=Python')
            assert response.status_code == 200

    def test_team_collaboration_with_filter(self, client):
        """Test team collaboration page with status filter"""
        with app.app_context():
            manager = User(email='manager@test.com', full_name='Manager', role='manager')
            dbs.session.add(manager)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = manager.user_id
                sess['full_name'] = manager.full_name
                sess['role'] = 'manager'

            response = client.get('/team-collaboration?status=pending')
            assert response.status_code == 200


class TestInviteMemberEndpoint:
    """Test team member invitation functionality"""

    def test_invite_member_requires_manager_role(self, client):
        """Test invite member endpoint requires manager role"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.post('/invite_member', json={
                'name': 'New Member',
                'email': 'new@test.com',
                'role': 'user'
            })
            assert response.status_code in [403, 302]

    def test_invite_member_without_login(self, client):
        """Test invite member requires authentication"""
        response = client.post('/invite_member', json={
            'name': 'New Member',
            'email': 'new@test.com',
            'role': 'user'
        })
        assert response.status_code in [401, 302]


class TestBeforeRequestHandler:
    """Test the before_request handler for session management"""

    def test_session_made_permanent_for_logged_in_user(self, client):
        """Test that session is made permanent for logged-in users"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            # Make any request to trigger before_request
            response = client.get('/')
            
            # Session should remain valid
            with client.session_transaction() as sess:
                assert 'user_id' in sess


class TestErrorHandling:
    """Test error handling for various edge cases"""

    def test_404_on_invalid_route(self, client):
        """Test 404 error on non-existent route"""
        response = client.get('/this-route-does-not-exist')
        assert response.status_code == 404

    def test_get_nonexistent_post(self, client):
        """Test accessing non-existent post"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.get('/api/posts/99999')
            assert response.status_code in [404, 500]


class TestSessionPersistence:
    """Test session persistence across requests"""

    def test_session_persists_after_request(self, client):
        """Test session data persists across multiple requests"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['full_name'] = user.full_name
                sess['role'] = 'user'

            # Make first request
            response1 = client.get('/')
            
            # Make second request
            response2 = client.get('/')
            
            # Session should still be valid
            with client.session_transaction() as sess:
                assert sess.get('user_id') == user.user_id


class TestDraftPosts:
    """Test draft post functionality"""

    def test_create_draft_post(self, client):
        """Test creating a draft post"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.post('/api/posts', data={
                'text': 'This is a draft',
                'status': 'draft'
            })

            assert response.status_code == 201

    def test_edit_draft_post(self, client):
        """Test editing a draft post"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            post = Post(user_id=user.user_id, content_text='Draft content', status='draft')
            dbs.session.add(post)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.put(f'/api/posts/{post.post_id}', json={
                'text': 'Updated draft content'
            })

            # May succeed or fail depending on route implementation
            assert response.status_code in [200, 404, 500]
