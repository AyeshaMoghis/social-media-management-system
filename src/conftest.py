"""
Pytest Fixtures and Configuration
Shared fixtures for notification system tests
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add source directory to path
sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture(scope='session')
def setup_test_env():
    """Setup test environment variables"""
    os.environ['TESTING'] = 'true'
    os.environ['MYSQL_HOST'] = '127.0.0.1'
    os.environ['MYSQL_USER'] = 'root'
    os.environ['MYSQL_PASSWORD'] = 'testpass'
    os.environ['MYSQL_DB'] = 'smms_test'
    os.environ['EMAIL_ENABLED'] = 'false'
    yield
    # Cleanup
    for key in ['TESTING', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB', 'EMAIL_ENABLED']:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    mock_cursor = MagicMock()
    mock_cursor.lastrowid = 1
    mock_cursor.rowcount = 1
    mock_cursor.fetchone.return_value = {'count': 1}
    mock_cursor.fetchall.return_value = []
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    return mock_conn


@pytest.fixture
def mock_notification_service():
    """Mock notification microservice responses"""
    with patch('notification_helper.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "status": "created",
            "notification_id": 1
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def sample_notification_payload():
    """Sample notification payload"""
    return {
        "user_id": 1,
        "post_id": 10,
        "status": "published",
        "platform": "LinkedIn",
        "notification_type": "system"
    }


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "user_id": 1,
        "full_name": "Test User",
        "email": "test@example.com",
        "role": "user"
    }


@pytest.fixture
def sample_post():
    """Sample post data"""
    return {
        "post_id": 10,
        "user_id": 1,
        "content": "Test post content",
        "status": "draft",
        "created_at": datetime.now()
    }


@pytest.fixture
def sample_notification():
    """Sample notification data"""
    return {
        "notification_id": 1,
        "user_id": 1,
        "post_id": 10,
        "schedule_id": None,
        "notification_type": "system",
        "title": "✅ Post published on LinkedIn",
        "message": "Your post (ID: 10) was successfully published on LinkedIn.",
        "sent_via": "in_app",
        "is_read": False,
        "read_at": None,
        "created_at": datetime.now()
    }


@pytest.fixture
def notifapp_client():
    """Create test client for notification microservice"""
    try:
        from notifapp import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    except ImportError:
        pytest.skip("notifapp module not available")


@pytest.fixture
def app_client():
    """Create test client for main app"""
    try:
        from app import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    except ImportError:
        pytest.skip("app module not available")


# ========================================
# PYTEST HOOKS
# ========================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers"""
    # Add unit marker to tests that don't have integration or e2e markers
    for item in items:
        if "integration" not in item.keywords and "e2e" not in item.keywords:
            item.add_marker(pytest.mark.unit)


def pytest_report_header(config):
    """Add custom header to pytest report"""
    return [
        "SMMS Notification System Test Suite",
        f"Python: {sys.version}",
        f"Pytest: {pytest.__version__}"
    ]
