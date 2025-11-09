"""
Pytest configuration - Forces tests to use SQLite (In-Memory)
"""
import sys
import os
from pathlib import Path
import pytest

# ==============================================================
# 1️⃣ Set environment variable BEFORE imports
# ==============================================================
os.environ['TESTING'] = 'true'

# ==============================================================
# 2️⃣ Add project paths
# ==============================================================
project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# ==============================================================
# 3️⃣ Import AFTER environment setup
# ==============================================================
from app import app, dbs

# ==============================================================
# 4️⃣ Fixtures
# ==============================================================

@pytest.fixture(scope='session')
def test_app():
    """Creates and configures the Flask test app."""
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    yield app


@pytest.fixture(scope='function')
def client(test_app):
    """Provides a Flask test client."""
    with test_app.test_client() as client:
        yield client


@pytest.fixture(scope='function')
def init_database(test_app):
    """Creates a clean database before each test."""
    with test_app.app_context():
        dbs.drop_all()
        dbs.create_all()
        yield dbs
        dbs.session.remove()
        dbs.drop_all()
