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
from mpxpy.file_job import FileJob
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


def test_verify_signature_rejects_empty_secret() -> None:
    body = b'payload'
    # A header that IS a valid HMAC keyed with the empty secret must still be
    # rejected: an empty secret fails closed rather than keying the HMAC with it.
    header = _sign(body, secret="")
    assert verify_signature(header, body, "") is False


def test_verify_signature_accepts_any_of_multiple_v1() -> None:
    body = b'{"event":"job.completed"}'
    t = int(time.time())
    message = f"{t}.".encode("utf-8") + body
    good = hmac.new(SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    wrong = hmac.new(b"whsec_other", message, hashlib.sha256).hexdigest()
    # During a secret rotation the header carries a v1 for each secret; a match
    # on any one of them verifies.
    assert verify_signature(f"t={t},v1={wrong},v1={good}", body, SECRET) is True
    assert verify_signature(f"t={t},v1={wrong},v1={wrong}", body, SECRET) is False


# webhook_config_get / set / test

def test_webhook_config_get_returns_config(client: MathpixClient) -> None:
    # The response carries the default_callback_* wire keys; WebhookConfig
    # exposes them under the bare callback_* names.
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
    assert config.callback_url == "https://example.com/hook"
    assert config.callback_headers == {"X-Token": "t"}
    assert config.callback_events == ["job.completed"]
    args, _ = mock_get.call_args
    assert args[0].endswith("/files/v1/webhook-config")


def test_webhook_config_set_preserves_unspecified_fields(client: MathpixClient) -> None:
    # Read-modify-write: setting only callback_url must preserve the existing headers
    # and events (the API's PUT is full-replacement, so the SDK reads then merges).
    # The bare callback_* params map onto the default_callback_* wire keys.
    current = {
        "signing_secret": "whsec_abc",
        "default_callback_url": "https://old.example.com/hook",
        "default_callback_headers": {"Authorization": "Bearer keep"},
        "default_callback_events": ["file.completed"],
    }
    with patch("mpxpy.mathpix_client.get") as mock_get, \
            patch("mpxpy.mathpix_client.put") as mock_put:
        mock_get.return_value = FakeResponse(json_body=current)
        mock_put.return_value = FakeResponse(json_body={**current, "default_callback_url": "https://new.example.com/hook"})
        config = client.webhook_config_set(callback_url="https://new.example.com/hook")
    assert isinstance(config, WebhookConfig)
    assert mock_get.called  # read-modify-write read the current config first
    args, kwargs = mock_put.call_args
    assert args[0].endswith("/files/v1/webhook-config")
    assert kwargs["json"] == {
        "default_callback_url": "https://new.example.com/hook",
        "default_callback_headers": {"Authorization": "Bearer keep"},
        "default_callback_events": ["file.completed"],
    }


def test_webhook_config_set_rejects_empty_events(client: MathpixClient) -> None:
    with pytest.raises(ValidationError):
        client.webhook_config_set(callback_events=[])


def test_webhook_config_test_returns_probe_without_raising(client: MathpixClient) -> None:
    probe = {"status": "failed", "response_code": 500, "detail": "endpoint returned 500"}
    with patch("mpxpy.mathpix_client.post") as mock_post:
        mock_post.return_value = FakeResponse(json_body=probe)
        result = client.webhook_config_test()
    assert result == probe
    args, _ = mock_post.call_args
    assert args[0].endswith("/files/v1/webhook-config/test")


# FileJob.finalize

def test_filejob_finalize_returns_map(client: MathpixClient) -> None:
    finalize_body = {"job_id": "job-1", "finalized_at": "2026-08-18T00:00:00Z", "message": "finalized"}
    job = FileJob(auth=client.auth, job_id="job-1")
    with patch("mpxpy.file_job.post") as mock_post:
        mock_post.return_value = FakeResponse(json_body=finalize_body)
        result = job.finalize()
    assert result == finalize_body
    args, _ = mock_post.call_args
    assert args[0].endswith("/files/v1/jobs/job-1/finalize")


def test_filejob_finalize_unknown_id_raises(client: MathpixClient) -> None:
    job = FileJob(auth=client.auth, job_id="job-missing")
    with patch("mpxpy.file_job.post") as mock_post:
        mock_post.return_value = FakeResponse(status_code=404, json_body={"error": "not_found"})
        with pytest.raises(FilesApiError) as exc_info:
            job.finalize()
    assert exc_info.value.error_id == "not_found"
