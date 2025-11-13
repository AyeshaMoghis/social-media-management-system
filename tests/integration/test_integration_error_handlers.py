"""
Tests for Error Handlers, Upload Routes, and Edge Cases - CORRECTED VERSION
Increases code coverage for remaining untested code paths
"""

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from io import BytesIO
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform


@pytest.mark.integration
class TestErrorHandlers:
    """Test application error handlers"""

    def test_404_error_handler(self, client):
        """Test 404 error handler returns correct page"""
        response = client.get('/nonexistent-page-12345')
        assert response.status_code == 404


@pytest.mark.integration
class TestUploadedFileRoute:
    """Test file upload and serving functionality"""

    def test_serve_nonexistent_file(self, client):
        """Test serving nonexistent file returns 404"""
        response = client.get('/uploads/nonexistent_file.jpg')
        assert response.status_code == 404


@pytest.mark.integration
class TestLinkedAccountsRoute:
    """Test linked accounts page with various states"""

    def test_linked_accounts_no_user_redirects(self, client):
        """Test linked accounts page redirects without session"""
        response = client.get('/linked-accounts', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_linked_accounts_with_no_accounts(self, client):
        """Test linked accounts page with user but no accounts"""
        with app.app_context():
            user = User(email="noaccounts@test.com", full_name="No Accounts User")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/linked-accounts')
        assert response.status_code == 200

    def test_linked_accounts_with_twitter_account(self, client):
        """Test linked accounts shows Twitter stats"""
        with app.app_context():
            user = User(email="twitteraccount@test.com", full_name="Twitter User")
            platform = Platform.query.filter_by(platform_name='Twitter').first()
            if not platform:
                platform = Platform(platform_name="Twitter")
                dbs.session.add(platform)
            
            dbs.session.add(user)
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="@twitteruser",
                follower_count=100,
                post_count=50
            )
            dbs.session.add(account)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/linked-accounts')
        assert response.status_code == 200
        # Should show Twitter stats


@pytest.mark.integration
class TestAccountDetailsRoute:
    """Test account details page"""

    def test_account_details_not_logged_in(self, client):
        """Test account details requires login"""
        response = client.get('/account-details/1', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_account_details_not_found(self, client):
        """Test account details for nonexistent account"""
        with app.app_context():
            user = User(email="details_test@test.com", full_name="Test User")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/account-details/99999', follow_redirects=True)
        # Should redirect to linked accounts or show error
        assert response.status_code == 200
        assert b'not found' in response.data.lower() or b'linked accounts' in response.data.lower()

    def test_account_details_wrong_user(self, client):
        """Test user cannot access another user's account details"""
        with app.app_context():
            user1 = User(email="user1_details@test.com", full_name="User 1")
            user2 = User(email="user2_details@test.com", full_name="User 2")
            platform = Platform.query.filter_by(platform_name="Twitter").first()
            if not platform:
                platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user1, user2, platform])
            dbs.session.commit()

            # Create account for user2
            account = LinkedAccount(
                user_id=user2.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="@user2"
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user1_id = user1.user_id
            account_id = account.account_id

        # Login as user1
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
            sess['role'] = 'user'

        # Try to access user2's account
        response = client.get(f'/account-details/{account_id}', follow_redirects=True)
        # Should redirect or show not found
        assert response.status_code == 200
        assert b'not found' in response.data.lower() or b'linked accounts' in response.data.lower()

    def test_account_details_success(self, client):
        """Test successful account details view"""
        with app.app_context():
            user = User(email="details_success@test.com", full_name="Test User")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="Test User LinkedIn",
                follower_count=250
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get(f'/account-details/{account_id}')
        assert response.status_code == 200


@pytest.mark.integration
class TestRefreshAccountRoute:
    """Test account refresh functionality"""

    def test_refresh_account_not_logged_in(self, client):
        """Test refresh requires login"""
        response = client.get('/refresh-account/1', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_refresh_account_not_found(self, client):
        """Test refresh nonexistent account"""
        with app.app_context():
            user = User(email="refresh_notfound@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/refresh-account/99999', follow_redirects=False)
        assert response.status_code == 302
        assert '/linked-accounts' in response.location

    def test_refresh_account_no_token(self, client):
        """Test refresh account without access token"""
        with app.app_context():
            user = User(email="refresh_notoken@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token=None,  # No token
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get(f'/refresh-account/{account_id}', follow_redirects=False)
        assert response.status_code == 302
        assert '/linked-accounts' in response.location

    @patch('src.app.requests.get')
    def test_refresh_linkedin_account_success(self, mock_get, client):
        """Test successful LinkedIn account refresh"""
        with app.app_context():
            user = User(email="refresh_li_success@test.com", full_name="Test")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="Old Name"
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "name": "Updated Name",
            "given_name": "Updated",
            "family_name": "Name"
        }

        response = client.get(f'/refresh-account/{account_id}', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            updated = dbs.session.get(LinkedAccount, account_id)
            assert updated.account_username == "Updated Name"

    @patch('src.app.requests.get')
    def test_refresh_twitter_account_success(self, mock_get, client):
        """Test successful Twitter account refresh"""
        with app.app_context():
            user = User(email="refresh_tw_success@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="Old User",
                follower_count=100
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "username": "newuser",
                "name": "New User",
                "public_metrics": {
                    "followers_count": 500,
                    "tweet_count": 200
                }
            }
        }

        response = client.get(f'/refresh-account/{account_id}', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            updated = dbs.session.get(LinkedAccount, account_id)
            assert updated.follower_count == 500
            assert updated.post_count == 200


@pytest.mark.integration
class TestDisconnectAccountRoute:
    """Test account disconnection"""

    def test_disconnect_account_not_logged_in(self, client):
        """Test disconnect requires login"""
        response = client.get('/disconnect-account/1', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_disconnect_account_not_found(self, client):
        """Test disconnect nonexistent account"""
        with app.app_context():
            user = User(email="disconnect_notfound@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/disconnect-account/99999', follow_redirects=False)
        assert response.status_code == 302
        assert '/linked-accounts' in response.location

    def test_disconnect_account_success(self, client):
        """Test successful account disconnection"""
        with app.app_context():
            user = User(email="disconnect_success@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get(f'/disconnect-account/{account_id}', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            deleted = dbs.session.get(LinkedAccount, account_id)
            assert deleted is None


@pytest.mark.integration
class TestPostSchedulerRoute:
    """Test post scheduler page access"""

    def test_post_scheduler_not_logged_in(self, client):
        """Test post scheduler requires login"""
        response = client.get('/post-scheduler', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_post_scheduler_no_accounts_redirects(self, client):
        """Test post scheduler redirects when no accounts linked"""
        with app.app_context():
            user = User(email="scheduler_noaccounts@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/post-scheduler', follow_redirects=False)
        assert response.status_code == 302
        assert '/linked-accounts' in response.location

    def test_post_scheduler_with_accounts(self, client):
        """Test post scheduler loads with linked accounts"""
        with app.app_context():
            user = User(email="scheduler_success@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/post-scheduler')
        assert response.status_code == 200


@pytest.mark.integration
class TestGetPostsAPIRoute:
    """Test GET /api/posts endpoint"""

    def test_get_posts_not_logged_in(self, client):
        """Test get posts requires authentication"""
        response = client.get('/api/posts')
        assert response.status_code == 401

    def test_get_posts_empty(self, client):
        """Test get posts with no posts"""
        with app.app_context():
            user = User(email="getposts_empty@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/api/posts')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_posts_with_filter(self, client):
        """Test get posts with status filter"""
        with app.app_context():
            user = User(email="getposts_filter@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()

            post1 = Post(user_id=user.user_id, content_text="Draft post", status='draft')
            post2 = Post(user_id=user.user_id, content_text="Published post", status='published')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/api/posts?status=draft')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['status'] == 'draft'

    def test_get_posts_with_limit(self, client):
        """Test get posts with limit parameter"""
        with app.app_context():
            user = User(email="getposts_limit@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()

            for i in range(5):
                post = Post(user_id=user.user_id, content_text=f"Post {i}", status='published')
                dbs.session.add(post)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/api/posts?limit=3')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3


@pytest.mark.integration
class TestHomeRoute:
    """Test home page routing logic"""

    def test_home_not_logged_in_redirects_to_login(self, client):
        """Test home redirects to login when not authenticated"""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_home_manager_redirects_to_manager_dashboard(self, client):
        """Test home redirects manager to manager dashboard"""
        with app.app_context():
            user = User(email="home_manager@test.com", full_name="Manager", role="manager")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'manager'

        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/dashboard/manager' in response.location

    def test_home_user_redirects_to_linked_accounts(self, client):
        """Test home redirects user to linked accounts"""
        with app.app_context():
            user = User(email="home_user@test.com", full_name="User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/linked-accounts' in response.location


if __name__ == '__main__':
    pytest.main([__file__, '-v'])