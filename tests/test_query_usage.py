from datetime import datetime, timedelta, timezone
import pytest
from mpxpy.mathpix_client import MathpixClient


@pytest.fixture
def client():
    return MathpixClient()


def test_query_usage_basic(client: MathpixClient):
    """Test basic usage query."""
    result = client.query_usage()
    assert isinstance(result, dict)
    assert "ocr_usage" in result
    assert isinstance(result["ocr_usage"], list)


def test_query_usage_with_date_range(client: MathpixClient):
    """Test usage query with date range."""
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=7)
    result = client.query_usage(
        from_date=from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        to_date=to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    assert isinstance(result, dict)
    assert "ocr_usage" in result


def test_query_usage_with_timespan(client: MathpixClient):
    """Test usage query with timespan aggregation."""
    result = client.query_usage(timespan="day")
    assert isinstance(result, dict)
    assert "ocr_usage" in result


def test_query_usage_with_group_by(client: MathpixClient):
    """Test usage query with grouping."""
    result = client.query_usage(
        timespan="day",
        group_by=["usage_type"]
    )
    assert isinstance(result, dict)
    assert "ocr_usage" in result


def test_query_usage_with_usage_type_filter(client: MathpixClient):
    """Test usage query filtered by usage type."""
    result = client.query_usage(usage_type="image")
    assert isinstance(result, dict)
    assert "ocr_usage" in result


def test_query_usage_pagination(client: MathpixClient):
    """Test usage query pagination parameters."""
    result = client.query_usage(page=1, per_page=10)
    assert isinstance(result, dict)
    assert "ocr_usage" in result
