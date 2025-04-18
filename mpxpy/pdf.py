import os
import time
import requests
from typing import Optional
from mpxpy.auth import Auth
from mpxpy.logger import logger

class Pdf:
    """Manages a Mathpix PDF conversion through the v3/pdf endpoint.

    This class handles operations on Mathpix PDFs, including checking status,
    downloading results in different formats, and waiting for processing to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        pdf_id: The unique identifier for this PDF.
    """
    def __init__(self, auth: Auth, pdf_id: str = None):
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
            raise ValueError("PDF requires an authenticated client")
        self.pdf_id = pdf_id or ''
        if not self.pdf_id:
            logger.error("PDF requires a PDF ID")
            raise ValueError("PDF requires a PDF ID")

    def wait_until_complete(self, timeout: int=None, ignore_conversions: bool=False):
        """Wait for the PDF processing and optional conversions to complete.

        Polls the PDF status until it's complete, then optionally checks conversion status
        until all conversions are complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Each second makes one status check.
            ignore_conversions: If True, only waits for PDF processing and ignores conversion status.

        Returns:
            bool: True if the processing (and conversions, if not ignored) completed successfully,
                  False if it timed out.
        """
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
                else:
                    ignore_conversions = True
                logger.info(f"PDF {self.pdf_id} processing in progress, waiting...")
            except Exception as e:
                logger.error(f"Exception during PDF status check: {e}")
            attempt += 1
            time.sleep(1)
        if pdf_completed and not ignore_conversions:
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
        result = pdf_completed and (conversion_completed or ignore_conversions)
        logger.info(f"Wait completed for PDF {self.pdf_id}, result: {result}")
        return result

    def pdf_status(self):
        """Get the current status of the PDF processing.

        Returns:
            dict: JSON response containing PDF processing status information.
        """
        logger.info(f"Getting status for PDF {self.pdf_id}")
        endpoint = self.auth.api_url + '/v3/pdf/' + self.pdf_id
        response = requests.get(endpoint, headers=self.auth.headers)
        return response.json()

    def pdf_conversion_status(self):
        """Get the current status of the PDF conversions.

        Returns:
            dict: JSON response containing conversion status information.
        """
        logger.info(f"Getting conversion status for PDF {self.pdf_id}")
        endpoint = self.auth.api_url + '/v3/converter/' + self.pdf_id
        response = requests.get(endpoint, headers=self.auth.headers)
        return response.json()

    def download_output(self, format: Optional[str]=None):
        """Download the processed PDF result.

        Args:
            format: Optional output format extension (e.g., 'docx', 'md', 'tex').
                   If not provided, returns the default PDF result.

        Returns:
            bytes: The binary content of the result.
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format: {format}")
        endpoint = self.auth.api_url + '/v3/pdf/' + self.pdf_id
        if format:
            endpoint = endpoint + '.' + format
        response = requests.get(endpoint, headers=self.auth.headers)
        return response.content

    def download_output_to_local_path(self, format: Optional[str] = None, path: Optional[str] = None):
        """Download the processed PDF (or optional conversion) result and save it to a local path.

        Args:
            format: Output format extension (e.g., 'docx', 'md', 'tex').
            path: Directory path where the file should be saved. Will be created if it doesn't exist.

        Returns:
            str: The path to the saved file.
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format {format} to path {path}")
        endpoint = self.auth.api_url + '/v3/pdf/' + self.pdf_id
        if format:
            endpoint = endpoint + '.' + format
        response = requests.get(endpoint, headers=self.auth.headers)
        os.makedirs(path, exist_ok=True)
        file_path = f"{path}/{self.pdf_id}.{format}"
        print(file_path)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"File saved successfully to {file_path}")
        return file_path