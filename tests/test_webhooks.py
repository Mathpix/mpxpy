"""Unit tests for webhook signature verification and the webhook config surface.

The signature tests use only the standard library; the client tests mock the
request layer, so no network access is required.
"""
import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from unittest.mock import patch
import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.webhooks import verify_signature, WebhookConfig
from mpxpy.errors import ValidationError, FilesApiError


SECRET = "whsec_test_secret"


def _sign(body: bytes, secret: str = SECRET, timestamp: Optional[int] = None) -> str:
    """Build a Mathpix-Signature header the same way the server does."""
    t = int(time.time()) if timestamp is None else timestamp
    message = f"{t}.".encode("utf-8") + body
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"t={t},v1={signature}"


class FakeResponse:
    def __init__(self, status_code: int = 200, json_body: Optional[Dict[str, Any]] = None) -> None:
        self.status_code = status_code
        self._json_body = json_body

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self) -> Dict[str, Any]:
        return self._json_body or {}


@pytest.fixture
def client() -> MathpixClient:
    return MathpixClient(app_id="test-app", app_key="test-key")


# verify_signature

def test_verify_signature_valid_bytes_and_str() -> None:
    body = b'{"event":"job.completed","job_id":"job-1"}'
    header = _sign(body)
    assert verify_signature(header, body, SECRET) is True
    # A str body must encode identically to the bytes body
    assert verify_signature(header, body.decode("utf-8"), SECRET) is True


def test_verify_signature_rejects_tampered_body() -> None:
    body = b'{"event":"job.completed"}'
    header = _sign(body)
    assert verify_signature(header, b'{"event":"job.failed"}', SECRET) is False


def test_verify_signature_rejects_wrong_secret() -> None:
    body = b'payload'
    header = _sign(body)
    assert verify_signature(header, body, "whsec_wrong") is False


def test_verify_signature_rejects_stale_timestamp() -> None:
    body = b'payload'
    stale = int(time.time()) - 10_000
    header = _sign(body, timestamp=stale)
    assert verify_signature(header, body, SECRET) is False
    # Widening the tolerance past the age accepts it again
    assert verify_signature(header, body, SECRET, tolerance_seconds=20_000) is True


def test_verify_signature_rejects_malformed_and_missing_fields() -> None:
    body = b'payload'
    assert verify_signature("not-a-signature-header", body, SECRET) is False
    assert verify_signature("", body, SECRET) is False
    # Present timestamp but missing v1
    assert verify_signature(f"t={int(time.time())}", body, SECRET) is False


# webhook_config_get / set / test

def test_webhook_config_get_returns_config(client: MathpixClient) -> None:
    config_body = {
        "signing_secret": "whsec_abc",
        "default_callback_url": "https://example.com/hook",
        "default_callback_headers": {"X-Token": "t"},
        "default_callback_events": ["job.completed"],
    }
    with patch("mpxpy.mathpix_client.get") as mock_get:
        mock_get.return_value = FakeResponse(json_body=config_body)
        config = client.webhook_config_get()
    assert isinstance(config, WebhookConfig)
    assert config.signing_secret == "whsec_abc"
    assert config.default_callback_url == "https://example.com/hook"
    assert config.default_callback_headers == {"X-Token": "t"}
    assert config.default_callback_events == ["job.completed"]
    args, _ = mock_get.call_args
    assert args[0].endswith("/files/v1/webhook-config")


def test_webhook_config_set_sends_only_provided_fields(client: MathpixClient) -> None:
    with patch("mpxpy.mathpix_client.put") as mock_put:
        mock_put.return_value = FakeResponse(json_body={"signing_secret": "whsec_abc"})
        config = client.webhook_config_set(default_callback_url="https://example.com/hook")
    assert isinstance(config, WebhookConfig)
    args, kwargs = mock_put.call_args
    assert args[0].endswith("/files/v1/webhook-config")
    assert kwargs["json"] == {"default_callback_url": "https://example.com/hook"}


def test_webhook_config_set_rejects_empty_events(client: MathpixClient) -> None:
    with pytest.raises(ValidationError):
        client.webhook_config_set(default_callback_events=[])


def test_webhook_config_test_returns_probe_without_raising(client: MathpixClient) -> None:
    probe = {"status": "failed", "response_code": 500, "detail": "endpoint returned 500"}
    with patch("mpxpy.mathpix_client.post") as mock_post:
        mock_post.return_value = FakeResponse(json_body=probe)
        result = client.webhook_config_test()
    assert result == probe
    args, _ = mock_post.call_args
    assert args[0].endswith("/files/v1/webhook-config/test")


# file_job_finalize

def test_file_job_finalize_returns_map(client: MathpixClient) -> None:
    finalize_body = {"job_id": "job-1", "finalized_at": "2026-08-18T00:00:00Z", "message": "finalized"}
    with patch("mpxpy.mathpix_client.post") as mock_post:
        mock_post.return_value = FakeResponse(json_body=finalize_body)
        result = client.file_job_finalize("job-1")
    assert result == finalize_body
    args, _ = mock_post.call_args
    assert args[0].endswith("/files/v1/jobs/job-1/finalize")


def test_file_job_finalize_unknown_id_raises(client: MathpixClient) -> None:
    with patch("mpxpy.mathpix_client.post") as mock_post:
        mock_post.return_value = FakeResponse(status_code=404, json_body={"error": "not_found"})
        with pytest.raises(FilesApiError) as exc_info:
            client.file_job_finalize("job-missing")
    assert exc_info.value.error_id == "not_found"
