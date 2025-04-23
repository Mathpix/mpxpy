import os
import time
import requests
from typing import Optional
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.errors import ConversionIncompleteError


class Conversion:
    """Manages a Mathpix conversion through the v3/converter endpoint.

    This class handles operations on Mathpix conversions, including checking status,
    downloading results in different formats, and waiting for conversion to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        conversion_id: The unique identifier for this conversion.
    """
    def __init__(self, auth: Auth , conversion_id: str = None):
        """Initialize a Conversion instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            conversion_id: The unique identifier for the conversion.

        Raises:
            ValueError: If auth is not provided or conversion_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("Conversion requires an authenticated client")
            raise ValueError("Conversion requires an authenticated client")
        self.conversion_id = conversion_id or ''
        if not self.conversion_id:
            logger.error("Conversion requires a Conversion ID")
            raise ValueError("Conversion requires a Conversion ID")

    def wait_until_complete(self, timeout: int=60):
        """Wait for the conversion to complete.

        Polls the conversion status until it's complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if the conversion completed successfully, False if it timed out.
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("Timeout must be a positive, non-zero integer")
        logger.info(f"Waiting for conversion {self.conversion_id} to complete (timeout: {timeout}s)")
        attempt = 1
        completed = False
        while attempt < timeout and not completed:
            logger.info(f'Checking conversion status... ({attempt}/{timeout})')
            conversion_status = self.conversion_status()
            if (conversion_status['status'] == 'completed' and all(
                    format_data['status'] == 'completed'
                    for _, format_data in conversion_status['conversion_status'].items()
            )):
                completed = True
                logger.info(f"Conversion {self.conversion_id} completed successfully")
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
        response = requests.get(endpoint, headers=self.auth.headers)
        return response.json()

    def download_output(self, format: Optional[str]=None):
        """Download the conversion result.

        Args:
            format: Optional output format extension (e.g., 'docx', 'pdf', 'tex').
                   If not provided, returns the default conversion result.

        Returns:
            bytes: The binary content of the conversion result.
        """
        logger.info(f"Downloading output for conversion {self.conversion_id} in format: {format}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter', self.conversion_id)
        if format:
            endpoint = endpoint + '.' + format
        response = requests.get(endpoint, headers=self.auth.headers)
        return response.content

    def download_output_to_local_path(self, format: Optional[str] = None, path: Optional[str] = None):
        """Download the conversion result and save it to a local file.

        Args:
            format: Output format extension (e.g., 'docx', 'pdf', 'tex').
            path: Directory path where the file should be saved. Will be created if it doesn't exist.

        Returns:
            str: The path to the saved file.
        """
        logger.info(f"Downloading conversion {self.conversion_id} in format {format} to path {path}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter', self.conversion_id)
        if format:
            endpoint = endpoint + '.' + format
        response = requests.get(endpoint, headers=self.auth.headers)
        os.makedirs(path, exist_ok=True)
        file_path = f"{path}/{self.conversion_id}.{format}"
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"File saved successfully to {file_path}")
        return file_path