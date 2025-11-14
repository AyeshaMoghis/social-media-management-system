"""
Unit tests for publishing functions (LinkedIn and Twitter)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.app import app, dbs, User, Platform, Post, ScheduledPost
from src.app import publish_to_linkedin, publish_to_twitter, check_and_publish_scheduled_posts


class TestPublishToLinkedIn:
    """Test LinkedIn publishing functionality"""

    def test_publish_to_linkedin_success(self, client):
        """Test successful LinkedIn post publishing"""
        with app.app_context():
            # Create test user and platform
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='linkedin',
                platform_user_id='linkedin_user_123',
                access_token='test_access_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            # Mock the requests.post call
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 201
                mock_response.json.return_value = {'id': 'urn:li:share:123456'}
                mock_post.return_value = mock_response

                result = publish_to_linkedin(platform.platform_id, 'Test post content')

                assert result is not None
                assert 'urn:li:share:123456' in result
                mock_post.assert_called_once()

    def test_publish_to_linkedin_with_invalid_platform(self, client):
        """Test LinkedIn publishing with non-existent platform"""
        with app.app_context():
            result = publish_to_linkedin(99999, 'Test content')
            assert result is None

    def test_publish_to_linkedin_api_error(self, client):
        """Test LinkedIn publishing with API error"""
        with app.app_context():
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='linkedin',
                platform_user_id='linkedin_user_123',
                access_token='test_access_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = 'Bad Request'
                mock_post.return_value = mock_response

                result = publish_to_linkedin(platform.platform_id, 'Test content')
                assert result is None


class TestPublishToTwitter:
    """Test Twitter publishing functionality"""

    def test_publish_to_twitter_success(self, client):
        """Test successful Twitter post publishing"""
        with app.app_context():
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='twitter',
                platform_user_id='twitter_user_123',
                access_token='test_access_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 201
                mock_response.json.return_value = {'data': {'id': '1234567890'}}
                mock_post.return_value = mock_response

                result = publish_to_twitter(platform.platform_id, 'Test tweet content')

                assert result is not None
                assert '1234567890' in result
                mock_post.assert_called_once()

    def test_publish_to_twitter_with_invalid_platform(self, client):
        """Test Twitter publishing with non-existent platform"""
        with app.app_context():
            result = publish_to_twitter(99999, 'Test content')
            assert result is None

    def test_publish_to_twitter_api_error(self, client):
        """Test Twitter publishing with API error"""
        with app.app_context():
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='twitter',
                platform_user_id='twitter_user_123',
                access_token='test_access_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 403
                mock_response.text = 'Forbidden'
                mock_post.return_value = mock_response

                result = publish_to_twitter(platform.platform_id, 'Test content')
                assert result is None


class TestScheduledPostChecker:
    """Test scheduled post checking and publishing"""

    def test_check_scheduled_posts_publishes_due_posts(self, client):
        """Test that due scheduled posts are published"""
        with app.app_context():
            # Create user
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            # Create platform
            platform = Platform(
                user_id=user.user_id,
                platform_name='twitter',
                platform_user_id='twitter_123',
                access_token='test_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            # Create post
            post = Post(
                user_id=user.user_id,
                content_text='Test scheduled post',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            # Create scheduled post (in the past, so it's due)
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=datetime(2020, 1, 1, 12, 0),
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()

            # Mock the publishing functions
            with patch('src.app.publish_to_twitter') as mock_twitter:
                mock_twitter.return_value = 'tweet_id_123'

                # Run the checker
                check_and_publish_scheduled_posts()

                # Verify publishing was attempted
                mock_twitter.assert_called_once()

                # Verify status updated
                dbs.session.refresh(scheduled)
                assert scheduled.status == 'published'
                assert scheduled.published_at is not None

    def test_check_scheduled_posts_skips_future_posts(self, client):
        """Test that future scheduled posts are not published"""
        with app.app_context():
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='twitter',
                platform_user_id='twitter_123',
                access_token='test_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text='Future post',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            # Schedule for far future
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=datetime(2030, 12, 31, 23, 59),
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()

            with patch('src.app.publish_to_twitter') as mock_twitter:
                check_and_publish_scheduled_posts()

                # Should not be called for future posts
                mock_twitter.assert_not_called()

                # Status should remain scheduled
                dbs.session.refresh(scheduled)
                assert scheduled.status == 'scheduled'

    def test_check_scheduled_posts_handles_errors(self, client):
        """Test that publishing errors are handled gracefully"""
        with app.app_context():
            user = User(email='test@test.com', full_name='Test User', role='user')
            dbs.session.add(user)
            dbs.session.commit()

            platform = Platform(
                user_id=user.user_id,
                platform_name='linkedin',
                platform_user_id='linkedin_123',
                access_token='test_token',
                expires_at=datetime(2030, 1, 1)
            )
            dbs.session.add(platform)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text='Test post',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=datetime(2020, 1, 1, 12, 0),
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()

            # Mock publishing to return None (failure)
            with patch('src.app.publish_to_linkedin') as mock_linkedin:
                mock_linkedin.return_value = None

                check_and_publish_scheduled_posts()

                # Status should be updated to failed
                dbs.session.refresh(scheduled)
                assert scheduled.status == 'failed'
                assert scheduled.error_message is not None
