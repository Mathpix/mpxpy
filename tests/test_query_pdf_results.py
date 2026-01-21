import os
from datetime import datetime, timedelta, timezone
import pytest
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_query_pdf_results_basic(client: MathpixClient):
    """Test basic PDF results query."""
    result = client.query_pdf_results()
    assert isinstance(result, dict)
    assert "pdfs" in result
    assert isinstance(result["pdfs"], list)


def test_query_pdf_results_with_date_range(client: MathpixClient):
    """Test PDF results query with date range."""
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=30)
    result = client.query_pdf_results(
        from_date=from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        to_date=to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    assert isinstance(result, dict)
    assert "pdfs" in result


def test_query_pdf_results_pagination(client: MathpixClient):
    """Test PDF results query pagination."""
    result = client.query_pdf_results(page=1, per_page=5)
    assert isinstance(result, dict)
    assert "pdfs" in result


def test_query_pdf_results_with_process_and_query(client: MathpixClient):
    """Test processing a PDF and then querying for it.

    Note: Results may not appear immediately in the query API due to
    async indexing, so we just verify the query returns a valid response.
    """
    pdf_file_path = os.path.join(current_dir, "files/pdfs/sample.pdf")
    if not os.path.exists(pdf_file_path):
        pytest.skip(f"Test file not found: {pdf_file_path}")
    pdf = client.pdf_new(file_path=pdf_file_path)
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    result = client.query_pdf_results(pdf_id=pdf.pdf_id)
    assert isinstance(result, dict)
    assert "pdfs" in result
    assert isinstance(result["pdfs"], list)
