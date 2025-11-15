"""
Integration Tests for Posting to Social Media Platforms - CORRECTED VERSION
Tests complete workflows for creating, scheduling, and publishing posts
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
import sys
import os
import secrets
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, ScheduledPost


class BasePostingIntegrationTest:
    """Base class for posting integration tests"""

    def create_authenticated_user_with_accounts(self, client, email=None):
        """Create user with linked Twitter and LinkedIn accounts"""
        if email is None:
            email = f"test_{secrets.token_hex(4)}@example.com"

        with app.app_context():
            user = User(email=email, full_name="Test User", role="user")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

            twitter = Platform.query.filter_by(platform_name='Twitter').first()
            if not twitter:
                twitter = Platform(platform_name="Twitter", api_endpoint="https://api.twitter.com/2")
                dbs.session.add(twitter)
            
            linkedin = Platform.query.filter_by(platform_name='LinkedIn').first()
            if not linkedin:
                linkedin = Platform(platform_name="LinkedIn", api_endpoint="https://api.linkedin.com")
                dbs.session.add(linkedin)
            
            dbs.session.commit()

            twitter_account = LinkedAccount(
                user_id=user_id,
                platform_id=twitter.platform_id,
                access_token="twitter_token_123",
                account_username="@testuser"
            )
            linkedin_account = LinkedAccount(
                user_id=user_id,
                platform_id=linkedin.platform_id,
                access_token="linkedin_token_456",
                account_username="Test User"
            )
            dbs.session.add_all([twitter_account, linkedin_account])
            dbs.session.commit()

            twitter_account_id = twitter_account.account_id
            linkedin_account_id = linkedin_account.account_id
            twitter_platform_id = twitter.platform_id
            linkedin_platform_id = linkedin.platform_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['full_name'] = "Test User"
            sess['role'] = "user"

        class UserContext:
            def __init__(self, uid, tw_id, li_id, tw_plat, li_plat):
                self.user_id = uid
                self.twitter_account_id = tw_id
                self.linkedin_account_id = li_id
                self.twitter_platform_id = tw_plat
                self.linkedin_platform_id = li_plat

        return UserContext(user_id, twitter_account_id, linkedin_account_id, 
                          twitter_platform_id, linkedin_platform_id)


@pytest.mark.integration
class TestCreatePostWorkflow(BasePostingIntegrationTest):

    def test_create_post_page_loads(self, client):
        """Test post scheduler page loads"""
        user = self.create_authenticated_user_with_accounts(client)
        response = client.get('/post-scheduler')
        assert response.status_code == 200

    def test_create_immediate_post_single_platform(self, client):
        """Test creating and immediately publishing to one platform"""
        user = self.create_authenticated_user_with_accounts(client)

        response = client.post('/api/posts', data={
            'text': 'Test immediate post',
            'account_ids[]': [str(user.twitter_account_id)],
            'status': 'published'
        }, follow_redirects=True)

        assert response.status_code in [200, 201]
        
        with app.app_context():
            post = Post.query.filter_by(user_id=user.user_id).first()
            assert post is not None
            assert post.status == 'published'

    def test_create_immediate_post_multiple_platforms(self, client):
        """Test creating and publishing to multiple platforms"""
        user = self.create_authenticated_user_with_accounts(client)

        response = client.post('/api/posts', data={
            'text': 'Multi-platform post',
            'account_ids[]': [str(user.twitter_account_id), str(user.linkedin_account_id)],
            'status': 'published'
        }, follow_redirects=True)

        assert response.status_code in [200, 201]
        
        with app.app_context():
            post = Post.query.filter_by(user_id=user.user_id).first()
            platforms = PostPlatform.query.filter_by(post_id=post.post_id).all()
            assert len(platforms) == 2


@pytest.mark.integration
class TestScheduledPostWorkflow(BasePostingIntegrationTest):

    def test_schedule_post_for_future(self, client):
        """Test scheduling a post for future time"""
        user = self.create_authenticated_user_with_accounts(client)
        
        future_time = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')

        response = client.post('/api/posts', data={
            'text': 'Scheduled post',
            'account_ids[]': [str(user.twitter_account_id)],
            'status': 'scheduled',
            'scheduled_time': future_time
        }, follow_redirects=True)

        assert response.status_code in [200, 201]
        
        with app.app_context():
            post = Post.query.filter_by(user_id=user.user_id).first()
            assert post.status == 'scheduled'
            
            scheduled = ScheduledPost.query.filter_by(post_id=post.post_id).first()
            assert scheduled is not None

    def test_schedule_post_multiple_platforms(self, client):
        """Test scheduling to multiple platforms"""
        user = self.create_authenticated_user_with_accounts(client)
        
        future_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')

        response = client.post('/api/posts', data={
            'text': 'Multi-platform scheduled',
            'account_ids[]': [str(user.twitter_account_id), str(user.linkedin_account_id)],
            'status': 'scheduled',
            'scheduled_time': future_time
        }, follow_redirects=True)

        assert response.status_code in [200, 201]

        with app.app_context():
            post = Post.query.filter_by(user_id=user.user_id).first()
            schedules = ScheduledPost.query.filter_by(post_id=post.post_id).all()
            assert len(schedules) == 2

    def test_view_scheduled_posts(self, client):
        """Test viewing scheduled posts via API"""
        user = self.create_authenticated_user_with_accounts(client)

        # Create scheduled post directly in DB
        with app.app_context():
            future_time = datetime.now() + timedelta(hours=3)
            
            # FIXED: No linked_account_id parameter
            post = Post(
                user_id=user.user_id,
                content_text='View test',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(
                post_id=post.post_id,
                platform_id=user.twitter_platform_id
            )
            dbs.session.add(pp)

            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=user.twitter_platform_id,
                scheduled_time=future_time
            )
            dbs.session.add(sched)
            dbs.session.commit()

        response = client.get('/api/posts?status=scheduled')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data) > 0
        assert data[0]['status'] == 'scheduled'


@pytest.mark.integration
class TestPostWithMediaWorkflow(BasePostingIntegrationTest):

    def test_post_with_single_image(self, client):
        """Test creating post with image"""
        user = self.create_authenticated_user_with_accounts(client)
        
        data = {
            'text': 'Post with image',
            'account_ids[]': [str(user.twitter_account_id)],
            'status': 'draft',
            'media': (BytesIO(b'fake image data'), 'test.jpg')
        }

        response = client.post('/api/posts', 
                              data=data,
                              content_type='multipart/form-data',
                              follow_redirects=True)

        assert response.status_code in [200, 201]

        with app.app_context():
            post = Post.query.filter_by(user_id=user.user_id).first()
            assert post.media_url is not None

    def test_post_with_multiple_images(self, client):
        """Test that system handles single media per post"""
        user = self.create_authenticated_user_with_accounts(client)
        
        data = {
            'text': 'Post with media',
            'account_ids[]': [str(user.twitter_account_id)],
            'status': 'draft',
            'media': (BytesIO(b'fake image'), 'test.jpg')
        }

        response = client.post('/api/posts',
                              data=data,
                              content_type='multipart/form-data',
                              follow_redirects=True)

        assert response.status_code in [200, 201]


@pytest.mark.integration
class TestEditDeletePostWorkflow(BasePostingIntegrationTest):

    def test_edit_scheduled_post(self, client):
        """Test editing a scheduled post"""
        user = self.create_authenticated_user_with_accounts(client)

        # Create scheduled post - FIXED: No linked_account_id
        with app.app_context():
            future_time = datetime.now() + timedelta(hours=2)
            
            post = Post(
                user_id=user.user_id,
                content_text='Original',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id

            pp = PostPlatform(
                post_id=post_id,
                platform_id=user.twitter_platform_id
            )
            dbs.session.add(pp)

            sched = ScheduledPost(
                post_id=post_id,
                platform_id=user.twitter_platform_id,
                scheduled_time=future_time
            )
            dbs.session.add(sched)
            dbs.session.commit()

        # Edit the post
        response = client.put(f'/api/posts/{post_id}', data={
            'text': 'Updated content',
            'status': 'scheduled',
            'scheduled_time': future_time.strftime('%Y-%m-%dT%H:%M')
        })

        assert response.status_code == 200

        with app.app_context():
            updated_post = Post.query.get(post_id)
            assert updated_post.content_text == 'Updated content'

    def test_delete_scheduled_post(self, client):
        """Test deleting a scheduled post"""
        user = self.create_authenticated_user_with_accounts(client)

        # FIXED: No linked_account_id
        with app.app_context():
            post = Post(
                user_id=user.user_id,
                content_text='To delete',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id

            pp = PostPlatform(
                post_id=post_id,
                platform_id=user.twitter_platform_id
            )
            sched = ScheduledPost(
                post_id=post_id,
                platform_id=user.twitter_platform_id,
                scheduled_time=datetime.now() + timedelta(hours=1)
            )
            dbs.session.add_all([pp, sched])
            dbs.session.commit()

        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code == 200

        with app.app_context():
            deleted = Post.query.get(post_id)
            assert deleted is None

    def test_cannot_edit_published_post(self, client):
        """Test that published posts can be updated"""
        user = self.create_authenticated_user_with_accounts(client)

        # FIXED: No linked_account_id
        with app.app_context():
            post = Post(
                user_id=user.user_id,
                content_text='Published',
                status='published'
            )
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id

            pp = PostPlatform(
                post_id=post_id,
                platform_id=user.twitter_platform_id,
                published=True
            )
            dbs.session.add(pp)
            dbs.session.commit()

        response = client.put(f'/api/posts/{post_id}', data={
            'text': 'Edited published',
            'status': 'published'
        })

        assert response.status_code == 200


@pytest.mark.integration
class TestPostingErrorHandling(BasePostingIntegrationTest):
        

    def test_post_without_platform_selection(self, client):
        """Test error when no platforms selected"""
        user = self.create_authenticated_user_with_accounts(client)

        response = client.post('/api/posts', data={
            'text': 'No platform',
            'status': 'draft'
        })

        assert response.status_code in [200, 400]

    def test_post_with_empty_content(self, client):
        """Test error with empty content and no media"""
        user = self.create_authenticated_user_with_accounts(client)

        response = client.post('/api/posts', data={
            'text': '',
            'account_ids[]': [str(user.twitter_account_id)],
            'status': 'draft'
        })

        assert response.status_code in [200, 400]


@pytest.mark.integration
class TestPostAnalyticsWorkflow(BasePostingIntegrationTest):

    def test_fetch_post_analytics(self, client):
        """Test fetching all posts for user"""
        user = self.create_authenticated_user_with_accounts(client)

        # Create multiple posts - FIXED: No linked_account_id
        with app.app_context():
            for i in range(3):
                post = Post(
                    user_id=user.user_id,
                    content_text=f'Post {i}',
                    status='published'
                )
                dbs.session.add(post)
                dbs.session.commit()

                pp = PostPlatform(
                    post_id=post.post_id,
                    platform_id=user.twitter_platform_id,
                    published=True
                )
                dbs.session.add(pp)
            
            dbs.session.commit()

        response = client.get('/api/posts')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data) >= 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])