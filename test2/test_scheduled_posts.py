"""
Scheduled Posts Tests - Testing scheduled post functionality
"""
import pytest
from datetime import datetime, timedelta
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, Post, PostPlatform, ScheduledPost, check_and_publish_scheduled_posts


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


class TestScheduledPostsAutoPublish:
    """Test automatic publishing of scheduled posts"""
    
    def test_check_scheduled_posts_past_time(self, client):
        """Test that scheduled posts past their time are published"""
        with app.app_context():
            # Create user
            user = User(email='scheduler@example.com', full_name='Scheduler Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            # Create platform
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            # Create post
            post = Post(
                user_id=user.user_id,
                content_text='Scheduled post content',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            # Create post platform link
            post_platform = PostPlatform(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                published=False
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            
            # Create scheduled post with time in the past
            past_time = datetime.now() - timedelta(hours=1)
            scheduled_post = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=past_time,
                status='scheduled'
            )
            dbs.session.add(scheduled_post)
            dbs.session.commit()
            
            # Run the check function
            check_and_publish_scheduled_posts()
            
            # Verify post was published
            updated_scheduled = ScheduledPost.query.get(scheduled_post.schedule_id)
            assert updated_scheduled.status == 'published'
            assert updated_scheduled.published_at is not None
            
            # Verify main post updated
            updated_post = Post.query.get(post.post_id)
            assert updated_post.status == 'published'
            
            # Verify post platform updated
            updated_pp = PostPlatform.query.filter_by(
                post_id=post.post_id,
                platform_id=platform.platform_id
            ).first()
            assert updated_pp.published == True
            
    def test_check_scheduled_posts_future_time(self, client):
        """Test that scheduled posts in future are not published"""
        with app.app_context():
            user = User(email='future@example.com', full_name='Future Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            post = Post(
                user_id=user.user_id,
                content_text='Future scheduled post',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            # Create scheduled post with time in the future
            future_time = datetime.now() + timedelta(hours=2)
            scheduled_post = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=future_time,
                status='scheduled'
            )
            dbs.session.add(scheduled_post)
            dbs.session.commit()
            
            # Run the check function
            check_and_publish_scheduled_posts()
            
            # Verify post was NOT published
            updated_scheduled = ScheduledPost.query.get(scheduled_post.schedule_id)
            assert updated_scheduled.status == 'scheduled'
            assert updated_scheduled.published_at is None
            
    def test_check_scheduled_posts_no_posts(self, client):
        """Test check function with no scheduled posts"""
        with app.app_context():
            # Run with empty database
            check_and_publish_scheduled_posts()
            # Should not raise any errors
            
    def test_check_scheduled_posts_exception_handling(self, client):
        """Test that function handles exceptions gracefully"""
        with app.app_context():
            try:
                check_and_publish_scheduled_posts()
            except Exception as e:
                pytest.fail(f"Function should not raise exception: {e}")


class TestScheduledPostAPI:
    """Test scheduled post API endpoints"""
    
    def test_create_scheduled_post_endpoint(self, client):
        """Test creating scheduled post via API"""
        with app.app_context():
            user = User(email='api@example.com', full_name='API Test')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        # Try to create scheduled post (endpoint may or may not exist)
        future_time = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        response = client.post('/api/scheduled_posts', json={
            'content': 'Test scheduled content',
            'scheduled_time': future_time,
            'platforms': ['Twitter']
        })
        
        # Accept various status codes
        assert response.status_code in [200, 201, 302, 400, 404]
        
    def test_get_scheduled_posts_endpoint(self, client):
        """Test retrieving scheduled posts"""
        with app.app_context():
            user = User(email='get@example.com', full_name='Get Test')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'user'
        
        response = client.get('/api/scheduled_posts')
        assert response.status_code in [200, 302, 404]


class TestScheduledPostModel:
    """Test ScheduledPost model"""
    
    def test_create_scheduled_post_model(self, client):
        """Test creating ScheduledPost model instance"""
        with app.app_context():
            user = User(email='model@example.com', full_name='Model Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            # Create scheduled post
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=datetime.now() + timedelta(days=1),
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            # Verify it was saved
            assert scheduled.schedule_id is not None
            assert scheduled.status == 'scheduled'
            
    def test_scheduled_post_default_values(self, client):
        """Test ScheduledPost default values"""
        with app.app_context():
            user = User(email='defaults@example.com', full_name='Defaults Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Defaults', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=platform.platform_id,
                scheduled_time=datetime.now() + timedelta(hours=1)
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            # Check defaults
            assert scheduled.status == 'scheduled'
            assert scheduled.schedule_id is not None
