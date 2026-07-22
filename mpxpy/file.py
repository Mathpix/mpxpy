import os
import time
import json
from typing import Optional, Dict, Any
from urllib.parse import urljoin
import requests
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.request_handler import get, delete
from mpxpy.errors import FilesystemError, ValidationError, ConversionIncompleteError, MathpixClientError, FilesApiError


class File:
    """Manages a document submitted to the Files API (files/v1).

    This class handles operations on Files API files, including checking status,
    downloading results in different formats, waiting for processing to complete,
    and deleting the file from Mathpix storage.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        file_id: The unique identifier for this file.
    """
    def __init__(
            self,
            auth: Auth,
            file_id: Optional[str] = None,
            request_options: Optional[Dict[str, Any]] = None,
            status_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a File instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            file_id: The unique identifier for the file.
            request_options: Optional dict of kwargs to pass to requests.
            status_result: Optional file-status response body to seed the
                lazy attributes with, avoiding an extra status request.

        Raises:
            ValidationError: If auth is not provided or file_id is empty.
        """
        self.auth: Auth = auth
        has_auth: bool = self.auth is not None
        if not has_auth:
            logger.error("File requires an authenticated client")
            raise ValidationError("File requires an authenticated client")
        self.file_id: str = file_id or ''
        has_file_id: bool = bool(self.file_id)
        if not has_file_id:
            logger.error("File requires a File ID")
            raise ValidationError("File requires a File ID")
        self.request_options: Dict[str, Any] = request_options or {}
        self._last_status: Optional[Dict[str, Any]] = status_result

    def _status_field(self, field: str) -> Any:
        """Return a field from the most recent status response, fetching one if needed."""
        has_cached_status: bool = self._last_status is not None
        if not has_cached_status:
            self.status()
        return (self._last_status or {}).get(field)

    @property
    def custom_id(self) -> Optional[str]:
        """The customer-supplied identifier echoed by the API, or None."""
        return self._status_field('custom_id')

    @property
    def filename(self) -> Optional[str]:
        """The display name supplied at submit, or the API default."""
        return self._status_field('filename')

    @property
    def num_pages(self) -> Optional[int]:
        """Total pages detected in the document (0 until the page split runs)."""
        return self._status_field('num_pages')

    @property
    def percent_done(self) -> Optional[float]:
        """Processing progress from 0.0 to 100.0."""
        return self._status_field('percent_done')

    @property
    def destination_uri(self) -> Optional[str]:
        """The result destination supplied at submit, or None."""
        return self._status_field('destination_uri')

    @property
    def destination_basename(self) -> Optional[str]:
        """The output basename supplied at submit, or None."""
        return self._status_field('destination_basename')

    @property
    def error(self) -> Optional[str]:
        """Machine-readable error code when status is 'error', else None."""
        return self._status_field('error')

    @property
    def error_info(self) -> Optional[Dict[str, Any]]:
        """The error id/message pair when status is 'error', else None."""
        return self._status_field('error_info')

    def wait_until_complete(self, timeout: int = 60) -> bool:
        """Wait for the file processing to complete.

        Polls the file status until it's complete or the timeout is reached.
        On failure the error details remain available via the `error` and
        `error_info` attributes.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if processing completed successfully, False if it errored or timed out.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        is_valid_timeout: bool = isinstance(timeout, int) and timeout > 0
        if not is_valid_timeout:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        logger.debug(f"Waiting for file {self.file_id} to complete (timeout: {timeout}s)")
        attempt: int = 1
        while attempt < timeout:
            logger.debug(f'Checking file status... ({attempt}/{timeout})')
            file_status: Dict[str, Any] = self.status()
            is_completed: bool = file_status.get('status') == 'completed'
            has_errored: bool = file_status.get('status') == 'error'
            if is_completed:
                logger.debug(f"File {self.file_id} completed successfully")
                return True
            elif has_errored:
                logger.error(f"File {self.file_id} processing failed")
                return False
            time.sleep(1)
            attempt += 1
        logger.warning(f"File {self.file_id} did not complete within timeout period ({timeout}s)")
        return False

    def wait_for_format(self, format: str, timeout: int = 60) -> bool:
        """Wait for a specific format conversion to complete.

        Polls the file status until the format is complete or the timeout is reached.
        Format conversions complete independently of the top-level file status and
        can lag behind it; a requested format that has not started converting yet is
        absent from the status response's `formats` map and is treated the same as
        one that is not yet completed.

        Args:
            format: The format to wait for (e.g., 'md', 'docx', 'latex', 'tex.zip').
                Note: Use 'latex' not 'tex' - the API uses 'latex' for status polling.
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if format conversion completed successfully, False if it timed out or errored.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        is_valid_timeout: bool = isinstance(timeout, int) and timeout > 0
        if not is_valid_timeout:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        is_tex_alias: bool = format == 'tex'
        if is_tex_alias:
            logger.info("wait_for_format: 'tex' converted to 'latex' (API uses 'latex' for status)")
            format = 'latex'
        logger.debug(f"Waiting for file {self.file_id} format '{format}' to complete (timeout: {timeout}s)")
        attempt: int = 1
        while attempt < timeout:
            logger.debug(f'Checking format status... ({attempt}/{timeout})')
            file_status: Dict[str, Any] = self.status()
            format_status: Optional[str] = file_status.get('formats', {}).get(format)
            is_format_completed: bool = format_status == 'completed'
            has_format_errored: bool = format_status == 'error'
            if is_format_completed:
                logger.debug(f"File {self.file_id} format '{format}' completed successfully")
                return True
            elif has_format_errored:
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
                - formats: Dict of per-format conversion statuses
                - filename, custom_id, destination_uri, destination_basename, format_primary
                - error, error_info: present when status is 'error'
        """
        logger.debug(f"Getting status for file {self.file_id}")
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}')
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        result: Dict[str, Any] = response.json()
        self._last_status = result
        return result

    def delete(self) -> Dict[str, Any]:
        """Permanently remove the file and its results from Mathpix-owned storage.

        Only files in a terminal state (completed or error) can be deleted; a file
        still being processed returns a conflict. Deleting is idempotent: repeating
        the call on an already-deleted file returns the same success body. Results
        delivered to a customer-owned bucket via destination_uri are not affected.

        Returns:
            dict: Response containing 'file_id' and 'status': 'deleted'.

        Raises:
            FilesApiError: If the file does not exist ('not_found'), belongs to a
                different group ('forbidden'), or is still processing ('conflict').
        """
        logger.debug(f"Deleting file {self.file_id}")
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}')
        response: requests.Response = delete(endpoint, headers=self.auth.headers, **self.request_options)
        has_failed: bool = not response.ok
        if has_failed:
            raise FilesApiError.from_response(response)
        return response.json()

    def _check_download_response(self, response: requests.Response) -> None:
        """Raise the appropriate error for a failed result download.

        Per the Files API, a format that is still converting returns 404 with an
        error body of 'format_not_ready'; a plain 'not_found' 404 means the file id
        does not exist; 415 'unsupported_format' means the extension was never
        requested. A 409 is also treated as format-not-ready for compatibility with
        older deployments.
        """
        is_success: bool = response.ok
        if is_success:
            return
        error_id: Optional[str] = None
        try:
            body: Dict[str, Any] = response.json()
            error_id = body.get('error') or (body.get('error_info') or {}).get('id')
        except ValueError:
            pass
        is_unsupported_format: bool = response.status_code == 415 or error_id == 'unsupported_format'
        if is_unsupported_format:
            raise ValidationError(f"Format was not requested or is not supported: {error_id or response.status_code}")
        is_format_not_ready: bool = response.status_code == 409 or error_id == 'format_not_ready'
        if is_format_not_ready:
            raise ConversionIncompleteError("Format not ready yet")
        is_missing_file: bool = error_id == 'not_found'
        if is_missing_file:
            raise MathpixClientError(f"File not found: {self.file_id}")
        is_unparsed_not_found: bool = response.status_code == 404
        if is_unparsed_not_found:
            raise ConversionIncompleteError("File not found")
        raise FilesApiError.from_response(response)

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
        is_directory_path: bool = path.endswith('/') or path.endswith('\\')
        if is_directory_path:
            filename: str = f"{self.file_id}.{conversion_format}"
            path = os.path.join(path, filename)
        logger.debug(f"Downloading output for file {self.file_id} in format {conversion_format} to path {path}")
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        self._check_download_response(response)
        try:
            directory: str = os.path.dirname(path)
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
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        self._check_download_response(response)
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
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        self._check_download_response(response)
        return response.content

    def json_result(self, conversion_format: str) -> Any:
        """Helper method to download the processed file result as JSON.

        Args:
            conversion_format: Output format extension (e.g., lines.json)

        Returns:
            dict: The result as a dictionary

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.debug(f"Downloading output for file {self.file_id} in format: {conversion_format}")
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/{self.file_id}.{conversion_format}')
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        self._check_download_response(response)
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
    def to_lines_json(self) -> Any:
        """Get the processed file result as lines.json."""
        return self.json_result(conversion_format='lines.json')

    def to_lines_mmd_json(self) -> Any:
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
