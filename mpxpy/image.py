import time
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.errors import AuthenticationError, ValidationError, MathpixClientError
from mpxpy.request_handler import get


class Image:
    """Handles image conversion requests to v3/text.

    This class processes images using the Mathpix API to extract structured content.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        request_id: A string storing the request_id of the image
        file_path: Path to a local image file, if using a local file.
        url: URL of a remote image, if using a remote file.
        improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true
        include_line_data: Optional boolean to include line by line OCR data
        metadata: Optional dict to attach metadata to a request
        is_async: Optional boolean to enable non-interactive requests
        result: A Dict to containing a request's result as initially configured
    """
    def __init__(
        self,
        auth: Auth,
        request_id: str,
        result: Dict[str, Any],
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        improve_mathpix: bool = True,
        include_line_data: Optional[bool] = False,
        metadata: Optional[Dict[str, Any]] = None,
        is_async: Optional[bool] = False,
        request_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an Image instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            request_id: A string storing the request_id of the image
            file_path: Path to a local image file.
            url: URL of a remote image.
            improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true
            include_line_data: Optional boolean to include line by line OCR data
            metadata: Optional dict to attach metadata to a request
            is_async: Optional boolean to enable non-interactive requests
            result: A Dict to containing a request's result as initially configured

        Raises:
            AuthenticationError: If auth is not provided
            ValidationError: If neither file_path nor url is provided,
                        or if both file_path and url are provided.
        """
        self.auth = auth
        if not self.auth:
            logger.error("Image requires an authenticated client")
            raise AuthenticationError("Image requires an authenticated client")
        self.file_path = file_path or ''
        self.url = url or ''
        if not self.file_path and not self.url:
            logger.error("Image requires a file path or file URL")
            raise ValidationError("Image requires a file path or file URL")
        if self.file_path and self.url:
            logger.error("Exactly one of file path or file URL must be provider")
            raise ValidationError("Exactly one of file path or file URL must be provider")
        self.request_id = request_id
        self.improve_mathpix = improve_mathpix
        self.include_line_data = include_line_data
        self.metadata = metadata
        self.is_async = is_async
        self.result = result
        self.request_options = request_options or {}

    def results(self):
        """Get OCR results.

        Returns the result, or if it's async, gets the result from ocr-results

        Returns:
            dict: JSON response containing OCR results, including extracted text and metadata.

        Raises:
            ValueError: If the API request fails.
        """
        if not self.is_async or 'text' in self.result or 'html' in self.result or 'latex_styled' in self.result or 'lines' in self.result:
            return self.result
        try:
            endpoint = urljoin(self.auth.api_url, f'v3/ocr-results?request_id={self.request_id}')
            response = get(endpoint, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            response_json = response.json()
            if 'ocr_results' in response_json and len(response_json['ocr_results']) > 0:
                result = response_json['ocr_results'][0]
                self.result = result
                return result
            return {}
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Mathpix async image result request failed: {e}")
        except Exception as e:
            raise MathpixClientError(f"Mathpix async image result request failed: {e}")

    def wait_until_complete(self, timeout=60) -> bool:
        """Wait for async image processing to complete.

        Polls the ocr-results endpoint until it's complete.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if the processing completed successfully, False if it timed out.
        """
        start_time = time.time()
        while time.time() < start_time + timeout:
            result = self.results()
            if 'image_id' in result:
                self.result = result
                return True
            time.sleep(1)
        return False


    def lines_json(self):
        """Get line-by-line OCR data for the image.

        Returns:
            list: Detailed information about each detected line of text.
        """
        if not self.include_line_data:
            raise ValueError('Image must have "include_line_data" set to True to return lines.json output.')
        result = self.result
        if 'line_data' in result:
            return result['line_data']
        elif self.is_async and 'result' in result:
            async_results = result['result']
            if 'line_data' in async_results:
                return async_results['line_data']
        return result

    def mmd(self):
        """Get the Mathpix Markdown (MMD) representation of the image.

        Returns:
            str: The recognized text in Mathpix Markdown format, with proper math formatting.
        """
        result = self.result
        if 'text' in result:
            return result['text']
        elif self.is_async and 'result' in result:
            async_results = result['result']
            if 'text' in async_results:
                return async_results['text']
        return result

    def latex_styled(self):
        """Get the latex_styled representation of the image.

        Returns:
            str: The latex_styled text output.
        """
        result = self.result
        if 'latex_styled' in result:
            return result['latex_styled']
        elif self.is_async and 'result' in result:
            async_results = result['result']
            if 'latex_styled' in async_results:
                return async_results['latex_styled']
        return result

    def html(self):
        """Get the html representation of the image.

        Returns:
            str: The html text output.
        """
        result = self.result
        if 'html' in result:
            return result['html']
        elif self.is_async and 'result' in result:
            async_results = result['result']
            if 'html' in async_results:
                return async_results['html']
        return result
