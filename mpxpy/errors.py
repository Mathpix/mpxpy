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
            'data_source_not_found', 'quota_exceeded'), or None if the response
            body could not be parsed.
        http_status: The HTTP status code of the failed response.
    """
    def __init__(self, message: str, error_id: Optional[str] = None, http_status: Optional[int] = None) -> None:
        super().__init__(message)
        self.error_id: Optional[str] = error_id
        self.http_status: Optional[int] = http_status

    @classmethod
    def from_response(cls, response: "requests.Response") -> "FilesApiError":
        """Build a FilesApiError from a non-2xx Files API response."""
        error_id: Optional[str] = None
        message: str = f"Files API request failed with HTTP {response.status_code}"
        try:
            body: Dict[str, Any] = response.json()
            error_info: Dict[str, Any] = body.get('error_info') or {}
            error_id = body.get('error') or error_info.get('id')
            message = error_info.get('message') or body.get('message') or message
        except ValueError:
            pass
        return cls(message, error_id=error_id, http_status=response.status_code)
