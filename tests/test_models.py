import pytest
from app import User, Platform, LinkedAccount, OAuthState, dbs

def test_user_creation(test_app, init_database):
    """Test creating a user"""
    with test_app.app_context():
        user = User(email="test@example.com")
        dbs.session.add(user)
        dbs.session.commit()
        
        assert user.user_id is not None
        assert user.email == "test@example.com"

def test_platform_creation(test_app, init_database):
    """Test creating a platform"""
    with test_app.app_context():
        platform = Platform(platform_name="LinkedIn")
        dbs.session.add(platform)
        dbs.session.commit()
        
        assert platform.platform_id is not None