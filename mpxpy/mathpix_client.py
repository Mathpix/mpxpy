import json
import os

import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

from mpxpy.pdf import Pdf
from mpxpy.image import Image
from mpxpy.file_batch import FileBatch
from mpxpy.conversion import Conversion
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.errors import MathpixClientError, ValidationError
from mpxpy.request_handler import post


class MathpixClient:
    """Client for interacting with the Mathpix API.

    This class provides methods to create and manage various Mathpix resources
    such as image processing, PDF conversions, and batch operations.

    Attributes:
        auth: An Auth instance managing API credentials and endpoints.
    """
    def __init__(self, app_id: str = None, app_key: str = None, api_url: str = None):
        """Initialize a new Mathpix client.

        Args:
            app_id: Optional Mathpix application ID. If None, will use environment variable.
            app_key: Optional Mathpix application key. If None, will use environment variable.
            api_url: Optional Mathpix API URL. If None, will use environment variable
                or default to the production API.
        """
        logger.info("Initializing MathpixClient")
        self.auth = Auth(app_id=app_id, app_key=app_key, api_url=api_url)
        logger.info(f"MathpixClient initialized with API URL: {self.auth.api_url}")

    def image_new(
            self,
            file_path: Optional[str] = None,
            file_url: Optional[str] = None,
    ):
        """Create a new Mathpix Image resource.

        Processes an image either from a local file or remote URL.

        Args:
            file_path: Path to a local image file.
            file_url: URL of a remote image.

        Returns:
            Image: A new Image instance.

        Raises:
            ValueError: If exactly one of file_path and file_url are not provided.
        """
        if (file_path is None and file_url is None) or (file_path is not None and file_url is not None):
            logger.error("Invalid parameters: Exactly one of file_path or file_url must be provided")
            raise ValidationError("Exactly one of file_path or file_url must be provided")
        if file_path:
            logger.info(f"Creating new Image: path={file_path}")
            return Image(auth=self.auth, file_path=file_path)
        else:
            logger.info(f"Creating new Image: url={file_url}")
            return Image(auth=self.auth, file_url=file_url)

    def pdf_new(
            self,
            file_path: Optional[str] = None,
            file_url: Optional[str] = None,
            file_batch_id: Optional[str] = None,
            webhook_url: Optional[str] = None,
            mathpix_webhook_secret: Optional[str] = None,
            webhook_payload: Optional[Dict[str, Any]] = None,
            webhook_enabled_events: Optional[List[str]] = None,
            conversion_formats: Optional[Dict[str, bool]] = None
    ) -> Pdf:
        """Send a file to Mathpix for processing.

        Uploads a PDF from a local file or remote URL and optionally requests conversions.

        Args:
            file_path: Path to a local PDF file.
            file_url: URL of a remote PDF file.
            file_batch_id: Optional batch ID to associate this file with. (Not yet enabled)
            webhook_url: Optional URL to receive webhook notifications. (Not yet enabled)
            mathpix_webhook_secret: Optional secret for webhook authentication. (Not yet enabled)
            webhook_payload: Optional custom payload to include in webhooks. (Not yet enabled)
            webhook_enabled_events: Optional list of events to trigger webhooks. (Not yet enabled)
            conversion_formats: Optional dict of formats to convert to (e.g. {"docx": True}).

        Returns:
            Pdf: A new Pdf instance

        Raises:
            ValueError: If neither file_path nor file_url, or both file_path and file_url are provided.
            FileNotFoundError: If the specified file_path does not exist.
            MathpixClientError: If the API request fails.
            NotImplementedError: If the API URL is set to the production API and webhook or file_batch_id parameters are provided.
        """
        if self.auth.api_url == 'https://api.mathpix.com':
            if any([webhook_url, mathpix_webhook_secret, webhook_payload, webhook_enabled_events]):
                logger.warning("Webhook features not available in production API")
                raise NotImplementedError(
                    "Webhook features are not yet available in the production API. "
                    "These features will be enabled in a future release."
                )

            if file_batch_id:
                logger.warning("File batch features not available in production API")
                raise NotImplementedError(
                    "File batches are not yet available in the production API. "
                    "This feature will be enabled in a future release."
                )
        if (file_path is None and file_url is None) or (file_path is not None and file_url is not None):
            logger.error("Invalid parameters: Exactly one of file_path or file_url must be provided")
            raise ValidationError("Exactly one of file_path or file_url must be provided")
        endpoint = os.path.join(self.auth.api_url, 'v3/pdf')
        options = {
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True
        }
        if file_batch_id:
            options["file_batch_id"] = file_batch_id
        if webhook_url:
            options["webhook_url"] = webhook_url
        if mathpix_webhook_secret:
            options["mathpix_webhook_secret"] = mathpix_webhook_secret
        if webhook_payload:
            options["webhook_payload"] = webhook_payload
        if webhook_enabled_events:
            options["webhook_enabled_events"] = webhook_enabled_events
        if conversion_formats:
            options["conversion_formats"] = conversion_formats
        data = {
            "options_json": json.dumps(options)
        }
        if file_path:
            logger.info(f"Creating new PDF: path={file_path}")
            path = Path(file_path)
            if not path.is_file():
                logger.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"File path not found: {file_path}")
            with path.open("rb") as pdf_file:
                files = {"file": pdf_file}
                try:
                    response = post(endpoint, data=data, files=files, headers=self.auth.headers)
                    response.raise_for_status()
                    response_json = response.json()
                    pdf_id = response_json['pdf_id']
                    logger.info(f"PDF from local path processing started, PDF ID: {pdf_id}")
                    return Pdf(
                        auth=self.auth,
                        pdf_id=pdf_id,
                        file_path=file_path,
                        file_batch_id=file_batch_id,
                        webhook_url=webhook_url,
                        mathpix_webhook_secret=mathpix_webhook_secret,
                        webhook_payload=webhook_payload,
                        webhook_enabled_events=webhook_enabled_events,
                        conversion_formats=conversion_formats
                    )
                except requests.exceptions.RequestException as e:
                    logger.error(f"PDF upload failed: {e}")
                    raise MathpixClientError(f"Mathpix PDF request failed: {e}")
        else:
            logger.info(f"Creating new PDF: url={file_url}")
            options["url"] = file_url
            try:
                response = post(endpoint, json=options, headers=self.auth.headers)
                response.raise_for_status()
                response_json = response.json()
                logger.info(response_json)
                pdf_id = response_json['pdf_id']
                logger.info(f"PDF from URL processing started, PDF ID: {pdf_id}")
                return Pdf(
                        auth=self.auth,
                        pdf_id=pdf_id,
                        file_url=file_url,
                        file_batch_id=file_batch_id,
                        webhook_url=webhook_url,
                        mathpix_webhook_secret=mathpix_webhook_secret,
                        webhook_payload=webhook_payload,
                        webhook_enabled_events=webhook_enabled_events,
                        conversion_formats=conversion_formats
                    )
            except requests.exceptions.RequestException as e:
                logger.error(f"URL processing failed: {e}")
                raise MathpixClientError(f"Mathpix PDF request failed: {e}")

    def file_batch_new(self):
        """Create a new file batch.

        Creates a new batch ID that can be used to group multiple file uploads.

        Note: This feature is not yet available in the production API.

        Returns:
            FileBatch: A new FileBatch instance.

        Raises:
            MathpixClientError: If the API request fails.
            NotImplementedError: If the API URL is set to the production API.
        """
        if self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("File batch feature not available in production API")
            raise NotImplementedError(
                "File batches are not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        logger.info("Creating new file batch")
        endpoint = os.path.join(self.auth.api_url, 'v3/file-batches')
        try:
            response = post(endpoint, headers=self.auth.headers)
            response.raise_for_status()
            response_json = response.json()
            file_batch_id = response_json['file_batch_id']
            logger.info(f"File batch created, ID: {file_batch_id}")
            return FileBatch(auth=self.auth, file_batch_id=file_batch_id)
        except requests.exceptions.RequestException as e:
            logger.error(f"File batch creation failed: {e}")
            raise MathpixClientError(f"Mathpix request failed: {e}")

    def conversion_new(self, mmd: str, conversion_formats: Dict[str, bool]):
        """Create a new conversion from Mathpix Markdown.

        Converts Mathpix Markdown (MMD) to various output formats.

        Args:
            mmd: Mathpix Markdown content to convert.
            conversion_formats: Dictionary specifying output formats and their options.

        Returns:
            Conversion: A new Conversion instance.

        Raises:
            MathpixClientError: If the API request fails.
        """
        logger.info(f"Starting new MMD conversions to: {conversion_formats}")
        endpoint = os.path.join(self.auth.api_url, 'v3/converter')
        options = {
            "mmd": mmd,
            "formats": conversion_formats
        }
        try:
            response = post(endpoint, json=options, headers=self.auth.headers)
            response.raise_for_status()
            response_json = response.json()
            if 'error' in response_json:
                logger.error(f"Conversion failed: {response_json}")
                raise MathpixClientError(f"Conversion failed: {response_json}")
            conversion_id = response_json['conversion_id']
            logger.info(f"Conversion created, ID: {conversion_id}")
            return Conversion(auth=self.auth, conversion_id=conversion_id, conversion_formats=conversion_formats)
        except requests.exceptions.RequestException as e:
            logger.error(f"Conversion request failed: {e}")
            raise MathpixClientError(f"Conversion request failed: {e}")