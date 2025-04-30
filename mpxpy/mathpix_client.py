import json
import os

import requests
from typing import Dict, Any, Optional, List, Tuple
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
            callback: Optional[Dict[str, Any]] = None,
            formats: Optional[List[str]] = None,
            data_options: Optional[Dict[str, Any]] = None,
            include_detected_alphabets: Optional[bool] = None,
            alphabets_allowed: Optional[Dict[str, Any]] = None,
            region: Optional[Dict[str, Any]] = None,
            enable_blue_hsv_filter: Optional[bool] = None,
            confidence_threshold: Optional[float] = None,
            confidence_rate_threshold: Optional[float] = None,
            include_equation_tags: Optional[bool] = None,
            include_line_data: Optional[bool] = None,
            include_word_data: Optional[bool] = None,
            include_smiles: Optional[bool] = None,
            include_inchi: Optional[bool] = None,
            include_geometry_data: Optional[bool] = None,
            include_diagram_text: Optional[bool] = None,
            auto_rotate_confidence_threshold: Optional[float] = None,
            rm_spaces: Optional[bool] = None,
            rm_fonts: Optional[bool] = None,
            idiomatic_eqn_arrays: Optional[bool] = None,
            idiomatic_braces: Optional[bool] = None,
            numbers_default_to_math: Optional[bool] = None,
            math_fonts_default_to_math: Optional[bool] = None,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            enable_spell_check: Optional[bool] = None,
            enable_tables_fallback: Optional[bool] = None,
            fullwidth_punctuation: Optional[bool] = None,
    ):
        """Create a new Mathpix Image resource.

        Processes an image either from a local file or remote URL.

        Args:
            file_path: Path to a local image file.
            file_url: URL of a remote image.
            callback: Optional callback object.
            formats: Optional list of formats, one of `text`, `data`, `html`, `latex_styled`.
            data_options: Optional object to specify outputs for data and html return fields.
            include_detected_alphabets: Optional flag to return detected alphabets.
            alphabets_allowed: Optional object to specify which alphabets to include in the output.
            region: Optional object to specify the image area with the pixel coordinates top_left_x, top_left_y, width, and height.
            enable_blue_hsv_filter: Optional flag to enable a special mode where only blue hue text is processed.
            confidence_threshold: Optional number between 0 and 1 to specify the threshold for triggering confidence errors.
            confidence_rate_threshold: Optional number between 0 and 1 to specify the threshold for triggering confidence errors.
            include_equation_tags: Optional flag to include equation number tags inside equations LaTeX.
            include_line_data: Optional flag to return information segmented line by line.
            include_word_data: Optional flag to return information segmented word by word.
            include_smiles: Optional flag to enable experimental chemistry diagram OCR.
            include_inchi: Optional flag to  include InChI data as XML attributes inside <smiles> elements.
            include_geometry_data: Optional flag to enable data extraction for geometry diagrams.
            include_diagram_text: Optional flag to enable text extractions from diagrams.
            auto_rotate_confidence_threshold: Optional number between 0 and 1 to specify the threshold for auto rotating images to the correct orientation.
            rm_spaces: Optional flag to remove extra white space from equations in latex_styled and text formats.
            rm_fonts: Optional flag to remove font commands from equations in latex_styled and text formats.
            idiomatic_eqn_arrays: Optional flag to specify how to handle a lists of arrays.
            idiomatic_braces: Optional flag to specify whether to remove unnecessary braces for LaTeX output.
            numbers_default_to_math: Optional flag to specify whether numbers are always math.
            math_fonts_default_to_math: Optional flag to specify whether math fonts are always math.
            math_inline_delimiters: Optional tuple of two strings to specify begin and end inline math delimiters.
            math_display_delimiters: Optional tuple of two strings to specify begin and end math display delimiters.
            enable_spell_check: Optional flag to enable a predictive mode for English handwriting.
            enable_tables_fallback: Optional flag to enable an advanced table processing algorithm.
            fullwidth_punctuation: Optional flag to control if punctuation will be fullwidth Unicode or halfwidth Unicode.

        Returns:
            Image: A new Image instance.

        Raises:
            ValueError: If exactly one of file_path and file_url are not provided.
        """
        if (file_path is None and file_url is None) or (file_path is not None and file_url is not None):
            logger.error("Invalid parameters: Exactly one of file_path or file_url must be provided")
            raise ValidationError("Exactly one of file_path or file_url must be provided")
        if len(formats) != 1:
            logger.error("Invalid parameters: formats can only contain one argument")
            raise ValidationError("Formats can only contain one argument")
        if confidence_threshold is not None and (confidence_threshold < 0 or confidence_threshold > 1):
            logger.error("Invalid parameters: confidence_threshold must be between 0 and 1")
            raise ValidationError("confidence_threshold must be between 0 and 1")
        if confidence_rate_threshold is not None and (confidence_rate_threshold < 0 or confidence_rate_threshold > 1):
            logger.error("Invalid parameters: confidence_rate_threshold must be between 0 and 1")
            raise ValidationError("confidence_rate_threshold must be between 0 and 1")
        if auto_rotate_confidence_threshold is not None and (auto_rotate_confidence_threshold < 0 or auto_rotate_confidence_threshold > 1):
            logger.error("Invalid parameters: auto_rotate_confidence_threshold must be between 0 and 1")
            raise ValidationError("auto_rotate_confidence_threshold must be between 0 and 1")
        image_options = {
            callback: callback,
            formats: formats,
            data_options: data_options,
            include_detected_alphabets: include_detected_alphabets,
            alphabets_allowed: alphabets_allowed,
            region: region,
            enable_blue_hsv_filter: enable_blue_hsv_filter,
            confidence_threshold: confidence_threshold,
            confidence_rate_threshold: confidence_rate_threshold,
            include_equation_tags: include_equation_tags,
            include_line_data: include_line_data,
            include_word_data: include_word_data,
            include_smiles: include_smiles,
            include_inchi: include_inchi,
            include_geometry_data: include_geometry_data,
            include_diagram_text: include_diagram_text,
            auto_rotate_confidence_threshold: auto_rotate_confidence_threshold,
            rm_spaces: rm_spaces,
            rm_fonts: rm_fonts,
            idiomatic_eqn_arrays: idiomatic_eqn_arrays,
            idiomatic_braces: idiomatic_braces,
            numbers_default_to_math: numbers_default_to_math,
            math_fonts_default_to_math: math_fonts_default_to_math,
            math_inline_delimiters: math_inline_delimiters,
            math_display_delimiters: math_display_delimiters,
            enable_spell_check: enable_spell_check,
            enable_tables_fallback: enable_tables_fallback,
            fullwidth_punctuation: fullwidth_punctuation,
        }
        if file_path:
            image_options['file_path'] = file_path
            logger.info(f"Creating new Image: url={file_url}")
        else:
            image_options['file_url'] = file_url
            logger.info(f"Creating new Image: url={file_url}")
        return Image(auth=self.auth, **image_options)

    def pdf_new(
            self,
            file_path: Optional[str] = None,
            file_url: Optional[str] = None,
            file_batch_uuid: Optional[str] = None,
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
            file_batch_uuid: Optional batch ID to associate this file with. (Not yet enabled)
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

            if file_batch_uuid:
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
        if file_batch_uuid:
            options["file_batch_uuid"] = file_batch_uuid
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
                        file_batch_uuid=file_batch_uuid,
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
                        file_batch_uuid=file_batch_uuid,
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
            file_batch_uuid = response_json['file_batch_uuid']
            logger.info(f"File batch created, ID: {file_batch_uuid}")
            return FileBatch(auth=self.auth, file_batch_uuid=file_batch_uuid)
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