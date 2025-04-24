import os
import time
from typing import Optional, Dict
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.request_handler import get
from mpxpy.errors import FilesystemError, ValidationError, ConversionIncompleteError


class Conversion:
    """Manages a Mathpix conversion through the v3/converter endpoint.

    This class handles operations on Mathpix conversions, including checking status,
    downloading results in different formats, and waiting for conversion to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        conversion_id: The unique identifier for this conversion.
        conversion_formats: Dictionary specifying output formats and their options.
    """
    def __init__(self, auth: Auth , conversion_id: str = None, conversion_formats: Dict[str, bool] = None):
        """Initialize a Conversion instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            conversion_id: The unique identifier for the conversion.

        Raises:
            ValidationError: If auth is not provided or conversion_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("Conversion requires an authenticated client")
            raise ValidationError("Conversion requires an authenticated client")
        self.conversion_id = conversion_id or ''
        if not self.conversion_id:
            logger.error("Conversion requires a Conversion ID")
            raise ValidationError("Conversion requires a Conversion ID")
        self.conversion_formats = conversion_formats

    def wait_until_complete(self, timeout: int=60):
        """Wait for the conversion to complete.

        Polls the conversion status until it's complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if the conversion completed successfully, False if it timed out.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        logger.info(f"Waiting for conversion {self.conversion_id} to complete (timeout: {timeout}s)")
        attempt = 1
        completed = False
        while attempt < timeout and not completed:
            logger.info(f'Checking conversion status... ({attempt}/{timeout})')
            conversion_status = self.conversion_status()
            if (conversion_status['status'] == 'completed' and all(
                    format_data['status'] == 'completed' or format_data['status'] == 'error'
                    for _, format_data in conversion_status['conversion_status'].items()
            )):
                completed = True
                logger.info(f"Conversion {self.conversion_id} completed successfully")
                break
            elif conversion_status['status'] == 'error':
                break
            time.sleep(1)
            attempt += 1
        if not completed:
            logger.warning(f"Conversion {self.conversion_id} did not complete within timeout period ({timeout}s)")
        return completed

    def conversion_status(self):
        """Get the current status of the conversion.

        Returns:
            dict: JSON response containing conversion status information.
        """
        logger.info(f"Getting status for conversion {self.conversion_id}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter', self.conversion_id)
        response = get(endpoint, headers=self.auth.headers)
        return response.json()

    def download_output(self, conversion_format: Optional[str]="pdf"):
        """Download the conversion result.

        Args:
            conversion_format: Optional output format extension (e.g., 'docx', 'pdf', 'tex').
                   If not provided, returns the default conversion result.

        Returns:
            bytes: The binary content of the conversion result.

        Raises:
            ConversionIncompleteError: If the specified format's conversion is not complete.
        """
        logger.info(f"Downloading output for conversion {self.conversion_id} in format: {conversion_format}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter', f'{self.conversion_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        try:
            data = response.json()
        except ValueError:
            return response.content
        if 'conversion_status' in data and conversion_format in data['conversion_status']:
            status = data['conversion_status'][conversion_format].get('status')
            if status != 'completed':
                raise ConversionIncompleteError(
                    f"Conversion to {conversion_format} is not complete (status: {status})"
                )
        return response.content

    def download_output_to_local_path(self, conversion_format: Optional[str] = "pdf", path: Optional[str] = ""):
        """Download the conversion result and save it to a local file.

        Args:
            conversion_format: Output format extension (e.g., 'docx', 'pdf', 'latex.pdf').
            path: Directory path where the file should be saved. Will be created if it doesn't exist.

        Returns:
            str: The path to the saved file.

        Raises:
            ConversionIncompleteError: If the conversion is not complete
            FilesystemError: If output fails to save to the local path
        """
        logger.info(f"Downloading conversion {self.conversion_id} in format {conversion_format} to path {path}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter', f'{self.conversion_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        if path != "":
            os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f'{self.conversion_id}.{conversion_format}')
        try:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception:
            raise FilesystemError('Failed to save file to system')
        logger.info(f"File saved successfully to {file_path}")
        return file_path