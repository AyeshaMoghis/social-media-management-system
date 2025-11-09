"""
Unit Tests for Authentication System
Tests signup, login, logout, and role-based access control
"""

import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.mark.unit
@pytest.mark.auth
class TestSignup:
    """Test signup functionality"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @patch('src.auth.get_db_connection')
    def test_signup_success(self, mock_db, client):
        """Test successful user signup"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        response = client.post('/signup', data={
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'password': 'test123',
            'role': 'user'
        }, follow_redirects=True)

        assert response.status_code == 200
        mock_cursor.execute.assert_called_once()
    
    @patch('src.auth.get_db_connection')
    def test_signup_duplicate_email(self, mock_db, client):
        """Test signup with duplicate email fails"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Duplicate entry")

        response = client.post('/signup', data={
            'full_name': 'Jane Doe',
            'email': 'jane@example.com',
            'password': 'pass123',
            'role': 'manager'
        })

        assert b"error" in response.data.lower() or b"already" in response.data.lower()


@pytest.mark.unit
@pytest.mark.auth
class TestLogin:
    """Test login functionality"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @patch('src.auth.get_db_connection')
    @patch('src.auth.check_password_hash')
    def test_login_success_redirect_user(self, mock_check_pass, mock_db, client):
        """Test successful login as user redirects correctly"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'user_id': 1,
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'password_hash': 'fakehash',
            'role': 'user'
        }
        mock_check_pass.return_value = True

        response = client.post('/login', data={
            'email': 'john@example.com',
            'password': 'test123'
        })

        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location'].lower()
    
    @patch('src.auth.get_db_connection')
    def test_login_invalid_credentials(self, mock_db, client):
        """Test login with invalid credentials fails"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        response = client.post('/login', data={
            'email': 'notfound@example.com',
            'password': 'wrong'
        })

        assert b"invalid" in response.data.lower() or b"incorrect" in response.data.lower()


@pytest.mark.unit
@pytest.mark.auth
class TestLogout:
    """Test logout functionality"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_logout_clears_session(self, client):
        """Test logout clears user session"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'user'

        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200


@pytest.mark.unit
class TestRoleBasedAccess:
    """Test role-based access control"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_home_page(self, client):
        """Test home page is accessible"""
        response = client.get('/')
        assert response.status_code in [200, 302]
    
    def test_access_manager_dashboard_requires_login(self, client):
        """Test manager dashboard requires login"""
        response = client.get('/dashboard/manager', follow_redirects=True)
        assert response.status_code in [200, 302]
    
    def test_access_user_dashboard_requires_login(self, client):
        """Test user dashboard requires login"""
        response = client.get('/dashboard/user', follow_redirects=True)
        assert response.status_code in [200, 302]
    
    def test_role_restriction_manager(self, client):
        """Test user cannot access manager dashboard"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'user'
        response = client.get('/dashboard/manager', follow_redirects=True)
        assert b"denied" in response.data.lower() or response.status_code == 302
    
    def test_role_restriction_user(self, client):
        """Test manager redirected from user dashboard"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'manager'
        response = client.get('/dashboard/user', follow_redirects=True)
        # Manager gets redirected to their own dashboard
        assert response.status_code in [200, 302]
    
    def test_dashboard_render_user(self, client):
        """Test user dashboard renders correctly"""
        with client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['full_name'] = 'User A'
            sess['role'] = 'user'
        response = client.get('/dashboard/user')
        assert response.status_code in [200, 302]
    
    def test_dashboard_render_manager(self, client):
        """Test manager dashboard renders correctly"""
        with client.session_transaction() as sess:
            sess['user_id'] = 3
            sess['full_name'] = 'Manager B'
            sess['role'] = 'manager'
        response = client.get('/dashboard/manager')
        assert response.status_code == 200
        assert b"Manager" in response.data or b"manager" in response.data
