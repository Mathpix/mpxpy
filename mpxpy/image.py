import json
from pathlib import Path
import requests
from typing import Optional
from urllib.parse import urljoin
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.errors import AuthenticationError, ValidationError
from mpxpy.request_handler import post


class Image:
    """Handles image conversion requests to v3/text.

    This class processes images using the Mathpix API to extract structured content.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        file_path: Path to a local image file, if using a local file.
        url: URL of a remote image, if using a remote file.
        improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true
    """
    def __init__(self, auth: Auth, file_path: Optional[str] = None, url: Optional[str] = None, improve_mathpix: bool = True):
        """Initialize an Image instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            file_path: Path to a local image file.
            url: URL of a remote image.
            improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true

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
        self.improve_mathpix = improve_mathpix

    def results(
            self,
            include_line_data: Optional[bool] = False,
    ):
        """Process the image and get OCR results.

        Sends the image to v3/text for OCR processing and returns the full result.

        Args:
            include_line_data: If True, includes detailed line-by-line OCR data in the result.

        Returns:
            dict: JSON response containing recognition results, including extracted text and metadata.

        Raises:
            FileNotFoundError: If the file_path does not point to an existing file.
            ValueError: If the API request fails.
        """
        logger.info(f"Processing image: path={self.file_path}, url={self.url}, include_line_data={include_line_data}")
        endpoint = urljoin(self.auth.api_url, 'v3/text')
        options = {
            "include_line_data": include_line_data,
            "metadata":{
                "improve_mathpix": self.improve_mathpix
            }
        }
        data = {
            "options_json": json.dumps(options)
        }
        if self.file_path:
            path = Path(self.file_path)
            if not path.is_file():
                logger.error(f"File not found: {self.file_path}")
                raise FileNotFoundError(f"File path not found: {self.file_path}")
            with path.open("rb") as pdf_file:
                files = {"file": pdf_file}
                try:
                    response = post(endpoint, data=data, files=files, headers=self.auth.headers)
                    response.raise_for_status()
                    logger.info("OCR processing successful")
                    return response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Mathpix image request failed: {e}")
                    raise ValueError(f"Mathpix image request failed: {e}")
        else:
            options["src"] = self.url
            try:
                response = post(endpoint, json=options, headers=self.auth.headers)
                response.raise_for_status()
                logger.info("OCR processing successful")
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Mathpix image request failed: {e}")
                raise ValueError(f"Mathpix image request failed: {e}")

    def lines_json(self):
        """Get line-by-line OCR data for the image.

        Returns:
            list: Detailed information about each detected line of text.
        """
        logger.info("Getting line-by-line OCR data")
        result = self.results(include_line_data=True)
        if 'line_data' in result:
            return result['line_data']
        return result

    def mmd(self):
        """Get the Mathpix Markdown (MMD) representation of the image.

        Returns:
            str: The recognized text in Mathpix Markdown format, with proper math formatting.
        """
        logger.info("Getting Mathpix Markdown (MMD) representation")
        result = self.results()
        if 'text' in result:
            return result['text']
        return result
