import pytest
from src.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 302  # Check it redirects
    assert response.location == '/login'  # Check it redirects to login

def test_access_manager_dashboard_requires_login(client):
    response = client.get('/dashboard/manager', follow_redirects=True)
    assert b"Access denied" in response.data

def test_access_user_dashboard_requires_login(client):
    response = client.get('/dashboard/user', follow_redirects=True)
    assert b"Access denied" in response.data

def test_role_restriction_manager(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'user'
    response = client.get('/dashboard/manager', follow_redirects=True)
    assert b"Access denied" in response.data

def test_role_restriction_user(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'manager'
    response = client.get('/dashboard/user', follow_redirects=True)
    assert b"Access denied" in response.data

def test_dashboard_render_user(client):
    # Create a user in the database
    from src.app import dbs, User
    user = User(user_id=2, email='user@test.com', full_name='User A', role='user')
    dbs.session.add(user)
    dbs.session.commit()
    
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['full_name'] = 'User A'
        sess['role'] = 'user'
    # User dashboard should render successfully (now renders directly instead of redirecting)
    response = client.get('/dashboard/user')
    assert response.status_code == 200
    assert b'User A' in response.data or b'Linked Accounts' in response.data
