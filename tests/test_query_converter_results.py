import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Any
import pytest
from mpxpy.mathpix_client import MathpixClient

TESTS_DIR = Path(__file__).parent


@pytest.fixture
def client():
    return MathpixClient()


def wait_for_conversion_id_in_results(
    query_fn: Callable[[], dict[str, Any]],
    conversion_id: str,
    timeout: int = 30
) -> dict[str, Any]:
    """Poll until conversion_id appears in query results."""
    start = time.time()
    while time.time() - start < timeout:
        result = query_fn()
        if result.get("documents"):
            for doc in result["documents"]:
                if doc.get("id") == conversion_id:
                    return result
        time.sleep(1)
    return query_fn()


def test_query_converter_results_basic(client: MathpixClient):
    """Test basic converter results query."""
    result = client.query_converter_results()
    assert isinstance(result, dict)
    assert "documents" in result
    assert isinstance(result["documents"], list)


def test_query_converter_results_with_date_range(client: MathpixClient):
    """Test converter results query with date range."""
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=30)
    result = client.query_converter_results(
        from_date=from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        to_date=to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    assert isinstance(result, dict)
    assert "documents" in result


def test_query_converter_results_pagination(client: MathpixClient):
    """Test converter results query pagination."""
    result = client.query_converter_results(page=1, per_page=5)
    assert isinstance(result, dict)
    assert "documents" in result


def test_query_converter_results_filter_by_conversion_id(client: MathpixClient):
    """Test converter results query after creating a conversion."""
    mmd_content = "# Test Document\n\nThis is a test for $E=mc^2$."
    conversion = client.conversion_new(mmd=mmd_content, convert_to_docx=True)
    conversion_id = conversion.conversion_id
    assert conversion.wait_until_complete(timeout=60)
    # Poll until our conversion appears in results
    result = wait_for_conversion_id_in_results(
        lambda: client.query_converter_results(),
        conversion_id,
        timeout=30
    )
    assert isinstance(result, dict)
    assert "documents" in result
    assert len(result["documents"]) >= 1
    # Verify our conversion_id is in the results
    conversion_ids = [d["id"] for d in result["documents"]]
    assert conversion_id in conversion_ids


def test_query_converter_results_response_structure(client: MathpixClient):
    """Test converter results response structure when results exist."""
    mmd_content = "# Structure Test\n\nTesting response structure."
    conversion = client.conversion_new(mmd=mmd_content, convert_to_docx=True)
    conversion_id = conversion.conversion_id
    assert conversion.wait_until_complete(timeout=60)
    # Poll until our conversion appears in results
    result = wait_for_conversion_id_in_results(
        lambda: client.query_converter_results(),
        conversion_id,
        timeout=30
    )
    assert isinstance(result, dict)
    assert "documents" in result
    assert len(result["documents"]) >= 1
    # Find our conversion and verify structure
    doc = next(d for d in result["documents"] if d["id"] == conversion_id)
    assert "id" in doc
    assert "status" in doc
    assert "created_at" in doc
    assert "modified_at" in doc
    assert doc["id"] == conversion_id
