import time
from typing import Dict, Any, Optional
from urllib.parse import urljoin
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.errors import ValidationError
from mpxpy.request_handler import get

class Batch:
    """Manages batch image processing through the /v3/batch endpoint.

    This class handles operations on batch image requests, including checking status,
    retrieving results, and waiting for processing to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        batch_id: The unique identifier for this batch.
    """
    def __init__(
            self,
            auth: Auth,
            batch_id: Optional[str] = None,
            request_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a Batch instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            batch_id: The unique identifier for the batch.
            request_options: Optional dict of kwargs to pass to requests.

        Raises:
            ValidationError: If auth is not provided or batch_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("Batch requires an authenticated client")
            raise ValidationError("Batch requires an authenticated client")
        self.batch_id = batch_id or ''
        if not self.batch_id:
            logger.error("Batch requires a batch ID")
            raise ValidationError("Batch requires a batch ID")
        self.request_options = request_options or {}

    def status(self) -> Dict[str, Any]:
        """Get the current status and results of the batch.

        Returns:
            dict: JSON response containing:
                - keys: List of all URL keys from the original batch request
                - callback: The callback configuration (if provided)
                - results: Dict mapping url_key -> OCR result (populated progressively)
        """
        logger.debug(f"Getting status for batch {self.batch_id}")
        endpoint = urljoin(self.auth.api_url, f'v3/batch/{self.batch_id}')
        response = get(endpoint, headers=self.auth.headers, **self.request_options)
        return response.json()

    def wait_until_complete(self, timeout: int = 60) -> bool:
        """Wait for all items in the batch to complete processing.

        Polls the batch status until all items are complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if all items completed successfully, False if timed out.

        Raises:
            ValidationError: If timeout is an invalid value.
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        logger.debug(f"Waiting for batch {self.batch_id} to complete (timeout: {timeout}s)")
        attempt = 1
        while attempt < timeout:
            logger.debug(f'Checking batch status... ({attempt}/{timeout})')
            batch_status = self.status()
            keys = batch_status.get('keys', [])
            results = batch_status.get('results', {})
            if keys and len(results) == len(keys):
                logger.debug(f"Batch {self.batch_id} completed: {len(results)}/{len(keys)} items")
                return True
            logger.debug(f"Batch {self.batch_id} in progress: {len(results)}/{len(keys)} items")
            time.sleep(1)
            attempt += 1
        logger.warning(f"Batch {self.batch_id} did not complete within timeout period ({timeout}s)")
        return False

    def results(self) -> Dict[str, Any]:
        """Get the results dict from the batch.

        Returns:
            dict: Mapping of url_key -> OCR result for each processed item.
        """
        status = self.status()
        return status.get('results', {})

    def keys(self) -> list:
        """Get the list of URL keys in this batch.

        Returns:
            list: URL keys from the original batch request.
        """
        status = self.status()
        return status.get('keys', [])
