import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Any
import pytest
from mpxpy.mathpix_client import MathpixClient

TEST_IMAGE_PATH = "tests/files/images/cases_hw.png"


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


def test_query_ocr_results_combined_filters(client: MathpixClient):
    """Test OCR results query with date range and request_id filters."""
    image = client.image_new(file_path=TEST_IMAGE_PATH)
    request_id = image.request_id
    wait_for_ocr_result(lambda: client.query_ocr_results(request_id=request_id))
    to_date = datetime.now(timezone.utc) + timedelta(minutes=5)
    from_date = to_date - timedelta(days=1)
    result = client.query_ocr_results(
        from_date=from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        to_date=to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        request_id=request_id,
        page=1,
        per_page=10,
    )
    assert isinstance(result, dict)
    assert "ocr_results" in result
    assert len(result["ocr_results"]) == 1
    assert result["ocr_results"][0]["image_id"] == request_id


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
