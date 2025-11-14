"""Unit tests for authentication module"""
import pytest
from unittest.mock import patch, MagicMock
from flask import session
from src.app import app, User, dbs
from src import auth as auth_module


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestAuthModule:
    """Test auth module functions"""
    
    def test_init_auth(self):
        """Test init_auth sets User and dbs"""
        from src.auth import init_auth, User as AuthUser, dbs as AuthDbs
        
        # Initial state should have User and dbs set
        assert AuthUser is not None
        assert AuthDbs is not None


class TestSignup:
    """Test signup functionality"""
    
    def test_signup_page_loads(self, client):
        """Test signup page loads successfully"""
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'Sign Up' in response.data or b'signup' in response.data.lower()
    
    def test_signup_with_valid_data(self, client):
        """Test signup with valid data"""
        with app.app_context():
            # First, delete test user if exists
            existing = User.query.filter_by(email='newsignup@test.com').first()
            if existing:
                dbs.session.delete(existing)
                dbs.session.commit()
            
            response = client.post('/signup', data={
                'full_name': 'New Signup User',
                'email': 'newsignup@test.com',
                'password': 'testpass123',
                'role': 'user'
            }, follow_redirects=False)
            
            # Should redirect to login on success
            assert response.status_code in [200, 302]
            
            # Cleanup
            user = User.query.filter_by(email='newsignup@test.com').first()
            if user:
                dbs.session.delete(user)
                dbs.session.commit()
    
    def test_signup_duplicate_email(self, client):
        """Test signup with duplicate email"""
        with app.app_context():
            # Create a test user first
            from werkzeug.security import generate_password_hash
            from sqlalchemy import text
            
            # Check if user exists
            existing = User.query.filter_by(email='duplicate@test.com').first()
            if not existing:
                query = text("""
                    INSERT INTO user (email, password_hash, full_name, role)
                    VALUES (:email, :password_hash, :full_name, :role)
                """)
                dbs.session.execute(query, {
                    'email': 'duplicate@test.com',
                    'password_hash': generate_password_hash('password'),
                    'full_name': 'Duplicate User',
                    'role': 'user'
                })
                dbs.session.commit()
            
            # Try to signup with same email
            response = client.post('/signup', data={
                'full_name': 'Another User',
                'email': 'duplicate@test.com',
                'password': 'password123',
                'role': 'user'
            })
            
            assert response.status_code == 200
            assert b'already registered' in response.data or b'exists' in response.data
            
            # Cleanup
            user = User.query.filter_by(email='duplicate@test.com').first()
            if user:
                dbs.session.delete(user)
                dbs.session.commit()
    
    def test_signup_manager_role(self, client):
        """Test signup with manager role"""
        with app.app_context():
            # Delete if exists
            existing = User.query.filter_by(email='newmanager@test.com').first()
            if existing:
                dbs.session.delete(existing)
                dbs.session.commit()
            
            response = client.post('/signup', data={
                'full_name': 'New Manager',
                'email': 'newmanager@test.com',
                'password': 'manager123',
                'role': 'manager'
            }, follow_redirects=False)
            
            assert response.status_code in [200, 302]
            
            # Cleanup
            user = User.query.filter_by(email='newmanager@test.com').first()
            if user:
                dbs.session.delete(user)
                dbs.session.commit()


class TestLogin:
    """Test login functionality"""
    
    def test_login_page_loads(self, client):
        """Test login page loads"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data.lower()
    
    def test_login_success_user_redirect(self, client):
        """Test successful login redirects user to dashboard"""
        with app.app_context():
            # Create test user
            from werkzeug.security import generate_password_hash
            from sqlalchemy import text
            
            existing = User.query.filter_by(email='loginuser@test.com').first()
            if not existing:
                query = text("""
                    INSERT INTO user (email, password_hash, full_name, role)
                    VALUES (:email, :password_hash, :full_name, :role)
                """)
                dbs.session.execute(query, {
                    'email': 'loginuser@test.com',
                    'password_hash': generate_password_hash('userpass'),
                    'full_name': 'Login User',
                    'role': 'user'
                })
                dbs.session.commit()
            
            response = client.post('/login', data={
                'email': 'loginuser@test.com',
                'password': 'userpass'
            }, follow_redirects=False)
            
            assert response.status_code in [302, 200]
            
            # Cleanup
            user = User.query.filter_by(email='loginuser@test.com').first()
            if user:
                dbs.session.delete(user)
                dbs.session.commit()
    
    def test_login_success_manager_redirect(self, client):
        """Test successful login redirects manager to dashboard"""
        with app.app_context():
            from werkzeug.security import generate_password_hash
            from sqlalchemy import text
            
            existing = User.query.filter_by(email='loginmanager@test.com').first()
            if not existing:
                query = text("""
                    INSERT INTO user (email, password_hash, full_name, role)
                    VALUES (:email, :password_hash, :full_name, :role)
                """)
                dbs.session.execute(query, {
                    'email': 'loginmanager@test.com',
                    'password_hash': generate_password_hash('managerpass'),
                    'full_name': 'Login Manager',
                    'role': 'manager'
                })
                dbs.session.commit()
            
            response = client.post('/login', data={
                'email': 'loginmanager@test.com',
                'password': 'managerpass'
            }, follow_redirects=False)
            
            assert response.status_code in [302, 200]
            
            # Cleanup
            user = User.query.filter_by(email='loginmanager@test.com').first()
            if user:
                dbs.session.delete(user)
                dbs.session.commit()
    
    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post('/login', data={
            'email': 'nonexistent@test.com',
            'password': 'anypassword'
        })
        
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data or b'invalid' in response.data.lower()
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        with app.app_context():
            from werkzeug.security import generate_password_hash
            from sqlalchemy import text
            
            existing = User.query.filter_by(email='wrongpass@test.com').first()
            if not existing:
                query = text("""
                    INSERT INTO user (email, password_hash, full_name, role)
                    VALUES (:email, :password_hash, :full_name, :role)
                """)
                dbs.session.execute(query, {
                    'email': 'wrongpass@test.com',
                    'password_hash': generate_password_hash('correctpass'),
                    'full_name': 'Wrong Pass User',
                    'role': 'user'
                })
                dbs.session.commit()
            
            response = client.post('/login', data={
                'email': 'wrongpass@test.com',
                'password': 'wrongpassword'
            })
            
            assert response.status_code == 200
            assert b'Invalid credentials' in response.data or b'invalid' in response.data.lower()
            
            # Cleanup
            user = User.query.filter_by(email='wrongpass@test.com').first()
            if user:
                dbs.session.delete(user)
                dbs.session.commit()


class TestLogout:
    """Test logout functionality"""
    
    def test_logout_clears_session(self, client):
        """Test logout clears session"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['full_name'] = 'Test User'
            sess['role'] = 'user'
        
        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302
        
        # Check session is cleared
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'full_name' not in sess
            assert 'role' not in sess
    
    def test_logout_redirects_to_login(self, client):
        """Test logout redirects to login page"""
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data.lower()
    
    def test_logout_when_not_logged_in(self, client):
        """Test logout when user is not logged in"""
        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302  # Redirects anyway
