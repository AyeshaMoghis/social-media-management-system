"""
Unit tests for authentication module
Tests all auth routes: signup, login, logout, Google OAuth, forgot password, OTP verification
"""
import pytest
from flask import session
from unittest.mock import Mock, patch, MagicMock
from werkzeug.security import generate_password_hash
import time
import os


class TestSignup:
    """Test user signup functionality"""
    
    def test_signup_get_request(self, client):
        """Test GET request renders signup page"""
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'signup' in response.data.lower() or b'sign up' in response.data.lower()
    
    def test_signup_success_user(self, client):
        """Test successful user signup"""
        response = client.post('/signup', data={
            'full_name': 'Test User',
            'email': 'newuser@example.com',
            'password': 'password123',
            'role': 'user'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Account created successfully' in response.data or b'created' in response.data.lower()
        
        # Verify user exists in database
        from src.app import User, dbs
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.full_name == 'Test User'
        assert user.role == 'user'
    
    def test_signup_success_manager(self, client):
        """Test successful manager signup"""
        response = client.post('/signup', data={
            'full_name': 'Test Manager',
            'email': 'newmanager@example.com',
            'password': 'password123',
            'role': 'manager'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        from src.app import User
        user = User.query.filter_by(email='newmanager@example.com').first()
        assert user is not None
        assert user.role == 'manager'
    
    def test_signup_duplicate_email(self, client, test_user):
        """Test signup with existing email"""
        response = client.post('/signup', data={
            'full_name': 'Another User',
            'email': 'user@example.com',  # Already exists
            'password': 'password123',
            'role': 'user'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already registered' in response.data.lower() or b'exists' in response.data.lower()
    
    def test_signup_default_role(self, client):
        """Test signup defaults to 'user' role if not specified"""
        response = client.post('/signup', data={
            'full_name': 'Default Role User',
            'email': 'defaultrole@example.com',
            'password': 'password123'
            # role not provided
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        from src.app import User
        user = User.query.filter_by(email='defaultrole@example.com').first()
        assert user.role == 'user'
    
    def test_signup_missing_fields(self, client):
        """Test signup with missing required fields"""
        response = client.post('/signup', data={
            'email': 'incomplete@example.com'
            # missing full_name and password
        })
        
        # Should either return 400 or render signup page with error
        assert response.status_code in [200, 400]


class TestLogin:
    """Test user login functionality"""
    
    def test_login_get_request(self, client):
        """Test GET request renders login page"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'sign in' in response.data.lower()
    
    def test_login_success_user(self, client, test_user):
        """Test successful user login"""
        response = client.post('/login', data={
            'email': 'user@example.com',
            'password': 'user123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check session was set
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert sess['role'] == 'user'
            assert sess['full_name'] == 'Test User'
    
    def test_login_success_manager(self, client, test_manager):
        """Test successful manager login redirects to manager dashboard"""
        response = client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert sess['role'] == 'manager'
    
    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post('/login', data={
            'email': 'nonexistent@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data or b'invalid' in response.data.lower()
        
        # Session should not be set
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post('/login', data={
            'email': 'user@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data or b'invalid' in response.data.lower()
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
    
    def test_login_empty_credentials(self, client):
        """Test login with empty credentials"""
        response = client.post('/login', data={
            'email': '',
            'password': ''
        })
        
        assert response.status_code in [200, 400]


class TestLogout:
    """Test logout functionality"""
    
    def test_logout_clears_session(self, client, test_user):
        """Test logout clears session data"""
        # First login
        client.post('/login', data={
            'email': 'user@example.com',
            'password': 'user123'
        })
        
        # Verify logged in
        with client.session_transaction() as sess:
            assert 'user_id' in sess
        
        # Logout
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Verify session cleared
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'role' not in sess
            assert 'full_name' not in sess
    
    def test_logout_redirects_to_login(self, client, test_user):
        """Test logout redirects to login page"""
        client.post('/login', data={
            'email': 'user@example.com',
            'password': 'user123'
        })
        
        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location


class TestGoogleOAuth:
    """Test Google OAuth login"""
    
    @patch('src.auth.oauth.google')
    def test_google_login_redirect(self, mock_google, client):
        """Test /login/google redirects to Google OAuth"""
        # Create a proper mock response that Flask can return
        from flask import Response
        mock_response = Response(status=302)
        mock_response.headers['Location'] = 'https://accounts.google.com/oauth'
        mock_google.authorize_redirect.return_value = mock_response
        
        response = client.get('/login/google')
        
        # Should call authorize_redirect
        mock_google.authorize_redirect.assert_called_once()
        # Verify it returned a redirect response
        assert response.status_code == 302
    
    @patch('src.auth.oauth.google')
    def test_google_callback_new_user(self, mock_google, client):
        """Test Google callback creates new user"""
        # Mock token and userinfo
        mock_google.authorize_access_token.return_value = {'access_token': 'test_token'}
        mock_google.get.return_value.json.return_value = {
            'email': 'googleuser@example.com',
            'name': 'Google User'
        }
        
        response = client.get('/google/callback', follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify user created
        from src.app import User
        user = User.query.filter_by(email='googleuser@example.com').first()
        assert user is not None
        assert user.full_name == 'Google User'
        assert user.role == 'user'
        
        # Verify logged in
        with client.session_transaction() as sess:
            assert sess['user_id'] == user.user_id
    
    @patch('src.auth.oauth.google')
    def test_google_callback_existing_user(self, mock_google, client, test_user):
        """Test Google callback with existing user"""
        mock_google.authorize_access_token.return_value = {'access_token': 'test_token'}
        mock_google.get.return_value.json.return_value = {
            'email': 'user@example.com',  # Existing user
            'name': 'Test User'
        }
        
        response = client.get('/google/callback', follow_redirects=True)
        
        assert response.status_code == 200
        
        # Should login existing user - check what the code actually sets
        with client.session_transaction() as sess:
            assert sess['user_id'] == test_user
            # The code sets user_id, full_name, and role - NOT email
            assert sess['full_name'] == 'Test User'
            assert sess['role'] == 'user'
    
    @patch('src.auth.oauth.google')
    def test_google_callback_no_email(self, mock_google, client):
        """Test Google callback fails without email"""
        mock_google.authorize_access_token.return_value = {'access_token': 'test_token'}
        mock_google.get.return_value.json.return_value = {
            'name': 'No Email User'
            # email missing
        }
        
        response = client.get('/google/callback', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Failed to get email' in response.data or b'failed' in response.data.lower()
        
        # Should not be logged in
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
    
    @patch('src.auth.oauth.google')
    def test_google_callback_manager(self, mock_google, client, test_manager):
        """Test Google callback redirects manager to manager dashboard"""
        mock_google.authorize_access_token.return_value = {'access_token': 'test_token'}
        mock_google.get.return_value.json.return_value = {
            'email': 'manager@example.com',
            'name': 'Test Manager'
        }
        
        response = client.get('/google/callback', follow_redirects=False)
        
        # Should redirect to manager dashboard
        assert response.status_code == 302

class TestForgotPassword:
    """Test forgot password functionality"""
    
    def test_forgot_password_get(self, client):
        """Test GET request renders forgot password page"""
        response = client.get('/forgot-password')
        assert response.status_code == 200
        assert b'forgot' in response.data.lower() or b'reset' in response.data.lower()
    
    @patch('src.auth.current_app')
    def test_forgot_password_success(self, mock_app, client, test_user):
        """Test forgot password sends OTP"""
        # Mock Flask-Mail
        mock_mail = MagicMock()
        mock_app.extensions = {'mail': mock_mail}
        
        response = client.post('/forgot-password', data={
            'email': 'user@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'OTP has been sent' in response.data or b'otp' in response.data.lower()
        
        # Check OTP stored in session
        with client.session_transaction() as sess:
            assert 'reset_email' in sess
            assert 'reset_otp' in sess
            assert sess['reset_email'] == 'user@example.com'
            assert isinstance(sess['reset_otp'], int)
            assert 100000 <= sess['reset_otp'] <= 999999
        
        # Verify email was sent
        mock_mail.send.assert_called_once()
    
    def test_forgot_password_invalid_email(self, client):
        """Test forgot password with non-existent email"""
        response = client.post('/forgot-password', data={
            'email': 'nonexistent@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'No account' in response.data or b'not exist' in response.data.lower()
    
    @patch('src.auth.current_app')
    def test_forgot_password_cooldown(self, mock_app, client, test_user):
        """Test OTP cooldown prevents spam"""
        mock_mail = MagicMock()
        mock_app.extensions = {'mail': mock_mail}
        
        # First request
        client.post('/forgot-password', data={
            'email': 'user@example.com'
        })
        
        # Immediate second request should fail
        response = client.post('/forgot-password', data={
            'email': 'user@example.com'
        }, follow_redirects=True)
        
        assert b'Please wait' in response.data or b'cooldown' in response.data.lower()


class TestVerifyOTP:
    """Test OTP verification"""
    
    def test_verify_otp_get(self, client):
        """Test GET request renders OTP verification page"""
        response = client.get('/verify-otp')
        assert response.status_code == 200
        assert b'otp' in response.data.lower() or b'verify' in response.data.lower()
    
    def test_verify_otp_success(self, client):
        """Test successful OTP verification"""
        # Set up session with OTP
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
            sess['reset_otp'] = 123456
        
        response = client.post('/verify-otp', data={
            'otp': '123456'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verified' in response.data.lower() or b'success' in response.data.lower()
    
    def test_verify_otp_invalid(self, client):
        """Test invalid OTP"""
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
            sess['reset_otp'] = 123456
        
        response = client.post('/verify-otp', data={
            'otp': '999999'  # Wrong OTP
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid OTP' in response.data or b'invalid' in response.data.lower()
    
    def test_verify_otp_max_attempts(self, client):
        """Test OTP verification locks after max attempts"""
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
            sess['reset_otp'] = 123456
            sess['otp_attempts'] = 5  # Already at max
        
        response = client.post('/verify-otp', data={
            'otp': '999999'
        }, follow_redirects=True)
        
        assert b'Too many attempts' in response.data or b'request a new' in response.data.lower()
        
        # OTP should be cleared
        with client.session_transaction() as sess:
            assert 'reset_otp' not in sess
    
    def test_verify_otp_string_comparison(self, client):
        """Test OTP verification handles string comparison correctly"""
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
            sess['reset_otp'] = 123456
        
        # Try with string input
        response = client.post('/verify-otp', data={
            'otp': '123456'  # String version
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'verified' in response.data.lower() or b'success' in response.data.lower()


class TestResetPassword:
    """Test password reset"""
    
    def test_reset_password_get(self, client):
        """Test GET request renders reset password page"""
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
        
        response = client.get('/reset-password')
        assert response.status_code == 200
        assert b'password' in response.data.lower() or b'reset' in response.data.lower()
    
    def test_reset_password_success(self, client, test_user):
        """Test successful password reset"""
        # Set up session after OTP verification
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
            sess['reset_otp'] = 123456
        
        new_password = 'newpassword123'
        response = client.post('/reset-password', data={
            'password': new_password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Password reset successful' in response.data or b'success' in response.data.lower()
        
        # Verify session cleared
        with client.session_transaction() as sess:
            assert 'reset_email' not in sess
            assert 'reset_otp' not in sess
        
        # Try logging in with new password
        response = client.post('/login', data={
            'email': 'user@example.com',
            'password': new_password
        }, follow_redirects=True)
        
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert 'user_id' in sess
    
    def test_reset_password_expired_session(self, client):
        """Test reset password fails without valid session"""
        # No reset_email in session
        response = client.post('/reset-password', data={
            'password': 'newpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Session expired' in response.data or b'expired' in response.data.lower()
    
    def test_reset_password_updates_hash(self, client, test_user):
        """Test password reset actually updates the hash"""
        from src.app import User, dbs
        from werkzeug.security import check_password_hash
        
        # Get original hash
        user = User.query.get(test_user)
        original_hash = user.password_hash
        
        # Reset password
        with client.session_transaction() as sess:
            sess['reset_email'] = 'user@example.com'
        
        client.post('/reset-password', data={
            'password': 'brandnewpassword'
        })
        
        # Check hash changed
        dbs.session.refresh(user)
        assert user.password_hash != original_hash
        assert check_password_hash(user.password_hash, 'brandnewpassword')


class TestAuthIntegration:
    """Integration tests for complete auth flows"""
    
    def test_complete_signup_login_logout_flow(self, client):
        """Test complete user journey: signup -> login -> logout"""
        # 1. Signup
        response = client.post('/signup', data={
            'full_name': 'Integration Test User',
            'email': 'integration@example.com',
            'password': 'testpass123',
            'role': 'user'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 2. Login
        response = client.post('/login', data={
            'email': 'integration@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert sess['user_id'] is not None
        
        # 3. Logout
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
    
    @patch('src.auth.current_app')
    def test_complete_password_reset_flow(self, mock_app, client, test_user):
        """Test complete password reset flow"""
        mock_mail = MagicMock()
        mock_app.extensions = {'mail': mock_mail}
        
        # 1. Request OTP
        response = client.post('/forgot-password', data={
            'email': 'user@example.com'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Get OTP from session
        with client.session_transaction() as sess:
            otp = sess['reset_otp']
        
        # 2. Verify OTP
        response = client.post('/verify-otp', data={
            'otp': str(otp)
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 3. Reset password
        response = client.post('/reset-password', data={
            'password': 'newpassword456'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 4. Login with new password
        response = client.post('/login', data={
            'email': 'user@example.com',
            'password': 'newpassword456'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert sess['user_id'] == test_user
    
    def test_role_based_redirect(self, client, test_user, test_manager):
        """Test users and managers redirect to correct dashboards"""
        # User login
        response = client.post('/login', data={
            'email': 'user@example.com',
            'password': 'user123'
        }, follow_redirects=False)
        
        # Should redirect to user dashboard
        assert response.status_code == 302
        assert 'user' in response.location.lower() or 'linked' in response.location.lower()
        
        # Logout
        client.get('/logout')
        
        # Manager login
        response = client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        }, follow_redirects=False)
        
        # Should redirect to manager dashboard
        assert response.status_code == 302
        assert 'manager' in response.location.lower()


# Fixtures for tests
@pytest.fixture
def test_user(client):
    """Create a test user"""
    from src.app import User, dbs
    from werkzeug.security import generate_password_hash
    
    user = User(
        email='user@example.com',
        password_hash=generate_password_hash('user123'),
        full_name='Test User',
        role='user'
    )
    dbs.session.add(user)
    dbs.session.commit()
    return user.user_id


@pytest.fixture
def test_manager(client):
    """Create a test manager"""
    from src.app import User, dbs
    from werkzeug.security import generate_password_hash
    
    manager = User(
        email='manager@example.com',
        password_hash=generate_password_hash('manager123'),
        full_name='Test Manager',
        role='manager'
    )
    dbs.session.add(manager)
    dbs.session.commit()
    return manager.user_id
