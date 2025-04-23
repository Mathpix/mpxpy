class MathpixClientError(Exception):
    """Base exception class for Mathpix client errors."""
    pass


class ConversionIncompleteError(MathpixClientError):
    """Exception raised when a PDF conversion is not complete."""

    def __init__(self, message, status_info=None):
        super().__init__(message)
        self.status_info = status_info or {}