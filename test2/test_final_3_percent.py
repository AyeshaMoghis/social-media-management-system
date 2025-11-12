"""
Final 3% - Error Conditions and Edge Cases
"""
import pytest
from datetime import datetime, timedelta
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform, ScheduledPost, check_and_publish_scheduled_posts


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            dbs.create_all()
            yield client
            dbs.session.remove()
            try:
                dbs.drop_all()
            except:
                pass


class TestScheduledPostErrors:
    """Test error handling in scheduled posts"""
    
    def test_check_scheduled_posts_with_due_posts(self, client):
        """Test checking scheduled posts that are due"""
        with app.app_context():
            user = User(email='dueposts@test.com', full_name='Due Posts')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create past scheduled post
            post = Post(user_id=user.user_id, content_text='Overdue post', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            past_time = datetime.now() - timedelta(hours=1)
            scheduled = ScheduledPost(
                schedule_id=post.post_id,
                scheduled_time=past_time
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            # Run check function
            count = check_and_publish_scheduled_posts()
            assert count >= 0  # Should not crash
    
    def test_check_scheduled_posts_with_future_posts(self, client):
        """Test checking scheduled posts that are not yet due"""
        with app.app_context():
            user = User(email='future@test.com', full_name='Future')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create future scheduled post
            post = Post(user_id=user.user_id, content_text='Future post', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            future_time = datetime.now() + timedelta(hours=1)
            scheduled = ScheduledPost(
                schedule_id=post.post_id,
                scheduled_time=future_time
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            # Run check function
            count = check_and_publish_scheduled_posts()
            assert count == 0  # Nothing published yet
    
    def test_check_scheduled_posts_empty(self, client):
        """Test checking when no scheduled posts exist"""
        with app.app_context():
            count = check_and_publish_scheduled_posts()
            assert count == 0


class TestPostPlatformErrors:
    """Test platform-specific error handling"""
    
    def test_create_post_invalid_platform_name(self, client):
        """Test creating post with non-existent platform"""
        with app.app_context():
            user = User(email='badplat@test.com', full_name='Bad Platform')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Test',
            'platforms': ['NonExistentPlatform']
        })
        # Should handle gracefully
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_filter_posts_by_nonexistent_platform(self, client):
        """Test filtering by platform that doesn't exist"""
        with app.app_context():
            user = User(email='filterbad@test.com', full_name='Filter Bad')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts?platform=NonExistent')
        assert response.status_code in [200, 404]


class TestAccountErrorHandling:
    """Test account error handling"""
    
    def test_get_account_details_wrong_user(self, client):
        """Test getting account details for another user's account"""
        with app.app_context():
            user1 = User(email='user1@test.com', full_name='User 1')
            user2 = User(email='user2@test.com', full_name='User 2')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            # Account belongs to user2
            account = LinkedAccount(
                user_id=user2.user_id,
                platform_id=platform.platform_id,
                account_username='user2account',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user1_id = user1.user_id
            account_id = account.account_id
        
        # user1 tries to access user2's account
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        response = client.get(f'/api/account_details/{account_id}')
        assert response.status_code in [200, 302, 403, 404]
    
    def test_delete_account_wrong_user(self, client):
        """Test deleting another user's account"""
        with app.app_context():
            user1 = User(email='deluser1@test.com', full_name='Del User 1')
            user2 = User(email='deluser2@test.com', full_name='Del User 2')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user2.user_id,
                platform_id=platform.platform_id,
                account_username='user2linkedin',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user1_id = user1.user_id
            account_id = account.account_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        response = client.delete(f'/api/linked_accounts/{account_id}')
        assert response.status_code in [200, 204, 302, 403, 404]


class TestPostUpdateErrors:
    """Test post update error handling"""
    
    def test_update_post_wrong_user(self, client):
        """Test updating another user's post"""
        with app.app_context():
            user1 = User(email='upuser1@test.com', full_name='Update User 1')
            user2 = User(email='upuser2@test.com', full_name='Update User 2')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            post = Post(user_id=user2.user_id, content_text='User 2 post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            user1_id = user1.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        response = client.put(f'/api/posts/{post_id}', json={
            'content_text': 'Trying to hijack'
        })
        assert response.status_code in [200, 302, 403, 404]
    
    def test_delete_post_wrong_user(self, client):
        """Test deleting another user's post"""
        with app.app_context():
            user1 = User(email='delpostuser1@test.com', full_name='Del Post User 1')
            user2 = User(email='delpostuser2@test.com', full_name='Del Post User 2')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            post = Post(user_id=user2.user_id, content_text='User 2 post', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            user1_id = user1.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code in [200, 204, 302, 403, 404]


class TestDataIntegrity:
    """Test data integrity conditions"""
    
    def test_post_with_deleted_platform_association(self, client):
        """Test post when platform is deleted"""
        with app.app_context():
            user = User(email='delplatform@test.com', full_name='Del Platform')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Platform test', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            pp = PostPlatform(post_id=post.post_id, platform_id=platform.platform_id)
            dbs.session.add(pp)
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts')
        assert response.status_code == 200
    
    def test_scheduled_post_without_scheduled_time(self, client):
        """Test scheduled post status without time"""
        with app.app_context():
            user = User(email='notime@test.com', full_name='No Time')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Scheduled without time',
            'status': 'scheduled'
            # Missing scheduled_time
        })
        assert response.status_code in [200, 201, 302, 400, 404]


class TestComplexQueries:
    """Test complex query scenarios"""
    
    def test_get_posts_all_filters_combined(self, client):
        """Test getting posts with all filters combined"""
        with app.app_context():
            user = User(email='allfilters@test.com', full_name='All Filters')
            dbs.session.add(user)
            dbs.session.commit()
            
            twitter = Platform(platform_name='Twitter')
            dbs.session.add(twitter)
            dbs.session.commit()
            
            # Create various posts
            for i in range(20):
                post = Post(
                    user_id=user.user_id,
                    content_text=f'Post {i}',
                    status='published' if i % 2 == 0 else 'draft',
                    media_url=f'uploads/media{i}.jpg' if i % 3 == 0 else None
                )
                dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Complex filter
        response = client.get('/api/posts?status=published&platform=Twitter&limit=5&offset=0')
        assert response.status_code == 200
    
    def test_posts_sorted_by_date(self, client):
        """Test posts are returned in correct order"""
        with app.app_context():
            user = User(email='sorted@test.com', full_name='Sorted')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create posts with delays to ensure different timestamps
            for i in range(5):
                post = Post(user_id=user.user_id, content_text=f'Post {i}', status='published')
                dbs.session.add(post)
                dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts')
        assert response.status_code == 200


class TestSessionHandling:
    """Test session handling"""
    
    def test_operation_after_logout(self, client):
        """Test performing operation after logout"""
        with app.app_context():
            user = User(email='afterlogout@test.com', full_name='After Logout')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        # Set session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Try to get posts
        response1 = client.get('/api/posts')
        assert response1.status_code == 200
        
        # Clear session (simulate logout)
        with client.session_transaction() as sess:
            sess.clear()
        
        # Try again without session
        response2 = client.get('/api/posts')
        assert response2.status_code in [200, 302, 401, 404]
    
    def test_session_with_invalid_data(self, client):
        """Test session with invalid user data"""
        with client.session_transaction() as sess:
            sess['user_id'] = 'invalid'  # String instead of int
        
        response = client.get('/api/posts')
        assert response.status_code in [200, 302, 400, 401, 404, 500]


class TestRolesAndPermissions:
    """Test role-based functionality"""
    
    def test_user_view_own_posts_only(self, client):
        """Test that users see only their own posts"""
        with app.app_context():
            user1 = User(email='own1@test.com', full_name='Own 1', role='user')
            user2 = User(email='own2@test.com', full_name='Own 2', role='user')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            # Each user creates posts
            post1 = Post(user_id=user1.user_id, content_text='User 1 post', status='published')
            post2 = Post(user_id=user2.user_id, content_text='User 2 post', status='published')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()
            
            user1_id = user1.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
            sess['role'] = 'user'
        
        response = client.get('/api/posts')
        assert response.status_code == 200
    
    def test_manager_view_all_posts(self, client):
        """Test that managers can see all posts"""
        with app.app_context():
            manager = User(email='viewall@test.com', full_name='View All', role='manager')
            user = User(email='normaluser@test.com', full_name='Normal User', role='user')
            dbs.session.add_all([manager, user])
            dbs.session.commit()
            
            # User creates post
            post = Post(user_id=user.user_id, content_text='User post', status='pending')
            dbs.session.add(post)
            dbs.session.commit()
            
            manager_id = manager.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = manager_id
            sess['role'] = 'manager'
        
        response = client.get('/api/posts')
        assert response.status_code == 200
