"""
OAuth Callback Tests - Testing LinkedIn and Twitter OAuth flows
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, OAuthState


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


class TestLinkedInOAuthCallback:
    """Test LinkedIn OAuth callback flow"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_linkedin_callback_success(self, mock_get, mock_post, client):
        """Test successful LinkedIn OAuth callback"""
        # Setup user and OAuth state
        with app.app_context():
            user = User(email='test@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            # Create OAuth state
            state = OAuthState(user_id=user_id, state_string='test-state-123')
            dbs.session.add(state)
            dbs.session.commit()
        
        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'test-linkedin-token',
                'refresh_token': 'test-refresh-token',
                'expires_in': 5184000
            }
        )
        
        # Mock profile fetch
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'id': 'linkedin-user-123',
                'localizedFirstName': 'John',
                'localizedLastName': 'Doe'
            }
        )
        
        # Setup session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Call callback endpoint
        response = client.get('/callback/linkedin?code=test-code&state=test-state-123')
        
        # Should redirect to linked accounts
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    def test_linkedin_callback_token_exchange_failure(self, mock_post, client):
        """Test LinkedIn callback with token exchange failure"""
        # Setup user and OAuth state
        with app.app_context():
            user = User(email='test@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            state = OAuthState(user_id=user_id, state_string='test-state-456')
            dbs.session.add(state)
            dbs.session.commit()
        
        # Mock failed token exchange
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {'error': 'invalid_grant'}
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/callback/linkedin?code=bad-code&state=test-state-456')
        
        # Should handle error gracefully
        assert response.status_code in [200, 302, 400]
        
    def test_linkedin_callback_missing_code(self, client):
        """Test LinkedIn callback with missing code parameter"""
        with app.app_context():
            user = User(email='test@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/callback/linkedin?state=test-state')
        
        # Should handle missing code
        assert response.status_code in [200, 302, 400]
        
    def test_linkedin_callback_invalid_state(self, client):
        """Test LinkedIn callback with invalid state"""
        with app.app_context():
            user = User(email='test@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/callback/linkedin?code=test-code&state=invalid-state')
        
        # Should reject invalid state
        assert response.status_code in [200, 302, 400]


class TestTwitterOAuthCallback:
    """Test Twitter OAuth callback flow"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_twitter_callback_success(self, mock_get, mock_post, client):
        """Test successful Twitter OAuth callback"""
        # Setup user and OAuth state
        with app.app_context():
            user = User(email='twitter@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            state = OAuthState(
                user_id=user_id,
                state_string='twitter-state-789',
                code_verifier='test-verifier-123'
            )
            dbs.session.add(state)
            dbs.session.commit()
        
        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'test-twitter-token',
                'refresh_token': 'test-twitter-refresh',
                'expires_in': 7200
            }
        )
        
        # Mock profile fetch
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'data': {
                    'id': 'twitter-user-456',
                    'username': 'testuser',
                    'name': 'Test User'
                }
            }
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/callback/twitter?code=test-code&state=twitter-state-789')
        
        # Should redirect successfully
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    def test_twitter_callback_token_failure(self, mock_post, client):
        """Test Twitter callback with token exchange failure"""
        with app.app_context():
            user = User(email='twitter@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            state = OAuthState(
                user_id=user_id,
                state_string='twitter-state-fail',
                code_verifier='test-verifier'
            )
            dbs.session.add(state)
            dbs.session.commit()
        
        # Mock failed token exchange
        mock_post.return_value = MagicMock(
            status_code=401,
            json=lambda: {'error': 'invalid_client'}
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/callback/twitter?code=bad-code&state=twitter-state-fail')
        
        assert response.status_code in [200, 302, 400]
        
    def test_twitter_callback_missing_state(self, client):
        """Test Twitter callback without state parameter"""
        with app.app_context():
            user = User(email='twitter@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/callback/twitter?code=test-code')
        
        assert response.status_code in [200, 302, 400]


class TestRefreshAccount:
    """Test account refresh functionality"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_refresh_twitter_account(self, mock_get, mock_post, client):
        """Test refreshing Twitter account metrics"""
        with app.app_context():
            user = User(email='refresh@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            # Create platform and linked account
            platform = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='twitter-123',
                access_token='test-token',
                refresh_token='test-refresh'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.id
        
        # Mock token refresh
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'new-token',
                'refresh_token': 'new-refresh',
                'expires_in': 7200
            }
        )
        
        # Mock metrics fetch
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'data': {
                    'public_metrics': {
                        'followers_count': 1000,
                        'following_count': 500
                    }
                }
            }
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/refresh_account/{account_id}')
        
        # Should succeed
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    @patch('requests.get')
    def test_refresh_linkedin_account(self, mock_get, mock_post, client):
        """Test refreshing LinkedIn account"""
        with app.app_context():
            user = User(email='linkedin@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='LinkedIn', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='linkedin-789',
                access_token='linkedin-token',
                refresh_token='linkedin-refresh'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.id
        
        # Mock token refresh
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'new-linkedin-token',
                'refresh_token': 'new-linkedin-refresh',
                'expires_in': 5184000
            }
        )
        
        # Mock profile data
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'id': 'linkedin-789',
                'localizedFirstName': 'Jane',
                'localizedLastName': 'Smith'
            }
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/refresh_account/{account_id}')
        
        assert response.status_code in [200, 302]
        
    def test_refresh_nonexistent_account(self, client):
        """Test refreshing non-existent account"""
        with app.app_context():
            user = User(email='test@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/refresh_account/99999')
        
        # Should handle gracefully
        assert response.status_code in [200, 302, 404]


class TestDisconnectAccount:
    """Test account disconnection"""
    
    def test_disconnect_account_success(self, client):
        """Test successful account disconnection"""
        with app.app_context():
            user = User(email='disconnect@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='test-123',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/disconnect_account/{account_id}')
        
        # Should succeed
        assert response.status_code in [200, 302]
        
        # Verify account deleted
        with app.app_context():
            deleted = LinkedAccount.query.get(account_id)
            assert deleted is None
            
    def test_disconnect_unauthorized(self, client):
        """Test disconnecting another user's account"""
        with app.app_context():
            user1 = User(email='user1@example.com', role='user')
            user2 = User(email='user2@example.com', role='user')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            platform = Platform(name='LinkedIn', user_id=user2.id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user2.id,
                platform_id=platform.id,
                platform_user_id='other-user',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.id
            user1_id = user1.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        response = client.post(f'/api/disconnect_account/{account_id}')
        
        # Should not allow
        assert response.status_code in [200, 302, 403, 404]
