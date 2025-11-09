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

from app import app, dbs, User, Platform, LinkedAccount, OAuthState, current_user, cleanup_old_oauth_states


@pytest.mark.unit
class TestUserModel(unittest.TestCase):
    """Test User model and related functions"""
    
    def test_user_creation(self):
        """Test user can be created with valid email"""
        user = User(email="user_creation_test@example.com")
        dbs.session.add(user)
        dbs.session.commit()
        
        self.assertIsNotNone(user.user_id)
        self.assertEqual(user.email, "user_creation_test@example.com")
        self.assertIsInstance(user.created_at, datetime)
    
    def test_user_email_unique_constraint(self):
        """Test user email must be unique"""
        user1 = User(email="unique_constraint_test@example.com")
        dbs.session.add(user1)
        dbs.session.commit()
        
        user2 = User(email="unique_constraint_test@example.com")
        dbs.session.add(user2)
        
        with self.assertRaises(Exception):
            dbs.session.commit()
    
    def test_current_user_creates_default_user(self):
        """Test current_user creates default user if none exists"""
        with app.test_request_context():
            with app.test_client().session_transaction() as sess:
                sess.clear()
            
            user = current_user()
            
            self.assertIsNotNone(user)
            self.assertEqual(user.email, "demo@user.com")


@pytest.mark.unit
class TestPlatformModel(unittest.TestCase):
    """Test Platform model"""
    
    def test_platform_creation(self):
        """Test platform can be created"""
        platform = Platform(
            platform_name="Twitter",
            api_endpoint="https://api.twitter.com/2",
            is_active=True
        )
        dbs.session.add(platform)
        dbs.session.commit()
        
        self.assertIsNotNone(platform.platform_id)
        self.assertEqual(platform.platform_name, "Twitter")
        self.assertTrue(platform.is_active)
    
    def test_platform_default_active_status(self):
        """Test platform is active by default"""
        platform = Platform(platform_name="LinkedIn")
        dbs.session.add(platform)
        dbs.session.commit()
        
        self.assertTrue(platform.is_active)


@pytest.mark.unit
class TestLinkedAccountModel(unittest.TestCase):
    """Test LinkedAccount model"""
    
    def test_linked_account_creation(self):
        """Test linked account can be created"""
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
        
        self.assertIsNotNone(account.account_id)
        self.assertEqual(account.access_token, "test_token")
        self.assertEqual(account.follower_count, 100)
    
    def test_linked_account_default_values(self):
        """Test linked account has correct default values"""
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
        
        self.assertEqual(account.follower_count, 0)
        self.assertEqual(account.post_count, 0)
        self.assertIsInstance(account.linked_at, datetime)
        self.assertIsInstance(account.last_synced, datetime)


@pytest.mark.unit
class TestOAuthStateModel(unittest.TestCase):
    """Test OAuthState model"""
    
    def test_oauth_state_creation(self):
        """Test OAuth state can be created"""
        state = OAuthState(
            state_id="test_state_123_unit",
            user_id=1,
            platform="twitter",
            code_verifier="test_verifier"
        )
        dbs.session.add(state)
        dbs.session.commit()
        
        retrieved = dbs.session.get(OAuthState, "test_state_123_unit")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.platform, "twitter")
    
    def test_cleanup_old_oauth_states(self):
        """Test cleanup removes old OAuth states"""
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
        
        self.assertIsNone(dbs.session.get(OAuthState, "old_state_unit"))
        self.assertIsNotNone(dbs.session.get(OAuthState, "new_state_unit"))


@pytest.mark.unit
@pytest.mark.social
class TestTwitterOAuthFlow(unittest.TestCase):
    """Test Twitter OAuth implementation"""
    
    @property
    def client(self):
        """Get test client - created fresh for each test automatically"""
        return app.test_client()
    
    def test_twitter_connect_creates_platform(self):
        """Test connecting to Twitter creates platform if not exists"""
        response = self.client.get('/connect/twitter')
        
        platform = Platform.query.filter_by(platform_name='Twitter').first()
        self.assertIsNotNone(platform)
        self.assertEqual(platform.api_endpoint, 'https://api.twitter.com/2')


@pytest.mark.unit
@pytest.mark.social
class TestLinkedInOAuthFlow(unittest.TestCase):
    """Test LinkedIn OAuth implementation"""
    
    @property
    def client(self):
        """Get test client - created fresh for each test automatically"""
        return app.test_client()
    
    def test_linkedin_connect_creates_platform(self):
        """Test connecting to LinkedIn creates platform if not exists"""
        response = self.client.get('/connect/linkedin')
        
        platform = Platform.query.filter_by(platform_name='LinkedIn').first()
        self.assertIsNotNone(platform)
        # Check that api_endpoint contains the base URL (actual value might be more specific)
        self.assertTrue(platform.api_endpoint.startswith('https://api.linkedin.com'))
    
    def test_linkedin_connect_generates_state(self):
        """Test LinkedIn connection generates OAuth state"""
        response = self.client.get('/connect/linkedin')
        
        states = OAuthState.query.filter_by(platform='linkedin').all()
        self.assertGreater(len(states), 0)
    
    def test_linkedin_connect_redirects_to_linkedin(self):
        """Test LinkedIn connection redirects to LinkedIn OAuth"""
        response = self.client.get('/connect/linkedin', follow_redirects=False)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('linkedin.com', response.location)
        self.assertIn('oauth/v2/authorization', response.location)
    
    @patch('requests.post')
    def test_linkedin_callback_success(self, mock_post):
        """Test successful LinkedIn OAuth callback"""
        user = User(email="linkedin_callback_test@example.com")
        dbs.session.add(user)
        dbs.session.commit()
        
        platform = Platform(platform_name="LinkedIn")
        dbs.session.add(platform)
        dbs.session.commit()
        
        state = OAuthState(
            state_id="test_state_linkedin",
            user_id=user.user_id,
            platform="linkedin"
        )
        dbs.session.add(state)
        dbs.session.commit()
        
        # Mock ID token
        id_token_payload = {
            "name": "Test User",
            "email": "linkedin_callback_test@example.com"
        }
        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(id_token_payload).encode()
        ).decode()
        fake_id_token = f"header.{encoded_payload}.signature"
        
        # Mock token exchange
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "test_access_token",
            "id_token": fake_id_token
        }
        
        # Execute callback
        response = self.client.get(
            '/callback/linkedin?code=test_code&state=test_state_linkedin',
            follow_redirects=False
        )
        
        # Verify
        self.assertEqual(response.status_code, 302)
        account = LinkedAccount.query.filter_by(user_id=user.user_id).first()
        self.assertIsNotNone(account)
        self.assertEqual(account.access_token, "test_access_token")
    
    def test_linkedin_callback_missing_parameters(self):
        """Test LinkedIn callback fails without required parameters"""
        response = self.client.get('/callback/linkedin')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'missing parameters', response.data)


@pytest.mark.unit
class TestAccountManagement(unittest.TestCase):
    """Test account management operations"""
    
    @property
    def client(self):
        """Get test client"""
        return app.test_client()
    
    def test_disconnect_account(self):
        """Test disconnecting an account"""
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
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.user_id
        
        response = self.client.get(
            f'/disconnect-account/{account_id}',
            follow_redirects=False
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(dbs.session.get(LinkedAccount, account_id))
    
    @patch('requests.get')
    def test_refresh_twitter_account(self, mock_get):
        """Test refreshing Twitter account data"""
        user = User(email="refresh_unit_test@example.com")
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
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.user_id
        
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
        
        response = self.client.get(
            f'/refresh-account/{account_id}',
            follow_redirects=False
        )
        
        self.assertEqual(response.status_code, 302)
        updated_account = dbs.session.get(LinkedAccount, account_id)
        self.assertEqual(updated_account.follower_count, 2000)
        self.assertEqual(updated_account.post_count, 1000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
