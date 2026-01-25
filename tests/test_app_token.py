import pytest
from mpxpy.mathpix_client import MathpixClient


@pytest.fixture
def client():
    return MathpixClient()


def test_app_token_new_basic(client: MathpixClient):
    """Test creating a basic app token."""
    result = client.app_token_new()
    assert isinstance(result, dict)
    assert 'app_token' in result
    assert result['app_token'].startswith('token_')
    assert 'app_token_expires_at' in result
    assert result['app_token_expires_at'] > 0


def test_app_token_new_with_strokes_session(client: MathpixClient):
    """Test creating an app token with strokes session."""
    result = client.app_token_new(include_strokes_session_id=True)
    assert isinstance(result, dict)
    assert 'app_token' in result
    assert 'strokes_session_id' in result
    assert result['strokes_session_id'].startswith('strokes_')


def test_app_token_new_with_expires(client: MathpixClient):
    """Test creating an app token with custom expiration."""
    result = client.app_token_new(expires=60)
    assert isinstance(result, dict)
    assert 'app_token' in result
    assert 'app_token_expires_at' in result


def test_app_token_new_with_user_id(client: MathpixClient):
    """Test creating an app token with user_id."""
    result = client.app_token_new(user_id='test_user_123')
    assert isinstance(result, dict)
    assert 'app_token' in result
    assert 'app_token_expires_at' in result


def test_app_token_get(client: MathpixClient):
    """Test getting app token info."""
    # First create a token
    create_result = client.app_token_new()
    app_token = create_result['app_token']
    # Then get its info
    result = client.app_token_get(app_token)
    assert isinstance(result, dict)
    assert result['app_token'] == app_token
    assert 'app_token_expires_at' in result
    assert 'app_id' in result
    assert 'group_id' in result


def test_app_token_delete(client: MathpixClient):
    """Test deleting an app token."""
    # First create a token
    create_result = client.app_token_new()
    app_token = create_result['app_token']
    # Then delete it
    result = client.app_token_delete(app_token)
    assert isinstance(result, dict)
    assert result['app_token'] == app_token
    assert 'app_id' in result
    assert 'group_id' in result


def test_app_token_get_after_delete_returns_error(client: MathpixClient):
    """Test that getting a deleted token returns an error response."""
    create_result = client.app_token_new()
    app_token = create_result['app_token']
    client.app_token_delete(app_token)
    result = client.app_token_get(app_token)
    # API returns 200 with error in body instead of 404
    assert 'error' in result
    assert result['error_info']['id'] == 'token_unknown'
