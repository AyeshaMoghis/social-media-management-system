"""
Pytest configuration - Forces tests to use SQLite (In-Memory)
"""
import os
import sys
from pathlib import Path
import pytest

# ==============================================================
# 1️⃣ Set environment variables BEFORE imports
# ==============================================================
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

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
# ⚠️ IMPORTANT: ensure your app/__init__.py defines `db = SQLAlchemy(app)`
# If your variable is called `dbs`, rename it to `db` in that file.
from app import app, db

# ==============================================================
# 4️⃣ Fixtures
# ==============================================================

@pytest.fixture(scope="session")
def test_app():
    """Creates and configures the Flask test app."""
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,
    })
    yield app


@pytest.fixture(scope="function")
def client(test_app):
    """Provides a Flask test client."""
    with test_app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def init_database(test_app):
    """Creates a clean in-memory SQLite database for each test."""
    with test_app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()
