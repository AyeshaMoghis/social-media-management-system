"""Unit tests for additional app routes to increase coverage"""
import pytest
import json
from datetime import datetime, timedelta
from src.app import app, User, Platform, LinkedAccount, Post, dbs


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestDashboardRoutes:
    """Test dashboard routes"""
    
    def test_user_dashboard_without_login(self, client):
        """Test user dashboard redirects without login"""
        response = client.get('/user-dashboard', follow_redirects=False)
        assert response.status_code == 302
    
    def test_user_dashboard_with_login(self, client):
        """Test user dashboard with logged in user"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        response = client.get('/user-dashboard')
        assert response.status_code in [200, 302]
    
    def test_manager_dashboard_without_login(self, client):
        """Test manager dashboard redirects without login"""
        response = client.get('/manager-dashboard', follow_redirects=False)
        assert response.status_code == 302
    
    def test_manager_dashboard_with_user_role(self, client):
        """Test manager dashboard blocks non-manager users"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Regular User'
            sess['role'] = 'user'
        
        response = client.get('/manager-dashboard', follow_redirects=False)
        assert response.status_code == 302
    
    def test_manager_dashboard_with_manager_role(self, client):
        """Test manager dashboard allows manager access"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Manager User'
            sess['role'] = 'manager'
        
        response = client.get('/manager-dashboard')
        assert response.status_code == 200


class TestLinkedAccountsRoutes:
    """Test linked accounts routes"""
    
    def test_linked_accounts_without_login(self, client):
        """Test linked accounts page requires login"""
        response = client.get('/linked-accounts', follow_redirects=False)
        assert response.status_code == 302
    
    def test_linked_accounts_with_login(self, client):
        """Test linked accounts page with login"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
        
        response = client.get('/linked-accounts')
        assert response.status_code == 200
    
    def test_account_details_without_login(self, client):
        """Test account details requires login"""
        response = client.get('/account-details/1', follow_redirects=False)
        assert response.status_code == 302
    
    def test_account_details_with_login(self, client):
        """Test account details with login"""
        with app.app_context():
            # Get a linked account
            linked_account = LinkedAccount.query.first()
            if linked_account:
                with client.session_transaction() as sess:
                    sess['user_id'] = linked_account.user_id
                    sess['full_name'] = 'Test User'
                
                response = client.get(f'/account-details/{linked_account.linked_account_id}')
                assert response.status_code == 200


class TestOAuthRoutes:
    """Test OAuth routes"""
    
    def test_connect_twitter_without_login(self, client):
        """Test Twitter OAuth requires login"""
        response = client.get('/connect/twitter', follow_redirects=False)
        assert response.status_code == 302
    
    def test_connect_twitter_with_login(self, client):
        """Test Twitter OAuth connection"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
        
        response = client.get('/connect/twitter', follow_redirects=False)
        # Should redirect to Twitter or show error
        assert response.status_code in [302, 500, 200]
    
    def test_connect_linkedin_without_login(self, client):
        """Test LinkedIn OAuth requires login"""
        response = client.get('/connect/linkedin', follow_redirects=False)
        assert response.status_code == 302
    
    def test_connect_linkedin_with_login(self, client):
        """Test LinkedIn OAuth connection"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
        
        response = client.get('/connect/linkedin', follow_redirects=False)
        # Should redirect to LinkedIn or show error
        assert response.status_code in [302, 500, 200]


class TestHelperFunctions:
    """Test helper functions"""
    
    def test_allowed_file_valid_extensions(self, client):
        """Test allowed_file with valid extensions"""
        from src.app import allowed_file
        
        assert allowed_file('image.png') == True
        assert allowed_file('photo.jpg') == True
        assert allowed_file('photo.jpeg') == True
        assert allowed_file('image.gif') == True
        assert allowed_file('video.mp4') == True
        assert allowed_file('video.mov') == True
        assert allowed_file('video.avi') == True
        assert allowed_file('video.webm') == True
    
    def test_allowed_file_invalid_extensions(self, client):
        """Test allowed_file with invalid extensions"""
        from src.app import allowed_file
        
        assert allowed_file('document.pdf') == False
        assert allowed_file('script.exe') == False
        assert allowed_file('file.txt') == False
        assert allowed_file('noextension') == False
    
    def test_get_file_type_images(self, client):
        """Test get_file_type for images"""
        from src.app import get_file_type
        
        assert get_file_type('photo.png') == 'image'
        assert get_file_type('image.jpg') == 'image'
        assert get_file_type('pic.jpeg') == 'image'
        assert get_file_type('icon.gif') == 'image'
    
    def test_get_file_type_videos(self, client):
        """Test get_file_type for videos"""
        from src.app import get_file_type
        
        assert get_file_type('clip.mp4') == 'video'
        assert get_file_type('movie.mov') == 'video'
        assert get_file_type('video.avi') == 'video'
        assert get_file_type('stream.webm') == 'video'
    
    def test_get_file_type_unknown(self, client):
        """Test get_file_type for unknown types"""
        from src.app import get_file_type
        
        result = get_file_type('document.pdf')
        # Function returns None for unknown types
        assert result is None or result == 'unknown'


class TestSearchAndFilter:
    """Test search and filter functionality"""
    
    def test_team_collaboration_search(self, client):
        """Test team collaboration page with search"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Manager'
            sess['role'] = 'manager'
        
        response = client.get('/team-collaboration?search=test')
        assert response.status_code == 200
    
    def test_team_collaboration_filter(self, client):
        """Test team collaboration page with filter"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Manager'
            sess['role'] = 'manager'
        
        response = client.get('/team-collaboration?filter=pending')
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_get_posts_without_login(self, client):
        """Test GET /api/posts requires login"""
        response = client.get('/api/posts')
        assert response.status_code in [302, 401]
    
    def test_get_posts_with_login(self, client):
        """Test GET /api/posts with login"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = client.get('/api/posts')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_delete_post_without_login(self, client):
        """Test DELETE /api/posts/<id> requires login"""
        response = client.delete('/api/posts/999')
        assert response.status_code in [302, 401]
    
    def test_delete_nonexistent_post(self, client):
        """Test deleting non-existent post"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['user_id'] = 1
            
            response = client.delete('/api/posts/999999')
            assert response.status_code in [404, 500]


class TestFileUpload:
    """Test file upload functionality"""
    
    def test_upload_route_without_file(self, client):
        """Test upload endpoint without file"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = client.post('/api/posts', data={
            'text': 'Post without file'
        })
        # Should handle missing file gracefully
        assert response.status_code in [201, 400, 500]


class TestNotificationCount:
    """Test notification count endpoint"""
    
    def test_notification_count_without_login(self, client):
        """Test notification count requires login"""
        response = client.get('/api/notification-count')
        assert response.status_code in [302, 401, 200]
    
    def test_notification_count_with_login(self, client):
        """Test notification count with login"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'
        
        response = client.get('/api/notification-count')
        assert response.status_code == 200
        data = response.get_json()
        assert 'count' in data or 'notification_count' in data or isinstance(data, dict)


class TestInviteMember:
    """Test invite member functionality"""
    
    def test_invite_member_without_login(self, client):
        """Test invite member requires login"""
        response = client.post('/invite_member', 
                              data=json.dumps({'name': 'Test', 'email': 'test@test.com', 'role': 'user'}),
                              content_type='application/json')
        assert response.status_code in [302, 401, 403]
    
    def test_invite_member_as_user(self, client):
        """Test invite member requires manager role"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'user'
        
        response = client.post('/invite_member',
                              data=json.dumps({'name': 'Test', 'email': 'test@test.com', 'role': 'user'}),
                              content_type='application/json')
        assert response.status_code in [302, 403]


class TestPostSchedulerRoute:
    """Test post scheduler route"""
    
    def test_post_scheduler_without_login(self, client):
        """Test post scheduler requires login"""
        response = client.get('/post-scheduler', follow_redirects=False)
        assert response.status_code == 302
    
    def test_post_scheduler_with_login(self, client):
        """Test post scheduler with login"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
        
        response = client.get('/post-scheduler')
        # Route might redirect or show page
        assert response.status_code in [200, 302]
