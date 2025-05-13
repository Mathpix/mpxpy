import time
from typing import Optional, List
import requests
from pydantic import BaseModel
from urllib.parse import urljoin
from mpxpy.pdf import Pdf
from mpxpy.auth import Auth
from mpxpy.logger import logger

class FilesResponse(BaseModel):
    files: List[Pdf]
    cursor: str
    has_more: bool

    model_config = {
        "arbitrary_types_allowed": True
    }

class FileBatch:
    """Manages a batch of Mathpix PDF processing requests.

    This class handles operations on Mathpix file batches, including checking status,
    retrieving processed files, and waiting for all processing to complete.

    Note:
        File batches are not yet available in the production API.
        This class will be enabled in a future release.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        file_batch_id: The unique identifier for this file batch.
    """
    def __init__(self, auth: Auth , file_batch_id: str = None):
        """Initialize a FileBatch instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            file_batch_id: The unique identifier for the file batch.

        Raises:
            ValueError: If auth is not provided or file_batch_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("FileBatch requires an authenticated client")
            raise ValueError("FileBatch requires an authenticated client")
        self.file_batch_id = file_batch_id or ''
        if not self.file_batch_id:
            logger.error("FileBatch requires a File Batch ID")
            raise ValueError("FileBatch requires a File Batch ID")

    def file_batch_is_processing(self):
        """Check if the file batch is still being processed.

        Returns:
            bool: True if any files in the batch are still processing, False if all
                 files are either completed or have errored out.
        """
        logger.info(f"Checking if file batch {self.file_batch_id} is still processing")
        endpoint = urljoin(self.auth.api_url, f'v3/file-batches/{self.file_batch_id}')
        response = requests.get(endpoint, headers=self.auth.headers)
        response_json = response.json()
        total_files = response_json["total_files"]
        completed_files = response_json["completed_files"]
        error_files = response_json["error_files"]
        still_processing = total_files != completed_files + error_files
        logger.info(f"Batch status: {completed_files}/{total_files} completed, {error_files} errors, still processing: {still_processing}")
        return still_processing

    def file_batch_status(self):
        """Get the current status of the file batch.

        Returns:
            dict: JSON response containing batch status information including counts
                 of total, completed, and error files.
        """
        logger.info(f"Getting status for file batch {self.file_batch_id}")
        endpoint =  urljoin(self.auth.api_url, f'v3/file-batches/{self.file_batch_id}')
        response = requests.get(endpoint, headers=self.auth.headers)
        return response.json()

    def files(self, cursor: Optional[str] = None) -> FilesResponse:
        """Retrieve the files in this batch, with pagination support.

        Args:
            cursor (Optional[str]): Pagination cursor for retrieving subsequent pages.

        Returns:
            FilesResponse: An object containing:
                - files (List[Pdf]): List of PDF objects in the current page.
                - cursor (str): Pagination cursor for the next page.
                - has_more (bool): Whether more pages of results are available.
        """
        logger.info(f"Retrieving files for batch {self.file_batch_id}")
        endpoint =  urljoin(self.auth.api_url, f'v3/file-batches/{self.file_batch_id}/files')
        if cursor:
            endpoint += f"?cursor={cursor}"
        response = requests.get(endpoint, headers=self.auth.headers)
        response_json = response.json()
        files = [Pdf(pdf_id=file) for file in response_json['results']]
        return FilesResponse(
            files=files,
            cursor=response_json['cursor'],
            has_more=response_json['has_more']
        )

    def wait_until_complete(self, timeout: int = 60):
        """Wait for all files in the batch to complete processing.

        Polls the batch status until all files are either completed or have errored out,
        or until the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if all files completed processing (successfully or with errors),
                  False if the timeout was reached before completion.
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("Timeout must be a positive, non-zero integer")
        logger.info(f"Waiting for file batch {self.file_batch_id} to complete (timeout: {timeout}s)")
        attempts = 1
        completed = False
        while attempts < timeout:
            file_batch_status = self.file_batch_status()
            total = file_batch_status["total_files"]
            completed_count = file_batch_status["completed_files"]
            error_count = file_batch_status["error_files"]
            if total == completed_count + error_count:
                completed = True
                logger.info(
                    f"File batch {self.file_batch_id} completed: {completed_count} successful, {error_count} errors, {total} total")
                break
            logger.info(f"File batch processing... Status: {completed_count}/{total} completed, {error_count} errors")
            time.sleep(1)
            attempts += 1
        if not completed:
            logger.warning(f"File batch {self.file_batch_id} did not complete within timeout period ({timeout}s)")
        return completed