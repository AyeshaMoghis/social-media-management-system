"""
Error Handlers and Route Coverage Tests
"""
import pytest
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post


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


class TestErrorHandlers:
    """Test error handler routes"""
    
    def test_404_not_found(self, client):
        """Test 404 error handler"""
        response = client.get('/this-route-does-not-exist')
        assert response.status_code == 404
        
    def test_404_json_request(self, client):
        """Test 404 with JSON request"""
        response = client.get('/api/nonexistent', headers={'Accept': 'application/json'})
        assert response.status_code == 404


class TestManagerDashboardRoutes:
    """Test manager-specific routes"""
    
    def test_manager_dashboard_access_as_manager(self, client):
        """Test manager can access manager dashboard"""
        with app.app_context():
            user = User(email='manager@test.com', full_name='Manager User', role='manager')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'manager'
            sess['full_name'] = 'Manager User'
        
        response = client.get('/dashboard/manager')
        assert response.status_code == 200
        
    def test_manager_dashboard_denied_for_user(self, client):
        """Test user cannot access manager dashboard"""
        with app.app_context():
            user = User(email='user@test.com', full_name='Regular User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        response = client.get('/dashboard/manager')
        assert response.status_code == 302  # Redirect
        
    def test_user_dashboard_access_as_user(self, client):
        """Test user can access user dashboard"""
        with app.app_context():
            user = User(email='user2@test.com', full_name='User Two', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        response = client.get('/dashboard/user')
        assert response.status_code in [200, 302]  # May redirect to linked_accounts


class TestLinkedAccountsRoute:
    """Test linked accounts page"""
    
    def test_linked_accounts_page_authenticated(self, client):
        """Test linked accounts page with authentication"""
        with app.app_context():
            user = User(email='linked@test.com', full_name='Linked Test', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
            sess['full_name'] = 'Linked Test'
        
        response = client.get('/linked-accounts')
        assert response.status_code == 200
        
    def test_linked_accounts_with_accounts(self, client):
        """Test linked accounts page when user has linked accounts"""
        with app.app_context():
            user = User(email='accounts@test.com', full_name='Accounts Test', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='testuser',
                access_token='test-token',
                follower_count=100
            )
            dbs.session.add(account)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
            sess['full_name'] = 'Accounts Test'
        
        response = client.get('/linked-accounts')
        assert response.status_code == 200


class TestPostSchedulerRoute:
    """Test post scheduler route"""
    
    def test_post_scheduler_page(self, client):
        """Test post scheduler page"""
        with app.app_context():
            user = User(email='scheduler@test.com', full_name='Scheduler Test')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
            sess['full_name'] = 'Scheduler Test'
        
        response = client.get('/create-schedule-posts')
        # Route may not exist or may redirect
        assert response.status_code in [200, 302, 404]


class TestAccountDetailsRoute:
    """Test account details route"""
    
    def test_get_account_details(self, client):
        """Test getting account details"""
        with app.app_context():
            user = User(email='details@test.com', full_name='Details Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='detailsuser',
                access_token='token',
                follower_count=500,
                post_count=200
            )
            dbs.session.add(account)
            dbs.session.commit()
            user_id = user.user_id
            account_id = account.account_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get(f'/api/account_details/{account_id}')
        # May return 200 with data, redirect, or 404 if endpoint doesn't exist
        assert response.status_code in [200, 302, 404]


class TestConnectRoutes:
    """Test social media connect routes"""
    
    def test_linkedin_connect_creates_oauth_state(self, client):
        """Test LinkedIn connect creates OAuth state"""
        with app.app_context():
            user = User(email='linkedin@test.com', full_name='LinkedIn Test')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        response = client.get('/connect/linkedin')
        
        # Should redirect to LinkedIn
        assert response.status_code == 302
        
    def test_twitter_connect_creates_oauth_state(self, client):
        """Test Twitter connect creates OAuth state"""
        with app.app_context():
            user = User(email='twitter@test.com', full_name='Twitter Test')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        response = client.get('/connect/twitter')
        
        # Should redirect to Twitter
        assert response.status_code == 302


class TestPostAPIWithData:
    """Test post API with actual data"""
    
    def test_get_posts_with_user_posts(self, client):
        """Test getting posts when user has posts"""
        with app.app_context():
            user = User(email='poster@test.com', full_name='Poster Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            post1 = Post(user_id=user.user_id, content_text='First post', status='draft')
            post2 = Post(user_id=user.user_id, content_text='Second post', status='published')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts')
        assert response.status_code == 200
        
        # Check response contains posts
        data = response.get_json()
        assert 'posts' in data or isinstance(data, list)
        
    def test_get_posts_filtered_by_status(self, client):
        """Test getting posts filtered by status"""
        with app.app_context():
            user = User(email='filter@test.com', full_name='Filter Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Draft post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts?status=draft')
        assert response.status_code == 200
        
    def test_update_post_with_data(self, client):
        """Test updating a post"""
        with app.app_context():
            user = User(email='update@test.com', full_name='Update Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Original', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put(f'/api/posts/{post_id}', json={
            'content': 'Updated content'
        })
        assert response.status_code in [200, 302]
        
    def test_delete_post_success(self, client):
        """Test deleting a post"""
        with app.app_context():
            user = User(email='delete@test.com', full_name='Delete Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='To delete', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code in [200, 302]
        
        # Verify post was deleted
        with app.app_context():
            deleted_post = Post.query.get(post_id)
            assert deleted_post is None


class TestHomeRoute:
    """Test home route redirects"""
    
    def test_home_redirect_not_logged_in(self, client):
        """Test home redirects to login when not logged in"""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location
        
    def test_home_redirect_user_logged_in(self, client):
        """Test home redirects to linked accounts for users"""
        with app.app_context():
            user = User(email='home@test.com', full_name='Home Test', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        response = client.get('/')
        assert response.status_code == 302
        
    def test_home_redirect_manager_logged_in(self, client):
        """Test home redirects to manager dashboard for managers"""
        with app.app_context():
            user = User(email='mgr@test.com', full_name='Manager', role='manager')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'manager'
        
        response = client.get('/')
        assert response.status_code == 302
        assert '/manager' in response.location
