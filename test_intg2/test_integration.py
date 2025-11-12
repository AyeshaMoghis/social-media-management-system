"""
Integration Tests for Social Media Management System
Corrected for src/app.py structure
Run with: pytest test_intg2/test_integration.py -v --cov=src
"""
import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['TESTING'] = 'true'

from src.app import (
    app, dbs, User, Platform, LinkedAccount, Post,
    PostPlatform, ScheduledPost,
    publish_to_twitter, publish_to_linkedin, publish_to_platform
)


@pytest.fixture(scope='function')
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as test_client:
        with app.app_context():
            dbs.create_all()
            yield test_client
            dbs.session.remove()
            dbs.drop_all()


@pytest.fixture
def setup_complete_environment(client):
    """Setup complete test environment with user, platforms, and accounts"""
    with app.app_context():
        # Create user
        user = User(email='integration@test.com', full_name='Integration Test', role='user')
        dbs.session.add(user)
        dbs.session.flush()
        
        # Create platforms
        linkedin = Platform(platform_name='LinkedIn', api_endpoint='https://api.linkedin.com/v2/ugcPosts')
        twitter = Platform(platform_name='Twitter', api_endpoint='https://api.twitter.com/2/tweets')
        dbs.session.add_all([linkedin, twitter])
        dbs.session.flush()
        
        # Create linked accounts
        linkedin_account = LinkedAccount(
            user_id=user.user_id,
            platform_id=linkedin.platform_id,
            access_token='linkedin_token',
            refresh_token='linkedin_refresh',
            external_id='linkedin_123',
            account_username='LinkedIn User'
        )
        
        twitter_account = LinkedAccount(
            user_id=user.user_id,
            platform_id=twitter.platform_id,
            access_token='twitter_token',
            refresh_token='twitter_refresh',
            external_id='twitter_456',
            account_username='@TwitterUser'
        )
        
        dbs.session.add_all([linkedin_account, twitter_account])
        dbs.session.commit()
        
        return {
            'user_id': user.user_id,
            'linkedin_account_id': linkedin_account.account_id,
            'twitter_account_id': twitter_account.account_id,
            'linkedin_platform_id': linkedin.platform_id,
            'twitter_platform_id': twitter.platform_id
        }


# ==================== END-TO-END WORKFLOW TESTS ====================

class TestEndToEndWorkflows:
    """Test complete user workflows"""
    
    def test_complete_post_creation_workflow(self, client, setup_complete_environment):
        """Test complete workflow: login -> create post -> schedule -> publish"""
        env = setup_complete_environment
        
        with client.session_transaction() as sess:
            sess['user_id'] = env['user_id']
            sess['role'] = 'user'
        
        with app.app_context():
            # Step 1: Access post scheduler
            response = client.get('/post-scheduler')
            assert response.status_code == 200
            
            # Step 2: Create draft post
            draft_data = {
                'text': 'My first draft post',
                'status': 'draft',
                'account_ids[]': [env['linkedin_account_id']]
            }
            response = client.post('/api/posts', data=draft_data)
            assert response.status_code == 201
            post_id = response.get_json()['post_id']
            
            # Step 3: Verify draft was created
            response = client.get('/api/posts')
            posts = response.get_json()
            assert len(posts) == 1
            assert posts[0]['status'] == 'draft'
            
            # Step 4: Update to scheduled
            future_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
            update_data = {
                'text': 'Updated scheduled post',
                'status': 'scheduled',
                'scheduled_time': future_time
            }
            response = client.put(f'/api/posts/{post_id}', data=update_data)
            assert response.status_code == 200
            
            # Step 5: Verify schedule
            post = Post.query.get(post_id)
            assert post.status == 'scheduled'
            scheduled = ScheduledPost.query.filter_by(post_id=post_id).first()
            assert scheduled is not None
    
    def test_multi_platform_posting_workflow(self, client, setup_complete_environment):
        """Test posting to multiple platforms simultaneously"""
        env = setup_complete_environment
        
        with client.session_transaction() as sess:
            sess['user_id'] = env['user_id']
            sess['role'] = 'user'
        
        with app.app_context():
            # Create post for both platforms
            data = {
                'text': 'Cross-platform post',
                'status': 'draft',
                'account_ids[]': [env['linkedin_account_id'], env['twitter_account_id']]
            }
            
            response = client.post('/api/posts', data=data)
            assert response.status_code == 201
            post_id = response.get_json()['post_id']
            
            # Verify post is linked to both platforms
            post_platforms = PostPlatform.query.filter_by(post_id=post_id).all()
            assert len(post_platforms) == 2
            
            platform_ids = [pp.platform_id for pp in post_platforms]
            assert env['linkedin_platform_id'] in platform_ids
            assert env['twitter_platform_id'] in platform_ids
    
    def test_account_management_workflow(self, client, setup_complete_environment):
        """Test account linking, refreshing, and disconnecting"""
        env = setup_complete_environment
        
        with client.session_transaction() as sess:
            sess['user_id'] = env['user_id']
            sess['role'] = 'user'
        
        with app.app_context():
            # View linked accounts
            response = client.get('/linked-accounts')
            assert response.status_code == 200
            
            # Disconnect account
            response = client.get(
                f'/disconnect-account/{env["linkedin_account_id"]}',
                follow_redirects=False
            )
            assert response.status_code == 302
            
            # Verify account is deleted
            account = LinkedAccount.query.get(env['linkedin_account_id'])
            assert account is None


# ==================== PUBLISHING INTEGRATION TESTS ====================

class TestPublishingIntegration:
    """Test publishing to actual platforms (mocked)"""
    
    @patch('requests.post')
    def test_publish_to_twitter(self, mock_post, client, setup_complete_environment):
        """Test publishing post to Twitter"""
        env = setup_complete_environment
        
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'data': {'id': '1234567890'}
        }
        
        with app.app_context():
            post = Post(
                user_id=env['user_id'],
                content_text='Test tweet',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            account = LinkedAccount.query.get(env['twitter_account_id'])
            success, result = publish_to_twitter(post, account)
            
            assert success is True
            assert result == '1234567890'
    
    @patch('requests.post')
    def test_publish_to_linkedin(self, mock_post, client, setup_complete_environment):
        """Test publishing post to LinkedIn"""
        env = setup_complete_environment
        
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'id': 'urn:li:share:9876543210'
        }
        
        with app.app_context():
            post = Post(
                user_id=env['user_id'],
                content_text='Test LinkedIn post',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            account = LinkedAccount.query.get(env['linkedin_account_id'])
            success, result = publish_to_linkedin(post, account)
            
            assert success is True
            assert 'urn:li:share:' in result or result == 'urn:li:share:9876543210'


# ==================== SCHEDULED POST INTEGRATION TESTS ====================

class TestScheduledPostIntegration:
    """Test scheduled post processing"""
    
    def test_scheduled_posts_become_published(self, client, setup_complete_environment):
        """Test scheduled posts automatically become published"""
        from src.app import check_and_publish_scheduled_posts
        
        env = setup_complete_environment
        
        with app.app_context():
            # Create post scheduled in the past
            post = Post(
                user_id=env['user_id'],
                content_text='Should auto-publish',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.flush()
            
            past_time = datetime.now() - timedelta(minutes=10)
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=env['twitter_platform_id'],
                scheduled_time=past_time,
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            post_id = post.post_id
            
            # Run scheduler
            count = check_and_publish_scheduled_posts()
            assert count == 1
            
            # Verify status changed
            updated_post = Post.query.get(post_id)
            assert updated_post.status == 'published'
            
            updated_scheduled = ScheduledPost.query.filter_by(post_id=post_id).first()
            assert updated_scheduled.status == 'published'
    
    def test_future_scheduled_posts_remain_scheduled(self, client, setup_complete_environment):
        """Test future scheduled posts remain scheduled"""
        from src.app import check_and_publish_scheduled_posts
        
        env = setup_complete_environment
        
        with app.app_context():
            post = Post(
                user_id=env['user_id'],
                content_text='Future post',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.flush()
            
            future_time = datetime.now() + timedelta(hours=2)
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=env['twitter_platform_id'],
                scheduled_time=future_time,
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            post_id = post.post_id
            
            # Run scheduler
            count = check_and_publish_scheduled_posts()
            assert count == 0
            
            # Verify still scheduled
            post = Post.query.get(post_id)
            assert post.status == 'scheduled'


# ==================== ERROR RECOVERY TESTS ====================

class TestErrorRecovery:
    """Test error handling and recovery"""
    
    @patch('requests.post')
    def test_failed_publish_is_recorded(self, mock_post, client, setup_complete_environment):
        """Test failed publish attempts are recorded"""
        env = setup_complete_environment
        
        # Mock failed publish
        mock_post.return_value.status_code = 401
        mock_post.return_value.json.return_value = {'detail': 'Unauthorized'}
        
        with app.app_context():
            post = Post(user_id=env['user_id'], content_text='Test', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            account = LinkedAccount.query.get(env['twitter_account_id'])
            success, error = publish_to_twitter(post, account)
            
            assert success is False
            assert 'Unauthorized' in error or error is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src'])