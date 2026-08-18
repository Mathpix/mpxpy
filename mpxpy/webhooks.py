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
    constant-time compares it to the header's ``v1`` value, so it must be
    called with the exact bytes Mathpix sent, before any JSON parsing or
    re-serialization changes them.

    A replay window guards against a captured-and-replayed delivery: the
    signature is rejected when the header timestamp is more than
    ``tolerance_seconds`` away from the current time in either direction.

    Args:
        signature_header: The raw ``Mathpix-Signature`` header value.
        body: The exact raw request body, as bytes or a str (encoded UTF-8).
        secret: The webhook signing secret.
        tolerance_seconds: Maximum allowed age of the signature timestamp, in
            seconds (default 300). Deliveries outside this window are rejected.

    Returns:
        bool: True if the signature is valid and within the replay window,
            False for any invalid, malformed, or missing input. Never raises.
    """
    try:
        has_inputs: bool = bool(signature_header) and secret is not None and body is not None
        if not has_inputs:
            return False
        parsed: Dict[str, str] = {}
        for part in signature_header.split(','):
            has_separator: bool = '=' in part
            if not has_separator:
                continue
            key, value = part.split('=', 1)
            parsed[key.strip()] = value.strip()
        timestamp: Optional[str] = parsed.get('t')
        provided_signature: Optional[str] = parsed.get('v1')
        has_required_fields: bool = bool(timestamp) and bool(provided_signature)
        if not has_required_fields:
            return False
        timestamp_seconds: int = int(timestamp)
        is_within_window: bool = abs(time.time() - timestamp_seconds) <= tolerance_seconds
        if not is_within_window:
            return False
        body_bytes: bytes = body.encode('utf-8') if isinstance(body, str) else body
        message: bytes = f"{timestamp}.".encode('utf-8') + body_bytes
        expected_signature: str = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_signature, provided_signature)
    except Exception:
        return False


class WebhookConfig:
    """The account-default webhook configuration for the Files API.

    Returned by ``MathpixClient.webhook_config_get`` and
    ``MathpixClient.webhook_config_set``. Wraps the webhook-config response with
    read-only properties: the signing secret used to verify delivery signatures
    and the account-default callback target applied to submissions that do not
    override it per-request.

    Attributes:
        signing_secret: The secret used to sign and verify webhook deliveries.
        callback_url: The account-default callback URL, or None.
        callback_headers: Account-default callback headers, or None.
        callback_events: Account-default subscribed event names, or None.
    """
    def __init__(self, response: Dict[str, Any]) -> None:
        """Initialize a WebhookConfig from a webhook-config response dict.

        Args:
            response: The JSON body from GET/PUT /files/v1/webhook-config. Its
                keys are the wire names default_callback_url/headers/events;
                they are exposed here under the bare callback_* names.
        """
        self._signing_secret: Optional[str] = response.get('signing_secret')
        self._callback_url: Optional[str] = response.get('default_callback_url')
        self._callback_headers: Optional[Dict[str, str]] = response.get('default_callback_headers')
        self._callback_events: Optional[List[str]] = response.get('default_callback_events')

    @property
    def signing_secret(self) -> Optional[str]:
        """The secret used to sign and verify webhook deliveries."""
        return self._signing_secret

    @property
    def callback_url(self) -> Optional[str]:
        """The account-default callback URL, or None."""
        return self._callback_url

    @property
    def callback_headers(self) -> Optional[Dict[str, str]]:
        """The account-default callback headers, or None."""
        return self._callback_headers

    @property
    def callback_events(self) -> Optional[List[str]]:
        """The account-default subscribed event names, or None."""
        return self._callback_events

    def to_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dict, omitting unset fields."""
        fields: Dict[str, Any] = {
            'signing_secret': self._signing_secret,
            'callback_url': self._callback_url,
            'callback_headers': self._callback_headers,
            'callback_events': self._callback_events,
        }
        return {key: value for key, value in fields.items() if value is not None}
