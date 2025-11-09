import pytest
from unittest.mock import patch

@patch('app.secrets.token_urlsafe')
def test_linkedin_connect(mock_token, client, init_database):
    """Test LinkedIn OAuth initiation"""
    mock_token.return_value = "test_state"
    
    response = client.get('/connect/linkedin')
    assert response.status_code == 302
    assert 'linkedin.com' in response.location