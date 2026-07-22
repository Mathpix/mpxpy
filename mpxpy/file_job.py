import re
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Iterator, Tuple, Union
from urllib.parse import urljoin, quote
import requests
from mpxpy.auth import Auth
from mpxpy.file import File
from mpxpy.logger import logger
from mpxpy.request_handler import get
from mpxpy.errors import ValidationError, FilesApiError

# Constraint shared by custom_id and Idempotency-Key values.
CUSTOM_ID_PATTERN: "re.Pattern[str]" = re.compile(r'^[A-Za-z0-9_\-.:]{1,256}$')

JOB_FILE_STATUSES: Tuple[str, ...] = ('pending', 'completed', 'error')


@dataclass
class FileSubmission:
    """One document in a batch submission to the Files API jobs endpoint.

    Attributes:
        source_uri: Remote location of the source document. Accepted schemes:
            s3://, gs://, public https://, or an Azure Blob HTTPS URL.
        custom_id: Optional customer-supplied identifier (max 256 chars,
            characters [A-Za-z0-9_-.:], case-sensitive). Requires the job to
            have an explicit job_id; (job_id, custom_id) is the idempotency key.
        filename: Optional display name for the file.
        destination_uri: Optional per-file destination for results. Requires a
            registered data source for the bucket.
        s3_region: Optional region of the destination_uri S3 bucket.
        destination_basename: Optional basename for output objects within
            destination_uri.
        page_ranges: Optional page range string, e.g. "1-5,8".
    """
    source_uri: str
    custom_id: Optional[str] = None
    filename: Optional[str] = None
    destination_uri: Optional[str] = None
    s3_region: Optional[str] = None
    destination_basename: Optional[str] = None
    page_ranges: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return the submission as a dict with unset fields omitted."""
        return {key: value for key, value in asdict(self).items() if value is not None}


class FileJob:
    """Manages a Files API job: a named container of file submissions.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        job_id: The unique identifier for this job.
        file_count: The number of submitted items, when known (set from the
            submission response; not kept up to date afterwards, use status()).
    """
    def __init__(
            self,
            auth: Auth,
            job_id: Optional[str] = None,
            file_count: Optional[int] = None,
            request_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a FileJob instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            job_id: The unique identifier for the job.
            file_count: Optional item count from the submission response.
            request_options: Optional dict of kwargs to pass to requests.

        Raises:
            ValidationError: If auth is not provided or job_id is empty.
        """
        self.auth: Auth = auth
        has_auth: bool = self.auth is not None
        if not has_auth:
            logger.error("FileJob requires an authenticated client")
            raise ValidationError("FileJob requires an authenticated client")
        self.job_id: str = job_id or ''
        has_job_id: bool = bool(self.job_id)
        if not has_job_id:
            logger.error("FileJob requires a Job ID")
            raise ValidationError("FileJob requires a Job ID")
        self.file_count: Optional[int] = file_count
        self.request_options: Dict[str, Any] = request_options or {}

    def status(self) -> Dict[str, Any]:
        """Get the job's status and counters.

        Returns:
            dict: JSON response containing:
                - job_id: The job identifier
                - status: 'processing' while any file is pending, 'completed'
                  when every file has reached a terminal state
                - file_count: Total files accepted into the job
                - files_completed: Files with final results
                - files_errored: Files in terminal error state
                - created_at, modified_at: ISO 8601 timestamps

        Raises:
            FilesApiError: If the request fails (e.g. 'not_found').
        """
        logger.debug(f"Getting status for job {self.job_id}")
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/jobs/{quote(self.job_id, safe="")}')
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        has_failed: bool = not response.ok
        if has_failed:
            raise FilesApiError.from_response(response)
        return response.json()

    def wait_until_complete(self, timeout: int, interval: float = 5.0) -> bool:
        """Wait for the job to complete.

        Polls the job status until it is 'completed' or the timeout is reached.
        Per-file failures do not fail the job; check files_errored on status()
        and list them with files(status='error').

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.
            interval: Seconds between polls (default 5.0). Large jobs can take a
                long time to complete; use a longer interval for them.

        Returns:
            bool: True if the job completed within the timeout, False otherwise.

        Raises:
            ValidationError: If timeout or interval is an invalid value.
        """
        is_valid_timeout: bool = isinstance(timeout, int) and timeout > 0
        if not is_valid_timeout:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        is_valid_interval: bool = interval > 0
        if not is_valid_interval:
            raise ValidationError("Interval must be a positive number")
        logger.debug(f"Waiting for job {self.job_id} to complete (timeout: {timeout}s)")
        deadline: float = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job_status: Dict[str, Any] = self.status()
            is_completed: bool = job_status.get('status') == 'completed'
            if is_completed:
                logger.debug(f"Job {self.job_id} completed")
                return True
            time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
        logger.warning(f"Job {self.job_id} did not complete within timeout period ({timeout}s)")
        return False

    def files(
            self,
            status: Optional[str] = None,
            limit: Optional[int] = None,
            paging_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get one page of the job's file listing.

        Args:
            status: Optional filter, one of 'pending', 'completed', 'error'.
                'pending' covers every file that has not reached a terminal state.
                The per-file 'status' field is populated only when this filter is
                used; it is null in the unfiltered listing.
            limit: Optional maximum items per page.
            paging_state: Opaque pagination cursor from the previous response's
                'next_page_token'.

        Returns:
            dict: Response containing 'files' (each with file_id, filename,
                status, custom_id) and 'next_page_token' (non-null when more
                pages remain).

        Raises:
            ValidationError: If status is not one of the allowed values.
            FilesApiError: If the request fails.
        """
        is_valid_status: bool = status is None or status in JOB_FILE_STATUSES
        if not is_valid_status:
            raise ValidationError(f"status must be one of: {', '.join(JOB_FILE_STATUSES)}")
        logger.debug(f"Listing files for job {self.job_id} (status={status})")
        endpoint: str = urljoin(self.auth.files_api_url, f'/files/v1/jobs/{quote(self.job_id, safe="")}/files')
        params: Dict[str, Any] = {}
        if status is not None:
            params['status'] = status
        if limit is not None:
            params['limit'] = limit
        if paging_state is not None:
            params['paging_state'] = paging_state
        response: requests.Response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
        has_failed: bool = not response.ok
        if has_failed:
            raise FilesApiError.from_response(response)
        return response.json()

    def files_iter(
            self,
            status: Optional[str] = None,
            limit: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over all files in the job, following pagination.

        Args:
            status: Optional filter, one of 'pending', 'completed', 'error'.
            limit: Optional page size for the underlying requests.

        Yields:
            dict: One file entry per iteration (file_id, filename, status, custom_id).
        """
        paging_state: Optional[str] = None
        while True:
            page: Dict[str, Any] = self.files(status=status, limit=limit, paging_state=paging_state)
            for file_entry in page.get('files', []):
                yield file_entry
            paging_state = page.get('next_page_token')
            has_more_pages: bool = bool(paging_state)
            if not has_more_pages:
                return

    def file_by_custom_id(self, custom_id: str) -> File:
        """Fetch a single file by the custom_id supplied at submission.

        Available only when the original submission supplied an explicit job_id
        and a per-item custom_id.

        Args:
            custom_id: The per-item identifier supplied at submission.

        Returns:
            File: A File instance for the matched file, seeded with its status.

        Raises:
            ValidationError: If custom_id is empty.
            FilesApiError: If the (job_id, custom_id) pair is unknown or belongs
                to another account ('not_found'; the two cases are
                indistinguishable by design).
        """
        has_custom_id: bool = bool(custom_id)
        if not has_custom_id:
            raise ValidationError("custom_id is required")
        logger.debug(f"Getting file by custom_id {custom_id} in job {self.job_id}")
        endpoint: str = urljoin(
            self.auth.files_api_url,
            f'/files/v1/jobs/{quote(self.job_id, safe="")}/files/{quote(custom_id, safe="")}'
        )
        response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
        has_failed: bool = not response.ok
        if has_failed:
            raise FilesApiError.from_response(response)
        result: Dict[str, Any] = response.json()
        return File(
            auth=self.auth,
            file_id=result['file_id'],
            request_options=self.request_options,
            status_result=result,
        )


def normalize_file_submission(item: Union[FileSubmission, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and convert one batch item to its request dict.

    Args:
        item: A FileSubmission or a plain dict with the same keys.

    Returns:
        dict: The submission dict with unset fields omitted.

    Raises:
        ValidationError: If the item is not a FileSubmission or dict, or has no source_uri.
    """
    is_submission_instance: bool = isinstance(item, FileSubmission)
    is_dict: bool = isinstance(item, dict)
    if is_submission_instance:
        submission: Dict[str, Any] = item.to_dict()
    elif is_dict:
        submission = {key: value for key, value in item.items() if value is not None}
    else:
        raise ValidationError(f"Each file must be a FileSubmission or dict, got: {type(item).__name__}")
    has_source_uri: bool = bool(submission.get('source_uri'))
    if not has_source_uri:
        raise ValidationError("Each file submission requires a source_uri")
    return submission
