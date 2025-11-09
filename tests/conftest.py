"""
Unified Pytest Configuration for SMMS
- Forces tests to use SQLite in-memory database
- Mocks MySQL connections to avoid real DB hits
- Provides Flask test client + session fixtures
- Works with both unittest and pytest style tests
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# ======================================================
# Environment Setup BEFORE any app imports
# ======================================================
os.environ["TESTING"] = "true"

# Mock mysql.connector BEFORE importing app modules
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Ensure project paths are importable
project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# Import Flask app + database (try both import paths)
try:
    from app import app, dbs, User, Platform, LinkedAccount, OAuthState
except ImportError:
    from src.app import app, dbs, User, Platform, LinkedAccount, OAuthState


# ======================================================
# FIXTURE: Setup Clean SQLite DB
# ======================================================
@pytest.fixture(scope="function", autouse=True)
def setup_test_environment():
    """Setup a fresh SQLite in-memory database before each test."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    with app.app_context():
        dbs.drop_all()
        dbs.create_all()
        yield
        dbs.session.remove()
        dbs.drop_all()


# ======================================================
# FIXTURE: Mock MySQL Connections (for auth.py)
# ======================================================
@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    """
    Globally mock MySQL connection in src.auth.get_db_connection()
    to prevent real DB usage during tests.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_conn.commit.return_value = None

    # Try to mock the auth module's connection function
    try:
        monkeypatch.setattr("src.auth.get_db_connection", lambda: mock_conn)
    except (AttributeError, ModuleNotFoundError):
        try:
            monkeypatch.setattr("auth.get_db_connection", lambda: mock_conn)
        except (AttributeError, ModuleNotFoundError):
            pass  # Auth module might not exist or be needed
    
    return mock_conn


# ======================================================
# FIXTURE: Flask Test Client
# ======================================================
@pytest.fixture
def client():
    """Provides a Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ======================================================
# FIXTURE: Simulated Sessions
# ======================================================
@pytest.fixture
def user_session(client):
    """Simulate a logged-in user session."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["full_name"] = "Test User"
        sess["role"] = "user"
    return client


@pytest.fixture
def manager_session(client):
    """Simulate a logged-in manager session."""
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["full_name"] = "Test Manager"
        sess["role"] = "manager"
    return client


# ======================================================
# FIXTURE: Test User Data
# ======================================================
@pytest.fixture
def test_user():
    """Create and return a test user in the database."""
    user = User(
        email="testuser@example.com",
        full_name="Test User",
        role="user"
    )
    dbs.session.add(user)
    dbs.session.commit()
    return user


@pytest.fixture
def test_manager():
    """Create and return a test manager in the database."""
    manager = User(
        email="testmanager@example.com",
        full_name="Test Manager",
        role="manager"
    )
    dbs.session.add(manager)
    dbs.session.commit()
    return manager


@pytest.fixture
def test_platform_twitter():
    """Create and return a Twitter platform."""
    platform = Platform(
        platform_name="Twitter",
        api_endpoint="https://api.twitter.com/2",
        is_active=True
    )
    dbs.session.add(platform)
    dbs.session.commit()
    return platform


@pytest.fixture
def test_platform_linkedin():
    """Create and return a LinkedIn platform."""
    platform = Platform(
        platform_name="LinkedIn",
        api_endpoint="https://api.linkedin.com/v2",
        is_active=True
    )
    dbs.session.add(platform)
    dbs.session.commit()
    return platform


@pytest.fixture
def test_linked_account(test_user, test_platform_twitter):
    """Create and return a linked Twitter account."""
    account = LinkedAccount(
        user_id=test_user.user_id,
        platform_id=test_platform_twitter.platform_id,
        access_token="test_access_token_123",
        refresh_token="test_refresh_token_123",
        account_username="Test User (@testuser)",
        follower_count=1000,
        post_count=500
    )
    dbs.session.add(account)
    dbs.session.commit()
    return account


# ======================================================
# Helper Functions for Tests
# ======================================================
def create_mock_twitter_response(username="testuser", name="Test User", 
                                  followers=1000, tweets=500):
    """Helper to create mock Twitter API response."""
    return {
        "data": {
            "id": "123456789",
            "username": username,
            "name": name,
            "public_metrics": {
                "followers_count": followers,
                "following_count": 200,
                "tweet_count": tweets,
                "listed_count": 10
            }
        }
    }


def create_mock_linkedin_id_token(name="Test User", email="test@example.com"):
    """Helper to create mock LinkedIn ID token."""
    import json
    import base64
    
    payload = {
        "sub": "linkedin_user_123",
        "name": name,
        "email": email,
        "email_verified": True
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"header.{encoded}.signature"


# ======================================================
# Pytest Configuration
# ======================================================
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication test"
    )
    config.addinivalue_line(
        "markers", "social: mark test as social media connection test"
    )
