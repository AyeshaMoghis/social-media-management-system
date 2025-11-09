"""
Pytest configuration - Forces tests to use SQLite
"""
import sys
import os
from pathlib import Path

# CRITICAL: Set environment variable BEFORE any imports
os.environ['TESTING'] = 'true'

# Add project paths
project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# NOW import after environment is set
from app import app, dbs as db
import pytest


@pytest.fixture(scope='function', autouse=True)
def setup_test_environment():
    """Setup fresh database for each test"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        dbs.drop_all()
        dbs.create_all()
        yield
        dbs.session.remove()
        dbs.drop_all()
