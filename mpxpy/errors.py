from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import requests


class MathpixClientError(Exception):
    """Base exception class for Mathpix client errors."""
    pass

class AuthenticationError(MathpixClientError):
    """Errors related to authentication"""
    def __init__(self, message):
        super().__init__(message)

class ValidationError(MathpixClientError):
    """Errors related to invalid inputs"""
    def __init__(self, message):
        super().__init__(message)

class FilesystemError(MathpixClientError):
    """Errors related to file system operations"""
    def __init__(self, message):
        super().__init__(message)

class ConversionIncompleteError(MathpixClientError):
    """Exception raised when a conversion is not complete."""
    def __init__(self, message, status_info=None):
        super().__init__(message)

class FilesApiError(MathpixClientError):
    """Errors returned by the Files API error envelope.

    Attributes:
        error_id: Stable machine-readable error code (e.g. 'not_found', 'conflict',
            'data_source_not_found', 'quota_exceeded').
        http_status: The HTTP status code of the failed response.
    """
    def __init__(self, message: str, error_id: Optional[str] = None, http_status: Optional[int] = None) -> None:
        super().__init__(message)
        self.error_id: Optional[str] = error_id
        self.http_status: Optional[int] = http_status


def parse_files_api_error_envelope(response: "requests.Response") -> Optional[Dict[str, Any]]:
    """Parse a Files API error envelope from a response body.

    Returns:
        dict: {'error_id': str, 'message': str} when the body is a JSON object
            carrying a recognizable error code ('error' string or
            'error_info.id'), otherwise None.
    """
    try:
        body: Any = response.json()
    except ValueError:
        return None
    is_json_object: bool = isinstance(body, dict)
    if not is_json_object:
        return None
    error_info: Any = body.get('error_info')
    has_error_info: bool = isinstance(error_info, dict)
    if not has_error_info:
        error_info = {}
    error_id: Any = body.get('error') or error_info.get('id')
    has_error_id: bool = isinstance(error_id, str) and bool(error_id)
    if not has_error_id:
        return None
    message: Any = error_info.get('message') or body.get('message') or error_id
    return {'error_id': error_id, 'message': str(message)}


def error_from_response(response: "requests.Response") -> MathpixClientError:
    """Build the appropriate exception for a non-2xx Files API response.

    Returns a FilesApiError when the body is a recognizable Files API error
    envelope, and a plain MathpixClientError for anything else (HTML error
    pages, empty bodies, non-object JSON).
    """
    envelope: Optional[Dict[str, Any]] = parse_files_api_error_envelope(response)
    if envelope is None:
        return MathpixClientError(f"Files API request failed with HTTP {response.status_code}")
    return FilesApiError(
        envelope['message'],
        error_id=envelope['error_id'],
        http_status=response.status_code,
    )
