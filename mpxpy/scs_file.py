import os
import sys
import time
import json
from typing import Optional, Dict, Any
from urllib.parse import urljoin
if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.request_handler import get
from mpxpy.errors import FilesystemError, ValidationError, ConversionIncompleteError


@deprecated("ScsFile is deprecated; use mpxpy.file.File instead")
class ScsFile:
    """Manages a file through the legacy files-api v1 endpoints.

    Deprecated: use mpxpy.file.File instead, which targets the public Files API
    and raises FilesApiError with the API's error codes. ScsFile is kept with
    its original behavior for compatibility during the deprecation window.

    This class handles operations on Mathpix files, including checking status,
    downloading results in different formats, and waiting for processing to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        file_id: The unique identifier for this file.
    """
    def __init__(
            self,
            auth: Auth,
            file_id: Optional[str] = None,
            request_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a File instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            file_id: The unique identifier for the file.
            request_options: Optional dict of kwargs to pass to requests.

        Raises:
            ValidationError: If auth is not provided or file_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("File requires an authenticated client")
            raise ValidationError("File requires an authenticated client")
        self.file_id = file_id or ''
        if not self.file_id:
            logger.error("File requires a File ID")
            raise ValidationError("File requires a File ID")
        self.request_options = request_options or {}

    def wait_until_complete(self, timeout: int = 60) -> bool:
        """Wait for the file processing to complete.

        Polls the file status until it's complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if processing completed successfully, False if it timed out.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        logger.debug(f"Waiting for file {self.file_id} to complete (timeout: {timeout}s)")
        attempt = 1
        while attempt < timeout:
            logger.debug(f'Checking file status... ({attempt}/{timeout})')
            file_status = self.status()
            if file_status.get('status') == 'completed':
                logger.debug(f"File {self.file_id} completed successfully")
                return True
            elif file_status.get('status') == 'error':
                logger.error(f"File {self.file_id} processing failed")
                return False
            time.sleep(1)
            attempt += 1
        logger.warning(f"File {self.file_id} did not complete within timeout period ({timeout}s)")
        return False

    def wait_for_format(self, format: str, timeout: int = 60) -> bool:
        """Wait for a specific format conversion to complete.

        Polls the file status until the format is complete or the timeout is reached.

        Args:
            format: The format to wait for (e.g., 'md', 'docx', 'latex', 'tex.zip').
                Note: Use 'latex' not 'tex' - the API uses 'latex' for status polling.
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if format conversion completed successfully, False if it timed out or errored.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        if format == 'tex':
            logger.info("wait_for_format: 'tex' converted to 'latex' (API uses 'latex' for status)")
            format = 'latex'
        logger.debug(f"Waiting for file {self.file_id} format '{format}' to complete (timeout: {timeout}s)")
        attempt = 1
        while attempt < timeout:
            logger.debug(f'Checking format status... ({attempt}/{timeout})')
            file_status = self.status()
            format_status = file_status.get('formats', {}).get(format)
            if format_status == 'completed':
                logger.debug(f"File {self.file_id} format '{format}' completed successfully")
                return True
            elif format_status == 'error':
                logger.error(f"File {self.file_id} format '{format}' failed")
                return False
            time.sleep(1)
            attempt += 1
        logger.warning(f"File {self.file_id} format '{format}' did not complete within timeout period ({timeout}s)")
        return False

    def status(self) -> Dict[str, Any]:
        """Get the current status of the file processing.

        Returns:
            dict: JSON response containing file status information including:
                - file_id: The file identifier
                - status: pending|split|completed|error
                - num_pages: Total number of pages
                - num_pages_completed: Pages processed so far
                - percent_done: Processing progress percentage
                - formats: Dict of format statuses
        """
        logger.debug(f"Getting status for file {self.file_id}")
        endpoint = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}')
        response = get(endpoint, headers=self.auth.headers, **self.request_options)
        return response.json()

    def save_file(self, path: str, conversion_format: str) -> str:
        """Helper function to save the processed file result to a local path.

        Args:
            path: The local file path where the output will be saved
            conversion_format: The format in which the output will be saved

        Returns:
            output_path: The path of the saved file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if path.endswith('/') or path.endswith('\\'):
            filename = f"{self.file_id}.{conversion_format}"
            path = os.path.join(path, filename)
        logger.debug(f"Downloading output for file {self.file_id} in format {conversion_format} to path {path}")
        endpoint = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers, **self.request_options)
        if response.status_code == 404:
            raise ConversionIncompleteError("File not found")
        if response.status_code == 409:
            raise ConversionIncompleteError("Format not ready yet")
        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception:
            raise FilesystemError('Failed to save file to system')
        logger.debug(f"File saved successfully to {path}")
        return path

    def text_result(self, conversion_format: str) -> str:
        """Helper method to download the processed file result as text.

        Args:
            conversion_format: Output format extension

        Returns:
            text: The result as a string (mmd, md, txt)

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.debug(f"Downloading output for file {self.file_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers, **self.request_options)
        if response.status_code == 404:
            raise ConversionIncompleteError("File not found")
        if response.status_code == 409:
            raise ConversionIncompleteError("Format not ready yet")
        return response.text

    def bytes_result(self, conversion_format: str) -> bytes:
        """Helper method to download the processed file result bytes.

        Args:
            conversion_format: Output format extension

        Returns:
            bytes: The binary content of the result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.debug(f"Downloading output for file {self.file_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers, **self.request_options)
        if response.status_code == 404:
            raise ConversionIncompleteError("File not found")
        if response.status_code == 409:
            raise ConversionIncompleteError("Format not ready yet")
        return response.content

    def json_result(self, conversion_format: str):
        """Helper method to download the processed file result as JSON.

        Args:
            conversion_format: Output format extension (e.g., lines.json)

        Returns:
            dict: The result as a dictionary

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.debug(f"Downloading output for file {self.file_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers, **self.request_options)
        if response.status_code == 404:
            raise ConversionIncompleteError("File not found")
        if response.status_code == 409:
            raise ConversionIncompleteError("Format not ready yet")
        return json.loads(response.text)

    # Text format methods
    def to_mmd_text(self) -> str:
        """Get the processed file result as Mathpix Markdown string."""
        return self.text_result(conversion_format='mmd')

    def to_md_text(self) -> str:
        """Get the processed file result as Markdown string."""
        return self.text_result(conversion_format='md')

    def to_tex_text(self) -> str:
        """Get the processed file result as LaTeX string."""
        return self.text_result(conversion_format='tex')

    # Binary format methods
    def to_docx_bytes(self) -> bytes:
        """Get the processed file result as DOCX bytes."""
        return self.bytes_result(conversion_format='docx')

    def to_xlsx_bytes(self) -> bytes:
        """Get the processed file result as XLSX bytes."""
        return self.bytes_result(conversion_format='xlsx')

    def to_pptx_bytes(self) -> bytes:
        """Get the processed file result as PPTX bytes."""
        return self.bytes_result(conversion_format='pptx')

    def to_pdf_bytes(self) -> bytes:
        """Get the processed file result as PDF bytes."""
        return self.bytes_result(conversion_format='pdf')

    def to_latex_pdf_bytes(self) -> bytes:
        """Get the processed file result as LaTeX-rendered PDF bytes."""
        return self.bytes_result(conversion_format='latex.pdf')

    def to_html_bytes(self) -> bytes:
        """Get the processed file result as HTML bytes."""
        return self.bytes_result(conversion_format='html')

    def to_tex_zip_bytes(self) -> bytes:
        """Get the processed file result as tex.zip bytes."""
        return self.bytes_result(conversion_format='tex.zip')

    def to_md_zip_bytes(self) -> bytes:
        """Get the processed file result as md.zip bytes."""
        return self.bytes_result(conversion_format='md.zip')

    def to_mmd_zip_bytes(self) -> bytes:
        """Get the processed file result as mmd.zip bytes."""
        return self.bytes_result(conversion_format='mmd.zip')

    def to_html_zip_bytes(self) -> bytes:
        """Get the processed file result as html.zip bytes."""
        return self.bytes_result(conversion_format='html.zip')

    def to_jpg_bytes(self) -> bytes:
        """Get the processed file result as JPG bytes."""
        return self.bytes_result(conversion_format='jpg')

    def to_png_bytes(self) -> bytes:
        """Get the processed file result as PNG bytes."""
        return self.bytes_result(conversion_format='png')

    # JSON format methods
    def to_lines_json(self):
        """Get the processed file result as lines.json."""
        return self.json_result(conversion_format='lines.json')

    def to_lines_mmd_json(self):
        """Get the processed file result as lines.mmd.json."""
        return self.json_result(conversion_format='lines.mmd.json')

    # File save methods
    def to_mmd_file(self, path: str) -> str:
        """Save the processed file result to a MMD file at a local path."""
        return self.save_file(path=path, conversion_format='mmd')

    def to_md_file(self, path: str) -> str:
        """Save the processed file result to a Markdown file at a local path."""
        return self.save_file(path=path, conversion_format='md')

    def to_docx_file(self, path: str) -> str:
        """Save the processed file result to a DOCX file at a local path."""
        return self.save_file(path=path, conversion_format='docx')

    def to_xlsx_file(self, path: str) -> str:
        """Save the processed file result to an XLSX file at a local path."""
        return self.save_file(path=path, conversion_format='xlsx')

    def to_pptx_file(self, path: str) -> str:
        """Save the processed file result to a PPTX file at a local path."""
        return self.save_file(path=path, conversion_format='pptx')

    def to_pdf_file(self, path: str) -> str:
        """Save the processed file result to a PDF file at a local path."""
        return self.save_file(path=path, conversion_format='pdf')

    def to_html_file(self, path: str) -> str:
        """Save the processed file result to an HTML file at a local path."""
        return self.save_file(path=path, conversion_format='html')

    def to_tex_zip_file(self, path: str) -> str:
        """Save the processed file result to a tex.zip file at a local path."""
        return self.save_file(path=path, conversion_format='tex.zip')
