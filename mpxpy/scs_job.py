import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.request_handler import get
from mpxpy.errors import ValidationError


class ScsJob:
    """Manages an SCS job through the files-api v1 endpoint.

    An SCS job groups multiple files together for batch processing and tracking.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        scs_job_id: The unique identifier for this job.
    """
    def __init__(
            self,
            auth: Auth,
            scs_job_id: Optional[str] = None,
            request_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an ScsJob instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            scs_job_id: The unique identifier for the job.
            request_options: Optional dict of kwargs to pass to requests.

        Raises:
            ValidationError: If auth is not provided or scs_job_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("ScsJob requires an authenticated client")
            raise ValidationError("ScsJob requires an authenticated client")
        self.scs_job_id = scs_job_id or ''
        if not self.scs_job_id:
            logger.error("ScsJob requires a Job ID")
            raise ValidationError("ScsJob requires a Job ID")
        self.request_options = request_options or {}

    def status(self) -> Dict[str, Any]:
        """Get the current status of the SCS job.

        Returns:
            dict: JSON response containing job status information including:
                - scs_job_id: The job identifier
                - group_id: The group this job belongs to
                - app_id: The application ID
                - created_at: Job creation timestamp
                - modified_at: Last modification timestamp
                - num_files_sent: Total files in the job
                - num_files_completed: Files that have finished processing
                - num_pages_sent: Total pages across all files
                - num_pages_completed: Pages that have finished processing
        """
        logger.debug(f"Getting status for SCS job {self.scs_job_id}")
        endpoint = urljoin(self.auth.files_api_url, '/files/v1/scs-jobs/status')
        params = {'scs_job_id': self.scs_job_id}
        response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
        return response.json()

    def wait_until_complete(self, timeout: int = 60) -> bool:
        """Wait for all files in the job to complete processing.

        Polls the job status until all files are complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if all files completed processing, False if it timed out.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        logger.debug(f"Waiting for SCS job {self.scs_job_id} to complete (timeout: {timeout}s)")
        attempt = 1
        while attempt < timeout:
            logger.debug(f'Checking job status... ({attempt}/{timeout})')
            job_status = self.status()
            num_files_sent = job_status.get('num_files_sent', 0)
            num_files_completed = job_status.get('num_files_completed', 0)
            if num_files_sent > 0 and num_files_completed >= num_files_sent:
                logger.debug(f"SCS job {self.scs_job_id} completed: {num_files_completed}/{num_files_sent} files")
                return True
            logger.debug(f"SCS job {self.scs_job_id} in progress: {num_files_completed}/{num_files_sent} files")
            time.sleep(1)
            attempt += 1
        logger.warning(f"SCS job {self.scs_job_id} did not complete within timeout period ({timeout}s)")
        return False
