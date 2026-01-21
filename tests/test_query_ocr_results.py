from datetime import datetime, timedelta, timezone
import pytest
from mpxpy.mathpix_client import MathpixClient


@pytest.fixture
def client():
    return MathpixClient()


def test_query_ocr_results_basic(client: MathpixClient):
    """Test basic OCR results query."""
    result = client.query_ocr_results()
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert isinstance(result["ocr_results"], list)


def test_query_ocr_results_with_date_range(client: MathpixClient):
    """Test OCR results query with date range."""
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=7)
    result = client.query_ocr_results(
        from_date=from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        to_date=to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    assert isinstance(result, dict)
    assert "ocr_results" in result


def test_query_ocr_results_pagination(client: MathpixClient):
    """Test OCR results query pagination."""
    result = client.query_ocr_results(page=1, per_page=5)
    assert isinstance(result, dict)
    assert "ocr_results" in result


def test_query_ocr_results_include_null(client: MathpixClient):
    """Test OCR results query including null results."""
    result = client.query_ocr_results(include_null_results=True)
    assert isinstance(result, dict)
    assert "ocr_results" in result
