import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Any
import pytest
from mpxpy.mathpix_client import MathpixClient

TESTS_DIR = Path(__file__).parent
TEST_IMAGE_PATH = str(TESTS_DIR / "files" / "images" / "cases_hw.png")
TEST_PDF_PATH = str(TESTS_DIR / "files" / "pdfs" / "sample.pdf")


@pytest.fixture
def client():
    return MathpixClient()


def wait_for_ocr_result(fn: Callable[[], dict[str, Any]], timeout: int = 10):
    """Retry fn until ocr_results is non-empty or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        result = fn()
        if result.get("ocr_results") and len(result["ocr_results"]) > 0:
            return result
        time.sleep(1)
    return fn()


def wait_for_request_id_in_results(
    query_fn: Callable[[], dict[str, Any]],
    request_id: str,
    timeout: int = 30
) -> dict[str, Any]:
    """Poll until request_id appears in query results."""
    start = time.time()
    while time.time() - start < timeout:
        result = query_fn()
        if result.get("ocr_results"):
            for ocr_result in result["ocr_results"]:
                if ocr_result.get("image_id") == request_id:
                    return result
        time.sleep(1)
    return query_fn()


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


def test_query_ocr_results_filter_by_request_id(client: MathpixClient):
    """Test OCR results query filtered by request_id returns the correct result."""
    image = client.image_new(file_path=TEST_IMAGE_PATH)
    request_id = image.request_id
    result = wait_for_ocr_result(lambda: client.query_ocr_results(request_id=request_id))
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) == 1
    assert result["ocr_results"][0]["image_id"] == request_id


def test_query_ocr_results_filter_by_tags(client: MathpixClient):
    """Test OCR results query filtered by tags returns matching results."""
    tag = f"mpxpy-test-{uuid.uuid4().hex[:8]}"
    image = client.image_new(file_path=TEST_IMAGE_PATH, tags=[tag])
    request_id = image.request_id
    result = wait_for_ocr_result(lambda: client.query_ocr_results(tags=[tag]))
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) >= 1
    request_ids = [r["image_id"] for r in result["ocr_results"]]
    assert request_id in request_ids


def test_query_ocr_results_nonexistent_request_id(client: MathpixClient):
    """Test OCR results query with nonexistent request_id returns empty."""
    result = client.query_ocr_results(request_id=str(uuid.uuid4()))
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) == 0


def test_query_ocr_results_nonexistent_pdf_id(client: MathpixClient):
    """Test OCR results query with nonexistent pdf_id returns empty."""
    result = client.query_ocr_results(pdf_id=str(uuid.uuid4()))
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) == 0


def test_query_ocr_results_filter_by_pdf_id(client: MathpixClient):
    """Test OCR results query filtered by pdf_id returns matching results."""
    pdf = client.pdf_new(file_path=TEST_PDF_PATH)
    pdf_id = pdf.pdf_id
    assert pdf.wait_until_complete(timeout=60)
    result = wait_for_ocr_result(lambda: client.query_ocr_results(pdf_id=pdf_id))
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) >= 1
    # All results should be from this PDF
    for ocr_result in result["ocr_results"]:
        assert "image_id" in ocr_result


def test_query_ocr_results_filter_is_handwritten(client: MathpixClient):
    """Test OCR results query with is_handwritten filter using handwritten image."""
    image = client.image_new(file_path=TEST_IMAGE_PATH)
    request_id = image.request_id
    # Poll until our handwritten image appears in is_handwritten=True results
    result = wait_for_request_id_in_results(
        lambda: client.query_ocr_results(is_handwritten=True, per_page=100),
        request_id,
        timeout=30
    )
    assert isinstance(result, dict)
    assert "ocr_results" in result
    # Verify our request_id is in the results
    request_ids = [r["image_id"] for r in result["ocr_results"]]
    assert request_id in request_ids
    # Verify the result has is_handwritten=True
    for ocr_result in result["ocr_results"]:
        if ocr_result["image_id"] == request_id:
            assert ocr_result["result"]["is_handwritten"] is True


def test_query_ocr_results_response_structure(client: MathpixClient):
    """Test OCR results response structure when results exist."""
    image = client.image_new(file_path=TEST_IMAGE_PATH)
    request_id = image.request_id
    result = wait_for_ocr_result(lambda: client.query_ocr_results(request_id=request_id))
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) == 1
    ocr_result = result["ocr_results"][0]
    assert "timestamp" in ocr_result
    assert "image_id" in ocr_result
    assert ocr_result["image_id"] == request_id
