#!/usr/bin/env python3
"""
Basic Unit Tests
Tests individual components in isolation
"""
import sys
import os

# Set TESTING environment variable BEFORE importing app
os.environ['TESTING'] = 'true'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.app import app, dbs, User, Platform, Post, allowed_file, get_file_type

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            dbs.create_all()
            yield client
            dbs.session.remove()
            try:
                dbs.drop_all()
            except:
                pass

@pytest.fixture
def sample_user(client):
    """Create a sample user"""
    with app.app_context():
        user = User(
            email='test@example.com',
            full_name='Test User',
            role='user'
        )
        dbs.session.add(user)
        dbs.session.commit()
        yield user

class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, client):
        """Test creating a new user"""
        with app.app_context():
            user = User(
                email='newuser@example.com',
                full_name='New User',
                role='user'
            )
            dbs.session.add(user)
            dbs.session.commit()
            
            assert user.user_id is not None
            assert user.email == 'newuser@example.com'
            assert user.full_name == 'New User'
            assert user.role == 'user'
    
    def test_user_email_unique(self, client, sample_user):
        """Test that user email must be unique"""
        with app.app_context():
            with pytest.raises(Exception):
                duplicate_user = User(
                    email='test@example.com',
                    full_name='Duplicate User'
                )
                dbs.session.add(duplicate_user)
                dbs.session.commit()

class TestPlatformModel:
    """Test Platform model"""
    
    def test_create_platform(self, client):
        """Test creating a platform"""
        with app.app_context():
            platform = Platform(
                platform_name='Twitter',
                api_endpoint='https://api.twitter.com',
                is_active=True
            )
            dbs.session.add(platform)
            dbs.session.commit()
            
            assert platform.platform_id is not None
            assert platform.platform_name == 'Twitter'
            assert platform.is_active is True

class TestPostModel:
    """Test Post model"""
    
    def test_create_post(self, client, sample_user):
        """Test creating a post"""
        with app.app_context():
            post = Post(
                user_id=sample_user.user_id,
                content_text='Test post content',
                status='draft'
            )
            dbs.session.add(post)
            dbs.session.commit()
            
            assert post.post_id is not None
            assert post.content_text == 'Test post content'
            assert post.status == 'draft'
    
    def test_post_status_enum(self, client, sample_user):
        """Test post status values"""
        with app.app_context():
            statuses = ['draft', 'pending', 'approved', 'rejected', 'scheduled', 'published', 'failed']
            
            for status in statuses:
                post = Post(
                    user_id=sample_user.user_id,
                    content_text=f'Post with {status} status',
                    status=status
                )
                dbs.session.add(post)
                dbs.session.commit()
                assert post.status == status

class TestHelperFunctions:
    """Test helper functions"""
    
    def test_allowed_file(self):
        """Test file extension validation"""
        from src.app import allowed_file
        
        # Valid files
        assert allowed_file('image.png') is True
        assert allowed_file('photo.jpg') is True
        assert allowed_file('video.mp4') is True
        
        # Invalid files
        assert allowed_file('document.pdf') is False
        assert allowed_file('script.py') is False
        assert allowed_file('noextension') is False
    
    def test_get_file_type(self):
        """Test file type detection"""
        from src.app import get_file_type
        
        assert get_file_type('image.png') == 'image'
        assert get_file_type('photo.jpg') == 'image'
        assert get_file_type('video.mp4') == 'video'
        assert get_file_type('document.pdf') is None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
