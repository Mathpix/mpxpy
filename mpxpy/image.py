import json
from pathlib import Path
import os
import requests
from typing import Optional, Dict, List, Any, Tuple
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
        file_url: URL of a remote image, if using a remote file.
    """
    def __init__(
            self,
            auth: Auth,
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
        """Initialize an Image instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            file_path: Path to a local image file.
            file_url: URL of a remote image.

        Raises:
            AuthenticationError: If auth is not provided
            ValidationError: If neither file_path nor file_url is provided,
                        or if both file_path and file_url are provided.
        """
        self.auth = auth
        if not self.auth:
            logger.error("Image requires an authenticated client")
            raise AuthenticationError("Image requires an authenticated client")
        self.file_path = file_path or ''
        self.file_url = file_url or ''
        if not self.file_path and not self.file_url:
            logger.error("Image requires a file path or file URL")
            raise ValidationError("Image requires a file path or file URL")
        if self.file_path and self.file_url:
            logger.error("Exactly one of file path or file URL must be provider")
            raise ValidationError("Exactly one of file path or file URL must be provider")
        self.callback = callback
        self.formats = formats
        self.data_options = data_options
        self.include_detected_alphabets = include_detected_alphabets
        self.alphabets_allowed = alphabets_allowed
        self.region = region
        self.enable_blue_hsv_filter = enable_blue_hsv_filter
        self.confidence_threshold = confidence_threshold
        self.confidence_rate_threshold = confidence_rate_threshold
        self.include_equation_tags = include_equation_tags
        self.include_line_data = include_line_data
        self.include_word_data = include_word_data
        self.include_smiles = include_smiles
        self.include_inchi = include_inchi
        self.include_geometry_data = include_geometry_data
        self.include_diagram_text = include_diagram_text
        self.auto_rotate_confidence_threshold = auto_rotate_confidence_threshold
        self.rm_spaces = rm_spaces
        self.rm_fonts = rm_fonts
        self.idiomatic_eqn_arrays = idiomatic_eqn_arrays
        self.idiomatic_braces = idiomatic_braces
        self.numbers_default_to_math = numbers_default_to_math
        self.math_fonts_default_to_math = math_fonts_default_to_math
        self.math_inline_delimiters = math_inline_delimiters
        self.math_display_delimiters = math_display_delimiters
        self.enable_spell_check = enable_spell_check
        self.enable_tables_fallback = enable_tables_fallback
        self.fullwidth_punctuation = fullwidth_punctuation

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
        logger.info(f"Processing image: path={self.file_path}, url={self.file_url}")
        endpoint = os.path.join(self.auth.api_url, 'v3/text')
        options = {
            "include_line_data": self.include_line_data
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
            options["src"] = self.file_url
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
        return result['line_data']

    def mmd(self):
        """Get the Mathpix Markdown (MMD) representation of the image.

        Returns:
            str: The recognized text in Mathpix Markdown format, with proper math formatting.
        """
        logger.info("Getting Mathpix Markdown (MMD) representation")
        result = self.results()
        return result['text']