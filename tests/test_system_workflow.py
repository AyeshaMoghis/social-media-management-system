"""
Complete System Tests for Social Media Management System
Tests end-to-end workflows including authentication, OAuth, posting, and scheduling
"""
import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import session
from werkzeug.security import generate_password_hash

# Import from src.app (your project structure uses src/)
from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, ScheduledPost, OAuthState


# ==========================================
# FIXTURES (client comes from conftest.py)
# ==========================================

@pytest.fixture
def test_user(client):
    """Create a test user"""
    user = User(
        email='testuser@example.com',
        password_hash=generate_password_hash('password123'),
        full_name='Test User',
        role='user'
    )
    dbs.session.add(user)
    dbs.session.commit()
    return user.user_id


@pytest.fixture
def test_manager(client):
    """Create a test manager"""
    manager = User(
        email='manager@example.com',
        password_hash=generate_password_hash('manager123'),
        full_name='Test Manager',
        role='manager'
    )
    dbs.session.add(manager)
    dbs.session.commit()
    return manager.user_id


@pytest.fixture
def linkedin_platform(client):
    """Create LinkedIn platform"""
    platform = Platform(
        platform_name='LinkedIn',
        api_endpoint='https://api.linkedin.com/v2/ugcPosts',
        is_active=True
    )
    dbs.session.add(platform)
    dbs.session.commit()
    return platform.platform_id


@pytest.fixture
def twitter_platform(client):
    """Create Twitter platform"""
    platform = Platform(
        platform_name='Twitter',
        api_endpoint='https://api.twitter.com/2',
        is_active=True
    )
    dbs.session.add(platform)
    dbs.session.commit()
    return platform.platform_id


# ==========================================
# TEST 1: USER REGISTRATION AND LOGIN FLOW
# ==========================================
class TestAuthenticationWorkflow:
    """Test complete authentication workflows"""
    
    def test_user_signup_and_login(self, client):
    
        response = client.post('/signup', data={
            'full_name': 'New User',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'role': 'user'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Account created successfully' in response.data

        # Step 2: Login
        response = client.post('/login', data={
            'email': 'newuser@example.com',
            'password': 'securepass123'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Instead of checking for 'Login successful', check that we're on the dashboard
        # The login succeeded if we see the user's name and dashboard elements
        assert b'New User' in response.data
        assert b'Linked Accounts' in response.data or b'Dashboard' in response.data
    
    def test_manager_signup_and_access(self, client):
        """Test manager can signup and access manager dashboard"""
        # Step 1: Sign up as manager
        response = client.post('/signup', data={
            'full_name': 'Manager User',
            'email': 'manager@test.com',
            'password': 'manager123',
            'role': 'manager'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Step 2: Login
        response = client.post('/login', data={
            'email': 'manager@test.com',
            'password': 'manager123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Step 3: Access manager dashboard
        response = client.get('/dashboard/manager')
        assert response.status_code == 200
    
    def test_login_with_invalid_credentials(self, client, test_user):
        """Test login fails with wrong password"""
        response = client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert b'Invalid credentials' in response.data
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
    
    def test_logout_workflow(self, client, test_user):
        """Test user can logout successfully"""
        # Login first
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Logout
        response = client.get('/logout', follow_redirects=True)
        assert b'logged out' in response.data
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


# ==========================================
# TEST 2: OAUTH INTEGRATION WORKFLOW
# ==========================================
class TestOAuthWorkflow:
    """Test OAuth connection workflows"""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_linkedin_oauth_complete_flow(self, mock_get, mock_post, 
                                         client, test_user, linkedin_platform):
        """Test complete LinkedIn OAuth connection"""
        # Step 1: Login user
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Step 2: Initiate OAuth
        response = client.get('/connect/linkedin')
        assert response.status_code == 302
        assert 'linkedin.com/oauth' in response.location
        
        # Extract state from redirect
        state = response.location.split('state=')[1].split('&')[0]
        
        # Step 3: Mock token exchange
        mock_post.return_value.json.return_value = {
            'access_token': 'test_linkedin_token_123'
        }
        
        # Step 4: Mock profile fetch
        mock_get.return_value.json.return_value = {
            'sub': 'linkedin_user_123',
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        # Step 5: Handle callback
        response = client.get(f'/callback/linkedin?code=test_code&state={state}',
                            follow_redirects=True)
        
        assert response.status_code == 200
        
        # Step 6: Verify account was created
        account = LinkedAccount.query.filter_by(user_id=test_user).first()
        assert account is not None
        assert account.access_token == 'test_linkedin_token_123'
        assert account.account_username == 'John Doe'
    
    @patch('requests.post')
    @patch('requests.get')
    def test_twitter_oauth_complete_flow(self, mock_get, mock_post,
                                        client, test_user, twitter_platform):
        """Test complete Twitter OAuth connection with PKCE"""
        # Step 1: Login user
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Step 2: Initiate OAuth
        response = client.get('/connect/twitter')
        assert response.status_code == 302
        assert 'twitter.com' in response.location
        
        # Extract state
        state = response.location.split('state=')[1].split('&')[0]
        
        # Step 3: Mock token exchange
        mock_post.return_value.json.return_value = {
            'access_token': 'twitter_token_456',
            'refresh_token': 'refresh_token_456'
        }
        
        # Step 4: Mock user info
        mock_get.return_value.json.return_value = {
            'data': {
                'id': 'twitter_user_456',
                'username': 'johndoe',
                'name': 'John Doe',
                'public_metrics': {
                    'followers_count': 150,
                    'tweet_count': 42
                }
            }
        }
        
        # Step 5: Handle callback
        response = client.get(f'/callback/twitter?code=test_code&state={state}',
                            follow_redirects=True)
        
        assert response.status_code == 200
        
        # Step 6: Verify account was created with metrics
        account = LinkedAccount.query.filter_by(user_id=test_user).first()
        assert account is not None
        assert account.follower_count == 150
        assert account.post_count == 42


# ==========================================
# TEST 3: POST CREATION AND PUBLISHING
# ==========================================
class TestPostWorkflow:
    """Test post creation, approval, and publishing workflows"""
    
    def test_draft_post_creation(self, client, test_user, linkedin_platform):
        """Test user can create a draft post"""
        # Login
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Create linked account first
        account = LinkedAccount(
            user_id=test_user,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='Test Account'
        )
        dbs.session.add(account)
        dbs.session.commit()
        account_id = account.account_id
        
        # Create draft post
        response = client.post('/api/posts', data={
            'text': 'This is a draft post',
            'account_ids[]': [account_id],
            'status': 'draft'
        })
        
        assert response.status_code == 201
        
        # Verify post was created
        post = Post.query.first()
        assert post is not None
        assert post.status == 'draft'
        assert post.content_text == 'This is a draft post'
    
    @patch('src.app.publish_to_linkedin')
    def test_immediate_publish_by_manager(self, mock_publish, client, 
                                         test_manager, linkedin_platform):
        """Test manager can publish immediately"""
        # Mock successful publish
        mock_publish.return_value = (True, 'post_123')
        
        # Login as manager
        client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        })
        
        # Create linked account
        account = LinkedAccount(
            user_id=test_manager,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='Manager Account'
        )
        dbs.session.add(account)
        dbs.session.commit()
        account_id = account.account_id
        
        # Create and publish post
        response = client.post('/api/posts', data={
            'text': 'Publishing immediately',
            'account_ids[]': [account_id],
            'status': 'published'
        })
        
        assert response.status_code == 201
        
        # Verify post was published
        post = Post.query.first()
        assert post.status == 'published'
        
        post_platform = PostPlatform.query.first()
        assert post_platform.published is True
        assert mock_publish.called
    
    def test_user_post_requires_approval(self, client, test_user, linkedin_platform):
        """Test regular user post goes to pending status"""
        # Login as user
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Create linked account
        account = LinkedAccount(
            user_id=test_user,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='User Account'
        )
        dbs.session.add(account)
        dbs.session.commit()
        account_id = account.account_id
        
        # Create post with published status (should become pending)
        response = client.post('/api/posts', data={
            'text': 'Needs approval',
            'account_ids[]': [account_id],
            'status': 'published'
        })
        
        assert response.status_code == 201
        
        # Verify status is pending (not published)
        post = Post.query.first()
        assert post.status == 'pending'


# ==========================================
# TEST 4: POST SCHEDULING WORKFLOW
# ==========================================
class TestSchedulingWorkflow:
    """Test post scheduling and auto-publishing"""
    
    def test_schedule_post_for_future(self, client, test_manager, linkedin_platform):
        """Test scheduling a post for future publishing"""
        # Login as manager
        client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        })
        
        # Create linked account
        account = LinkedAccount(
            user_id=test_manager,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='Manager Account'
        )
        dbs.session.add(account)
        dbs.session.commit()
        account_id = account.account_id
        
        # Schedule post for 1 hour from now
        future_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        
        response = client.post('/api/posts', data={
            'text': 'Scheduled post',
            'account_ids[]': [account_id],
            'status': 'scheduled',
            'scheduled_time': future_time
        })
        
        assert response.status_code == 201
        
        # Verify scheduled post was created
        post = Post.query.first()
        assert post.status == 'scheduled'
        
        sched_post = ScheduledPost.query.first()
        assert sched_post is not None
        assert sched_post.status == 'scheduled'
    
    @patch('src.app.publish_to_linkedin')
    def test_auto_publish_past_scheduled_time(self, mock_publish, client, 
                                             test_manager, linkedin_platform):
        """Test auto-publishing when scheduled time has passed"""
        # Mock successful publish
        mock_publish.return_value = (True, 'scheduled_post_123')
        
        # Login as manager
        client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        })
        
        # Create linked account
        account = LinkedAccount(
            user_id=test_manager,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='Manager Account'
        )
        dbs.session.add(account)
        dbs.session.commit()
        account_id = account.account_id
        
        # Create post scheduled in the past
        past_time = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M')
        
        client.post('/api/posts', data={
            'text': 'Past scheduled post',
            'account_ids[]': [account_id],
            'status': 'scheduled',
            'scheduled_time': past_time
        })
        
        # Trigger scheduled post check
        from src.app import check_and_publish_scheduled_posts
        published_count = check_and_publish_scheduled_posts()
        
        assert published_count == 1
        
        # Verify post is now published
        post = Post.query.first()
        assert post.status == 'published'
        
        sched_post = ScheduledPost.query.first()
        assert sched_post.status == 'published'


# ==========================================
# TEST 5: MANAGER APPROVAL WORKFLOW
# ==========================================
class TestApprovalWorkflow:
    """Test manager approval and rejection workflows"""
    
    def test_manager_approve_pending_post(self, client, test_user, 
                                         test_manager, linkedin_platform):
        """Test manager can approve pending posts"""
        # Create pending post as user
        post = Post(
            user_id=test_user,
            content_text='Pending post for approval',
            status='pending'
        )
        dbs.session.add(post)
        dbs.session.flush()
        
        account = LinkedAccount(
            user_id=test_user,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='User Account'
        )
        dbs.session.add(account)
        dbs.session.flush()
        
        post_platform = PostPlatform(
            post_id=post.post_id,
            platform_id=linkedin_platform
        )
        dbs.session.add(post_platform)
        dbs.session.commit()
        post_id = post.post_id
        
        # Login as manager
        client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        })
        
        # Approve post
        response = client.post('/update_post_status', json={
            'post_id': post_id,
            'action': 'approved'
        })
        
        assert response.status_code == 200
        
        # Verify status changed
        post = Post.query.get(post_id)
        assert post.status == 'approved'
    
    def test_manager_reject_pending_post(self, client, test_user,
                                        test_manager, linkedin_platform):
        """Test manager can reject pending posts"""
        # Create pending post
        post = Post(
            user_id=test_user,
            content_text='Post to be rejected',
            status='pending'
        )
        dbs.session.add(post)
        dbs.session.commit()
        post_id = post.post_id
        
        # Login as manager
        client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        })
        
        # Reject post
        response = client.post('/update_post_status', json={
            'post_id': post_id,
            'action': 'rejected'
        })
        
        assert response.status_code == 200
        
        # Verify rejection
        post = Post.query.get(post_id)
        assert post.status == 'rejected'


# ==========================================
# TEST 6: MULTI-PLATFORM PUBLISHING
# ==========================================
class TestMultiPlatformWorkflow:
    """Test publishing to multiple platforms simultaneously"""
    
    @patch('src.app.publish_to_linkedin')
    @patch('src.app.publish_to_twitter')
    def test_publish_to_multiple_platforms(self, mock_twitter, mock_linkedin,
                                          client, test_manager, 
                                          linkedin_platform, twitter_platform):
        """Test publishing same post to LinkedIn and Twitter"""
        # Mock successful publishes
        mock_linkedin.return_value = (True, 'linkedin_post_123')
        mock_twitter.return_value = (True, 'twitter_post_456')
        
        # Login as manager
        client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        })
        
        # Create accounts for both platforms
        linkedin_acc = LinkedAccount(
            user_id=test_manager,
            platform_id=linkedin_platform,
            access_token='linkedin_token',
            account_username='LinkedIn Account'
        )
        twitter_acc = LinkedAccount(
            user_id=test_manager,
            platform_id=twitter_platform,
            access_token='twitter_token',
            account_username='Twitter Account'
        )
        dbs.session.add_all([linkedin_acc, twitter_acc])
        dbs.session.commit()
        linkedin_id = linkedin_acc.account_id
        twitter_id = twitter_acc.account_id
        
        # Publish to both platforms
        response = client.post('/api/posts', data={
            'text': 'Multi-platform post',
            'account_ids[]': [linkedin_id, twitter_id],
            'status': 'published'
        })
        
        assert response.status_code == 201
        
        # Verify both platforms were published to
        post_platforms = PostPlatform.query.all()
        assert len(post_platforms) == 2
        assert all(pp.published for pp in post_platforms)
        
        assert mock_linkedin.called
        assert mock_twitter.called


# ==========================================
# TEST 7: POST EDITING AND DELETION
# ==========================================
class TestPostManagementWorkflow:
    """Test editing and deleting posts"""
    
    def test_edit_draft_post(self, client, test_user, linkedin_platform):
        """Test editing a draft post"""
        # Create draft post
        post = Post(
            user_id=test_user,
            content_text='Original text',
            status='draft'
        )
        dbs.session.add(post)
        dbs.session.commit()
        post_id = post.post_id
        
        # Login
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Edit post
        response = client.put(f'/api/posts/{post_id}', json={
            'text': 'Updated text',
            'status': 'draft'
        })
        
        assert response.status_code == 200
        
        # Verify update
        post = Post.query.get(post_id)
        assert post.content_text == 'Updated text'
    
    @patch('src.app.delete_from_linkedin')
    def test_delete_published_post(self, mock_delete, client, 
                                  test_user, linkedin_platform):
        """Test deleting a published post removes it from platform"""
        # Mock successful deletion
        mock_delete.return_value = (True, 'Deleted successfully')
        
        # Create published post
        account = LinkedAccount(
            user_id=test_user,
            platform_id=linkedin_platform,
            access_token='test_token',
            account_username='User Account'
        )
        dbs.session.add(account)
        dbs.session.flush()
        
        post = Post(
            user_id=test_user,
            content_text='Post to delete',
            status='published'
        )
        dbs.session.add(post)
        dbs.session.flush()
        
        post_platform = PostPlatform(
            post_id=post.post_id,
            platform_id=linkedin_platform,
            published=True,
            platform_post_id='linkedin_123'
        )
        dbs.session.add(post_platform)
        dbs.session.commit()
        post_id = post.post_id
        
        # Login
        client.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        
        # Delete post
        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code == 200
        
        # Verify deletion from platform was attempted
        assert mock_delete.called
        
        # Verify post was deleted from database
        post = Post.query.get(post_id)
        assert post is None


# ==========================================
# RUN TESTS
# ==========================================
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
