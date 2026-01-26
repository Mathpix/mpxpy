import os
import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.batch import Batch
from mpxpy.errors import ValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


# Public test image URLs
TEST_IMAGE_URLS = {
    "algebra": "https://mathpix-ocr-examples.s3.amazonaws.com/algebra.jpg",
    "quadratic": "https://mathpix-ocr-examples.s3.amazonaws.com/quadratic.jpg",
}


def test_batch_create(client: MathpixClient):
    """Test creating a batch request."""
    batch = client.batch_new(urls=TEST_IMAGE_URLS)
    assert isinstance(batch, Batch)
    assert batch.batch_id is not None
    # batch_id can be an int or string
    assert batch.batch_id


def test_batch_wait_and_results(client: MathpixClient):
    """Test waiting for batch completion and retrieving results."""
    batch = client.batch_new(urls=TEST_IMAGE_URLS)
    assert batch.batch_id is not None
    completed = batch.wait_until_complete(timeout=60)
    assert completed, "Batch did not complete within timeout"
    results = batch.results()
    assert isinstance(results, dict)
    # Should have results for both images
    assert "algebra" in results
    assert "quadratic" in results
    # Each result should have LaTeX (since ocr_behavior defaults to "latex")
    for key, result in results.items():
        assert "latex" in result or "error" in result, f"No latex or error in result for {key}"


def test_batch_keys(client: MathpixClient):
    """Test retrieving batch keys."""
    batch = client.batch_new(urls=TEST_IMAGE_URLS)
    batch.wait_until_complete(timeout=60)
    keys = batch.keys()
    assert isinstance(keys, list)
    assert "algebra" in keys
    assert "quadratic" in keys


def test_batch_status(client: MathpixClient):
    """Test getting batch status."""
    batch = client.batch_new(urls=TEST_IMAGE_URLS)
    batch.wait_until_complete(timeout=60)
    status = batch.status()
    assert isinstance(status, dict)
    assert "keys" in status
    assert "results" in status


def test_batch_text_mode(client: MathpixClient):
    """Test batch with text mode."""
    batch = client.batch_new(
        urls=TEST_IMAGE_URLS,
        ocr_behavior="text"
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    # In text mode, should have text output
    for key, result in results.items():
        assert "text" in result or "error" in result, f"No text or error in result for {key}"


def test_batch_with_formats(client: MathpixClient):
    """Test batch with specific formats requested."""
    batch = client.batch_new(
        urls={"algebra": TEST_IMAGE_URLS["algebra"]},
        formats=["latex_simplified", "text"]
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "algebra" in results


def test_batch_single_image(client: MathpixClient):
    """Test batch with a single image."""
    batch = client.batch_new(urls={"single": TEST_IMAGE_URLS["algebra"]})
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "single" in results


def test_batch_validation_empty_urls():
    """Test validation with empty urls dict."""
    client = MathpixClient()
    with pytest.raises(ValidationError, match="must not be empty"):
        client.batch_new(urls={})


def test_batch_validation_timeout():
    """Test validation with invalid timeout."""
    client = MathpixClient()
    batch = client.batch_new(urls=TEST_IMAGE_URLS)
    with pytest.raises(ValidationError, match="positive"):
        batch.wait_until_complete(timeout=0)
    with pytest.raises(ValidationError, match="positive"):
        batch.wait_until_complete(timeout=-1)


def test_batch_with_per_item_options(client: MathpixClient):
    """Test batch with per-item options (url as object)."""
    urls = {
        "custom": {
            "url": TEST_IMAGE_URLS["algebra"],
            "formats": ["latex_simplified"]
        }
    }
    batch = client.batch_new(urls=urls)
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "custom" in results


def test_batch_with_metadata(client: MathpixClient):
    """Test batch with metadata."""
    batch = client.batch_new(
        urls={"algebra": TEST_IMAGE_URLS["algebra"]},
        metadata={"source": "test", "user_id": "123"}
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "algebra" in results


def test_batch_with_confidence_threshold(client: MathpixClient):
    """Test batch with confidence threshold."""
    batch = client.batch_new(
        urls={"algebra": TEST_IMAGE_URLS["algebra"]},
        confidence_threshold=0.5,
        confidence_rate_threshold=0.3
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "algebra" in results


def test_batch_with_include_detected_alphabets(client: MathpixClient):
    """Test batch with include_detected_alphabets option."""
    batch = client.batch_new(
        urls={"algebra": TEST_IMAGE_URLS["algebra"]},
        include_detected_alphabets=True
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "algebra" in results
    # Result should include detected_alphabets when requested
    result = results["algebra"]
    if "error" not in result:
        assert "detected_alphabets" in result


def test_batch_with_alphabets_allowed(client: MathpixClient):
    """Test batch with alphabets_allowed option."""
    batch = client.batch_new(
        urls={"algebra": TEST_IMAGE_URLS["algebra"]},
        alphabets_allowed={"en": True, "zh": False}
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "algebra" in results


def test_batch_text_mode_with_data_options(client: MathpixClient):
    """Test batch in text mode with data_options."""
    batch = client.batch_new(
        urls={"algebra": TEST_IMAGE_URLS["algebra"]},
        ocr_behavior="text",
        data_options={
            "include_latex": True,
            "include_mathml": True
        }
    )
    completed = batch.wait_until_complete(timeout=60)
    assert completed
    results = batch.results()
    assert "algebra" in results
