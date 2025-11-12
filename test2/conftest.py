"""
Test configuration and fixtures for test2 directory
"""
import pytest
import os

# Set testing environment BEFORE importing app
os.environ['TESTING'] = 'true'

from src.app import app, dbs


@pytest.fixture(scope='function')
def session():
    """Provide a database session for tests"""
    with app.app_context():
        dbs.create_all()
        yield dbs.session
        dbs.session.remove()
        dbs.drop_all()


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key-12345'
    
    with app.test_client() as test_client:
        with app.app_context():
            dbs.create_all()
            yield test_client
            dbs.session.remove()
            dbs.drop_all()
