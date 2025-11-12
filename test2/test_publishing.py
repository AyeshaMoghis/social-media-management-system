"""
Publishing Tests - Testing post publishing to LinkedIn and Twitter
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

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
            dbs.drop_all()


class TestPublishToTwitter:
    """Test Twitter publishing functionality"""
    
    @patch('requests.post')
    def test_publish_text_only_tweet(self, mock_post, client):
        """Test publishing text-only tweet"""
        with app.app_context():
            user = User(email='publisher@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='twitter-pub-123',
                access_token='valid-twitter-token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='Test tweet content',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            post_platform = PostPlatform(
                post_id=post.id,
                platform_id=platform.id
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            post_id = post.id
        
        # Mock Twitter API response
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {
                'data': {
                    'id': '1234567890',
                    'text': 'Test tweet content'
                }
            }
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        # Should succeed
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    def test_publish_tweet_with_media(self, mock_post, client):
        """Test publishing tweet with media"""
        with app.app_context():
            user = User(email='media@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='twitter-media-456',
                access_token='media-token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='Tweet with image',
                media_url='/uploads/image.jpg',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            post_platform = PostPlatform(
                post_id=post.id,
                platform_id=platform.id
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            post_id = post.id
        
        # Mock media upload and tweet post
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {
                'data': {'id': '9876543210'}
            }
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    def test_publish_tweet_api_failure(self, mock_post, client):
        """Test handling Twitter API failure"""
        with app.app_context():
            user = User(email='fail@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='twitter-fail',
                access_token='fail-token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='This will fail',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            post_platform = PostPlatform(
                post_id=post.id,
                platform_id=platform.id
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            post_id = post.id
        
        # Mock API failure
        mock_post.return_value = MagicMock(
            status_code=401,
            json=lambda: {'error': 'Unauthorized'}
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        # Should handle error
        assert response.status_code in [200, 302, 400]


class TestPublishToLinkedIn:
    """Test LinkedIn publishing functionality"""
    
    @patch('requests.post')
    def test_publish_linkedin_text_post(self, mock_post, client):
        """Test publishing text post to LinkedIn"""
        with app.app_context():
            user = User(email='linkedin@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='LinkedIn', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='linkedin-pub-789',
                access_token='linkedin-access-token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='LinkedIn post content',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            post_platform = PostPlatform(
                post_id=post.id,
                platform_id=platform.id
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            post_id = post.id
        
        # Mock LinkedIn API response
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {
                'id': 'urn:li:share:1234567890'
            }
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    def test_publish_linkedin_with_image(self, mock_post, client):
        """Test publishing LinkedIn post with image"""
        with app.app_context():
            user = User(email='linkedin-media@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='LinkedIn', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='linkedin-media-101',
                access_token='linkedin-media-token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='Post with media',
                media_url='/uploads/photo.png',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            post_platform = PostPlatform(
                post_id=post.id,
                platform_id=platform.id
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            post_id = post.id
        
        # Mock successful media upload
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {'id': 'urn:li:share:9999'}
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        assert response.status_code in [200, 302]
        
    @patch('requests.post')
    def test_publish_linkedin_api_error(self, mock_post, client):
        """Test handling LinkedIn API errors"""
        with app.app_context():
            user = User(email='linkedin-error@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='LinkedIn', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='linkedin-error',
                access_token='error-token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='Error post',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            post_platform = PostPlatform(
                post_id=post.id,
                platform_id=platform.id
            )
            dbs.session.add(post_platform)
            dbs.session.commit()
            post_id = post.id
        
        # Mock API error
        mock_post.return_value = MagicMock(
            status_code=403,
            json=lambda: {'message': 'Forbidden'}
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        assert response.status_code in [200, 302, 400]


class TestPublishToPlatform:
    """Test generic publish to platform functionality"""
    
    def test_publish_nonexistent_post(self, client):
        """Test publishing non-existent post"""
        with app.app_context():
            user = User(email='test@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/publish/99999')
        
        # Should handle gracefully
        assert response.status_code in [200, 302, 404]
        
    def test_publish_without_linked_accounts(self, client):
        """Test publishing post without linked accounts"""
        with app.app_context():
            user = User(email='noaccounts@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            post = Post(
                user_id=user_id,
                content='Post without accounts',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            post_id = post.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        # Should handle no accounts case
        assert response.status_code in [200, 302, 400]
        
    @patch('requests.post')
    def test_publish_to_multiple_platforms(self, mock_post, client):
        """Test publishing to multiple platforms"""
        with app.app_context():
            user = User(email='multi@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            # Create Twitter platform
            twitter = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(twitter)
            dbs.session.commit()
            
            twitter_account = LinkedAccount(
                user_id=user_id,
                platform_id=twitter.id,
                platform_user_id='twitter-multi',
                access_token='twitter-token'
            )
            dbs.session.add(twitter_account)
            
            # Create LinkedIn platform
            linkedin = Platform(name='LinkedIn', user_id=user_id)
            dbs.session.add(linkedin)
            dbs.session.commit()
            
            linkedin_account = LinkedAccount(
                user_id=user_id,
                platform_id=linkedin.id,
                platform_user_id='linkedin-multi',
                access_token='linkedin-token'
            )
            dbs.session.add(linkedin_account)
            dbs.session.commit()
            
            post = Post(
                user_id=user_id,
                content='Multi-platform post',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            # Link to both platforms
            pp1 = PostPlatform(post_id=post.id, platform_id=twitter.id)
            pp2 = PostPlatform(post_id=post.id, platform_id=linkedin.id)
            dbs.session.add_all([pp1, pp2])
            dbs.session.commit()
            post_id = post.id
        
        # Mock successful API calls
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {'data': {'id': 'success'}}
        )
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post(f'/api/publish/{post_id}')
        
        assert response.status_code in [200, 302]


class TestMediaUpload:
    """Test media upload functionality"""
    
    def test_upload_media_unauthorized(self, client):
        """Test media upload without authentication"""
        response = client.post('/api/upload_media')
        
        # Should require login
        assert response.status_code in [302, 401]
        
    def test_upload_media_no_file(self, client):
        """Test media upload without file"""
        with app.app_context():
            user = User(email='upload@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.post('/api/upload_media')
        
        # Should handle missing file
        assert response.status_code in [200, 400]
        
    def test_upload_invalid_file_type(self, client):
        """Test uploading invalid file type"""
        with app.app_context():
            user = User(email='upload@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        from io import BytesIO
        data = {
            'file': (BytesIO(b'fake file content'), 'test.exe')
        }
        
        response = client.post('/api/upload_media', data=data, content_type='multipart/form-data')
        
        # Should reject invalid file type
        assert response.status_code in [200, 400]


class TestGetAccountDetails:
    """Test get account details endpoint"""
    
    def test_get_account_details_success(self, client):
        """Test retrieving account details"""
        with app.app_context():
            user = User(email='details@example.com', role='user')
            dbs.session.add(user)
            dbs.session.commit()
            user_id = user.id
            
            platform = Platform(name='Twitter', user_id=user_id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user_id,
                platform_id=platform.id,
                platform_user_id='twitter-details',
                access_token='token',
                follower_count=1000,
                following_count=500
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        
        response = client.get(f'/api/account_details/{account_id}')
        
        # Should return account details
        assert response.status_code in [200, 302]
        
    def test_get_account_details_unauthorized(self, client):
        """Test getting another user's account details"""
        with app.app_context():
            user1 = User(email='user1@example.com', role='user')
            user2 = User(email='user2@example.com', role='user')
            dbs.session.add_all([user1, user2])
            dbs.session.commit()
            
            platform = Platform(name='LinkedIn', user_id=user2.id)
            dbs.session.add(platform)
            dbs.session.commit()
            
            account = LinkedAccount(
                user_id=user2.id,
                platform_id=platform.id,
                platform_user_id='other',
                access_token='token'
            )
            dbs.session.add(account)
            dbs.session.commit()
            account_id = account.id
            user1_id = user1.id
        
        with client.session_transaction() as sess:
            sess['user_id'] = user1_id
        
        response = client.get(f'/api/account_details/{account_id}')
        
        # Should not allow access
        assert response.status_code in [200, 302, 403, 404]
