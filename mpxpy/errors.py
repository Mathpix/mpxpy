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
