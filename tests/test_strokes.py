import json
from pathlib import Path
import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.errors import ValidationError


@pytest.fixture
def client():
    return MathpixClient()


@pytest.fixture
def quadratic_strokes() -> dict[str, list[list[int]]]:
    """Load quadratic equation strokes from JSON file."""
    strokes_path = Path(__file__).parent / "files" / "strokes" / "quadratic_eq.json"
    with open(strokes_path) as f:
        data = json.load(f)
    return data["strokes"]


def test_strokes_recognition(client: MathpixClient, quadratic_strokes: dict[str, list[list[int]]]):
    """Test basic stroke recognition."""
    result = client.strokes_new(strokes=quadratic_strokes)
    assert isinstance(result, dict)
    assert 'request_id' in result
    # Should recognize something - check that we get a response
    assert result.get('latex') is not None or result.get('text') is not None


def test_strokes_response_fields(client: MathpixClient, quadratic_strokes: dict[str, list[list[int]]]):
    """Test that response contains expected fields."""
    result = client.strokes_new(strokes=quadratic_strokes)
    assert isinstance(result, dict)
    assert 'request_id' in result


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


def test_strokes_session(client: MathpixClient, quadratic_strokes: dict[str, list[list[int]]]):
    """Test that strokes session with incremental strokes produces same result as one-shot."""
    # Get one-shot result
    oneshot_result = client.strokes_new(strokes=quadratic_strokes)
    oneshot_latex = oneshot_result.get('latex')
    # Create app token with strokes session
    token_result = client.app_token_new(include_strokes_session_id=True)
    strokes_session_id = token_result['strokes_session_id']
    # Submit strokes incrementally (simulating live drawing)
    num_strokes = len(quadratic_strokes['x'])
    session_result = None
    for i in range(num_strokes):
        partial_strokes = {
            'x': quadratic_strokes['x'][i: i + 1],
            'y': quadratic_strokes['y'][i: i + 1],
        }
        session_result = client.strokes_new(strokes=partial_strokes, strokes_session_id=strokes_session_id)
    assert session_result is not None
    session_latex = session_result.get('latex')
    # Final result should match one-shot
    assert oneshot_latex == session_latex
