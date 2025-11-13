"""
Unit Tests for Social Media Management System
Tests individual components in isolation with mocked dependencies
"""

import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import secrets
from datetime import datetime, timedelta
import base64
import hashlib

# Import your app components
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, OAuthState, current_user, cleanup_old_oauth_states


@pytest.mark.unit
class TestUserModel:
    """Test User model and related functions"""
    
    def test_user_creation(self):
        """Test user can be created with valid email"""
        with app.app_context():
            user = User(email="user_creation_test@example.com")
            dbs.session.add(user)
            dbs.session.commit()
            
            assert user.user_id is not None
            assert user.email == "user_creation_test@example.com"
            assert isinstance(user.created_at, datetime)
    
    def test_user_email_unique_constraint(self):
        """Test user email must be unique"""
        with app.app_context():
            user1 = User(email="unique_constraint_test@example.com")
            dbs.session.add(user1)
            dbs.session.commit()
            
            user2 = User(email="unique_constraint_test@example.com")
            dbs.session.add(user2)
            
            with pytest.raises(Exception):
                dbs.session.commit()
    
    def test_current_user_creates_default_user(self, client):
        """Test current_user returns None when no session"""
        with app.test_request_context():
            with client.session_transaction() as sess:
                sess.clear()
            
            user = current_user()
            
            # Should return None when no user_id in session
            assert user is None


@pytest.mark.unit
class TestPlatformModel:
    """Test Platform model"""
    
    def test_platform_creation(self):
        """Test platform can be created"""
        with app.app_context():
            platform = Platform(
                platform_name="Twitter",
                api_endpoint="https://api.twitter.com/2",
                is_active=True
            )
            dbs.session.add(platform)
            dbs.session.commit()
            
            assert platform.platform_id is not None
            assert platform.platform_name == "Twitter"
            assert platform.is_active is True
    
    def test_platform_default_active_status(self):
        """Test platform is active by default"""
        with app.app_context():
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add(platform)
            dbs.session.commit()
            
            assert platform.is_active is True


@pytest.mark.unit
class TestLinkedAccountModel:
    """Test LinkedAccount model"""
    
    def test_linked_account_creation(self):
        """Test linked account can be created"""
        with app.app_context():
            user = User(email="linked_account_creation@example.com")
            platform = Platform(platform_name="Twitter")
            dbs.session.add(user)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="test_token",
                account_username="@testuser",
                follower_count=100,
                post_count=50
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            assert account.account_id is not None
            assert account.access_token == "test_token"
            assert account.follower_count == 100
    
    def test_linked_account_default_values(self):
        """Test linked account has correct default values"""
        with app.app_context():
            user = User(email="linked_account_defaults@example.com")
            platform = Platform(platform_name="Twitter")
            dbs.session.add(user)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            assert account.follower_count == 0
            assert account.post_count == 0
            assert isinstance(account.linked_at, datetime)
            assert isinstance(account.last_synced, datetime)


@pytest.mark.unit
class TestOAuthStateModel:
    """Test OAuthState model"""
    
    def test_oauth_state_creation(self):
        """Test OAuth state can be created"""
        with app.app_context():
            state = OAuthState(
                state_id="test_state_123_unit",
                user_id=1,
                platform="twitter",
                code_verifier="test_verifier"
            )
            dbs.session.add(state)
            dbs.session.commit()
            
            retrieved = dbs.session.get(OAuthState, "test_state_123_unit")
            assert retrieved is not None
            assert retrieved.platform == "twitter"
    
    def test_cleanup_old_oauth_states(self):
        """Test cleanup removes old OAuth states"""
        with app.app_context():
            old_state = OAuthState(
                state_id="old_state_unit",
                user_id=1,
                platform="twitter",
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
            
            new_state = OAuthState(
                state_id="new_state_unit",
                user_id=1,
                platform="twitter"
            )
            
            dbs.session.add(old_state)
            dbs.session.add(new_state)
            dbs.session.commit()
            
            cleanup_old_oauth_states()
            
            assert dbs.session.get(OAuthState, "old_state_unit") is None
            assert dbs.session.get(OAuthState, "new_state_unit") is not None


@pytest.mark.unit
@pytest.mark.social
class TestTwitterOAuthFlow:
    """Test Twitter OAuth implementation"""
    
    def test_twitter_connect_creates_platform(self, client):
        """Test connecting to Twitter creates platform if not exists"""
        # Create authenticated session
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        # Need to create a user first
        with app.app_context():
            user = User(email="twitter_test@example.com", full_name="Test User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        response = client.get('/connect/twitter')
        
        with app.app_context():
            platform = Platform.query.filter_by(platform_name='Twitter').first()
            assert platform is not None
            assert platform.api_endpoint == 'https://api.twitter.com/2'


@pytest.mark.unit
@pytest.mark.social
class TestLinkedInOAuthFlow:
    """Test LinkedIn OAuth implementation"""
    
    def test_linkedin_connect_creates_platform(self, client):
        """Test connecting to LinkedIn creates platform if not exists"""
        # Create user first
        with app.app_context():
            user = User(email="linkedin_test@example.com", full_name="Test User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        # Create authenticated session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        response = client.get('/connect/linkedin')
        
        with app.app_context():
            platform = Platform.query.filter_by(platform_name='LinkedIn').first()
            assert platform is not None
            # Check that api_endpoint contains the base URL
            assert platform.api_endpoint.startswith('https://api.linkedin.com')
    
    def test_linkedin_connect_generates_state(self, client):
        """Test LinkedIn connection generates OAuth state"""
        # Create user first
        with app.app_context():
            user = User(email="linkedin_state_test@example.com", full_name="Test User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        # Create authenticated session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        response = client.get('/connect/linkedin')
        
        with app.app_context():
            states = OAuthState.query.filter_by(platform='linkedin', user_id=user_id).all()
            assert len(states) > 0
    
    def test_linkedin_connect_redirects_to_linkedin(self, client):
        """Test LinkedIn connection redirects to LinkedIn OAuth"""
        # Create user first
        with app.app_context():
            user = User(email="linkedin_redirect_test@example.com", full_name="Test User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        # Create authenticated session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        response = client.get('/connect/linkedin', follow_redirects=False)
        
        assert response.status_code == 302
        assert 'linkedin.com' in response.location
        assert 'oauth/v2/authorization' in response.location
    
    
    def test_linkedin_callback_missing_parameters(self, client):
        """Test LinkedIn callback fails without required parameters"""
        response = client.get('/callback/linkedin')
        
        assert response.status_code == 400
        assert b'missing parameters' in response.data


@pytest.mark.unit
class TestAccountManagement:
    """Test account management operations"""
    
    def test_disconnect_account(self, client):
        """Test disconnecting an account"""
        with app.app_context():
            user = User(email="disconnect_unit_test@example.com")
            platform = Platform(platform_name="Twitter")
            dbs.session.add(user)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="test_token",
                account_username="@testuser"
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            account_id = account.account_id
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get(
            f'/disconnect-account/{account_id}',
            follow_redirects=False
        )
        
        assert response.status_code == 302
        with app.app_context():
            assert dbs.session.get(LinkedAccount, account_id) is None
    
    @patch('requests.get')
    def test_refresh_twitter_account(self, mock_get, client):
        """Test refreshing Twitter account data"""
        with app.app_context():
            user = User(email="refresh_unit_test@example.com")
            platform = Platform(platform_name="Twitter")
            dbs.session.add(user)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="test_token",
                account_username="@testuser",
                follower_count=1000,
                post_count=500
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            account_id = account.account_id
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Mock Twitter API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "username": "updateduser",
                "name": "Updated User",
                "public_metrics": {
                    "followers_count": 2000,
                    "tweet_count": 1000
                }
            }
        }
        
        response = client.get(
            f'/refresh-account/{account_id}',
            follow_redirects=False
        )
        
        assert response.status_code == 302
        with app.app_context():
            updated_account = dbs.session.get(LinkedAccount, account_id)
            assert updated_account.follower_count == 2000
            assert updated_account.post_count == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
