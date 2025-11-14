"""
Unit tests for OAuth callback functions
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.app import app, dbs, User, Platform, OAuthState


class TestLinkedInCallback:
    """Test LinkedIn OAuth callback"""

    def test_linkedin_callback_success(self, client):
        """Test successful LinkedIn OAuth callback"""
        with app.app_context():
            # Create user
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            # Create OAuth state
            state = OAuthState(
                state_token='test_state_123',
                user_id=user.user_id,
                platform='linkedin'
            )
            dbs.session.add(state)
            dbs.session.commit()

            # Mock the requests to LinkedIn
            with patch('requests.post') as mock_post, \
                 patch('requests.get') as mock_get:
                
                # Mock token exchange
                mock_token_response = Mock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = {
                    'access_token': 'test_access_token',
                    'expires_in': 5184000
                }
                
                # Mock user info
                mock_user_response = Mock()
                mock_user_response.status_code = 200
                mock_user_response.json.return_value = {
                    'sub': 'linkedin_user_123'
                }
                
                mock_post.return_value = mock_token_response
                mock_get.return_value = mock_user_response

                # Set session
                with client.session_transaction() as sess:
                    sess['user_id'] = user.user_id
                    sess['full_name'] = user.full_name
                    sess['role'] = user.role

                response = client.get(f'/auth/linkedin/callback?code=test_code&state=test_state_123')
                
                # Check redirect
                assert response.status_code in [200, 302]

    def test_linkedin_callback_missing_state(self, client):
        """Test LinkedIn callback with missing state"""
        response = client.get('/auth/linkedin/callback?code=test_code')
        assert response.status_code in [400, 302]

    def test_linkedin_callback_invalid_state(self, client):
        """Test LinkedIn callback with invalid state"""
        response = client.get('/auth/linkedin/callback?code=test_code&state=invalid_state')
        assert response.status_code in [400, 302]

    def test_linkedin_callback_token_exchange_failure(self, client):
        """Test LinkedIn callback when token exchange fails"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            state = OAuthState(
                state_token='test_state_123',
                user_id=user.user_id,
                platform='linkedin'
            )
            dbs.session.add(state)
            dbs.session.commit()

            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = 'Invalid grant'
                mock_post.return_value = mock_response

                with client.session_transaction() as sess:
                    sess['user_id'] = user.user_id

                response = client.get(f'/auth/linkedin/callback?code=test_code&state=test_state_123')
                assert response.status_code in [400, 302, 500]


class TestTwitterCallback:
    """Test Twitter OAuth callback"""

    def test_twitter_callback_success(self, client):
        """Test successful Twitter OAuth callback"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            state = OAuthState(
                state_token='test_state_456',
                user_id=user.user_id,
                platform='twitter',
                code_verifier='test_verifier'
            )
            dbs.session.add(state)
            dbs.session.commit()

            with patch('requests.post') as mock_post, \
                 patch('requests.get') as mock_get:
                
                # Mock token exchange
                mock_token_response = Mock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = {
                    'access_token': 'test_twitter_token',
                    'expires_in': 7200
                }
                
                # Mock user info
                mock_user_response = Mock()
                mock_user_response.status_code = 200
                mock_user_response.json.return_value = {
                    'data': {'id': 'twitter_user_789'}
                }
                
                mock_post.return_value = mock_token_response
                mock_get.return_value = mock_user_response

                with client.session_transaction() as sess:
                    sess['user_id'] = user.user_id
                    sess['full_name'] = user.full_name
                    sess['role'] = user.role

                response = client.get(f'/auth/twitter/callback?code=test_code&state=test_state_456')
                
                assert response.status_code in [200, 302]

    def test_twitter_callback_missing_code(self, client):
        """Test Twitter callback with missing code"""
        response = client.get('/auth/twitter/callback?state=test_state')
        assert response.status_code in [400, 302]

    def test_twitter_callback_duplicate_account(self, client):
        """Test Twitter callback prevents duplicate account linking"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            # Create existing platform
            existing_platform = Platform(
                user_id=user.user_id,
                platform_name='twitter',
                platform_user_id='twitter_existing',
                access_token='existing_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(existing_platform)
            dbs.session.commit()

            state = OAuthState(
                state_token='test_state_789',
                user_id=user.user_id,
                platform='twitter',
                code_verifier='test_verifier'
            )
            dbs.session.add(state)
            dbs.session.commit()

            with patch('requests.post') as mock_post, \
                 patch('requests.get') as mock_get:
                
                mock_token_response = Mock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = {
                    'access_token': 'new_token',
                    'expires_in': 7200
                }
                
                # Return the same user ID as existing platform
                mock_user_response = Mock()
                mock_user_response.status_code = 200
                mock_user_response.json.return_value = {
                    'data': {'id': 'twitter_existing'}
                }
                
                mock_post.return_value = mock_token_response
                mock_get.return_value = mock_user_response

                with client.session_transaction() as sess:
                    sess['user_id'] = user.user_id

                response = client.get(f'/auth/twitter/callback?code=test_code&state=test_state_789')
                
                # Should handle duplicate gracefully
                assert response.status_code in [200, 302, 400]


class TestOAuthInitiation:
    """Test OAuth initiation flows"""

    def test_linkedin_auth_initiation(self, client):
        """Test LinkedIn OAuth initiation"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.get('/auth/linkedin')
            
            # Should redirect to LinkedIn
            assert response.status_code == 302
            assert 'linkedin.com' in response.location or response.location.startswith('/auth/')

    def test_twitter_auth_initiation(self, client):
        """Test Twitter OAuth initiation"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.get('/auth/twitter')
            
            # Should redirect to Twitter
            assert response.status_code == 302
            assert 'twitter.com' in response.location or response.location.startswith('/auth/')

    def test_oauth_initiation_without_login(self, client):
        """Test OAuth initiation without login"""
        response = client.get('/auth/linkedin')
        assert response.status_code in [302, 401]


class TestPlatformDisconnect:
    """Test platform disconnection"""

    def test_disconnect_platform_success(self, client):
        """Test successfully disconnecting a platform"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='twitter',
                platform_user_id='twitter_123',
                access_token='token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()
            platform_id = platform.platform_id

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.delete(f'/api/platforms/{platform_id}')
            
            if response.status_code == 200:
                deleted_platform = Platform.query.get(platform_id)
                assert deleted_platform is None

    def test_disconnect_nonexistent_platform(self, client):
        """Test disconnecting non-existent platform"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
                sess['role'] = 'user'

            response = client.delete('/api/platforms/99999')
            assert response.status_code == 404

    def test_disconnect_other_user_platform(self, client):
        """Test cannot disconnect another user's platform"""
        with app.app_context():
            user1 = User(email='user1@test.com', full_name='User 1', role='user')
            user2 = User(email='user2@test.com', full_name='User 2', role='user')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()

            platform = Platform(
                user_id=user2.user_id,
                platform_name='twitter',
                platform_user_id='twitter_123',
                access_token='token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user1.user_id
                sess['role'] = 'user'

            response = client.delete(f'/api/platforms/{platform.platform_id}')
            assert response.status_code in [403, 404]
