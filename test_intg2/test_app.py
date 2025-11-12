"""
Unit Tests for Social Media Management System
Corrected for src/app.py structure
Run with: pytest test_intg2/test_app.py -v --cov=src --cov-report=html
"""
import pytest
import os
import sys
from datetime import datetime, timedelta
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment BEFORE importing app
os.environ['TESTING'] = 'true'

# Import from src package
from src.app import (
    app, dbs, User, Platform, LinkedAccount, Post, 
    PostPlatform, ScheduledPost, OAuthState,
    allowed_file, get_file_type, cleanup_old_oauth_states
)


@pytest.fixture(scope='function')
def client():
    """Create test client with in-memory database"""
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
def sample_user(client):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(
            email='test@example.com',
            full_name='Test User',
            role='user'
        )
        dbs.session.add(user)
        dbs.session.commit()
        return user.user_id


@pytest.fixture
def sample_platform(client):
    """Create sample platforms"""
    with app.app_context():
        platforms = [
            Platform(platform_name='LinkedIn', api_endpoint='https://api.linkedin.com/v2/ugcPosts'),
            Platform(platform_name='Twitter', api_endpoint='https://api.twitter.com/2/tweets'),
            Platform(platform_name='X', api_endpoint='https://api.twitter.com/2/tweets')
        ]
        for p in platforms:
            dbs.session.add(p)
        dbs.session.commit()
        return [p.platform_id for p in platforms]


@pytest.fixture
def sample_linked_account(client, sample_user, sample_platform):
    """Create a linked account"""
    with app.app_context():
        account = LinkedAccount(
            user_id=sample_user,
            platform_id=sample_platform[0],
            access_token='test_token_123',
            refresh_token='refresh_token_123',
            external_id='linkedin_user_123',
            account_username='Test LinkedIn User'
        )
        dbs.session.add(account)
        dbs.session.commit()
        return account.account_id


@pytest.fixture
def authenticated_session(client, sample_user):
    """Create authenticated session"""
    with client.session_transaction() as sess:
        sess['user_id'] = sample_user
        sess['role'] = 'user'
        sess['full_name'] = 'Test User'
    return client


# ==================== AUTHENTICATION TESTS ====================

class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_home_redirect_when_not_logged_in(self, client):
        """Test home page redirects to login when not authenticated"""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_home_redirect_when_logged_in(self, authenticated_session, sample_user):
        """Test home page redirects to dashboard when authenticated"""
        response = authenticated_session.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert 'linked-accounts' in response.location
    
    def test_protected_route_requires_auth(self, client):
        """Test protected routes require authentication"""
        response = client.get('/linked-accounts', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location


# ==================== DATABASE MODEL TESTS ====================

class TestModels:
    """Test database models"""
    
    def test_user_creation(self, client):
        """Test User model creation"""
        with app.app_context():
            user = User(email='model@test.com', full_name='Model Test')
            dbs.session.add(user)
            dbs.session.commit()
            
            retrieved = User.query.filter_by(email='model@test.com').first()
            assert retrieved is not None
            assert retrieved.full_name == 'Model Test'
            assert retrieved.role == 'user'
    
    def test_platform_creation(self, client):
        """Test Platform model creation"""
        with app.app_context():
            platform = Platform(platform_name='Instagram', api_endpoint='https://api.instagram.com')
            dbs.session.add(platform)
            dbs.session.commit()
            
            retrieved = Platform.query.filter_by(platform_name='Instagram').first()
            assert retrieved is not None
            assert retrieved.is_active is True
    
    def test_linked_account_creation(self, client, sample_user, sample_platform):
        """Test LinkedAccount model creation"""
        with app.app_context():
            account = LinkedAccount(
                user_id=sample_user,
                platform_id=sample_platform[0],
                access_token='token123'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            retrieved = LinkedAccount.query.filter_by(user_id=sample_user).first()
            assert retrieved is not None
            assert retrieved.access_token == 'token123'
    
    def test_post_creation(self, client, sample_user):
        """Test Post model creation"""
        with app.app_context():
            post = Post(
                user_id=sample_user,
                content_text='Test post content',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            retrieved = Post.query.filter_by(user_id=sample_user).first()
            assert retrieved is not None
            assert retrieved.content_text == 'Test post content'
            assert retrieved.status == 'draft'


# ==================== LINKED ACCOUNTS TESTS ====================

class TestLinkedAccounts:
    """Test linked accounts functionality"""
    
    def test_linked_accounts_page_loads(self, authenticated_session):
        """Test linked accounts page loads successfully"""
        response = authenticated_session.get('/linked-accounts')
        assert response.status_code == 200
    
    def test_disconnect_account(self, authenticated_session, sample_linked_account):
        """Test disconnecting a linked account"""
        with app.app_context():
            response = authenticated_session.get(
                f'/disconnect-account/{sample_linked_account}', 
                follow_redirects=True
            )
            assert response.status_code == 200
            
            account = LinkedAccount.query.get(sample_linked_account)
            assert account is None


# ==================== POST MANAGEMENT TESTS ====================

class TestPostManagement:
    """Test post creation, editing, and deletion"""
    
    def test_post_scheduler_page_loads(self, authenticated_session, sample_linked_account):
        """Test post scheduler page loads"""
        response = authenticated_session.get('/post-scheduler')
        assert response.status_code == 200
    
    def test_create_draft_post(self, authenticated_session, sample_linked_account):
        """Test creating a draft post"""
        with app.app_context():
            data = {
                'text': 'This is a test draft post',
                'status': 'draft',
                'account_ids[]': [sample_linked_account]
            }
            
            response = authenticated_session.post('/api/posts', data=data)
            assert response.status_code == 201
            
            posts = Post.query.all()
            assert len(posts) == 1
            assert posts[0].content_text == 'This is a test draft post'
            assert posts[0].status == 'draft'
    
    def test_create_scheduled_post(self, authenticated_session, sample_linked_account):
        """Test creating a scheduled post"""
        with app.app_context():
            future_time = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
            
            data = {
                'text': 'Scheduled post',
                'status': 'scheduled',
                'scheduled_time': future_time,
                'account_ids[]': [sample_linked_account]
            }
            
            response = authenticated_session.post('/api/posts', data=data)
            assert response.status_code == 201
            
            posts = Post.query.all()
            assert len(posts) == 1
            assert posts[0].status == 'scheduled'
            
            scheduled = ScheduledPost.query.filter_by(post_id=posts[0].post_id).first()
            assert scheduled is not None
    
    def test_get_posts(self, authenticated_session, sample_user, sample_linked_account):
        """Test retrieving posts"""
        with app.app_context():
            # Create test posts
            post1 = Post(user_id=sample_user, content_text='Post 1', status='draft')
            post2 = Post(user_id=sample_user, content_text='Post 2', status='published')
            dbs.session.add_all([post1, post2])
            dbs.session.commit()
            
            response = authenticated_session.get('/api/posts')
            assert response.status_code == 200
            
            data = response.get_json()
            assert len(data) == 2
    
    def test_update_post(self, authenticated_session, sample_user, sample_linked_account):
        """Test updating a post"""
        with app.app_context():
            post = Post(user_id=sample_user, content_text='Original', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id
            
            data = {
                'text': 'Updated content',
                'status': 'draft'
            }
            
            response = authenticated_session.put(f'/api/posts/{post_id}', data=data)
            assert response.status_code == 200
            
            updated_post = Post.query.get(post_id)
            assert updated_post.content_text == 'Updated content'
    
    def test_delete_post(self, authenticated_session, sample_user):
        """Test deleting a post"""
        with app.app_context():
            post = Post(user_id=sample_user, content_text='To delete', status='draft')
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.post_id
            
            response = authenticated_session.delete(f'/api/posts/{post_id}')
            assert response.status_code == 200
            
            deleted_post = Post.query.get(post_id)
            assert deleted_post is None
    
    def test_create_post_without_content(self, authenticated_session, sample_linked_account):
        """Test that post creation fails without content"""
        data = {
            'text': '',
            'status': 'draft',
            'account_ids[]': [sample_linked_account]
        }
        
        response = authenticated_session.post('/api/posts', data=data)
        assert response.status_code == 400
    
    def test_create_post_without_account(self, authenticated_session):
        """Test that post creation fails without selected account"""
        data = {
            'text': 'Test post',
            'status': 'draft'
        }
        
        response = authenticated_session.post('/api/posts', data=data)
        assert response.status_code == 400


# ==================== HELPER FUNCTION TESTS ====================

class TestHelperFunctions:
    """Test helper functions"""
    
    def test_allowed_file(self):
        """Test file extension validation"""
        assert allowed_file('image.jpg') is True
        assert allowed_file('image.png') is True
        assert allowed_file('video.mp4') is True
        assert allowed_file('document.pdf') is False
        assert allowed_file('script.exe') is False
    
    def test_get_file_type(self):
        """Test file type detection"""
        assert get_file_type('photo.jpg') == 'image'
        assert get_file_type('photo.png') == 'image'
        assert get_file_type('clip.mp4') == 'video'
        assert get_file_type('unknown.txt') is None
    
    def test_cleanup_old_oauth_states(self, client):
        """Test OAuth state cleanup"""
        with app.app_context():
            # Create old state
            old_state = OAuthState(
                state_id='old123',
                user_id=1,
                platform='linkedin',
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
            
            # Create recent state
            new_state = OAuthState(
                state_id='new456',
                user_id=1,
                platform='linkedin',
                created_at=datetime.utcnow()
            )
            
            dbs.session.add_all([old_state, new_state])
            dbs.session.commit()
            
            cleanup_old_oauth_states()
            
            # Old should be deleted
            assert OAuthState.query.get('old123') is None
            # New should remain
            assert OAuthState.query.get('new456') is not None


# ==================== API ERROR HANDLING TESTS ====================

class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_unauthorized_api_access(self, client):
        """Test API returns 401 for unauthorized access"""
        response = client.get('/api/posts')
        assert response.status_code == 401
    
    def test_invalid_post_id(self, authenticated_session):
        """Test updating non-existent post"""
        response = authenticated_session.put('/api/posts/99999', data={'text': 'test'})
        assert response.status_code == 404
    
    def test_delete_nonexistent_post(self, authenticated_session):
        """Test deleting non-existent post"""
        response = authenticated_session.delete('/api/posts/99999')
        assert response.status_code == 404


# ==================== FILE UPLOAD TESTS ====================

class TestFileUploads:
    """Test file upload functionality"""
    
    def test_upload_valid_image(self, authenticated_session, sample_linked_account):
        """Test uploading valid image file"""
        data = {
            'text': 'Post with valid image',
            'status': 'draft',
            'account_ids[]': [sample_linked_account],
            'media': (BytesIO(b'fake image content'), 'test.jpg')
        }
        
        response = authenticated_session.post(
            '/api/posts',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
    
    def test_upload_invalid_file_type(self, authenticated_session, sample_linked_account):
        """Test uploading invalid file type"""
        data = {
            'text': 'Post with invalid file',
            'status': 'draft',
            'account_ids[]': [sample_linked_account],
            'media': (BytesIO(b'fake pdf content'), 'test.pdf')
        }
        
        response = authenticated_session.post(
            '/api/posts',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400


# ==================== SCHEDULED POST TESTS ====================

class TestScheduledPosts:
    """Test scheduled post functionality"""
    
    def test_check_and_publish_scheduled_posts(self, client, sample_user, sample_platform):
        """Test automatic publishing of scheduled posts"""
        from src.app import check_and_publish_scheduled_posts
        
        with app.app_context():
            # Create a post scheduled in the past
            post = Post(
                user_id=sample_user,
                content_text='Past scheduled post',
                status='scheduled'
            )
            dbs.session.add(post)
            dbs.session.flush()
            
            past_time = datetime.now() - timedelta(minutes=5)
            scheduled = ScheduledPost(
                post_id=post.post_id,
                platform_id=sample_platform[0],
                scheduled_time=past_time,
                status='scheduled'
            )
            dbs.session.add(scheduled)
            dbs.session.commit()
            
            # Run the check
            count = check_and_publish_scheduled_posts()
            
            # Verify it was marked as published
            updated_scheduled = ScheduledPost.query.filter_by(post_id=post.post_id).first()
            assert updated_scheduled.status == 'published'
            assert count == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src', '--cov-report=html', '--cov-report=term'])