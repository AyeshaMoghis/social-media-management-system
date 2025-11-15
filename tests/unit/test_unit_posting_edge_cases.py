"""
Edge Cases and Additional Coverage for Posting API
Tests uncovered code paths in create, update, delete post operations
"""

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from datetime import datetime, timedelta
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, ScheduledPost


@pytest.mark.unit
class TestCreatePostEdgeCases:
    """Test edge cases in post creation"""

    def test_create_post_not_authenticated(self, client):
        """Test creating post without authentication"""
        response = client.post('/api/posts', data={
            'text': 'Test post',
            'status': 'draft'
        })
        assert response.status_code == 401

    def test_create_post_with_media_invalid_extension(self, client):
        """Test creating post with invalid file type"""
        with app.app_context():
            user = User(email="invalid_media@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.post('/api/posts', 
            data={
                'text': 'Post with invalid file',
                'account_ids[]': ['1'],
                'status': 'draft',
                'media': (BytesIO(b'fake pdf'), 'document.pdf')
            },
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid file type' in data['error']

    def test_create_post_with_invalid_scheduled_time_format(self, client):
        """Test creating post with invalid datetime format"""
        with app.app_context():
            user = User(email="invalid_time@test.com", full_name="Test")
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

        response = client.post('/api/posts', data={
            'text': 'Scheduled post',
            'account_ids[]': [str(account_id)],
            'status': 'scheduled',
            'scheduled_time': 'invalid-datetime-format'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid scheduled time format' in data['error']

    def test_create_post_scheduled_without_time(self, client):
        """Test creating scheduled post without scheduled_time"""
        with app.app_context():
            user = User(email="sched_notime@test.com", full_name="Test")
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

        response = client.post('/api/posts', data={
            'text': 'Scheduled without time',
            'account_ids[]': [str(account_id)],
            'status': 'scheduled'
            # No scheduled_time provided
        })

        # Should create as scheduled even without explicit time
        assert response.status_code == 201

    def test_create_draft_post(self, client):
        """Test creating draft post explicitly"""
        with app.app_context():
            user = User(email="draft@test.com", full_name="Test")
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

        response = client.post('/api/posts', data={
            'text': 'Draft post',
            'account_ids[]': [str(account_id)],
            'status': 'draft'
        })

        assert response.status_code == 201
        
        with app.app_context():
            post = Post.query.filter_by(user_id=user_id).first()
            assert post.status == 'draft'

    @patch('src.app.publish_to_twitter')
    def test_create_published_post_with_failure(self, mock_publish, client):
        """Test creating published post when platform publish fails"""
        with app.app_context():
            user = User(email="pub_fail@test.com", full_name="Test")
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

        mock_publish.return_value = (False, "API Error")

        response = client.post('/api/posts', data={
            'text': 'Publish fail',
            'account_ids[]': [str(account_id)],
            'status': 'published'
        })

        assert response.status_code == 201
        
        with app.app_context():
            post = Post.query.filter_by(user_id=user_id).first()
            pp = PostPlatform.query.filter_by(post_id=post.post_id).first()
            assert pp.published == False
            assert pp.error_message == "API Error"

    def test_create_post_exception_handling(self, client):
        """Test post creation handles exceptions properly"""
        with app.app_context():
            user = User(email="exception@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        with patch('src.app.LinkedAccount.query') as mock_query:
            mock_query.get.side_effect = Exception("Database error")

            response = client.post('/api/posts', data={
                'text': 'Exception test',
                'account_ids[]': ['1'],
                'status': 'draft'
            })

            assert response.status_code == 500


@pytest.mark.unit
class TestUpdatePostEdgeCases:
    """Test edge cases in post update"""

    def test_update_post_not_authenticated(self, client):
        """Test updating post without authentication"""
        response = client.put('/api/posts/1', data={
            'text': 'Updated'
        })
        assert response.status_code == 401

    def test_update_post_not_found(self, client):
        """Test updating nonexistent post"""
        with app.app_context():
            user = User(email="update_notfound@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.put('/api/posts/99999', data={
            'text': 'Updated'
        })

        assert response.status_code == 404

    def test_update_post_to_draft(self, client):
        """Test updating post to draft status"""
        with app.app_context():
            user = User(email="update_draft@test.com", full_name="Test")
            platform = Platform(platform_name="Twitter")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Original",
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(post_id=post.post_id, platform_id=platform.platform_id)
            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=datetime.now() + timedelta(hours=1)
            )
            dbs.session.add_all([pp, sched])
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id
            sched_id = sched.schedule_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.put(f'/api/posts/{post_id}', data={
            'text': 'Updated to draft',
            'status': 'draft'
        })

        assert response.status_code == 200

        with app.app_context():
            # Scheduled post should be deleted
            assert ScheduledPost.query.get(sched_id) is None
            post = Post.query.get(post_id)
            assert post.status == 'draft'

    @patch('requests.delete')
    @patch('requests.post')
    def test_update_published_post_twitter(self, mock_post, mock_delete, client):
        """Test updating published Twitter post (delete and repost)"""
        with app.app_context():
            user = User(email="update_twitter@test.com", full_name="Test")
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

            post = Post(
                user_id=user.user_id,
                content_text="Original tweet",
                status='published'
            )
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                platform_post_id="tweet_123",
                published=True
            )
            dbs.session.add(pp)
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        mock_delete.return_value.status_code = 200
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "data": {"id": "new_tweet_456"}
        }

        response = client.put(f'/api/posts/{post_id}', data={
            'text': 'Updated tweet',
            'status': 'published'
        })

        assert response.status_code == 200
        assert mock_delete.called
        assert mock_post.called

    def test_update_published_post_linkedin_not_supported(self, client):
        """Test that LinkedIn published posts can't be edited"""
        with app.app_context():
            user = User(email="update_linkedin@test.com", full_name="Test")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                external_id="abc",
                account_username="Test User"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(
                user_id=user.user_id,
                content_text="Original post",
                status='published'
            )
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                platform_post_id="li_post_123",
                published=True
            )
            dbs.session.add(pp)
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.put(f'/api/posts/{post_id}', data={
            'text': 'Updated LinkedIn post',
            'status': 'published'
        })

        assert response.status_code == 200

        with app.app_context():
            pp = PostPlatform.query.filter_by(post_id=post_id).first()
            # Should have error message about LinkedIn not supporting edits
            assert pp.error_message is not None
            assert "doesn't support editing" in pp.error_message

    def test_update_post_invalid_scheduled_time(self, client):
        """Test updating post with invalid scheduled time format"""
        with app.app_context():
            user = User(email="update_invalidtime@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()

            post = Post(user_id=user.user_id, content_text="Test", status='draft')
            dbs.session.add(post)
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.put(f'/api/posts/{post_id}', data={
            'status': 'scheduled',
            'scheduled_time': 'bad-format'
        })

        assert response.status_code == 400

    def test_update_post_exception_handling(self, client):
        """Test update post handles exceptions"""
        with app.app_context():
            user = User(email="update_exception@test.com", full_name="Test")
            post = Post(user_id=1, content_text="Test", status='draft')
            dbs.session.add(user)
            dbs.session.add(post)
            dbs.session.commit()
            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        with patch('src.app.Post.query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.first.side_effect = Exception("Database error")
            mock_query.filter_by.return_value = mock_filter

            response = client.put(f'/api/posts/{post_id}', data={
                'text': 'Updated'
            })

            assert response.status_code == 500


@pytest.mark.unit
class TestDeletePostEdgeCases:
    """Test edge cases in post deletion"""

    def test_delete_post_not_authenticated(self, client):
        """Test deleting post without authentication"""
        response = client.delete('/api/posts/1')
        assert response.status_code == 401

    def test_delete_post_not_found(self, client):
        """Test deleting nonexistent post"""
        with app.app_context():
            user = User(email="delete_notfound@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.delete('/api/posts/99999')
        assert response.status_code == 404

    @patch('src.app.delete_tweet')
    def test_delete_post_with_twitter(self, mock_delete, client):
        """Test deleting post that was published to Twitter"""
        with app.app_context():
            user = User(email="delete_twitter@test.com", full_name="Test")
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

            post = Post(user_id=user.user_id, content_text="Test", status='published')
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                platform_post_id="tweet_123",
                published=True
            )
            dbs.session.add(pp)
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        mock_delete.return_value = True

        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code == 200
        assert mock_delete.called

    def test_delete_post_with_linkedin(self, client):
        """Test deleting post that was published to LinkedIn"""
        with app.app_context():
            user = User(email="delete_linkedin@test.com", full_name="Test")
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add_all([user, platform])
            dbs.session.commit()

            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token="token",
                external_id="abc",
                account_username="Test User"
            )
            dbs.session.add(account)
            dbs.session.commit()

            post = Post(user_id=user.user_id, content_text="Test", status='published')
            dbs.session.add(post)
            dbs.session.commit()

            pp = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                platform_post_id="li_post_123",
                published=True
            )
            dbs.session.add(pp)
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code == 200
        # LinkedIn deletion not supported, but post should still be deleted locally

    def test_delete_post_with_media_file(self, client):
        """Test deleting post removes associated media file"""
        with app.app_context():
            user = User(email="delete_media@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()

            # Create a fake media file
            upload_dir = app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            test_file = os.path.join(upload_dir, "test_delete.jpg")
            with open(test_file, 'wb') as f:
                f.write(b'test')

            post = Post(
                user_id=user.user_id,
                content_text="Post with media",
                media_url=test_file,
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()

            user_id = user.user_id
            post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code == 200
        # Media file should be deleted
        assert not os.path.exists(test_file)

    def test_delete_post_exception_handling(self, client):
        """Test delete post handles exceptions"""
        with app.app_context():
            user = User(email="delete_exception@test.com", full_name="Test")
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'

        with patch('src.app.Post.query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.first.side_effect = Exception("Database error")
            mock_query.filter_by.return_value = mock_filter

            response = client.delete('/api/posts/1')
            assert response.status_code == 500


if __name__ == '__main__':
    pytest.main([__file__, '-v'])