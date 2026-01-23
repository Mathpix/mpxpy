import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Any
import pytest
from mpxpy.mathpix_client import MathpixClient

TESTS_DIR = Path(__file__).parent
TEST_PDF_PATH = str(TESTS_DIR / "files" / "pdfs" / "sample.pdf")


@pytest.fixture
def client():
    return MathpixClient()


def wait_for_pdf_id_in_results(
    query_fn: Callable[[], dict[str, Any]],
    pdf_id: str,
    timeout: int = 30
) -> dict[str, Any]:
    """Poll until pdf_id appears in query results."""
    start = time.time()
    while time.time() - start < timeout:
        result = query_fn()
        if result.get("pdfs"):
            for pdf_result in result["pdfs"]:
                if pdf_result.get("id") == pdf_id:
                    return result
        time.sleep(1)
    return query_fn()


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


def test_query_pdf_results_filter_by_pdf_id(client: MathpixClient):
    """Test PDF results query filtered by pdf_id returns the correct result."""
    pdf = client.pdf_new(file_path=TEST_PDF_PATH)
    pdf_id = pdf.pdf_id
    assert pdf.wait_until_complete(timeout=60)
    # Poll until our PDF appears in results
    result = wait_for_pdf_id_in_results(
        lambda: client.query_pdf_results(pdf_id=pdf_id),
        pdf_id,
        timeout=30
    )
    assert isinstance(result, dict)
    assert "pdfs" in result
    assert len(result["pdfs"]) >= 1
    # Verify our pdf_id is in the results
    pdf_ids = [p["id"] for p in result["pdfs"]]
    assert pdf_id in pdf_ids


def test_query_pdf_results_nonexistent_pdf_id(client: MathpixClient):
    """Test PDF results query with nonexistent pdf_id returns empty."""
    result = client.query_pdf_results(pdf_id=str(uuid.uuid4()))
    assert isinstance(result, dict)
    assert "pdfs" in result
    assert len(result["pdfs"]) == 0


def test_query_pdf_results_response_structure(client: MathpixClient):
    """Test PDF results response structure when results exist."""
    pdf = client.pdf_new(file_path=TEST_PDF_PATH)
    pdf_id = pdf.pdf_id
    assert pdf.wait_until_complete(timeout=60)
    # Poll until our PDF appears in results
    result = wait_for_pdf_id_in_results(
        lambda: client.query_pdf_results(pdf_id=pdf_id),
        pdf_id,
        timeout=30
    )
    assert isinstance(result, dict)
    assert "pdfs" in result
    assert len(result["pdfs"]) >= 1
    # Find our PDF and verify structure
    pdf_result = next(p for p in result["pdfs"] if p["id"] == pdf_id)
    assert "id" in pdf_result
    assert "status" in pdf_result
    assert "created_at" in pdf_result
    assert "modified_at" in pdf_result
    assert "num_pages" in pdf_result
    assert pdf_result["id"] == pdf_id
