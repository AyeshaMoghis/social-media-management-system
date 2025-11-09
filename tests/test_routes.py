import pytest

def test_home_redirect(client, init_database):
    """Test home page redirects"""
    response = client.get('/')
    assert response.status_code == 302
    assert '/linked-accounts' in response.location

def test_linked_accounts_loads(client, init_database):
    """Test linked accounts page"""
    response = client.get('/linked-accounts')
    assert response.status_code == 200