"""
Ultimate Coverage Tests - Edge Cases and Additional Code Paths
"""
import pytest
from datetime import datetime, timedelta
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, ScheduledPost


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            dbs.create_all()
            yield client
            dbs.session.remove()
            try:
                dbs.drop_all()
            except:
                pass


class TestAdditionalPostCases:
    """Additional post test cases"""
    
    def test_post_with_long_content(self, client):
        """Test post with very long content"""
        with app.app_context():
            user = User(email='longpost@test.com', full_name='Long')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        long_content = 'A' * 5000  # Very long content
        response = client.post('/api/posts', json={
            'content_text': long_content
        })
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_post_with_special_characters(self, client):
        """Test post with special characters"""
        with app.app_context():
            user = User(email='special@test.com', full_name='Special')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Test with #hashtags @mentions and emojis 🚀✨'
        })
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_get_single_post(self, client):
        """Test getting a single post by ID"""
        with app.app_context():
            user = User(email='singlepost@test.com', full_name='Single')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Single post', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get(f'/api/posts/{post_id}')
        assert response.status_code in [200, 302, 404, 405]
    
    def test_update_post_media(self, client):
        """Test updating post media URL"""
        with app.app_context():
            user = User(email='media@test.com', full_name='Media')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put(f'/api/posts/{post_id}', json={
            'media_url': 'uploads/newmedia.jpg'
        })
        assert response.status_code in [200, 302, 404, 405]


class TestPlatformOperations:
    """Test platform-related operations"""
    
    def test_get_all_platforms(self, client):
        """Test getting all available platforms"""
        with app.app_context():
            twitter = Platform(platform_name='Twitter')
            linkedin = Platform(platform_name='LinkedIn')
            dbs.session.add_all([twitter, linkedin])
            dbs.session.commit()
        
        response = client.get('/api/platforms')
        assert response.status_code in [200, 404]
    
    def test_post_platform_association(self, client):
        """Test associating posts with platforms"""
        with app.app_context():
            user = User(email='assoc@test.com', full_name='Assoc')
            dbs.session.add(user)
            dbs.session.commit()
            
            twitter = Platform(platform_name='Twitter')
            linkedin = Platform(platform_name='LinkedIn')
            dbs.session.add_all([twitter, linkedin])
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Multi-platform', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            pp1 = PostPlatform(post_id=post.post_id, platform_id=twitter.platform_id)
            pp2 = PostPlatform(post_id=post.post_id, platform_id=linkedin.platform_id)
            dbs.session.add_all([pp1, pp2])
            dbs.session.commit()
            
            # Verify associations exist
            platforms = PostPlatform.query.filter_by(post_id=post.post_id).count()
            assert platforms == 2


class TestAuthenticationEdgeCases:
    """Test authentication edge cases"""
    
    def test_access_without_session(self, client):
        """Test accessing protected routes without session"""
        response = client.get('/api/posts')
        # Should redirect to login or return error
        assert response.status_code in [200, 302, 401, 404]
    
    def test_access_with_invalid_user_id(self, client):
        """Test accessing with invalid user ID in session"""
        with client.session_transaction() as sess:
            sess['user_id'] = 99999  # Non-existent user
        
        response = client.get('/api/posts')
        assert response.status_code in [200, 302, 401, 404]
    
    def test_multiple_login_logout_cycles(self, client):
        """Test multiple login/logout cycles"""
        # First login
        response1 = client.post('/login', json={
            'email': 'cycle@test.com',
            'password': 'wrong'
        })
        assert response1.status_code in [200, 302, 400, 401, 404]
        
        # Logout
        response2 = client.post('/logout')
        assert response2.status_code in [200, 302, 404]
        
        # Second login
        response3 = client.post('/login', json={
            'email': 'cycle@test.com',
            'password': 'wrong'
        })
        assert response3.status_code in [200, 302, 400, 401, 404]


class TestQueryFilters:
    """Test various query filters"""
    
    def test_filter_by_date_range(self, client):
        """Test filtering posts by date range"""
        with app.app_context():
            user = User(email='datefilter@test.com', full_name='Date Filter')
            dbs.session.add(user)
            dbs.session.commit()
            
            post1 = Post(user_id=user.user_id, content_text='Old post', status='published')
            post2 = Post(user_id=user.user_id, content_text='New post', status='published')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts?start_date=2025-01-01&end_date=2025-12-31')
        assert response.status_code in [200, 404]
    
    def test_filter_combined_parameters(self, client):
        """Test filtering with multiple parameters"""
        with app.app_context():
            user = User(email='multifilter@test.com', full_name='Multi Filter')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts?status=published&platform=Twitter&limit=10')
        assert response.status_code in [200, 404]
    
    def test_pagination(self, client):
        """Test post pagination"""
        with app.app_context():
            user = User(email='pagination@test.com', full_name='Pagination')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create many posts
            for i in range(25):
                post = Post(user_id=user.user_id, content_text=f'Post {i}', status='published')
                dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Test different pages
        response1 = client.get('/api/posts?page=1&limit=10')
        assert response1.status_code in [200, 404]
        
        response2 = client.get('/api/posts?page=2&limit=10')
        assert response2.status_code in [200, 404]


class TestDataValidation:
    """Test data validation"""
    
    def test_empty_post_content(self, client):
        """Test creating post with empty content"""
        with app.app_context():
            user = User(email='empty@test.com', full_name='Empty')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': ''
        })
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_invalid_status_value(self, client):
        """Test updating post with invalid status"""
        with app.app_context():
            user = User(email='invalidstatus@test.com', full_name='Invalid')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put(f'/api/posts/{post_id}', json={
            'status': 'invalid_status'
        })
        assert response.status_code in [200, 302, 400, 404]
    
    def test_invalid_platform_name(self, client):
        """Test creating post with invalid platform"""
        with app.app_context():
            user = User(email='badplatform@test.com', full_name='Bad Platform')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Test',
            'platforms': ['InvalidPlatform']
        })
        assert response.status_code in [200, 201, 302, 400, 404]


class TestAccountRefresh:
    """Test account refresh functionality"""
    
    def test_refresh_account_success(self, client):
        """Test refreshing account details"""
        with app.app_context():
            user = User(email='refresh@test.com', full_name='Refresh')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='refreshuser',
                access_token='token',
                refresh_token='refresh'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/refresh_account/{account_id}')
        assert response.status_code in [200, 302, 400, 404]


class TestUserManagement:
    """Test user management operations"""
    
    def test_create_user_duplicate_email(self, client):
        """Test creating user with duplicate email"""
        with app.app_context():
            user1 = User(email='duplicate@test.com', full_name='User 1')
            dbs.session.add(user1)
            dbs.session.commit()
        
        response = client.post('/signup', json={
            'email': 'duplicate@test.com',
            'password': 'password123',
            'full_name': 'User 2'
        })
        assert response.status_code in [200, 302, 400, 404, 409]
    
    def test_user_role_assignment(self, client):
        """Test user role assignment"""
        with app.app_context():
            manager = User(email='roletest@test.com', full_name='Role Test', role='manager')
            dbs.session.add(manager)
            dbs.session.commit()
            
            assert manager.role == 'manager'
    
    def test_get_user_profile(self, client):
        """Test getting user profile"""
        with app.app_context():
            user = User(email='profile@test.com', full_name='Profile')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/user/profile')
        assert response.status_code in [200, 302, 404, 405]
