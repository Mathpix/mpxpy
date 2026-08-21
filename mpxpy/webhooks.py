import hmac
import hashlib
import time
from typing import Optional, Dict, Any, List, Union


def verify_signature(
        signature_header: str,
        body: Union[bytes, str],
        secret: str,
        tolerance_seconds: int = 300,
) -> bool:
    """Verify a Mathpix webhook signature.

    Mathpix signs each webhook delivery with the header
    ``Mathpix-Signature: t=<unix_seconds>,v1=<hex>`` where ``<hex>`` is the
    lowercase hex HMAC-SHA256 of the string ``"{t}.{raw_body}"`` (the
    unix-seconds timestamp, a literal dot, then the exact raw request body),
    keyed by the UTF-8 bytes of your webhook signing secret. Fetch the secret
    with ``MathpixClient.webhook_config_get().signing_secret``.

    This function recomputes that HMAC over the raw request body and
    constant-time compares it to the header's ``v1`` value(s), so it must be
    called with the exact bytes Mathpix sent, before any JSON parsing or
    re-serialization changes them. A delivery header carries a single ``v1``
    value today; this function also accepts a header bearing more than one
    ``v1`` and passes if any one matches, so it keeps working if signature
    rotation is added later.

    A replay window guards against a captured-and-replayed delivery: the
    signature is rejected when the header timestamp is more than
    ``tolerance_seconds`` away from the current time in either direction.

    Args:
        signature_header: The raw ``Mathpix-Signature`` header value.
        body: The exact raw request body, as bytes or a str (encoded UTF-8).
        secret: Your webhook signing secret. An empty or otherwise falsy
            secret fails closed (returns False) rather than keying the HMAC
            with it.
        tolerance_seconds: Maximum allowed age of the signature timestamp, in
            seconds (default 300). Deliveries outside this window are rejected.

    Returns:
        bool: True if the signature is valid and within the replay window,
            False for any invalid, malformed, or missing input. Never raises.
    """
    try:
        has_inputs: bool = bool(signature_header) and bool(secret) and body is not None
        if not has_inputs:
            return False
        timestamp: Optional[str] = None
        provided_signatures: List[str] = []
        for part in signature_header.split(','):
            has_separator: bool = '=' in part
            if not has_separator:
                continue
            key, value = part.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key == 't':
                timestamp = value
            elif key == 'v1':
                provided_signatures.append(value)
        has_v1: bool = len(provided_signatures) > 0
        if timestamp is None or not has_v1:
            return False
        timestamp_seconds: int = int(timestamp)
        is_within_window: bool = abs(time.time() - timestamp_seconds) <= tolerance_seconds
        if not is_within_window:
            return False
        body_bytes: bytes = body.encode('utf-8') if isinstance(body, str) else body
        message: bytes = f"{timestamp}.".encode('utf-8') + body_bytes
        expected_signature: str = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected_signature, provided) for provided in provided_signatures)
    except Exception:
        return False


class WebhookConfig:
    """The webhook configuration for the Files API.

    Returned by ``MathpixClient.webhook_config_get``. Wraps the webhook-config
    response, exposing the signing secret used to verify webhook delivery
    signatures (see ``mpxpy.webhooks.verify_signature``). The signing secret is
    the whole stored configuration: where a delivery goes, what headers it
    carries, and which events fire are per-submission callback arguments.

    Attributes:
        signing_secret: The secret used to sign and verify webhook deliveries.
    """
    def __init__(self, response: Dict[str, Any]) -> None:
        """Initialize a WebhookConfig from a webhook-config response dict.

        Args:
            response: The JSON body from GET /files/v1/webhook-config.
        """
        self._signing_secret: Optional[str] = response.get('signing_secret')

    @property
    def signing_secret(self) -> Optional[str]:
        """The secret used to sign and verify webhook deliveries."""
        return self._signing_secret
