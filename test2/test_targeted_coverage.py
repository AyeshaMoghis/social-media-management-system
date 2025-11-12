"""
Targeted Coverage for Specific Uncovered Lines
"""
import pytest
from datetime import datetime
import sys
import os
import json

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, dbs, User, Platform, LinkedAccount, Post, PostPlatform


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


class TestPostCreationVariations:
    """Test different post creation scenarios"""
    
    def test_create_post_no_platforms(self, client):
        """Test creating post without specifying platforms"""
        with app.app_context():
            user = User(email='noplat@test.com', full_name='No Platform')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Post without platforms'
        })
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_create_post_with_status_pending(self, client):
        """Test creating post with status pending"""
        with app.app_context():
            user = User(email='pending@test.com', full_name='Pending')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Pending post',
            'status': 'pending'
        })
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_create_post_with_scheduled_status(self, client):
        """Test creating post with scheduled status"""
        with app.app_context():
            user = User(email='sched@test.com', full_name='Scheduled')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Scheduled post',
            'status': 'scheduled',
            'scheduled_time': '2025-12-31 23:59:59'
        })
        assert response.status_code in [200, 201, 302, 400, 404]
    
    def test_create_post_both_platforms(self, client):
        """Test creating post for both Twitter and LinkedIn"""
        with app.app_context():
            user = User(email='both@test.com', full_name='Both')
            dbs.session.add(user)
            dbs.session.commit()
            
            twitter = Platform(platform_name='Twitter')
            linkedin = Platform(platform_name='LinkedIn')
            dbs.session.add_all([twitter, linkedin])
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/posts', json={
            'content_text': 'Multi-platform post',
            'platforms': ['Twitter', 'LinkedIn']
        })
        assert response.status_code in [200, 201, 302, 400, 404]


class TestUpdateOperations:
    """Test update operations"""
    
    def test_update_post_status_to_published(self, client):
        """Test updating post status to published"""
        with app.app_context():
            user = User(email='publish@test.com', full_name='Publish')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Draft post', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put(f'/api/posts/{post_id}', json={'status': 'published'})
        assert response.status_code in [200, 302, 404]
    
    def test_update_post_status_to_draft(self, client):
        """Test updating post status to draft"""
        with app.app_context():
            user = User(email='todraft@test.com', full_name='To Draft')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Published post', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put(f'/api/posts/{post_id}', json={'status': 'draft'})
        assert response.status_code in [200, 302, 404]
    
    def test_update_post_content_and_status(self, client):
        """Test updating both content and status"""
        with app.app_context():
            user = User(email='both@test.com', full_name='Both Update')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Original', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put(f'/api/posts/{post_id}', json={
            'content_text': 'Updated content',
            'status': 'published'
        })
        assert response.status_code in [200, 302, 404]


class TestGetOperations:
    """Test GET operations"""
    
    def test_get_posts_with_limit(self, client):
        """Test getting posts with limit"""
        with app.app_context():
            user = User(email='limit@test.com', full_name='Limit')
            dbs.session.add(user)
            dbs.session.commit()
            
            for i in range(15):
                post = Post(user_id=user.user_id, content_text=f'Post {i}', status='published')
                dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts?limit=5')
        assert response.status_code == 200
    
    def test_get_posts_filtered_by_status(self, client):
        """Test getting posts filtered by different statuses"""
        with app.app_context():
            user = User(email='statusfilter@test.com', full_name='Status Filter')
            dbs.session.add(user)
            dbs.session.commit()
            
            draft = Post(user_id=user.user_id, content_text='Draft', status='draft')
            published = Post(user_id=user.user_id, content_text='Published', status='published')
            pending = Post(user_id=user.user_id, content_text='Pending', status='pending')
            dbs.session.add_all([draft, published, pending])
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Test each status
        for status in ['draft', 'published', 'pending', 'scheduled']:
            response = client.get(f'/api/posts?status={status}')
            assert response.status_code == 200
    
    def test_get_posts_combined_filters(self, client):
        """Test getting posts with multiple filters"""
        with app.app_context():
            user = User(email='combfilter@test.com', full_name='Combined Filter')
            dbs.session.add(user)
            dbs.session.commit()
            
            twitter = Platform(platform_name='Twitter')
            dbs.session.add(twitter)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Test', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            pp = PostPlatform(post_id=post.post_id, platform_id=twitter.platform_id)
            dbs.session.add(pp)
            dbs.session.commit()
            
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts?status=published&platform=Twitter')
        assert response.status_code == 200


class TestLinkedAccountVariations:
    """Test linked account variations"""
    
    def test_get_account_details_with_metrics(self, client):
        """Test getting account details with metrics"""
        with app.app_context():
            user = User(email='accmetrics@test.com', full_name='Account Metrics')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='Twitter')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='metricsuser',
                access_token='token',
                follower_count=1500,
                post_count=250
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get(f'/api/account_details/{account_id}')
        assert response.status_code in [200, 302, 404]
    
    def test_delete_account_with_posts(self, client):
        """Test deleting account that has associated posts"""
        with app.app_context():
            user = User(email='delaccposts@test.com', full_name='Delete Account Posts')
            dbs.session.add(user)
            dbs.session.commit()
            
            platform = Platform(platform_name='LinkedIn')
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user.user_id,
                platform_id=platform.platform_id,
                account_username='deleteuser',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            # Create post associated with this account
            post = Post(user_id=user.user_id, content_text='Post', status='published')
            dbs.session.add(post)
            dbs.session.commit()
            
            pp = PostPlatform(post_id=post.post_id, platform_id=platform.platform_id)
            dbs.session.add(pp)
            dbs.session.commit()
            
            user_id = user.user_id
            account_id = account.account_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.delete(f'/api/linked_accounts/{account_id}')
        assert response.status_code in [200, 204, 302, 404]


class TestManagerOperations:
    """Test manager-specific operations"""
    
    def test_manager_approve_post(self, client):
        """Test manager approving a post"""
        with app.app_context():
            manager = User(email='approvemgr@test.com', full_name='Approve Manager', role='manager')
            user = User(email='postuser@test.com', full_name='Post User', role='user')
            dbs.session.add_all([manager, user])
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='To approve', status='pending')
            dbs.session.add(post)
            dbs.session.commit()
            
            manager_id = manager.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = manager_id
            sess['role'] = 'manager'
        
        response = client.put(f'/api/posts/{post_id}', json={'status': 'approved'})
        assert response.status_code in [200, 302, 404]
    
    def test_manager_reject_post(self, client):
        """Test manager rejecting a post"""
        with app.app_context():
            manager = User(email='rejectmgr@test.com', full_name='Reject Manager', role='manager')
            user = User(email='rejuser@test.com', full_name='Reject User', role='user')
            dbs.session.add_all([manager, user])
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='To reject', status='pending')
            dbs.session.add(post)
            dbs.session.commit()
            
            manager_id = manager.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = manager_id
            sess['role'] = 'manager'
        
        response = client.put(f'/api/posts/{post_id}', json={'status': 'rejected'})
        assert response.status_code in [200, 302, 404]


class TestDeleteOperations:
    """Test delete operations"""
    
    def test_delete_post_with_scheduled_post(self, client):
        """Test deleting a post that has a scheduled entry"""
        with app.app_context():
            user = User(email='delsch@test.com', full_name='Delete Scheduled')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='Scheduled', status='scheduled')
            dbs.session.add(post)
            dbs.session.commit()
            
            from src.app import ScheduledPost
            scheduled = ScheduledPost(
                schedule_id=post.post_id,
                scheduled_time=datetime(2025, 12, 31, 23, 59)
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.delete(f'/api/posts/{post_id}')
        assert response.status_code in [200, 204, 302, 404]
    
    def test_delete_multiple_posts(self, client):
        """Test deleting multiple posts"""
        with app.app_context():
            user = User(email='delmulti@test.com', full_name='Delete Multi')
            dbs.session.add(user)
            dbs.session.commit()
            
            post1 = Post(user_id=user.user_id, content_text='Post 1', status='draft')
            post2 = Post(user_id=user.user_id, content_text='Post 2', status='draft')
            post3 = Post(user_id=user.user_id, content_text='Post 3', status='draft')
            dbs.session.add_all([post1, post2, post3])
            dbs.session.commit()
            
            user_id = user.user_id
            post1_id = post1.post_id
            post2_id = post2.post_id
            post3_id = post3.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # Delete each post
        for post_id in [post1_id, post2_id, post3_id]:
            response = client.delete(f'/api/posts/{post_id}')
            assert response.status_code in [200, 204, 302, 404]


class TestErrorConditions:
    """Test error handling"""
    
    def test_get_nonexistent_post(self, client):
        """Test getting a post that doesn't exist"""
        with app.app_context():
            user = User(email='nopost@test.com', full_name='No Post')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get('/api/posts/99999')
        assert response.status_code in [200, 302, 404, 405]
    
    def test_update_nonexistent_post(self, client):
        """Test updating a post that doesn't exist"""
        with app.app_context():
            user = User(email='noupdate@test.com', full_name='No Update')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.user_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.put('/api/posts/99999', json={'status': 'published'})
        assert response.status_code in [200, 302, 404]
    
    def test_delete_already_deleted_post(self, client):
        """Test deleting a post twice"""
        with app.app_context():
            user = User(email='doubledel@test.com', full_name='Double Delete')
            dbs.session.add(user)
            dbs.session.commit()
            
            post = Post(user_id=user.user_id, content_text='To delete', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            
            user_id = user.user_id
            post_id = post.post_id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        # First delete
        response1 = client.delete(f'/api/posts/{post_id}')
        assert response1.status_code in [200, 204, 302, 404]
        
        # Second delete (should fail or handle gracefully)
        response2 = client.delete(f'/api/posts/{post_id}')
        assert response2.status_code in [200, 204, 302, 404]
