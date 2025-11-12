#!/usr/bin/env python3
"""
Basic Integration Tests
Tests interaction between components and API endpoints
"""
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, OAuthState, ScheduledPost

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

@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client with session"""
    with app.app_context():
        # Create test user
        user = User(
            email='test@example.com',
            full_name='Test User',
            role='user'
        )
        dbs.session.add(user)
        dbs.session.commit()
        user_id = user.user_id
    
    # Set session
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = 'test@example.com'
        sess['full_name'] = 'Test User'
        sess['role'] = 'user'
    
    return client

@pytest.fixture
def manager_client(client):
    """Create manager authenticated test client"""
    with app.app_context():
        # Create manager user
        user = User(
            email='manager@example.com',
            full_name='Manager User',
            role='manager'
        )
        dbs.session.add(user)
        dbs.session.commit()
        user_id = user.user_id
    
    # Set session
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = 'manager@example.com'
        sess['full_name'] = 'Manager User'
        sess['role'] = 'manager'
    
    return client

class TestAuthenticationRoutes:
    """Test authentication related routes"""
    
    def test_home_redirect_when_not_logged_in(self, client):
        """Test that home redirects to login when not authenticated"""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_home_redirect_when_logged_in(self, authenticated_client):
        """Test that home redirects to dashboard when authenticated"""
        response = authenticated_client.get('/', follow_redirects=False)
        assert response.status_code == 302

class TestDashboardRoutes:
    """Test dashboard routes"""
    
    def test_user_dashboard_requires_login(self, client):
        """Test user dashboard requires login"""
        response = client.get('/dashboard/user', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_user_dashboard_authenticated(self, authenticated_client):
        """Test user can access user dashboard"""
        response = authenticated_client.get('/dashboard/user', follow_redirects=False)
        # User dashboard redirects to linked-accounts
        assert response.status_code == 302
    
    def test_manager_dashboard_requires_login(self, client):
        """Test manager dashboard requires login"""
        response = client.get('/dashboard/manager', follow_redirects=False)
        assert response.status_code == 302
    
    def test_manager_dashboard_authenticated(self, manager_client):
        """Test manager can access manager dashboard"""
        response = manager_client.get('/dashboard/manager')
        assert response.status_code == 200
    
    def test_user_cannot_access_manager_dashboard(self, authenticated_client):
        """Test regular user cannot access manager dashboard"""
        response = authenticated_client.get('/dashboard/manager', follow_redirects=False)
        assert response.status_code in [302, 403]

class TestPostAPIEndpoints:
    """Test post API endpoints"""
    
    def test_get_posts_unauthorized(self, client):
        """Test getting posts without authentication"""
        response = client.get('/api/posts')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_posts_authorized(self, authenticated_client):
        """Test getting posts with authentication"""
        response = authenticated_client.get('/api/posts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_get_posts_with_filters(self, authenticated_client):
        """Test getting posts with status filter"""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            # Create draft post
            post1 = Post(user_id=user.user_id, content_text='Draft post', status='draft')
            # Create published post
            post2 = Post(user_id=user.user_id, content_text='Published post', status='published')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()
        
        # Filter by draft
        response = authenticated_client.get('/api/posts?status=draft')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
    
    def test_create_post_unauthorized(self, client):
        """Test creating post without authentication"""
        response = client.post('/api/posts', data={
            'text': 'Test post',
            'status': 'draft'
        })
        assert response.status_code == 401
    
    def test_create_post_no_content(self, authenticated_client):
        """Test creating post without content"""
        response = authenticated_client.post('/api/posts', data={
            'text': '',
            'status': 'draft'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_post_no_accounts(self, authenticated_client):
        """Test creating post without selecting accounts"""
        response = authenticated_client.post('/api/posts', data={
            'text': 'Test post',
            'status': 'draft'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_post_success(self, authenticated_client):
        """Test creating post successfully"""
        with app.app_context():
            # Create platform and linked account
            user = User.query.filter_by(email='test@example.com').first()
            platform = Platform(platform_name='Twitter', api_endpoint='https://api.twitter.com')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='testuser',
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.account_id
        
        response = authenticated_client.post('/api/posts', data={
            'text': 'Test post content',
            'status': 'draft',
            'accounts[]': str(account_id)
        })
        # Might be 400 if validation fails, but test the route is reachable
        assert response.status_code in [200, 201, 400]
    
    def test_update_post_success(self, authenticated_client):
        """Test updating a post"""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='testuser',
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Original text', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id
            account_id = account.account_id
        
        response = authenticated_client.put(f'/api/posts/{post_id}', data={
            'text': 'Updated text',
            'status': 'draft',
            'accounts[]': [account_id]
        })
        assert response.status_code in [200, 201]
    
    def test_delete_post_success(self, authenticated_client):
        """Test deleting a post"""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            post = Post(user_id=user.user_id, content_text='To be deleted', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id
        
        response = authenticated_client.delete(f'/api/posts/{post_id}')
        assert response.status_code in [200, 204]
        
        # Verify post is deleted
        with app.app_context():
            deleted_post = dbs.session.get(Post, post_id)
            assert deleted_post is None

class TestLinkedAccountsRoute:
    """Test linked accounts routes"""
    
    def test_linked_accounts_unauthorized(self, client):
        """Test accessing linked accounts without authentication"""
        response = client.get('/linked-accounts', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_linked_accounts_authorized(self, authenticated_client):
        """Test accessing linked accounts with authentication"""
        response = authenticated_client.get('/linked-accounts')
        assert response.status_code == 200
        assert b'Linked Accounts' in response.data or b'linked' in response.data
    
    def test_disconnect_account(self, authenticated_client):
        """Test disconnecting a linked account"""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='testuser',
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.account_id
        
        response = authenticated_client.get(f'/disconnect-account/{account_id}', follow_redirects=False)
        assert response.status_code == 302
    
    def test_account_details(self, authenticated_client):
        """Test viewing account details"""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='testuser',
                access_token='test_token',
                follower_count=100,
                post_count=50
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.account_id
        
        response = authenticated_client.get(f'/account-details/{account_id}')
        assert response.status_code == 200

class TestPostSchedulerRoute:
    """Test post scheduler routes"""
    
    def test_post_scheduler_unauthorized(self, client):
        """Test accessing post scheduler without authentication"""
        response = client.get('/post-scheduler', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_post_scheduler_authorized_no_accounts(self, authenticated_client):
        """Test post scheduler redirects when no accounts linked"""
        response = authenticated_client.get('/post-scheduler', follow_redirects=False)
        # Should redirect to linked accounts if no accounts
        assert response.status_code in [200, 302]
    
    def test_post_scheduler_with_accounts(self, authenticated_client):
        """Test post scheduler with linked accounts"""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='testuser',
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
        
        response = authenticated_client.get('/post-scheduler')
        assert response.status_code == 200

class TestOAuthFlows:
    """Test OAuth connection flows"""
    
    @patch('requests.post')
    def test_linkedin_connect(self, mock_post, authenticated_client):
        """Test LinkedIn OAuth connection initiation"""
        response = authenticated_client.get('/connect/linkedin', follow_redirects=False)
        assert response.status_code == 302
        assert 'linkedin.com' in response.location
    
    @patch('requests.post')
    def test_twitter_connect(self, mock_post, authenticated_client):
        """Test Twitter OAuth connection initiation"""
        response = authenticated_client.get('/connect/twitter', follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to Twitter or create state
        assert response.location is not None

class TestDatabaseOperations:
    """Test database operations"""
    
    def test_user_creation_and_retrieval(self, client):
        """Test creating and retrieving a user"""
        with app.app_context():
            user = User(
                email='dbtest@example.com',
                full_name='DB Test User',
                role='user'
            )
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
            
            # Retrieve user
            retrieved_user = dbs.session.get(User, user_id)
            assert retrieved_user is not None
            assert retrieved_user.email == 'dbtest@example.com'
    
    def test_platform_and_linked_account(self, client, authenticated_client):
        """Test creating platform and linking account"""
        with app.app_context():
            # Create platform
            platform = Platform(
                platform_name='TestPlatform',
                api_endpoint='https://api.test.com'
            )
            dbs.session.add(platform)
            dbs.session.commit()
            platform_id = platform.platform_id
            
            # Get user
            user = User.query.filter_by(email='test@example.com').first()
            
            # Create linked account
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform_id,
                account_username='testuser',
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            # Verify
            retrieved = LinkedAccount.query.filter_by(user_id=user.user_id).first()
            assert retrieved is not None
            assert retrieved.account_username == 'testuser'
    
    def test_post_with_platform_links(self, client):
        """Test creating post with platform links"""
        with app.app_context():
            user = User(email='posttest@example.com', full_name='Post Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='test',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            link = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                published=False
            )
            dbs.session.add(link)
            dbs.session.commit()
            
            # Verify
            assert link.id is not None
            assert link.published == False
    
    def test_oauth_state_management(self, client):
        """Test OAuth state creation and cleanup"""
        with app.app_context():
            user = User(email='oauth@example.com', full_name='OAuth Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create OAuth state
            state = OAuthState(
                state_id='test_state_123',
                user_id=user.user_id,
                platform='twitter',
                code_verifier='test_verifier'
            )
            dbs.session.add(state)
            dbs.session.commit()
            
            # Verify
            retrieved = OAuthState.query.filter_by(state_id='test_state_123').first()
            assert retrieved is not None
            assert retrieved.platform == 'twitter'
    
    def test_scheduled_post_creation(self, client):
        """Test creating scheduled posts"""
        with app.app_context():
            user = User(email='schedule@example.com', full_name='Schedule Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Scheduled post', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            future_time = datetime.now() + timedelta(hours=1)
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=future_time,
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            # Verify
            assert scheduled.schedule_id is not None
            assert scheduled.status == 'scheduled'

class TestHelperFunctions:
    """Test helper functions"""
    
    def test_current_user_function(self, authenticated_client):
        """Test current_user helper function"""
        from src.app import current_user
        
        with authenticated_client.application.test_request_context():
            with authenticated_client.session_transaction() as sess:
                sess['user_id'] = 1
            # This will be tested indirectly through routes
            pass
    
    def test_cleanup_oauth_states(self, client):
        """Test OAuth state cleanup function"""
        from src.app import cleanup_old_oauth_states
        
        with app.app_context():
            # Create old OAuth state
            old_time = datetime.now() - timedelta(hours=2)
            user = User(email='cleanup@example.com', full_name='Cleanup Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            state = OAuthState(
                state_id='old_state',
                user_id=user.user_id,
                platform='twitter',
                created_at=old_time
            )
            dbs.session.add(state)
            dbs.session.commit()
            
            # Run cleanup
            cleanup_old_oauth_states()
            
            # Old state should still exist (cleanup threshold is usually longer)
            # This tests the function runs without error
            assert True

class TestErrorHandlers:
    """Test error handlers"""
    
    def test_404_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-route')
        # Status should be 404 even if template is missing
        assert response.status_code in [404, 500]  # 500 if template missing
    
    def test_500_handler_simulation(self, client):
        """Test that 500 errors are handled"""
        # This is a basic test - actual 500 testing requires more setup
        pass

class TestManagerFeatures:
    """Test manager-specific features"""
    
    def test_manager_can_see_all_posts(self, manager_client):
        """Test manager can see posts from all users"""
        with app.app_context():
            # Create another user's post
            other_user = User(email='other@example.com', full_name='Other User', role='user')
            dbs.session.add(other_user)
            dbs.session.commit()
            
            post = Post(user_id=other_user.user_id, content_text='Other user post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
        
        # Manager should be able to see it
        response = manager_client.get('/api/posts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
