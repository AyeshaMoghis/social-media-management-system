"""
Integration Tests for Social Media Management System
Tests multiple components working together with real database
"""

import unittest
import pytest
from unittest.mock import patch
import json
import base64
from datetime import datetime, timedelta
import sys
import os
import secrets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, OAuthState


class BaseIntegrationTest:
    """Base class for integration tests with common setup"""
    
    def create_authenticated_user(self, client, email=None):
        """Create and authenticate a test user"""
        if email is None:
            email = f"test_{secrets.token_hex(4)}@example.com"
        
        with app.app_context():
            user = User(email=email, full_name="Test User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            
            # Refresh to get the user_id
            dbs.session.refresh(user)
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['full_name'] = "Test User"
            sess['role'] = "user"
        
        # Return mock user object
        class UserMock:
            def __init__(self, uid):
                self.user_id = uid
        return UserMock(user_id)


class TestCompleteTwitterAuthFlow(BaseIntegrationTest):
    """Integration test for complete Twitter OAuth flow"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_complete_twitter_oauth_flow(self, mock_get, mock_post, client):
        """Test complete Twitter authentication flow from start to finish"""
        # Setup authenticated user
        user = self.create_authenticated_user(client)
        
        # Step 1: User initiates Twitter connection
        response = client.get('/connect/twitter', follow_redirects=False)
        
        # Verify platform created
        with app.app_context():
            platform = Platform.query.filter_by(platform_name='Twitter').first()
            assert platform is not None, "Twitter platform should be created"
            
            # Verify OAuth state created
            oauth_state = OAuthState.query.filter_by(platform='twitter', user_id=user.user_id).first()
            assert oauth_state is not None, "OAuth state should be created"
            assert oauth_state.code_verifier is not None, "PKCE verifier should be generated"
            
            state_id = oauth_state.state_id
        
        # Verify redirect to Twitter
        assert response.status_code == 302
        assert 'twitter.com' in response.location
        
        # Step 2: Mock Twitter's token exchange
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "twitter_access_token_12345",
            "refresh_token": "twitter_refresh_token_12345",
            "token_type": "bearer",
            "expires_in": 7200
        }
        
        # Step 3: Mock Twitter's user info API
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "id": "123456789",
                "username": "johndoe",
                "name": "John Doe",
                "public_metrics": {
                    "followers_count": 5000,
                    "following_count": 200,
                    "tweet_count": 1500,
                    "listed_count": 10
                }
            }
        }
        
        # Step 4: Simulate callback from Twitter
        callback_response = client.get(
            f'/callback/twitter?code=auth_code_xyz&state={state_id}',
            follow_redirects=False
        )
        
        # Verify successful redirect
        assert callback_response.status_code == 302
        assert '/linked-accounts' in callback_response.location
        
        # Step 5: Verify account saved in database
        with app.app_context():
            platform = Platform.query.filter_by(platform_name='Twitter').first()
            linked_account = LinkedAccount.query.filter_by(
                user_id=user.user_id,
                platform_id=platform.platform_id
            ).first()
            
            assert linked_account is not None, "Linked account should be saved"
            assert linked_account.access_token == "twitter_access_token_12345"
            assert linked_account.refresh_token == "twitter_refresh_token_12345"
            assert linked_account.account_username == "John Doe (@johndoe)"
            assert linked_account.follower_count == 5000
            assert linked_account.post_count == 1500
            
            # Step 6: Verify OAuth state cleaned up
            remaining_state = dbs.session.get(OAuthState, state_id)
            assert remaining_state is None, "OAuth state should be deleted after use"
        
        # Step 7: Verify linked accounts page displays the account
        accounts_response = client.get('/linked-accounts')
        assert accounts_response.status_code == 200
        assert b'John Doe' in accounts_response.data
        assert b'5000' in accounts_response.data or b'5,000' in accounts_response.data


class TestCompleteLinkedInAuthFlow(BaseIntegrationTest):
    """Integration test for complete LinkedIn OAuth flow"""
    
    @patch('requests.post')
    def test_complete_linkedin_oauth_flow(self, mock_post, client):
        """Test complete LinkedIn authentication flow from start to finish"""
        # Setup authenticated user
        user = self.create_authenticated_user(client)
        
        # Step 1: User initiates LinkedIn connection
        response = client.get('/connect/linkedin', follow_redirects=False)
        
        # Verify platform created and get state
        with app.app_context():
            platform = Platform.query.filter_by(platform_name='LinkedIn').first()
            assert platform is not None, "LinkedIn platform should be created"
            
            # Verify OAuth state created
            oauth_state = OAuthState.query.filter_by(platform='linkedin', user_id=user.user_id).first()
            assert oauth_state is not None, "OAuth state should be created"
            state_id = oauth_state.state_id
        
        # Verify redirect to LinkedIn
        assert response.status_code == 302
        assert 'linkedin.com' in response.location
        
        # Step 2: Create mock ID token with user info
        id_token_payload = {
            "sub": "linkedin_user_123",
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "email_verified": True
        }
        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(id_token_payload).encode()
        ).decode()
        fake_id_token = f"header.{encoded_payload}.signature"
        
        # Step 3: Mock LinkedIn's token exchange
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "linkedin_access_token_67890",
            "expires_in": 5184000,
            "refresh_token": "linkedin_refresh_token_67890",
            "refresh_token_expires_in": 31536000,
            "scope": "openid profile email",
            "token_type": "Bearer",
            "id_token": fake_id_token
        }
        
        # Step 4: Simulate callback from LinkedIn
        callback_response = client.get(
            f'/callback/linkedin?code=linkedin_code_abc&state={state_id}',
            follow_redirects=False
        )
        
        # Verify successful redirect
        assert callback_response.status_code == 302
        assert '/linked-accounts' in callback_response.location
        
        # Step 5: Verify account saved in database
        with app.app_context():
            platform = Platform.query.filter_by(platform_name='LinkedIn').first()
            linked_account = LinkedAccount.query.filter_by(
                user_id=user.user_id,
                platform_id=platform.platform_id
            ).first()
            
            assert linked_account is not None, "Linked account should be saved"
            assert linked_account.access_token == "linkedin_access_token_67890"
            assert linked_account.account_username == "Jane Smith"
            
            # Step 6: Verify OAuth state cleaned up
            remaining_state = dbs.session.get(OAuthState, state_id)
            assert remaining_state is None, "OAuth state should be deleted after use"


class TestDuplicateAccountPrevention(BaseIntegrationTest):
    """Test prevention of duplicate account linking"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_cannot_link_same_twitter_account_twice(self, mock_get, mock_post, client):
        """Test that the same Twitter account cannot be linked twice"""
        # Create authenticated user
        user = self.create_authenticated_user(client, "duplicate_prevention@example.com")
        
        with app.app_context():
            # Create platform
            platform = Platform(platform_name="Twitter")
            dbs.session.add(platform)
            dbs.session.commit()
            platform_id = platform.platform_id
            
            # First linking - create existing account
            existing_account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform_id,
                access_token="existing_token",
                account_username="John Doe (@johndoe)",
                follower_count=5000,
                post_count=1500
            )
            dbs.session.add(existing_account)
            dbs.session.commit()
            
            # Attempt second linking of same account
            oauth_state = OAuthState(
                state_id="test_state_dup",
                user_id=user.user_id,
                platform="twitter",
                code_verifier="test_verifier"
            )
            dbs.session.add(oauth_state)
            dbs.session.commit()
        
        # Mock responses
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh"
        }
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "username": "johndoe",
                "name": "John Doe",
                "public_metrics": {
                    "followers_count": 5100,
                    "tweet_count": 1550
                }
            }
        }
        
        # Callback should update existing account, not create duplicate
        response = client.get(
            '/callback/twitter?code=code&state=test_state_dup',
            follow_redirects=False
        )
        
        with app.app_context():
            # Count accounts
            account_count = LinkedAccount.query.filter_by(
                user_id=user.user_id,
                platform_id=platform_id
            ).count()
            
            # Should still be 1 account (updated, not duplicated)
            assert account_count == 1
            
            # Verify account was updated with new token
            updated_account = LinkedAccount.query.filter_by(
                user_id=user.user_id,
                platform_id=platform_id
            ).first()
            assert updated_account.access_token == "new_token"


class TestMultiplePlatformLinking(BaseIntegrationTest):
    """Test linking multiple platforms for same user"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_user_can_link_multiple_platforms(self, mock_get, mock_post, client):
        """Test that a user can link both Twitter and LinkedIn"""
        # Create authenticated user
        user = self.create_authenticated_user(client, "multiplatform_user@example.com")
        
        with app.app_context():
            # Link Twitter
            twitter_state = OAuthState(
                state_id="twitter_state_multi",
                user_id=user.user_id,
                platform="twitter",
                code_verifier="verifier"
            )
            dbs.session.add(twitter_state)
            dbs.session.commit()
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "twitter_token",
            "refresh_token": "twitter_refresh"
        }
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "username": "user123",
                "name": "Test User",
                "public_metrics": {
                    "followers_count": 100,
                    "tweet_count": 50
                }
            }
        }
        
        client.get('/callback/twitter?code=code1&state=twitter_state_multi')
        
        with app.app_context():
            # Link LinkedIn
            linkedin_state = OAuthState(
                state_id="linkedin_state_multi",
                user_id=user.user_id,
                platform="linkedin"
            )
            dbs.session.add(linkedin_state)
            dbs.session.commit()
        
        id_token_payload = {"name": "Test User", "email": "multi@example.com"}
        encoded = base64.urlsafe_b64encode(json.dumps(id_token_payload).encode()).decode()
        
        mock_post.return_value.json.return_value = {
            "access_token": "linkedin_token",
            "id_token": f"h.{encoded}.s"
        }
        
        client.get('/callback/linkedin?code=code2&state=linkedin_state_multi')
        
        # Verify both accounts exist
        with app.app_context():
            accounts = LinkedAccount.query.filter_by(user_id=user.user_id).all()
            assert len(accounts) == 2, "User should have 2 linked accounts"
            
            platforms = [dbs.session.get(Platform, acc.platform_id).platform_name for acc in accounts]
            assert 'Twitter' in platforms
            assert 'LinkedIn' in platforms


class TestAccountRefreshIntegration(BaseIntegrationTest):
    """Test account refresh functionality"""
    
    @patch('requests.get')
    def test_refresh_updates_twitter_metrics(self, mock_get, client):
        """Test that refreshing updates Twitter account metrics"""
        # Setup authenticated user
        user = self.create_authenticated_user(client, "refresh_test@example.com")
        
        with app.app_context():
            platform = Platform(platform_name="Twitter")
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="valid_token",
                account_username="Old Name (@oldname)",
                follower_count=1000,
                post_count=500
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            account_id = account.account_id
            original_sync_time = account.last_synced
        
        # Mock updated data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "username": "newname",
                "name": "New Name",
                "public_metrics": {
                    "followers_count": 2000,
                    "tweet_count": 1000
                }
            }
        }
        
        # Refresh account
        response = client.get(f'/refresh-account/{account_id}')
        
        # Verify updates
        with app.app_context():
            updated_account = dbs.session.get(LinkedAccount, account_id)
            assert updated_account.follower_count == 2000
            assert updated_account.post_count == 1000
            assert updated_account.account_username == "New Name (@newname)"
            assert updated_account.last_synced > original_sync_time


class TestAccountDisconnectIntegration(BaseIntegrationTest):
    """Test account disconnection"""
    
    def test_disconnect_removes_account_completely(self, client):
        """Test that disconnecting removes account and all related data"""
        # Setup authenticated user
        user = self.create_authenticated_user(client, "disconnect_test@example.com")
        
        with app.app_context():
            platform = Platform(platform_name="Twitter")
            dbs.session.add(platform)
            dbs.session.commit()
            
            account1 = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token1",
                account_username="Account 1"
            )
            account2 = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token2",
                account_username="Account 2"
            )
            dbs.session.add(account1)
            dbs.session.add(account2)
            dbs.session.commit()
            
            account1_id = account1.account_id
            account2_id = account2.account_id
        
        # Disconnect account1
        response = client.get(f'/disconnect-account/{account1_id}')
        
        # Verify account1 removed but account2 remains
        with app.app_context():
            assert dbs.session.get(LinkedAccount, account1_id) is None
            assert dbs.session.get(LinkedAccount, account2_id) is not None


class TestErrorHandlingIntegration(BaseIntegrationTest):
    """Test error handling in OAuth flows"""
    
    @patch('requests.post')
    def test_twitter_token_exchange_failure(self, mock_post, client):
        """Test handling of Twitter token exchange failure"""
        user = self.create_authenticated_user(client, "error_test@example.com")
        
        with app.app_context():
            oauth_state = OAuthState(
                state_id="error_state_tw",
                user_id=user.user_id,
                platform="twitter",
                code_verifier="verifier"
            )
            dbs.session.add(oauth_state)
            dbs.session.commit()
        
        # Mock failed token exchange
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            "error": "invalid_grant",
            "error_description": "The provided authorization grant is invalid"
        }
        
        response = client.get('/callback/twitter?code=bad_code&state=error_state_tw')
        
        # Should return error
        assert response.status_code == 400
        assert b'Token exchange failed' in response.data
        
        # No account should be created
        with app.app_context():
            accounts = LinkedAccount.query.filter_by(user_id=user.user_id).all()
            assert len(accounts) == 0
    
    @patch('requests.post')
    def test_linkedin_missing_access_token(self, mock_post, client):
        """Test handling when LinkedIn doesn't return access token"""
        user = self.create_authenticated_user(client, "notoken_test@example.com")
        
        with app.app_context():
            oauth_state = OAuthState(
                state_id="notoken_state_li",
                user_id=user.user_id,
                platform="linkedin"
            )
            dbs.session.add(oauth_state)
            dbs.session.commit()
        
        # Mock response without access token
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "expires_in": 5184000
            # Missing access_token
        }
        
        response = client.get('/callback/linkedin?code=code&state=notoken_state_li')
        
        # Should return error
        assert response.status_code == 400
        assert b'Failed to get access token' in response.data


class TestOAuthStateCleanup(BaseIntegrationTest):
    """Test OAuth state cleanup functionality"""
    
    def test_cleanup_removes_only_old_states(self, client):
        """Test that cleanup removes old states but keeps recent ones"""
        with app.app_context():
            # Create old states (> 10 minutes)
            old_state1 = OAuthState(
                state_id="old1_cleanup",
                user_id=1,
                platform="twitter",
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
            old_state2 = OAuthState(
                state_id="old2_cleanup",
                user_id=1,
                platform="linkedin",
                created_at=datetime.utcnow() - timedelta(minutes=20)
            )
            
            # Create recent states
            new_state1 = OAuthState(
                state_id="new1_cleanup",
                user_id=1,
                platform="twitter",
                created_at=datetime.utcnow() - timedelta(minutes=5)
            )
            new_state2 = OAuthState(
                state_id="new2_cleanup",
                user_id=1,
                platform="linkedin",
                created_at=datetime.utcnow()
            )
            
            dbs.session.add_all([old_state1, old_state2, new_state1, new_state2])
            dbs.session.commit()
            
            # Trigger cleanup
            from src.app import cleanup_old_oauth_states
            cleanup_old_oauth_states()
            
            # Verify old states removed
            assert dbs.session.get(OAuthState, "old1_cleanup") is None
            assert dbs.session.get(OAuthState, "old2_cleanup") is None
            
            # Verify new states remain
            assert dbs.session.get(OAuthState, "new1_cleanup") is not None
            assert dbs.session.get(OAuthState, "new2_cleanup") is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
