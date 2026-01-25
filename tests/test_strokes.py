import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.strokes import StrokesResult
from mpxpy.errors import ValidationError


@pytest.fixture
def client():
    return MathpixClient()


# Sample stroke data representing "3x^2"
SAMPLE_STROKES = {
    "x": [
        [131, 131, 130, 129, 128, 128, 128, 129, 131, 134, 138, 143, 150, 157, 167, 175, 184, 186, 188],
        [131, 130, 128, 126, 125, 126, 129, 134, 141, 150, 160, 169, 179, 188, 195],
        [231, 231, 233, 237, 244, 253, 264, 276, 288, 296],
        [305, 306, 310, 316, 325, 335, 347, 358, 368],
        [383, 384, 387, 393, 401, 412, 423, 433, 443]
    ],
    "y": [
        [188, 190, 194, 202, 213, 223, 233, 239, 241, 242, 239, 232, 222, 211, 198, 188, 181, 180, 180],
        [192, 192, 194, 198, 206, 217, 228, 239, 249, 258, 264, 267, 267, 263, 258],
        [199, 198, 198, 199, 202, 206, 210, 213, 215, 216],
        [188, 188, 189, 191, 194, 196, 198, 198, 197],
        [138, 139, 140, 143, 147, 151, 155, 157, 157]
    ]
}


def test_strokes_recognition(client: MathpixClient):
    """Test basic stroke recognition."""
    result = client.strokes_new(strokes=SAMPLE_STROKES)
    assert isinstance(result, StrokesResult)
    assert result.request_id is not None
    # Should recognize something - check that we get a response
    assert result.latex is not None or result.text is not None


def test_strokes_result_attributes(client: MathpixClient):
    """Test that StrokesResult has all expected attributes."""
    result = client.strokes_new(strokes=SAMPLE_STROKES)
    # Check all attributes exist (may be None but should be accessible)
    assert hasattr(result, 'session_id')
    assert hasattr(result, 'request_id')
    assert hasattr(result, 'text')
    assert hasattr(result, 'latex')
    assert hasattr(result, 'latex_simplified')
    assert hasattr(result, 'latex_confidence')
    assert hasattr(result, 'position')
    assert hasattr(result, 'detection_map')
    assert hasattr(result, 'detection_list')


def test_strokes_to_dict(client: MathpixClient):
    """Test that to_dict() returns the raw response."""
    result = client.strokes_new(strokes=SAMPLE_STROKES)
    raw_dict = result.to_dict()
    assert isinstance(raw_dict, dict)
    assert 'request_id' in raw_dict


def test_strokes_validation_missing_x():
    """Test validation when x is missing."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="must contain 'x' and 'y'"):
        client.strokes_new(strokes={"y": [[1, 2, 3]]})


def test_strokes_validation_missing_y():
    """Test validation when y is missing."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="must contain 'x' and 'y'"):
        client.strokes_new(strokes={"x": [[1, 2, 3]]})


def test_strokes_validation_empty_x():
    """Test validation when x is empty."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="must be non-empty"):
        client.strokes_new(strokes={"x": [], "y": [[1, 2, 3]]})


def test_strokes_validation_mismatched_stroke_count():
    """Test validation when x and y have different number of strokes."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="same number of strokes"):
        client.strokes_new(strokes={
            "x": [[1, 2, 3], [4, 5, 6]],
            "y": [[1, 2, 3]]
        })


def test_strokes_validation_mismatched_point_count():
    """Test validation when a stroke has mismatched x and y point counts."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="same number of points"):
        client.strokes_new(strokes={
            "x": [[1, 2, 3]],
            "y": [[1, 2]]
        })


def test_strokes_validation_empty_stroke():
    """Test validation when a stroke is empty."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="cannot be empty"):
        client.strokes_new(strokes={
            "x": [[]],
            "y": [[]]
        })


def test_strokes_repr():
    """Test StrokesResult string representation."""
    result = StrokesResult({"latex": "x^2", "latex_confidence": 0.95, "request_id": "test"})
    repr_str = repr(result)
    assert "x^2" in repr_str
    assert "0.95" in repr_str


def test_strokes_repr_with_error():
    """Test StrokesResult string representation with error."""
    result = StrokesResult({"error": "test error", "request_id": "test"})
    repr_str = repr(result)
    assert "error" in repr_str
    assert "test error" in repr_str


# App Token Tests

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
