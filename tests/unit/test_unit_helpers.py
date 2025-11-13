"""
Comprehensive Unit Tests for Helper Functions and Utilities
Covers all helper functions to increase code coverage to 90+
"""

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import datetime, timedelta
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import (
    app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, ScheduledPost,
    OAuthState, current_user, cleanup_old_oauth_states, allowed_file, get_file_type,
    check_and_publish_scheduled_posts, refresh_twitter_token,
    publish_to_twitter, publish_to_linkedin, publish_to_platform,
    delete_tweet
)


@pytest.mark.unit
class TestHelperFunctions:
    """Test all helper functions"""

    

    def test_current_user_without_session(self):
        """Test current_user returns None without session"""
        with app.test_request_context():
            from flask import session
            session.clear()
            user = current_user()
            assert user is None

    def test_cleanup_old_oauth_states(self):
        """Test cleanup removes old OAuth states"""
        with app.app_context():
            # Create old state (15 minutes ago)
            old_state = OAuthState(
                state_id="old_cleanup_test",
                user_id=1,
                platform="twitter",
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
            
            # Create new state (5 minutes ago)
            new_state = OAuthState(
                state_id="new_cleanup_test",
                user_id=1,
                platform="linkedin",
                created_at=datetime.utcnow() - timedelta(minutes=5)
            )
            
            dbs.session.add(old_state)
            dbs.session.add(new_state)
            dbs.session.commit()
            
            # Run cleanup
            cleanup_old_oauth_states()
            
            # Old state should be deleted
            assert dbs.session.get(OAuthState, "old_cleanup_test") is None
            # New state should remain
            assert dbs.session.get(OAuthState, "new_cleanup_test") is not None

    def test_allowed_file_valid_extensions(self):
        """Test allowed_file accepts valid file extensions"""
        assert allowed_file("image.png") == True
        assert allowed_file("photo.jpg") == True
        assert allowed_file("pic.jpeg") == True
        assert allowed_file("animation.gif") == True
        assert allowed_file("video.mp4") == True
        assert allowed_file("clip.mov") == True
        assert allowed_file("movie.avi") == True
        assert allowed_file("web.webm") == True

    def test_allowed_file_invalid_extensions(self):
        """Test allowed_file rejects invalid file extensions"""
        assert allowed_file("document.pdf") == False
        assert allowed_file("script.exe") == False
        assert allowed_file("data.txt") == False
        assert allowed_file("noextension") == False

    def test_allowed_file_case_insensitive(self):
        """Test allowed_file is case insensitive"""
        assert allowed_file("IMAGE.PNG") == True
        assert allowed_file("Video.MP4") == True
        assert allowed_file("Photo.JpEg") == True

    def test_get_file_type_images(self):
        """Test get_file_type correctly identifies images"""
        assert get_file_type("photo.png") == "image"
        assert get_file_type("pic.jpg") == "image"
        assert get_file_type("image.jpeg") == "image"
        assert get_file_type("animation.gif") == "image"

    def test_get_file_type_videos(self):
        """Test get_file_type correctly identifies videos"""
        assert get_file_type("video.mp4") == "video"
        assert get_file_type("clip.mov") == "video"
        assert get_file_type("movie.avi") == "video"
        assert get_file_type("web.webm") == "video"

    def test_get_file_type_unknown(self):
        """Test get_file_type returns None for unknown types"""
        assert get_file_type("document.pdf") is None
        assert get_file_type("script.exe") is None

    def test_get_file_type_case_insensitive(self):
        """Test get_file_type is case insensitive"""
        assert get_file_type("IMAGE.PNG") == "image"
        assert get_file_type("VIDEO.MP4") == "video"


@pytest.mark.unit
class TestScheduledPostsFunctions:
    """Test scheduled posts helper functions"""

    def test_check_and_publish_scheduled_posts_no_posts(self):
        """Test check_and_publish when no scheduled posts exist"""
        with app.app_context():
            count = check_and_publish_scheduled_posts()
            assert count == 0

    def test_check_and_publish_scheduled_posts_future_posts(self):
        """Test that future scheduled posts are not published"""
        with app.app_context():
            user = User(email="future_post@test.com", full_name="Test User")
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform.query.filter_by(platform_name='Twitter').first()
            if not platform:
                platform = Platform(platform_name="Twitter")
                dbs.session.add(platform)
                dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Future post",
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            future_time = datetime.now() + timedelta(hours=2)
            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=future_time,
                status='scheduled'
            )
            dbs.session.add(sched)
            dbs.session.commit()

            # Should not publish future posts
            count = check_and_publish_scheduled_posts()
            assert count == 0

            # Status should remain scheduled
            updated_sched = ScheduledPost.query.get(sched.schedule_id)
            assert updated_sched.status == 'scheduled'

    def test_check_and_publish_scheduled_posts_past_posts(self):
        """Test that past scheduled posts are published"""
        with app.app_context():
            user = User(email="past_post@test.com", full_name="Test User")
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform.query.filter_by(platform_name='Twitter').first()
            if not platform:
                platform = Platform(platform_name="Twitter")
                dbs.session.add(platform)
                dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Past post",
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id
            )
            dbs.session.add(pp)
            dbs.session.commit()

            # Create scheduled post in the past
            past_time = datetime.now() - timedelta(minutes=5)
            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=past_time,
                status='scheduled'
            )
            dbs.session.add(sched)
            dbs.session.commit()

            # Should publish past posts
            count = check_and_publish_scheduled_posts()
            assert count == 1

            # Status should be updated to published
            updated_sched = ScheduledPost.query.get(sched.schedule_id)
            assert updated_sched.status == 'published'

            updated_post = Post.query.get(post.post_id)
            assert updated_post.status == 'published'

    def test_check_and_publish_handles_errors(self):
        """Test that check_and_publish handles errors gracefully"""
        with app.app_context():
            with patch('src.app.ScheduledPost.query') as mock_query:
                mock_query.filter.side_effect = Exception("Database error")
                
                count = check_and_publish_scheduled_posts()
                assert count == 0  # Should return 0 on error


@pytest.mark.unit
class TestTwitterPublishingFunctions:
    """Test Twitter publishing helper functions"""

    @patch('src.app.requests.post')
    def test_publish_to_twitter_success(self, mock_post):
        """Test successful Twitter post publication"""
        with app.app_context():
            user = User(email="twitter_pub@test.com", full_name="Test User")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="valid_token",
                account_username="@testuser"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test tweet",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            # Mock successful Twitter API response
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "data": {"id": "1234567890"}
            }

            success, result = publish_to_twitter(post, account)
            
            assert success == True
            assert result == "1234567890"

    @patch('src.app.requests.post')
    def test_publish_to_twitter_failure(self, mock_post):
        """Test failed Twitter post publication"""
        with app.app_context():
            user = User(email="twitter_fail@test.com", full_name="Test User")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="invalid_token",
                account_username="@testuser"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test tweet",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            # Mock failed Twitter API response
            mock_post.return_value.status_code = 403
            mock_post.return_value.json.return_value = {
                "detail": "Forbidden"
            }
            mock_post.return_value.text = "Forbidden"

            success, result = publish_to_twitter(post, account)
            
            assert success == False
            assert "Forbidden" in result

    @patch('src.app.requests.post')
    @patch('src.app.refresh_twitter_token')
    def test_publish_to_twitter_token_refresh(self, mock_refresh, mock_post):
        """Test Twitter publish with token refresh on 401"""
        with app.app_context():
            user = User(email="twitter_refresh@test.com", full_name="Test User")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="expired_token",
                refresh_token="refresh_token",
                account_username="@testuser"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test tweet",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            # First call returns 401, second call succeeds
            mock_post.return_value.status_code = 401
            mock_refresh.return_value = "new_token"
            
            # Change behavior after refresh
            def side_effect(*args, **kwargs):
                if mock_post.call_count == 1:
                    response = MagicMock()
                    response.status_code = 401
                    return response
                else:
                    response = MagicMock()
                    response.status_code = 201
                    response.json.return_value = {"data": {"id": "123"}}
                    return response
            
            mock_post.side_effect = side_effect

            success, result = publish_to_twitter(post, account)
            
            assert mock_refresh.called
            assert success == True

    @patch('src.app.requests.post')
    def test_publish_to_twitter_exception(self, mock_post):
        """Test Twitter publish handles exceptions"""
        with app.app_context():
            user = User(email="twitter_exception@test.com", full_name="Test User")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                account_username="@testuser"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test tweet",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            mock_post.side_effect = Exception("Network error")

            success, result = publish_to_twitter(post, account)
            
            assert success == False
            assert "Network error" in result


@pytest.mark.unit
class TestLinkedInPublishingFunctions:
    """Test LinkedIn publishing helper functions"""

    @patch('src.app.requests.post')
    def test_publish_to_linkedin_success(self, mock_post):
        """Test successful LinkedIn post publication"""
        with app.app_context():
            user = User(email="linkedin_pub@test.com", full_name="Test User")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="valid_token",
                external_id="abc123",
                account_username="Test User"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test LinkedIn post",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            # Mock successful LinkedIn API response
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "id": "urn:li:share:123456"
            }
            mock_post.return_value.headers = {}
            mock_post.return_value.text = '{"id":"urn:li:share:123456"}'

            success, result = publish_to_linkedin(post, account)
            
            assert success == True
            assert "123456" in result or "urn" in result

    @patch('src.app.requests.post')
    def test_publish_to_linkedin_no_token(self, mock_post):
        """Test LinkedIn publish fails without access token"""
        with app.app_context():
            user = User(email="linkedin_notoken@test.com", full_name="Test User")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token=None,  # No token
                account_username="Test User"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test post",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            success, result = publish_to_linkedin(post, account)
            
            assert success == False
            assert "No access token" in result

    @patch('src.app.requests.post')
    def test_publish_to_linkedin_api_error(self, mock_post):
        """Test LinkedIn publish handles API errors"""
        with app.app_context():
            user = User(email="linkedin_error@test.com", full_name="Test User")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                external_id="abc123",
                account_username="Test User"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Test post",
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            mock_post.return_value.status_code = 400
            mock_post.return_value.text = "Bad Request"

            success, result = publish_to_linkedin(post, account)
            
            assert success == False
            assert "400" in result


@pytest.mark.unit
class TestPublishToPlatform:
    """Test platform-agnostic publishing function"""

    @patch('src.app.publish_to_twitter')
    def test_publish_to_platform_twitter(self, mock_twitter):
        """Test publish_to_platform calls correct Twitter function"""
        with app.app_context():
            user = User(email="platform_twitter@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(user_id=user.user_id, content_text="Test")
            dbs.session.add(post)
            dbs.session.commit()

            mock_twitter.return_value = (True, "tweet_123")

            success, result = publish_to_platform(post, account)
            
            assert mock_twitter.called
            assert success == True

    @patch('src.app.publish_to_linkedin')
    def test_publish_to_platform_linkedin(self, mock_linkedin):
        """Test publish_to_platform calls correct LinkedIn function"""
        with app.app_context():
            user = User(email="platform_linkedin@test.com", full_name="Test")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                external_id="abc"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(user_id=user.user_id, content_text="Test")
            dbs.session.add(post)
            dbs.session.commit()

            mock_linkedin.return_value = (True, "post_123")

            success, result = publish_to_platform(post, account)
            
            assert mock_linkedin.called
            assert success == True

    def test_publish_to_platform_unsupported(self):
        """Test publish_to_platform handles unsupported platforms"""
        with app.app_context():
            user = User(email="platform_unsupported@test.com", full_name="Test")
            platform = Platform(platform_name="Instagram")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(user_id=user.user_id, content_text="Test")
            dbs.session.add(post)
            dbs.session.commit()

            success, result = publish_to_platform(post, account)
            
            assert success == False
            assert "not supported" in result


@pytest.mark.unit
class TestTwitterTokenRefresh:
    """Test Twitter token refresh functionality"""

    @patch('src.app.requests.post')
    def test_refresh_twitter_token_success(self, mock_post):
        """Test successful token refresh"""
        with app.app_context():
            user = User(email="refresh_success@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="old_token",
                refresh_token="refresh_token",
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()

            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "access_token": "new_token",
                "refresh_token": "new_refresh"
            }

            new_token = refresh_twitter_token(account)
            
            assert new_token == "new_token"
            assert account.access_token == "new_token"
            assert account.refresh_token == "new_refresh"

    @patch('src.app.requests.post')
    def test_refresh_twitter_token_failure(self, mock_post):
        """Test failed token refresh"""
        with app.app_context():
            user = User(email="refresh_fail@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="old_token",
                refresh_token="invalid_refresh",
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()

            mock_post.return_value.status_code = 400
            mock_post.return_value.json.return_value = {
                "error": "invalid_grant"
            }

            new_token = refresh_twitter_token(account)
            
            assert new_token is None

    @patch('src.app.requests.post')
    def test_refresh_twitter_token_exception(self, mock_post):
        """Test token refresh handles exceptions"""
        with app.app_context():
            user = User(email="refresh_exception@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                refresh_token="refresh",
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()

            mock_post.side_effect = Exception("Network error")

            new_token = refresh_twitter_token(account)
            
            assert new_token is None


@pytest.mark.unit
class TestDeleteTweet:
    """Test tweet deletion functionality"""

    @patch('src.app.requests.delete')
    def test_delete_tweet_success(self, mock_delete):
        """Test successful tweet deletion"""
        with app.app_context():
            user = User(email="delete_success@test.com", full_name="Test")
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

            mock_delete.return_value.status_code = 200

            result = delete_tweet(account, "1234567890")
            
            assert result == True

    @patch('src.app.requests.delete')
    def test_delete_tweet_failure(self, mock_delete):
        """Test failed tweet deletion"""
        with app.app_context():
            user = User(email="delete_fail@test.com", full_name="Test")
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

            mock_delete.return_value.status_code = 404
            mock_delete.return_value.text = "Not found"

            result = delete_tweet(account, "nonexistent")
            
            assert result == False

    @patch('src.app.requests.delete')
    @patch('src.app.refresh_twitter_token')
    def test_delete_tweet_with_token_refresh(self, mock_refresh, mock_delete):
        """Test tweet deletion with token refresh on 401"""
        with app.app_context():
            user = User(email="delete_refresh@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="expired_token",
                refresh_token="refresh",
                account_username="@test"
            )
            dbs.session.add(account)
            dbs.session.commit()

            # First call returns 401, second succeeds
            def side_effect(*args, **kwargs):
                if mock_delete.call_count == 1:
                    response = MagicMock()
                    response.status_code = 401
                    return response
                else:
                    response = MagicMock()
                    response.status_code = 200
                    return response
            
            mock_delete.side_effect = side_effect
            mock_refresh.return_value = "new_token"

            result = delete_tweet(account, "1234567890")
            
            assert mock_refresh.called
            assert result == True

    @patch('src.app.requests.delete')
    def test_delete_tweet_exception(self, mock_delete):
        """Test delete_tweet handles exceptions"""
        with app.app_context():
            user = User(email="delete_exception@test.com", full_name="Test")
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

            mock_delete.side_effect = Exception("Network error")

            result = delete_tweet(account, "1234567890")
            
            assert result == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])