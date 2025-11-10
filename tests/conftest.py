"""
Test configuration and fixtures
"""
import pytest
import os

# Set testing environment BEFORE importing app
os.environ['TESTING'] = 'true'

from src.app import app, dbs


@pytest.fixture(scope='function', autouse=True)
def setup_database():
    """Setup test database before each test and cleanup after"""
    with app.app_context():
        # Create all tables
        dbs.create_all()
        
        yield
        
        # Cleanup after test
        dbs.session.remove()
        dbs.drop_all()


@pytest.fixture
def client():
    """Create test client - single instance per test"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    with app.test_client() as test_client:
        yield test_client
