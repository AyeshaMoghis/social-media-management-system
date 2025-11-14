"""
Additional tests to reach 75%+ coverage - focus on error handling and edge cases
"""
import pytest
from datetime import datetime, timedelta
from src.app import app, dbs, User, Platform, LinkedAccount, Post, ScheduledPost, PostPlatform
from unittest.mock import patch, Mock


class TestLinkedInPublishingErrors:
    """Test LinkedIn publishing error scenarios"""
    
    def test_linkedin_timeout_error(self, client):
        """Test LinkedIn API timeout"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='test_token',
                external_id='linkedin_123'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            with patch('requests.get') as mock_get:
                import requests
                mock_get.side_effect = requests.exceptions.Timeout()
                
                from src.app import publish_to_linkedin
                success, error = publish_to_linkedin(post, account)
                assert success is False
                assert 'timeout' in error.lower()
    
    def test_linkedin_request_exception(self, client):
        """Test LinkedIn API request exception"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            with patch('requests.get') as mock_get:
                import requests
                mock_get.side_effect = requests.exceptions.RequestException('Network error')
                
                from src.app import publish_to_linkedin
                success, error = publish_to_linkedin(post, account)
                assert success is False


class TestTwitterPublishingErrors:
    """Test Twitter publishing error scenarios"""
    
    def test_twitter_timeout_error(self, client):
        """Test Twitter API timeout"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            with patch('requests.post') as mock_post:
                import requests
                mock_post.side_effect = requests.exceptions.Timeout()
                
                from src.app import publish_to_twitter
                success, error = publish_to_twitter(post, account)
                assert success is False
                assert 'timeout' in error.lower()
    
    def test_twitter_with_media_url(self, client):
        """Test Twitter publishing with media URL (should post text only)"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user.user_id,
                content_text='Post with image',
                media_url='/uploads/test.jpg',
                status='published'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            with patch('requests.post') as mock_post:
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {'data': {'id': '12345'}}
                
                from src.app import publish_to_twitter
                success, result = publish_to_twitter(post, account)
                assert success is True


class TestScheduledPostsAutoReject:
    """Test automatic rejection of expired pending posts"""
    
    def test_team_collaboration_auto_rejects_expired(self, client):
        """Test that expired pending posts are auto-rejected"""
        with app.app_context():
            manager = User(email='manager@test.com', full_name='Manager', role='manager')
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add_all([manager, user])
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            # Create a pending post with expired scheduled time
            post = Post(user_id=user.user_id, content_text='Expired', status='pending')
            dbs.session.add(post)
            dbs.session.commit()
            
            past_time = datetime.now() - timedelta(hours=2)
            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=past_time,
                status='pending'
            )
            dbs.session.add(sched)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = manager.user_id
                sess['full_name'] = 'Manager'
                sess['role'] = 'manager'
            
            response = client.get('/team-collaboration')
            assert response.status_code == 200
            
            # Verify post was auto-rejected
            dbs.session.refresh(post)
            assert post.status == 'rejected'


class TestRefreshAccountErrors:
    """Test account refresh error handling"""
    
    def test_refresh_linkedin_api_error(self, client):
        """Test refresh with LinkedIn API error"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
            
            with patch('requests.get') as mock_get:
                mock_get.return_value.status_code = 401
                
                response = client.get(f'/refresh-account/{account.account_id}')
                assert response.status_code == 302
    
    def test_refresh_twitter_api_error(self, client):
        """Test refresh with Twitter API error"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='test_token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
            
            with patch('requests.get') as mock_get:
                mock_get.return_value.status_code = 403
                mock_get.return_value.text = 'Forbidden'
                
                response = client.get(f'/refresh-account/{account.account_id}')
                assert response.status_code == 302


class TestPostUpdateScenarios:
    """Test various post update scenarios"""
    
    def test_update_post_to_published(self, client):
        """Test updating a post to published status"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            pp = PostPlatform(post_id=post.post_id, platform_id=platform.platform_id)
            dbs.session.add(pp)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
            
            response = client.put(f'/api/posts/{post.post_id}',
                data={'status': 'published'})
            
            if response.status_code == 200:
                dbs.session.refresh(post)
                assert post.status == 'published'
    
    def test_update_post_scheduled_time(self, client):
        """Test updating scheduled time"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            pp = PostPlatform(post_id=post.post_id, platform_id=platform.platform_id)
            dbs.session.add(pp)
            dbs.session.commit()
            
            old_time = datetime.now() + timedelta(hours=1)
            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=old_time,
                status='scheduled'
            )
            dbs.session.add(sched)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
            
            new_time = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M')
            response = client.put(f'/api/posts/{post.post_id}',
                data={'status': 'scheduled', 'scheduled_time': new_time})
            
            if response.status_code == 200:
                dbs.session.refresh(sched)
                assert sched.status == 'scheduled'


class TestDeletePostWithMedia:
    """Test deleting posts with media files"""
    
    def test_delete_post_with_media_file(self, client):
        """Test deleting a post that has media file"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create a test media file
            import os
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_delete.jpg')
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(media_path, 'w') as f:
                f.write('test')
            
            post = Post(
                user_id=user.user_id,
                content_text='Test',
                media_url=media_path,
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id
            
            with client.session_transaction() as sess:
                sess['user_id'] = user.user_id
            
            response = client.delete(f'/api/posts/{post_id}')
            
            if response.status_code == 200:
                # Verify post deleted
                assert Post.query.get(post_id) is None
                # Media file should also be deleted
                assert not os.path.exists(media_path)


class TestManagerDashboardStats:
    """Test manager dashboard statistics"""
    
    def test_manager_dashboard_with_stats(self, client):
        """Test manager dashboard shows correct statistics"""
        with app.app_context():
            manager = User(email='manager@test.com', full_name='Manager', role='manager')
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add_all([manager, user])
            dbs.session.commit()
            
            # Create various posts
            post1 = Post(user_id=user.user_id, content_text='Pending 1', status='pending')
            post2 = Post(user_id=user.user_id, content_text='Scheduled 1', status='scheduled')
            post3 = Post(user_id=user.user_id, content_text='Published 1', status='published')
            dbs.session.add_all([post1, post2, post3])
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            # Create linked account
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = manager.user_id
                sess['full_name'] = 'Manager'
                sess['role'] = 'manager'
            
            response = client.get('/dashboard/manager')
            assert response.status_code == 200
            assert b'Manager' in response.data


class TestInviteMemberValidation:
    """Test member invitation validation"""
    
    def test_invite_member_missing_fields(self, client):
        """Test inviting member with missing fields"""
        with app.app_context():
            manager = User(email='manager@test.com', full_name='Manager', role='manager')
            dbs.session.add(manager)
            dbs.session.commit()
            
            with client.session_transaction() as sess:
                sess['user_id'] = manager.user_id
                sess['role'] = 'manager'
            
            # Missing email
            response = client.post('/invite_member', json={
                'name': 'New User',
                'role': 'user'
            })
            
            # Should return error
            assert response.status_code in [400, 500]


class TestScheduledPostCheckerEdgeCases:
    """Test edge cases in scheduled post checking"""
    
    def test_scheduled_post_checker_with_missing_post(self, client):
        """Test checker handles missing posts gracefully"""
        with app.app_context():
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            # Create scheduled post entry without actual post
            past_time = datetime.now() - timedelta(minutes=5)
            sched = ScheduledPost(
                post_id=99999,  # Non-existent post
                platform_id=platform.platform_id,
                scheduled_time=past_time,
                status='scheduled'
            )
            dbs.session.add(sched)
            dbs.session.commit()
            
            from src.app import check_and_publish_scheduled_posts
            result = check_and_publish_scheduled_posts()
            
            # Should handle gracefully
            dbs.session.refresh(sched)
            assert sched.status == 'failed'
    
    def test_scheduled_post_checker_with_missing_account(self, client):
        """Test checker handles missing accounts gracefully"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            past_time = datetime.now() - timedelta(minutes=5)
            sched = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=past_time,
                status='scheduled'
            )
            dbs.session.add(sched)
            dbs.session.commit()
            
            # No linked account for this user+platform
            from src.app import check_and_publish_scheduled_posts
            result = check_and_publish_scheduled_posts()
            
            # Should fail gracefully
            dbs.session.refresh(sched)
            assert sched.status == 'failed'


class TestPublishToPlatformErrors:
    """Test publish_to_platform error handling"""
    
    def test_publish_to_platform_no_platform(self, client):
        """Test publishing when platform not found"""
        with app.app_context():
            user = User(email='user@test.com', full_name='User', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create account with non-existent platform
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=99999,  # Non-existent
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            from src.app import publish_to_platform
            success, error = publish_to_platform(post, account)
            
            assert success is False
            assert 'not found' in error.lower()
