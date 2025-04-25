import os
import time
from typing import Optional, Dict, Any, List
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.errors import ValidationError, ConversionIncompleteError, FilesystemError
from mpxpy.request_handler import get


class Pdf:
    """Manages a Mathpix PDF conversion through the v3/pdf endpoint.

    This class handles operations on Mathpix PDFs, including checking status,
    downloading results in different formats, and waiting for processing to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        pdf_id: The unique identifier for this PDF.
        file_path: Path to a local PDF file.
        file_url: URL of a remote PDF file.
        file_batch_id: Optional batch ID to associate this file with. (Not yet enabled)
        webhook_url: Optional URL to receive webhook notifications. (Not yet enabled)
        mathpix_webhook_secret: Optional secret for webhook authentication. (Not yet enabled)
        webhook_payload: Optional custom payload to include in webhooks. (Not yet enabled)
        webhook_enabled_events: Optional list of events to trigger webhooks. (Not yet enabled)
        conversion_formats: Optional dict of formats to convert to (e.g. {"docx": True}).
    """
    def __init__(
            self,
            auth: Auth,
            pdf_id: str = None,
            file_path: Optional[str] = None,
            file_url: Optional[str] = None,
            file_batch_id: Optional[str] = None,
            webhook_url: Optional[str] = None,
            mathpix_webhook_secret: Optional[str] = None,
            webhook_payload: Optional[Dict[str, Any]] = None,
            webhook_enabled_events: Optional[List[str]] = None,
            conversion_formats: Optional[Dict[str, bool]] = None
    ):
        """Initialize a PDF instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            pdf_id: The unique identifier for the PDF.

        Raises:
            ValueError: If auth is not provided or pdf_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("PDF requires an authenticated client")
            raise ValidationError("PDF requires an authenticated client")
        self.pdf_id = pdf_id or ''
        if not self.pdf_id:
            logger.error("PDF requires a PDF ID")
            raise ValidationError("PDF requires a PDF ID")
        self.file_path = file_path
        self.file_url = file_url
        self.file_batch_id = file_batch_id
        self.webhook_url = webhook_url
        self.mathpix_webhook_secret = mathpix_webhook_secret
        self.webhook_payload = webhook_payload
        self.webhook_enabled_events = webhook_enabled_events
        self.conversion_formats = conversion_formats

    def wait_until_complete(self, timeout: int=60, ignore_conversions: bool=False):
        """Wait for the PDF processing and optional conversions to complete.

        Polls the PDF status until it's complete, then optionally checks conversion status
        until all conversions are complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.
            ignore_conversions: If True, only waits for PDF processing and ignores conversion status.

        Returns:
            bool: True if the processing (and conversions, if not ignored) completed successfully,
                  False if it timed out.
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("Timeout must be a positive, non-zero integer")
        logger.info(f"Waiting for PDF {self.pdf_id} to complete (timeout: {timeout}s, ignore_conversions: {ignore_conversions})")
        attempt = 1
        pdf_completed = False
        conversion_completed = False
        while attempt < timeout and not pdf_completed:
            try:
                status = self.pdf_status()
                logger.info(f"PDF status check attempt {attempt}/{timeout}: {status}")
                if isinstance(status, dict) and 'status' in status and status['status'] == 'completed':
                    pdf_completed = True
                    logger.info(f"PDF {self.pdf_id} processing completed")
                    break
                elif isinstance(status, dict) and 'error' in status:
                    logger.error(f"Error in PDF {self.pdf_id} processing: {status.get('error')}")
                logger.info(f"PDF {self.pdf_id} processing in progress, waiting...")
            except Exception as e:
                logger.error(f"Exception during PDF status check: {e}")
            attempt += 1
            time.sleep(1)
        if pdf_completed and self.conversion_formats and not ignore_conversions:
            logger.info(f"Checking conversion status for PDF {self.pdf_id}")
            while attempt < timeout and not conversion_completed:
                try:
                    conv_status = self.pdf_conversion_status()
                    logger.info(f"Conversion status check attempt {attempt}/{timeout}: {conv_status}")
                    if (isinstance(conv_status, dict) and 
                        'error' in conv_status and 
                        'error_info' in conv_status and 
                        conv_status['error_info'].get('id') == 'cnv_unknown_id'):
                        logger.info("Conversion ID not found yet, trying again...")
                    elif (isinstance(conv_status, dict) and 
                        'status' in conv_status and 
                        conv_status['status'] == 'completed' and
                        'conversion_status' in conv_status and
                        all(format_data['status'] == 'completed'
                            for _, format_data in conv_status['conversion_status'].items())):
                        logger.info(f"All conversions completed for PDF {self.pdf_id}")
                        conversion_completed = True
                        break
                    else:
                        logger.info(f"Conversions for PDF {self.pdf_id} in progress, waiting...")
                except Exception as e:
                    logger.error(f"Exception during conversion status check: {e}")
                attempt += 1
                time.sleep(1)
        result = pdf_completed and (conversion_completed or ignore_conversions or not self.conversion_formats)
        logger.info(f"Wait completed for PDF {self.pdf_id}, result: {result}")
        return result

    def pdf_status(self):
        """Get the current status of the PDF processing.

        Returns:
            dict: JSON response containing PDF processing status information.
        """
        logger.info(f"Getting status for PDF {self.pdf_id}")
        endpoint = os.path.join(self.auth.api_url, 'v3/pdf', self.pdf_id)
        response = get(endpoint, headers=self.auth.headers)
        return response.json()

    def pdf_conversion_status(self):
        """Get the current status of the PDF conversions.

        Returns:
            dict: JSON response containing conversion status information.
        """
        logger.info(f"Getting conversion status for PDF {self.pdf_id}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter', self.pdf_id)
        response = get(endpoint, headers=self.auth.headers)
        return response.json()

    def download_output(self, conversion_format: Optional[str]='pdf'):
        """Download the processed PDF result.

        Args:
            conversion_format: Optional output format extension (e.g., 'docx', 'md', 'tex').
                   If not provided, returns the default PDF result.

        Returns:
            bytes: The binary content of the result.

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format: {conversion_format}")
        endpoint = os.path.join(self.auth.api_url, 'v3/pdf', f'{self.pdf_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        return response.content

    def download_output_to_local_path(self, conversion_format: Optional[str] = 'pdf', path: Optional[str] = ""):
        """Download the processed PDF (or optional conversion) result and save it to a local path.

        Args:
            conversion_format: Output format extension (e.g., 'docx', 'md', 'tex').
            path: Directory path where the file should be saved. Will be created if it doesn't exist.

        Returns:
            str: The path to the saved file.

        Raises:
            ConversionIncompleteError: If the conversion is not complete
            FilesystemError: If output fails to save to the local path
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format {conversion_format} to path {path}")
        endpoint = os.path.join(self.auth.api_url, 'v3/pdf', f'{self.pdf_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        if path != "":
            os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f'{self.pdf_id}.{conversion_format}')
        try:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception:
            raise FilesystemError('Failed to save file to system')
        logger.info(f"File saved successfully to {file_path}")
        return file_path