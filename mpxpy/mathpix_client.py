import sys
import json
import requests
from typing import Dict, Any, Optional, List, Set, Tuple, Union
if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated
from pathlib import Path
from urllib.parse import urljoin
from mpxpy.pdf import Pdf
from mpxpy.image import Image
from mpxpy.file import File
from mpxpy.scs_file import ScsFile
from mpxpy.file_batch import FileBatch
from mpxpy.file_job import FileJob, FileSubmission, normalize_file_submission
from mpxpy.data_source import DataSource, PROVIDERS, AUTH_METHODS_BY_PROVIDER
from mpxpy.conversion import Conversion
from mpxpy.batch import Batch
from mpxpy.auth import Auth
from mpxpy.logger import logger, configure_logging
from mpxpy.errors import MathpixClientError, ValidationError, FilesApiError, error_from_response
from mpxpy.request_handler import post, get


def _apply_processing_options(
        options: Dict[str, Any],
        alphabets_allowed: Optional[Dict[str, str]] = None,
        rm_spaces: Optional[bool] = True,
        rm_fonts: Optional[bool] = False,
        idiomatic_eqn_arrays: Optional[bool] = False,
        include_equation_tags: Optional[bool] = False,
        include_smiles: Optional[bool] = True,
        include_chemistry_as_image: Optional[bool] = False,
        include_diagram_text: Optional[bool] = False,
        numbers_default_to_math: Optional[bool] = False,
        math_inline_delimiters: Optional[Tuple[str, str]] = None,
        math_display_delimiters: Optional[Tuple[str, str]] = None,
        page_ranges: Optional[str] = None,
        enable_spell_check: Optional[bool] = False,
        auto_number_sections: Optional[bool] = False,
        remove_section_numbering: Optional[bool] = False,
        preserve_section_numbering: Optional[bool] = True,
        enable_tables_fallback: Optional[bool] = False,
        fullwidth_punctuation: Optional[bool] = None,
) -> None:
    """Apply the OCR/conversion options shared with v3/pdf to a request options dict.

    Only non-default values are added, matching the request shape used across
    the client.
    """
    if alphabets_allowed is not None:
        options["alphabets_allowed"] = alphabets_allowed
    if not rm_spaces:
        options["rm_spaces"] = rm_spaces
    if rm_fonts:
        options["rm_fonts"] = rm_fonts
    if idiomatic_eqn_arrays:
        options["idiomatic_eqn_arrays"] = idiomatic_eqn_arrays
    if include_equation_tags:
        options["include_equation_tags"] = True
    if not include_smiles:
        options["include_smiles"] = include_smiles
    if include_chemistry_as_image:
        options["include_chemistry_as_image"] = True
    if include_diagram_text:
        options["include_diagram_text"] = include_diagram_text
    if numbers_default_to_math:
        options["numbers_default_to_math"] = numbers_default_to_math
    if math_inline_delimiters is not None:
        options["math_inline_delimiters"] = math_inline_delimiters
    if math_display_delimiters is not None:
        options["math_display_delimiters"] = math_display_delimiters
    if page_ranges is not None:
        options["page_ranges"] = page_ranges
    if enable_spell_check:
        options["enable_spell_check"] = enable_spell_check
    if auto_number_sections:
        options["auto_number_sections"] = auto_number_sections
    if remove_section_numbering:
        options["remove_section_numbering"] = remove_section_numbering
    if not preserve_section_numbering:
        options["preserve_section_numbering"] = preserve_section_numbering
    if enable_tables_fallback:
        options["enable_tables_fallback"] = enable_tables_fallback
    if fullwidth_punctuation:
        options["fullwidth_punctuation"] = fullwidth_punctuation


def _reject_reserved_conversion_options(
        conversion_options: Optional[Dict[str, object]],
        reserved: Set[str],
) -> None:
    """Reject conversion_options keys that would override validated request fields.

    The conversion_options pass-through is merged into the request body after the
    explicit arguments, so without this check a caller could silently replace
    fields the method has already validated (e.g. source_uri, files, custom_id).
    """
    has_conversion_options: bool = bool(conversion_options)
    if not has_conversion_options:
        return
    conflicting: Set[str] = reserved.intersection(conversion_options or {})
    has_conflicts: bool = bool(conflicting)
    if has_conflicts:
        raise ValidationError(
            f"conversion_options may not override validated request fields: {', '.join(sorted(conflicting))}"
        )


class MathpixClient:
    """Client for interacting with the Mathpix API.

    This class provides methods to create and manage various Mathpix resources
    such as image processing, PDF conversions, and batch operations.

    Attributes:
        auth: An Auth instance managing API credentials and endpoints.
    """
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        api_url: Optional[str] = None,
        files_api_url: Optional[str] = None,
        improve_mathpix: bool = True,
        request_options: Optional[Dict[str, Any]] = None
    ):
        """Initialize a new Mathpix client.

        Args:
            app_id: Optional Mathpix application ID. If None, will use environment variable.
            app_key: Optional Mathpix application key. If None, will use environment variable.
            api_url: Optional Mathpix API URL. If None, will use environment variable or default to the production API.
            files_api_url: Optional files-api URL for internal testing. If None, defaults to api_url.
            improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true.
            request_options: Optional dict of keyword arguments to pass to the requests library (e.g. {'verify': False} for SSL verification).
        """
        logger.debug("Initializing MathpixClient")
        self.auth = Auth(app_id=app_id, app_key=app_key, api_url=api_url, files_api_url=files_api_url)
        configure_logging()
        self.improve_mathpix = improve_mathpix
        self.request_options = request_options or {}
        logger.debug(f"MathpixClient initialized with API URL: {self.auth.api_url}")

    def image_new(
            self,
            file_path: Optional[str] = None,
            url: Optional[str] = None,
            improve_mathpix: Optional[bool] = True,
            metadata: Optional[Dict[str, Any]] = None,
            tags: Optional[List[str]] = None,
            is_async: Optional[bool] = False,
            callback: Optional[Dict[str, Any]] = None,
            formats: Optional[List[str]] = None,
            data_options: Optional[Dict[str, Any]] = None,
            include_detected_alphabets: Optional[bool] = False,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            region: Optional[Dict[str, float]] = None,
            enable_blue_hsv_filter: Optional[bool] = False,
            confidence_threshold: Optional[float] = None,
            confidence_rate_threshold: Optional[float] = None,
            include_equation_tags: Optional[bool] = False,
            include_line_data: Optional[bool] = False,
            include_word_data: Optional[bool] = False,
            include_smiles: Optional[bool] = False,
            include_inchi: Optional[bool] = False,
            include_geometry_data: Optional[bool] = False,
            include_diagram_text: Optional[bool] = False,
            auto_rotate_confidence_threshold: Optional[float] = None,
            rm_spaces: Optional[bool] = True,
            rm_fonts: Optional[bool] = False,
            idiomatic_eqn_arrays: Optional[bool] = False,
            idiomatic_braces: Optional[bool] = False,
            numbers_default_to_math: Optional[bool] = False,
            math_fonts_default_to_math: Optional[bool] = False,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            enable_spell_check: Optional[bool] = False,
            enable_tables_fallback: Optional[bool] = False,
            fullwidth_punctuation: Optional[bool] = None
    ):
        r"""Process an image either from a local file or remote URL.

        Args:
            file_path: Path to a local image file.
            url: URL of a remote image.
            improve_mathpix: Optional boolean to enable Mathpix to retain user output.
            metadata: Optional dict to attach metadata to a request
            tags: Optional list of strings which can be used to identify results using the /v3/ocr-results endpoint
            is_async: Optional boolean to enable non-interactive requests
            callback: Optional Callback Object (see https://docs.mathpix.com/#callback-object)
            formats: Optional list of formats ('text', 'data', 'html', or 'latex_styled')
            data_options: Optional DataOptions dict (see https://docs.mathpix.com/#dataoptions-object)
            include_detected_alphabets: Optional boolean to return the detected alphabets
            alphabets_allowed: Optional dict to list alphabets allowed in the output (see https://docs.mathpix.com/#alphabetsallowed-object)
            region: Optional dict to specify the image area with pixel coordinates 'top_left_x', 'top_left_y', 'width', 'height'
            enable_blue_hsv_filter: Optional boolean to enable a special mode of image processing where it processes blue hue text exclusively
            confidence_threshold: Optional number between 0 and 1 to specify a threshold for triggering confidence errors (file level threshold)
            confidence_rate_threshold: Optional number between 0 and 1 to specify a threshold for triggering confidence errors, default 0.75 (symbol level threshold)
            include_equation_tags: Optional boolean to specify whether to include equation number tags inside equations LaTeX. When set to True, it sets "idiomatic_eqn_arrays": True because equation numbering works better in those environments compared to the array environment
            include_line_data: Optional boolean to return information segmented line by line
            include_word_data: Optional boolean to return information segmented word by word
            include_smiles: Optional boolean to enable experimental chemistry diagram OCR via RDKIT normalized SMILES
            include_inchi: Optional boolean to include InChI data as XML attributes inside <smiles> elements
            include_geometry_data: Optional boolean to enable data extraction for geometry diagrams (currently only supports triangle diagrams)
            include_diagram_text: Optional boolean to enable text extraction from diagrams (for use with "include_line_data": True). The extracted text will be part of line data, and not part of the "text" or any other output format specified. the "parent_id" of these text lines will correspond to the "id" of one of the diagrams in the line data. Diagrams will also have "children_ids" to store references to those text lines
            auto_rotate_confidence_threshold: Optional number between 0 and 1 to specify threshold for auto rotating images to the correct orientation, default 0.99
            rm_spaces: Optional boolean to determine whether extra white space is removed from equations in "latex_styled" and "text" formats
            rm_fonts: Optional boolean to determine whether font commands such as \mathbf and \mathrm are removed from equations in "latex_styled" and "text" formats
            idiomatic_eqn_arrays: Optional boolean to specify whether to use aligned, gathered, or cases instead of an array environment for a list of equations
            idiomatic_braces: Optional boolean to specify whether to remove unnecessary braces for LaTeX output
            numbers_default_to_math: Optional boolean to specify whether numbers are always math
            math_fonts_default_to_math: Optional boolean to specify whether math fonts are always math
            math_inline_delimiters: Optional [str, str] tuple to specify begin inline math and end inline math delimiters for "text" outputs
            math_display_delimiters: Optional [str, str] tuple to specify begin display math and end display math delimiters for "text" outputs
            enable_spell_check: Optional boolean to enable a predictive mode for English handwriting
            enable_tables_fallback: Optional boolean to enable an advanced table processing algorithm that supports very large and complex tables
            fullwidth_punctuation: Optional boolean to specify whether punctuation will be fullwidth Unicode

        Returns:
            Image: A new Image instance.

        Raises:
            ValueError: If exactly one of file_path and url are not provided.
        """
        if (file_path is None and url is None) or (file_path is not None and url is not None):
            logger.error("Invalid parameters: Exactly one of file_path or url must be provided")
            raise ValidationError("Exactly one of file_path or url must be provided")
        endpoint = urljoin(self.auth.api_url, 'v3/text')
        image_options: Dict[str, Any] = {
            "metadata": {
                "mpxpy": True,
                **(metadata or {})
            }
        }
        if tags is not None:
            image_options["tags"] = tags
        if is_async:
            image_options["async"] = is_async
        if callback is not None:
            image_options["callback"] = callback
        if formats is not None:
            image_options["formats"] = formats
        if data_options is not None:
            image_options["data_options"] = data_options
        if include_detected_alphabets:
            image_options["include_detected_alphabets"] = include_detected_alphabets
        if alphabets_allowed is not None:
            image_options["alphabets_allowed"] = alphabets_allowed
        if region is not None:
            image_options["region"] = region
        if enable_blue_hsv_filter:
            image_options["enable_blue_hsv_filter"] = enable_blue_hsv_filter
        if confidence_threshold is not None:
            image_options["confidence_threshold"] = confidence_threshold
        if confidence_rate_threshold is not None:
            image_options["confidence_rate_threshold"] = confidence_rate_threshold
        if include_equation_tags:
            image_options["include_equation_tags"] = include_equation_tags
        if include_line_data:
            image_options["include_line_data"] = include_line_data
        if include_word_data:
            image_options["include_word_data"] = include_word_data
        if include_smiles:
            image_options["include_smiles"] = include_smiles
        if include_inchi:
            image_options["include_inchi"] = include_inchi
        if include_geometry_data:
            image_options["include_geometry_data"] = include_geometry_data
        if include_diagram_text:
            image_options["include_diagram_text"] = include_diagram_text
        if auto_rotate_confidence_threshold is not None:
            image_options["auto_rotate_confidence_threshold"] = auto_rotate_confidence_threshold
        if not rm_spaces:
            image_options["rm_spaces"] = rm_spaces
        if rm_fonts:
            image_options["rm_fonts"] = rm_fonts
        if idiomatic_eqn_arrays:
            image_options["idiomatic_eqn_arrays"] = idiomatic_eqn_arrays
        if idiomatic_braces:
            image_options["idiomatic_braces"] = idiomatic_braces
        if numbers_default_to_math:
            image_options["numbers_default_to_math"] = numbers_default_to_math
        if math_fonts_default_to_math:
            image_options["math_fonts_default_to_math"] = math_fonts_default_to_math
        if math_inline_delimiters is not None:
            image_options["math_inline_delimiters"] = math_inline_delimiters
        if math_display_delimiters is not None:
            image_options["math_display_delimiters"] = math_display_delimiters
        if enable_spell_check:
            image_options["enable_spell_check"] = enable_spell_check
        if enable_tables_fallback:
            image_options["enable_tables_fallback"] = enable_tables_fallback
        if fullwidth_punctuation:
            image_options["fullwidth_punctuation"] = fullwidth_punctuation
        if not self.improve_mathpix:
            logger.debug('improve_mathpix set to False on the client')
            image_options["metadata"]["improve_mathpix"] = False
        elif not improve_mathpix:
            image_options["metadata"]["improve_mathpix"] = False
        data = {
            "options_json": json.dumps(image_options)
        }
        if file_path:
            path = Path(file_path)
            if not path.is_file():
                logger.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"File path not found: {file_path}")
            with path.open("rb") as image_file:
                files = {"file": image_file}
                result = None
                try:
                    response = post(endpoint, data=data, files=files, headers=self.auth.headers, **self.request_options)
                    response.raise_for_status()
                    result = response.json()
                    request_id = result['request_id']
                    return Image(auth=self.auth, request_id=request_id, file_path=file_path, improve_mathpix=improve_mathpix, include_line_data=include_line_data, metadata=metadata, result=result, is_async=is_async, request_options=self.request_options)
                except requests.exceptions.RequestException as e:
                    raise ValueError(f"Mathpix image request failed: {e}")
                except Exception as e:
                    if result is not None:
                        raise MathpixClientError(f"Mathpix image request failed: {result}")
                    raise MathpixClientError(f"Mathpix image request failed: {e}")
        else:
            image_options["src"] = url
            result = None
            try:
                response = post(endpoint, json=image_options, headers=self.auth.headers, **self.request_options)
                response.raise_for_status()
                result = response.json()
                request_id = result['request_id']
                return Image(auth=self.auth, request_id=request_id, url=url, improve_mathpix=improve_mathpix, include_line_data=include_line_data, metadata=metadata, result=result, is_async=is_async, request_options=self.request_options)
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Mathpix image request failed: {e}")
            except Exception as e:
                if result is not None:
                    raise MathpixClientError(f"Mathpix image request failed: {result}")
                raise MathpixClientError(f"Mathpix image request failed: {e}")

    def pdf_new(
            self,
            file_path: Optional[str] = None,
            url: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            rm_spaces: Optional[bool] = True,
            rm_fonts: Optional[bool] = False,
            idiomatic_eqn_arrays: Optional[bool] = False,
            include_equation_tags: Optional[bool] = False,
            include_smiles: Optional[bool] = True,
            include_chemistry_as_image: Optional[bool] = False,
            include_diagram_text: Optional[bool] = False,
            numbers_default_to_math: Optional[bool] = False,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            page_ranges: Optional[str] = None,
            enable_spell_check: Optional[bool] = False,
            auto_number_sections: Optional[bool] = False,
            remove_section_numbering: Optional[bool] = False,
            preserve_section_numbering: Optional[bool] = True,
            enable_tables_fallback: Optional[bool] = False,
            fullwidth_punctuation: Optional[bool] = None,
            convert_to_docx: Optional[bool] = False,
            convert_to_md: Optional[bool] = False,
            convert_to_mmd: Optional[bool] = False,
            convert_to_tex_zip: Optional[bool] = False,
            convert_to_html: Optional[bool] = False,
            convert_to_pdf: Optional[bool] = False,
            convert_to_md_zip: Optional[bool] = False,
            convert_to_mmd_zip: Optional[bool] = False,
            convert_to_pptx: Optional[bool] = False,
            convert_to_html_zip: Optional[bool] = False,
            improve_mathpix: Optional[bool] = True,
            file_batch_id: Optional[str] = None,
            webhook_url: Optional[str] = None,
            mathpix_webhook_secret: Optional[str] = None,
            webhook_payload: Optional[Dict[str, Any]] = None,
            webhook_enabled_events: Optional[List[str]] = None,
    ) -> Pdf:
        r"""Uploads a PDF, document, or ebook from a local file or remote URL and optionally requests conversions.

        Args:
            file_path: Path to a local PDF file.
            url: URL of a remote PDF file.
            metadata: Optional dict to attach metadata to a request
            alphabets_allowed: Optional dict to list alphabets allowed in the output (see https://docs.mathpix.com/#alphabetsallowed-object)
            rm_spaces: Optional boolean to determine whether extra white space is removed from equations in "latex_styled" and "text" formats
            rm_fonts: Optional boolean to determine whether font commands such as \mathbf and \mathrm are removed from equations in "latex_styled" and "text" formats
            idiomatic_eqn_arrays: Optional boolean to specify whether to use aligned, gathered, or cases instead of an array environment for a list of equations
            include_equation_tags: Optional boolean to specify whether to include equation number tags inside equations LaTeX. When set to True, it sets "idiomatic_eqn_arrays": True because equation numbering works better in those environments compared to the array environment
            include_smiles: Optional boolean to enable experimental chemistry diagram OCR via RDKIT normalized SMILES
            include_chemistry_as_image: Optional boolean to return an image crop containing SMILES in the alt-text for chemical diagrams
            include_diagram_text: Optional boolean to enable text extraction from diagrams (for use with "include_line_data": True). The extracted text will be part of line data, and not part of the "text" or any other output format specified. the "parent_id" of these text lines will correspond to the "id" of one of the diagrams in the line data. Diagrams will also have "children_ids" to store references to those text lines
            numbers_default_to_math: Optional boolean to specify whether numbers are always math
            math_inline_delimiters: Optional [str, str] tuple to specify begin inline math and end inline math delimiters for "text" outputs
            math_display_delimiters: Optional [str, str] tuple to specify begin display math and end display math delimiters for "text" outputs
            page_ranges: Specifies a page range as a comma-separated string. Examples include 2,4-6 which selects pages [2,4,5,6] and 2 - -2 which selects all pages starting with the second page and ending with the next-to-last page
            enable_spell_check: Optional boolean to enable a predictive mode for English handwriting
            auto_number_sections: Optional[bool] = False,
            remove_section_numbering: Specifies whether to remove existing numbering for sections and subsections. Defaults to false
            preserve_section_numbering: Specifies whether to keep existing section numbering as is. Defaults to true
            enable_tables_fallback: Optional boolean to enable an advanced table processing algorithm that supports very large and complex tables
            fullwidth_punctuation: Optional boolean to specify whether punctuation will be fullwidth Unicode
            convert_to_docx: Optional boolean to automatically convert your result to docx
            convert_to_md: Optional boolean to automatically convert your result to md
            convert_to_mmd: Optional boolean to automatically convert your result to mmd
            convert_to_tex_zip: Optional boolean to automatically convert your result to tex.zip
            convert_to_html: Optional boolean to automatically convert your result to html
            convert_to_pdf: Optional boolean to automatically convert your result to pdf
            convert_to_md_zip: Optional boolean to automatically convert your result to md.zip
            convert_to_mmd_zip: Optional boolean to automatically convert your result to mmd.zip
            convert_to_pptx: Optional boolean to automatically convert your result to pptx
            convert_to_html_zip: Optional boolean to automatically convert your result to html.zip
            improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true
            file_batch_id: Optional batch ID to associate this file with.
            webhook_url: Optional URL to receive webhook notifications. (Not yet enabled)
            mathpix_webhook_secret: Optional secret for webhook authentication. (Not yet enabled)
            webhook_payload: Optional custom payload to include in webhooks. (Not yet enabled)
            webhook_enabled_events: Optional list of events to trigger webhooks. (Not yet enabled)

        Returns:
            Pdf: A new Pdf instance

        Raises:
            ValueError: If neither file_path nor url, or both file_path and url are provided.
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
        if (file_path is None and url is None) or (file_path is not None and url is not None):
            logger.error("Invalid parameters: Exactly one of file_path or url must be provided")
            raise ValidationError("Exactly one of file_path or url must be provided")
        if not self.improve_mathpix:
            logger.debug('improve_mathpix set to False on the client')
            improve_mathpix = False
        elif not improve_mathpix:
            improve_mathpix = False
        endpoint = urljoin(self.auth.api_url, 'v3/pdf')
        options = {
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True,
            "conversion_formats": {},
            "metadata": {
                "improve_mathpix": improve_mathpix,
                "mpxpy": True,
                **(metadata or {})
            },
        }
        if alphabets_allowed is not None:
            options["alphabets_allowed"] = alphabets_allowed
        if not rm_spaces:
            options["rm_spaces"] = rm_spaces
        if rm_fonts:
            options["rm_fonts"] = rm_fonts
        if idiomatic_eqn_arrays:
            options["idiomatic_eqn_arrays"] = idiomatic_eqn_arrays
        if include_equation_tags:
            options["include_equation_tags"] = True
        if not include_smiles:
            options["include_smiles"] = include_smiles
        if include_chemistry_as_image:
            options["include_chemistry_as_image"] = True
        if include_diagram_text:
            options["include_diagram_text"] = include_diagram_text
        if numbers_default_to_math:
            options["numbers_default_to_math"] = numbers_default_to_math
        if math_inline_delimiters is not None:
            options["math_inline_delimiters"] = math_inline_delimiters
        if math_display_delimiters is not None:
            options["math_display_delimiters"] = math_display_delimiters
        if page_ranges is not None:
            options["page_ranges"] = page_ranges
        if enable_spell_check:
            options["enable_spell_check"] = enable_spell_check
        if auto_number_sections:
            options["auto_number_sections"] = auto_number_sections
        if remove_section_numbering:
            options["remove_section_numbering"] = remove_section_numbering
        if not preserve_section_numbering:
            options["preserve_section_numbering"] = preserve_section_numbering
        if enable_tables_fallback:
            options["enable_tables_fallback"] = enable_tables_fallback
        if fullwidth_punctuation:
            options["fullwidth_punctuation"] = fullwidth_punctuation
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
        if convert_to_docx:
            options["conversion_formats"]['docx'] = True
        if convert_to_md:
            options["conversion_formats"]['md'] = True
        if convert_to_mmd:
            options["conversion_formats"]['mmd'] = True
        if convert_to_tex_zip:
            options["conversion_formats"]['tex.zip'] = True
        if convert_to_html:
            options["conversion_formats"]['html'] = True
        if convert_to_pdf:
            options["conversion_formats"]['pdf'] = True
        if convert_to_pptx:
            options["conversion_formats"]['pptx'] = True
        if convert_to_md_zip:
            options["conversion_formats"]['md.zip'] = True
        if convert_to_mmd_zip:
            options["conversion_formats"]['mmd.zip'] = True
        if convert_to_html_zip:
            options["conversion_formats"]['html.zip'] = True
        data = {
            "options_json": json.dumps(options)
        }
        if file_path:
            logger.debug(f"Creating new PDF: path={file_path}")
            path = Path(file_path)
            if not path.is_file():
                logger.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"File path not found: {file_path}")
            with path.open("rb") as pdf_file:
                files = {"file": pdf_file}
                response_json = None
                try:
                    response = post(endpoint, data=data, files=files, headers=self.auth.headers, **self.request_options)
                    response.raise_for_status()
                    response_json = response.json()
                    pdf_id = response_json['pdf_id']
                    logger.debug(f"PDF from local path processing started, PDF ID: {pdf_id}")
                    return Pdf(
                        auth=self.auth,
                        pdf_id=pdf_id,
                        file_path=file_path,
                        convert_to_docx=convert_to_docx,
                        convert_to_md=convert_to_md,
                        convert_to_mmd=convert_to_mmd,
                        convert_to_tex_zip=convert_to_tex_zip,
                        convert_to_html=convert_to_html,
                        convert_to_pdf=convert_to_pdf,
                        convert_to_md_zip=convert_to_md_zip,
                        convert_to_mmd_zip=convert_to_mmd_zip,
                        convert_to_pptx=convert_to_pptx,
                        convert_to_html_zip=convert_to_html_zip,
                        improve_mathpix=improve_mathpix,
                        file_batch_id=file_batch_id,
                        webhook_url=webhook_url,
                        mathpix_webhook_secret=mathpix_webhook_secret,
                        webhook_payload=webhook_payload,
                        webhook_enabled_events=webhook_enabled_events,
                        request_options=self.request_options,
                    )
                except requests.exceptions.RequestException as e:
                    if response_json:
                        logger.error(f"PDF upload failed: {response_json}")
                    raise MathpixClientError(f"Mathpix PDF request failed: {e}")
        else:
            logger.debug(f"Creating new PDF: url={url}")
            options["url"] = url
            response_json = None
            try:
                response = post(endpoint, json=options, headers=self.auth.headers, **self.request_options)
                response.raise_for_status()
                response_json = response.json()
                pdf_id = response_json['pdf_id']
                logger.debug(f"PDF from URL processing started, PDF ID: {pdf_id}")
                return Pdf(
                        auth=self.auth,
                        pdf_id=pdf_id,
                        url=url,
                        convert_to_docx=convert_to_docx,
                        convert_to_md=convert_to_md,
                        convert_to_mmd=convert_to_mmd,
                        convert_to_tex_zip=convert_to_tex_zip,
                        convert_to_html=convert_to_html,
                        convert_to_pdf=convert_to_pdf,
                        convert_to_md_zip=convert_to_md_zip,
                        convert_to_mmd_zip=convert_to_mmd_zip,
                        convert_to_pptx=convert_to_pptx,
                        convert_to_html_zip=convert_to_html_zip,
                        improve_mathpix=improve_mathpix,
                        file_batch_id=file_batch_id,
                        webhook_url=webhook_url,
                        mathpix_webhook_secret=mathpix_webhook_secret,
                        webhook_payload=webhook_payload,
                        webhook_enabled_events=webhook_enabled_events,
                        request_options=self.request_options,
                    )
            except Exception as e:
                if response_json:
                    logger.error(f"PDF upload failed: {response_json}")
                raise MathpixClientError(f"Mathpix PDF request failed: {e}")

    def pdf_delete(self, pdf_id: str):
        """Delete a PDF and all associated files from S3.

        Args:
            pdf_id: The PDF ID to delete.

        Returns:
            dict: Pre-deletion status info including 'deleted_at' timestamp.
        """
        endpoint = urljoin(self.auth.api_url, f'v3/pdf/{pdf_id}')
        response = requests.delete(endpoint, headers=self.auth.headers, **self.request_options)
        result = response.json()
        if response.status_code == 404:
            raise MathpixClientError(f"PDF not found: {pdf_id}")
        if 'error' in result:
            raise MathpixClientError(f"Cannot delete PDF: {result.get('error')}")
        return result

    def conversion_delete(self, conversion_id: str):
        """Delete a conversion and all associated output files from S3.

        Args:
            conversion_id: The conversion ID to delete.

        Returns:
            dict: Final status info for the conversion.
        """
        endpoint = urljoin(self.auth.api_url, f'v3/converter/{conversion_id}')
        response = requests.delete(endpoint, headers=self.auth.headers, **self.request_options)
        result = response.json()
        if response.status_code == 404:
            raise MathpixClientError(f"Conversion not found: {conversion_id}")
        if 'error' in result:
            raise MathpixClientError(f"Cannot delete conversion: {result.get('error')}")
        return result

    def file_batch_new(self):
        """Creates a new file batch ID that can be used to group multiple file uploads.

        Note: This feature is not yet available in the production API.

        Returns:
            FileBatch: A new FileBatch instance.

        Raises:
            MathpixClientError: If the API request fails.
        """
        endpoint = urljoin(self.auth.api_url, 'v3/file-batches')
        try:
            response = post(endpoint, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            response_json = response.json()
            file_batch_id = response_json['file_batch_id']
            return FileBatch(auth=self.auth, file_batch_id=file_batch_id, request_options=self.request_options)
        except requests.exceptions.RequestException as e:
            logger.error(f"File batch creation failed: {e}")
            raise MathpixClientError(f"Mathpix request failed: {e}")

    def conversion_new(
            self,
            mmd: str,
            convert_to_docx: Optional[bool] = False,
            convert_to_md: Optional[bool] = False,
            convert_to_tex_zip: Optional[bool] = False,
            convert_to_html: Optional[bool] = False,
            convert_to_pdf: Optional[bool] = False,
            convert_to_latex_pdf: Optional[bool] = False,
            convert_to_md_zip: Optional[bool] = False,
            convert_to_mmd_zip: Optional[bool] = False,
            convert_to_pptx: Optional[bool] = False,
            convert_to_html_zip: Optional[bool] = False,
    ):
        """Converts Mathpix Markdown (MMD) to various output formats.

        Args:
            mmd: Mathpix Markdown content to convert.
            convert_to_docx: Optional boolean to convert your result to docx
            convert_to_md: Optional boolean to convert your result to md
            convert_to_tex_zip: Optional boolean to convert your result to tex.zip
            convert_to_html: Optional boolean to convert your result to html
            convert_to_pdf: Optional boolean to convert your result to pdf
            convert_to_latex_pdf: Optional boolean to convert your result to pdf containing LaTeX
            convert_to_md_zip: Optional boolean to automatically convert your result to md.zip
            convert_to_mmd_zip: Optional boolean to automatically convert your result to mmd.zip
            convert_to_pptx: Optional boolean to automatically convert your result to pptx
            convert_to_html_zip: Optional boolean to automatically convert your result to html.zip

        Returns:
            Conversion: A new Conversion instance.

        Raises:
            MathpixClientError: If the API request fails.
        """
        logger.debug("Starting new MMD conversion")
        endpoint = urljoin(self.auth.api_url, 'v3/converter')
        options = {
            "mmd": mmd,
            "formats": {}
        }
        if convert_to_docx:
            options["formats"]['docx'] = True
        if convert_to_md:
            options["formats"]['md'] = True
        if convert_to_tex_zip:
            options["formats"]['tex.zip'] = True
        if convert_to_html:
            options["formats"]['html'] = True
        if convert_to_pdf:
            options["formats"]['pdf'] = True
        if convert_to_latex_pdf:
            options["formats"]['latex.pdf'] = True
        if convert_to_pptx:
            options["formats"]['pptx'] = True
        if convert_to_md_zip:
            options["formats"]['md.zip'] = True
        if convert_to_mmd_zip:
            options["formats"]['mmd.zip'] = True
        if convert_to_html_zip:
            options["formats"]['html.zip'] = True
        if len(options['formats'].items()) == 0:
            raise ValidationError("At least one format is required.")
        response_json = None
        try:
            response = post(endpoint, json=options, headers=self.auth.headers)
            response.raise_for_status()
            response_json = response.json()
            if 'error' in response_json:
                logger.error(f"Conversion failed: {response_json}")
                raise MathpixClientError(f"Conversion failed: {response_json}")
            conversion_id = response_json['conversion_id']
            logger.debug(f"Conversion created, ID: {conversion_id}")
            return Conversion(
                auth=self.auth,
                conversion_id=conversion_id,
                convert_to_docx=convert_to_docx,
                convert_to_md=convert_to_md,
                convert_to_tex_zip=convert_to_tex_zip,
                convert_to_html=convert_to_html,
                convert_to_pdf=convert_to_pdf,
                convert_to_latex_pdf=convert_to_latex_pdf,
                convert_to_md_zip=convert_to_md_zip,
                convert_to_mmd_zip=convert_to_mmd_zip,
                convert_to_pptx=convert_to_pptx,
                convert_to_html_zip=convert_to_html_zip,
                request_options=self.request_options,
            )
        except Exception as e:
            if response_json:
                logger.error(f"Conversion failed: {response_json}")
            raise MathpixClientError(f"Mathpix conversion request failed: {e}")

    def file_new(
            self,
            source_uri: Optional[str] = None,
            file_path: Optional[str] = None,
            job_id: Optional[str] = None,
            custom_id: Optional[str] = None,
            idempotency_key: Optional[str] = None,
            filename: Optional[str] = None,
            conversion_formats: Optional[Dict[str, bool]] = None,
            conversion_options: Optional[Dict[str, object]] = None,
            destination_uri: Optional[str] = None,
            destination_basename: Optional[str] = None,
            s3_region: Optional[str] = None,
            image_output_mode: Optional[str] = None,
            include_page_info: Optional[bool] = None,
            metadata: Optional[Dict[str, object]] = None,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            rm_spaces: Optional[bool] = True,
            rm_fonts: Optional[bool] = False,
            idiomatic_eqn_arrays: Optional[bool] = False,
            include_equation_tags: Optional[bool] = False,
            include_smiles: Optional[bool] = True,
            include_chemistry_as_image: Optional[bool] = False,
            include_diagram_text: Optional[bool] = False,
            numbers_default_to_math: Optional[bool] = False,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            page_ranges: Optional[str] = None,
            enable_spell_check: Optional[bool] = False,
            auto_number_sections: Optional[bool] = False,
            remove_section_numbering: Optional[bool] = False,
            preserve_section_numbering: Optional[bool] = True,
            enable_tables_fallback: Optional[bool] = False,
            fullwidth_punctuation: Optional[bool] = None,
    ) -> File:
        """Submit a single document for async processing.

        Exactly one of source_uri or file_path must be provided. A source_uri
        submits via POST /files/v1/uri and may be an s3://, gs://, public
        https://, or Azure Blob HTTPS URL; non-public sources require a
        registered data source for the bucket, see
        https://docs.mathpix.com/reference/files-v1-data-sources
        A file_path uploads a local file via multipart POST /files/v1.

        Args:
            source_uri: Remote location of the source document.
            file_path: Path to a local file to upload.
            job_id: Optional job to associate this file with. Required whenever
                custom_id is supplied.
            custom_id: Optional customer-supplied identifier (max 256 chars,
                characters [A-Za-z0-9_-.:], case-sensitive). Requires job_id;
                (job_id, custom_id) is the idempotency key: re-submitting the same
                pair returns the original file rather than creating a new one, as
                long as the original file is still live (pending, split, or
                completed). Not supported for local file_path uploads.
            idempotency_key: Optional client-generated key sent as the
                Idempotency-Key header (same constraints as custom_id). Makes a
                standalone submission safe to retry: re-sending the same request
                returns the original file_id instead of creating a duplicate. If
                both a (job_id, custom_id) pair and an idempotency_key are present,
                the pair takes precedence. Not supported for local file_path
                uploads.
            filename: Optional display name for the file (defaults to
                '<file_id>.pdf').
            conversion_formats: Dict of format names to enable (e.g., {'docx': True,
                'md': True}). Mathpix Markdown (mmd) is always produced.
            conversion_options: Additional request options dict, merged into the
                request body last. May not override the validated request fields
                source_uri, job_id, custom_id, or metadata.
            destination_uri: Optional destination for results. Same scheme rules as
                source_uri; must be backed by a registered data source. When omitted,
                results stay in Mathpix storage and are fetched via the download
                helpers on File.
            destination_basename: Optional basename for output objects within
                destination_uri (defaults to the file_id).
            s3_region: Optional region of the destination_uri S3 bucket.
            image_output_mode: Set to 'local' to write cropped images into
                destination_uri storage under images/, instead of the Mathpix CDN.
            include_page_info: Include per-page information in the output.
            metadata: Optional dict to attach metadata to the request.
            alphabets_allowed: Optional dict to list alphabets allowed in the output.
            rm_spaces: Remove extra white space from equations (default True).
            rm_fonts: Remove font commands from equations (default False).
            idiomatic_eqn_arrays: Use aligned/gathered/cases instead of array (default False).
            include_equation_tags: Include equation number tags in LaTeX (default False).
            include_smiles: Enable chemistry diagram OCR via SMILES (default True).
            include_chemistry_as_image: Return image crop for chemical diagrams (default False).
            include_diagram_text: Enable text extraction from diagrams (default False).
            numbers_default_to_math: Numbers are always math (default False).
            math_inline_delimiters: Tuple of (begin, end) delimiters for inline math.
            math_display_delimiters: Tuple of (begin, end) delimiters for display math.
            page_ranges: Page range string (e.g., "2,4-6").
            enable_spell_check: Enable predictive mode for English handwriting (default False).
            auto_number_sections: Auto-number sections (default False).
            remove_section_numbering: Remove existing section numbering (default False).
            preserve_section_numbering: Keep existing section numbering (default True).
            enable_tables_fallback: Enable advanced table processing (default False).
            fullwidth_punctuation: Use fullwidth Unicode punctuation (default None).

        Returns:
            File: A new File instance for polling status and downloading results.

        Raises:
            ValidationError: If not exactly one of source_uri and file_path is
                provided, custom_id is supplied without job_id, custom_id or
                idempotency_key is supplied for a local upload, or
                conversion_options contains a reserved request field.
            FileNotFoundError: If the specified file_path does not exist.
            FilesApiError: If the API rejects the submission.
            MathpixClientError: If the request fails.
        """
        has_exactly_one_source: bool = sum(x is not None for x in [source_uri, file_path]) == 1
        if not has_exactly_one_source:
            raise ValidationError("Exactly one of source_uri or file_path must be provided")
        _reject_reserved_conversion_options(conversion_options, {'source_uri', 'job_id', 'custom_id', 'metadata'})
        has_custom_id: bool = custom_id is not None
        if has_custom_id:
            has_job_id: bool = job_id is not None
            if not has_job_id:
                raise ValidationError("custom_id requires an explicit job_id")
        has_idempotency_key: bool = idempotency_key is not None
        if file_path is not None:
            is_uri_only_option_set: bool = has_custom_id or has_idempotency_key
            if is_uri_only_option_set:
                raise ValidationError("custom_id and idempotency_key are not supported for local file_path uploads")
            return self._file_new_multipart(
                file_path=file_path,
                job_id=job_id,
                filename=filename,
                conversion_formats=conversion_formats,
                conversion_options=conversion_options,
                destination_uri=destination_uri,
                destination_basename=destination_basename,
                s3_region=s3_region,
                image_output_mode=image_output_mode,
                include_page_info=include_page_info,
                metadata=metadata,
                alphabets_allowed=alphabets_allowed,
                rm_spaces=rm_spaces,
                rm_fonts=rm_fonts,
                idiomatic_eqn_arrays=idiomatic_eqn_arrays,
                include_equation_tags=include_equation_tags,
                include_smiles=include_smiles,
                include_chemistry_as_image=include_chemistry_as_image,
                include_diagram_text=include_diagram_text,
                numbers_default_to_math=numbers_default_to_math,
                math_inline_delimiters=math_inline_delimiters,
                math_display_delimiters=math_display_delimiters,
                page_ranges=page_ranges,
                enable_spell_check=enable_spell_check,
                auto_number_sections=auto_number_sections,
                remove_section_numbering=remove_section_numbering,
                preserve_section_numbering=preserve_section_numbering,
                enable_tables_fallback=enable_tables_fallback,
                fullwidth_punctuation=fullwidth_punctuation,
            )
        has_source_uri: bool = bool(source_uri)
        if not has_source_uri:
            raise ValidationError("source_uri must be a non-empty string")
        options: Dict[str, object] = {
            "source_uri": source_uri,
        }
        if metadata:
            options["metadata"] = metadata
        if filename:
            options["filename"] = filename
        if conversion_formats:
            options["conversion_formats"] = conversion_formats
        if destination_uri:
            options["destination_uri"] = destination_uri
        if destination_basename:
            options["destination_basename"] = destination_basename
        if s3_region:
            options["s3_region"] = s3_region
        if image_output_mode:
            options["image_output_mode"] = image_output_mode
        if include_page_info is not None:
            options["include_page_info"] = include_page_info
        if custom_id:
            options["custom_id"] = custom_id
        if job_id:
            options["job_id"] = job_id
        _apply_processing_options(
            options,
            alphabets_allowed=alphabets_allowed,
            rm_spaces=rm_spaces,
            rm_fonts=rm_fonts,
            idiomatic_eqn_arrays=idiomatic_eqn_arrays,
            include_equation_tags=include_equation_tags,
            include_smiles=include_smiles,
            include_chemistry_as_image=include_chemistry_as_image,
            include_diagram_text=include_diagram_text,
            numbers_default_to_math=numbers_default_to_math,
            math_inline_delimiters=math_inline_delimiters,
            math_display_delimiters=math_display_delimiters,
            page_ranges=page_ranges,
            enable_spell_check=enable_spell_check,
            auto_number_sections=auto_number_sections,
            remove_section_numbering=remove_section_numbering,
            preserve_section_numbering=preserve_section_numbering,
            enable_tables_fallback=enable_tables_fallback,
            fullwidth_punctuation=fullwidth_punctuation,
        )
        if conversion_options:
            options.update(conversion_options)
        logger.debug(f"Creating new file via Files API: source_uri={source_uri}")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/uri')
        headers: Dict[str, str] = dict(self.auth.headers)
        if has_idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        try:
            response: requests.Response = post(endpoint, json=options, headers=headers, **self.request_options)
            has_failed: bool = not response.ok
            if has_failed:
                raise error_from_response(response)
            response_json: Dict[str, Any] = response.json()
            file_id: str = response_json['file_id']
            logger.debug(f"File from URI started, file_id: {file_id}")
            return File(auth=self.auth, file_id=file_id, request_options=self.request_options)
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix Files API request failed: {e}")

    def _file_new_multipart(
            self,
            file_path: str,
            job_id: Optional[str] = None,
            filename: Optional[str] = None,
            conversion_formats: Optional[Dict[str, bool]] = None,
            conversion_options: Optional[Dict[str, object]] = None,
            destination_uri: Optional[str] = None,
            destination_basename: Optional[str] = None,
            s3_region: Optional[str] = None,
            image_output_mode: Optional[str] = None,
            include_page_info: Optional[bool] = None,
            metadata: Optional[Dict[str, object]] = None,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            rm_spaces: Optional[bool] = True,
            rm_fonts: Optional[bool] = False,
            idiomatic_eqn_arrays: Optional[bool] = False,
            include_equation_tags: Optional[bool] = False,
            include_smiles: Optional[bool] = True,
            include_chemistry_as_image: Optional[bool] = False,
            include_diagram_text: Optional[bool] = False,
            numbers_default_to_math: Optional[bool] = False,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            page_ranges: Optional[str] = None,
            enable_spell_check: Optional[bool] = False,
            auto_number_sections: Optional[bool] = False,
            remove_section_numbering: Optional[bool] = False,
            preserve_section_numbering: Optional[bool] = True,
            enable_tables_fallback: Optional[bool] = False,
            fullwidth_punctuation: Optional[bool] = None,
    ) -> File:
        """Upload a local file via multipart POST /files/v1 for file_new.

        The multipart endpoint uses the legacy field names, so job_id and
        destination_uri are translated to scs_job_id and destination_s3_uri.
        """
        options: Dict[str, object] = {}
        if metadata:
            options["metadata"] = metadata
        if conversion_formats:
            options["conversion_formats"] = conversion_formats
        if job_id:
            options["scs_job_id"] = job_id
        if destination_uri:
            options["destination_s3_uri"] = destination_uri
        if destination_basename:
            options["destination_basename"] = destination_basename
        if s3_region:
            options["s3_region"] = s3_region
        if image_output_mode:
            options["image_output_mode"] = image_output_mode
        if include_page_info is not None:
            options["include_page_info"] = include_page_info
        _apply_processing_options(
            options,
            alphabets_allowed=alphabets_allowed,
            rm_spaces=rm_spaces,
            rm_fonts=rm_fonts,
            idiomatic_eqn_arrays=idiomatic_eqn_arrays,
            include_equation_tags=include_equation_tags,
            include_smiles=include_smiles,
            include_chemistry_as_image=include_chemistry_as_image,
            include_diagram_text=include_diagram_text,
            numbers_default_to_math=numbers_default_to_math,
            math_inline_delimiters=math_inline_delimiters,
            math_display_delimiters=math_display_delimiters,
            page_ranges=page_ranges,
            enable_spell_check=enable_spell_check,
            auto_number_sections=auto_number_sections,
            remove_section_numbering=remove_section_numbering,
            preserve_section_numbering=preserve_section_numbering,
            enable_tables_fallback=enable_tables_fallback,
            fullwidth_punctuation=fullwidth_punctuation,
        )
        if conversion_options:
            options.update(conversion_options)
        logger.debug(f"Creating new file via Files API multipart: path={file_path}")
        path: Path = Path(file_path)
        is_existing_file: bool = path.is_file()
        if not is_existing_file:
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File path not found: {file_path}")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1')
        data: Dict[str, str] = {"options_json": json.dumps(options)}
        if filename:
            data["filename"] = filename
        if job_id:
            data["scs_job_id"] = job_id
        with path.open("rb") as f:
            files: Dict[str, Any] = {"file": f}
            try:
                response: requests.Response = post(endpoint, data=data, files=files, headers=self.auth.headers, **self.request_options)
                has_failed: bool = not response.ok
                if has_failed:
                    raise error_from_response(response)
                response_json: Dict[str, Any] = response.json()
                file_id: str = response_json['file_id']
                logger.debug(f"File upload started, file_id: {file_id}")
                return File(auth=self.auth, file_id=file_id, request_options=self.request_options)
            except requests.exceptions.RequestException as e:
                raise MathpixClientError(f"Mathpix Files API multipart request failed: {e}")

    def file_job_new(
            self,
            files: List[Union[FileSubmission, Dict[str, Any]]],
            job_id: Optional[str] = None,
            idempotency_key: Optional[str] = None,
            conversion_formats: Optional[Dict[str, bool]] = None,
            conversion_options: Optional[Dict[str, object]] = None,
            image_output_mode: Optional[str] = None,
            metadata: Optional[Dict[str, object]] = None,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            rm_spaces: Optional[bool] = True,
            rm_fonts: Optional[bool] = False,
            idiomatic_eqn_arrays: Optional[bool] = False,
            include_equation_tags: Optional[bool] = False,
            include_smiles: Optional[bool] = True,
            include_chemistry_as_image: Optional[bool] = False,
            include_diagram_text: Optional[bool] = False,
            numbers_default_to_math: Optional[bool] = False,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            enable_spell_check: Optional[bool] = False,
            auto_number_sections: Optional[bool] = False,
            remove_section_numbering: Optional[bool] = False,
            preserve_section_numbering: Optional[bool] = True,
            enable_tables_fallback: Optional[bool] = False,
            fullwidth_punctuation: Optional[bool] = None,
    ) -> FileJob:
        """Submit a batch of documents for async processing in one call.

        Submits documents in bulk via POST /files/v1/jobs; the server enforces
        an items-per-call ceiling (currently 200,000). The request is
        accept-and-defer: it returns immediately with a job_id and file_count,
        then submits the items in the background. Per-item failures (bad or
        unsupported source_uri, missing data source) are NOT reported
        synchronously; each surfaces as that file's error status when you poll
        the job. Poll FileJob.status() for completion and list failed items with
        FileJob.files(status='error').

        OCR and conversion options apply to every file in the submitted request.
        To vary settings across subsets of a larger job, make multiple calls with
        the same job_id and different options.

        Args:
            files: List of FileSubmission instances or dicts with the same keys
                (source_uri required; custom_id, filename, destination_uri,
                s3_region, destination_basename, page_ranges optional).
            job_id: Optional caller-supplied job id. If omitted the server
                generates one. Required whenever any item carries a custom_id.
            idempotency_key: Optional client-generated key sent as the
                Idempotency-Key header, making the entire batch submission safe to
                retry: re-sending the same request returns the original response
                without re-enqueuing any file. Honored only when no job_id is
                supplied; an explicit job_id wins and the header is ignored for
                job derivation.
            conversion_formats: Job-wide conversion formats, applied to every file
                (e.g., {'docx': True, 'md': True}).
            conversion_options: Additional request options dict, merged into the
                request body last. May not override the validated request fields
                files, job_id, or metadata.
            image_output_mode: Job-wide. Set to 'local' to write cropped images
                into each file's destination_uri storage. Applies only to files
                that set a destination_uri.
            metadata: Optional dict to attach metadata to the request.
            alphabets_allowed: Optional dict to list alphabets allowed in the output.
            rm_spaces: Remove extra white space from equations (default True).
            rm_fonts: Remove font commands from equations (default False).
            idiomatic_eqn_arrays: Use aligned/gathered/cases instead of array (default False).
            include_equation_tags: Include equation number tags in LaTeX (default False).
            include_smiles: Enable chemistry diagram OCR via SMILES (default True).
            include_chemistry_as_image: Return image crop for chemical diagrams (default False).
            include_diagram_text: Enable text extraction from diagrams (default False).
            numbers_default_to_math: Numbers are always math (default False).
            math_inline_delimiters: Tuple of (begin, end) delimiters for inline math.
            math_display_delimiters: Tuple of (begin, end) delimiters for display math.
            enable_spell_check: Enable predictive mode for English handwriting (default False).
            auto_number_sections: Auto-number sections (default False).
            remove_section_numbering: Remove existing section numbering (default False).
            preserve_section_numbering: Keep existing section numbering (default True).
            enable_tables_fallback: Enable advanced table processing (default False).
            fullwidth_punctuation: Use fullwidth Unicode punctuation (default None).

        Returns:
            FileJob: A new FileJob instance seeded with the response's job_id and
            file_count.

        Raises:
            ValidationError: If files is empty, an item is malformed or missing
                source_uri, a custom_id is duplicated within the batch, any
                custom_id is supplied without an explicit job_id, or
                conversion_options contains a reserved request field.
            FilesApiError: If the API rejects the submission (e.g. over the
                items-per-call ceiling or an identifier failing the
                charset/length constraint).
            MathpixClientError: If the request fails.
        """
        has_files: bool = bool(files)
        if not has_files:
            raise ValidationError("files must be a non-empty list")
        _reject_reserved_conversion_options(conversion_options, {'files', 'job_id', 'metadata'})
        normalized: List[Dict[str, Any]] = [normalize_file_submission(item) for item in files]
        has_explicit_job_id: bool = job_id is not None
        seen_custom_ids: Set[str] = set()
        for submission in normalized:
            item_custom_id: Optional[str] = submission.get('custom_id')
            has_item_custom_id: bool = item_custom_id is not None
            if not has_item_custom_id:
                continue
            if not has_explicit_job_id:
                raise ValidationError("custom_id requires an explicit job_id")
            is_duplicate_custom_id: bool = item_custom_id in seen_custom_ids
            if is_duplicate_custom_id:
                raise ValidationError(f"Duplicate custom_id within the batch: {item_custom_id!r}")
            seen_custom_ids.add(item_custom_id)
        has_idempotency_key: bool = idempotency_key is not None
        if has_idempotency_key and has_explicit_job_id:
            logger.warning("idempotency_key is ignored for job derivation when an explicit job_id is supplied")
        logger.debug(f"Submitting job with {len(normalized)} files")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/jobs')
        body: Dict[str, Any] = {
            "files": normalized,
        }
        if metadata:
            body["metadata"] = metadata
        if job_id:
            body["job_id"] = job_id
        if conversion_formats:
            body["conversion_formats"] = conversion_formats
        if image_output_mode:
            body["image_output_mode"] = image_output_mode
        _apply_processing_options(
            body,
            alphabets_allowed=alphabets_allowed,
            rm_spaces=rm_spaces,
            rm_fonts=rm_fonts,
            idiomatic_eqn_arrays=idiomatic_eqn_arrays,
            include_equation_tags=include_equation_tags,
            include_smiles=include_smiles,
            include_chemistry_as_image=include_chemistry_as_image,
            include_diagram_text=include_diagram_text,
            numbers_default_to_math=numbers_default_to_math,
            math_inline_delimiters=math_inline_delimiters,
            math_display_delimiters=math_display_delimiters,
            enable_spell_check=enable_spell_check,
            auto_number_sections=auto_number_sections,
            remove_section_numbering=remove_section_numbering,
            preserve_section_numbering=preserve_section_numbering,
            enable_tables_fallback=enable_tables_fallback,
            fullwidth_punctuation=fullwidth_punctuation,
        )
        if conversion_options:
            body.update(conversion_options)
        headers: Dict[str, str] = dict(self.auth.headers)
        if has_idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        try:
            response: requests.Response = post(endpoint, json=body, headers=headers, **self.request_options)
            has_failed: bool = not response.ok
            if has_failed:
                raise error_from_response(response)
            response_json: Dict[str, Any] = response.json()
            response_job_id: str = response_json['job_id']
            logger.debug(f"Job accepted, job_id: {response_job_id}")
            return FileJob(
                auth=self.auth,
                job_id=response_job_id,
                file_count=response_json.get('file_count'),
                request_options=self.request_options,
            )
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix Files API job request failed: {e}")

    def file_job_list(
            self,
            start: Optional[str] = None,
            end: Optional[str] = None,
            limit: int = 100,
            paging_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the jobs submitted under your account, newest first.

        Args:
            start: Earliest submission date to include, yyyy-MM-dd (UTC).
                Providing only one of start/end queries that single day.
            end: Latest submission date to include, yyyy-MM-dd (UTC).
            limit: Maximum jobs per page, 1-1000 (default 100).
            paging_state: Opaque pagination cursor from the previous response's
                'next_page_token'.

        Returns:
            dict: Response containing 'jobs' (each with job_id and created_at)
                and 'next_page_token' (non-null when more pages remain).

        Raises:
            FilesApiError: If the request fails (e.g. 'bad_request' for a
                malformed date or a limit outside 1-1000).
        """
        logger.debug("Listing jobs from the Files API")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/jobs')
        params: Dict[str, object] = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if paging_state:
            params["paging_state"] = paging_state
        try:
            response: requests.Response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            has_failed: bool = not response.ok
            if has_failed:
                raise error_from_response(response)
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix Files API list jobs request failed: {e}")

    def file_get(self, file_id: str) -> File:
        """Fetch an existing file and return its File instance.

        Performs GET /files/v1/{file_id}; the returned File is seeded with the
        response, so the lazy status attributes are populated without another
        request.

        Args:
            file_id: The file's identifier.

        Returns:
            File: A File instance seeded with the file's current status.

        Raises:
            FilesApiError: If the file does not exist ('not_found') or belongs
                to a different group ('forbidden').
            MathpixClientError: If the request fails without a Files API error body.
        """
        file: File = File(auth=self.auth, file_id=file_id, request_options=self.request_options)
        file.status()
        return file

    def file_delete(self, file_id: str) -> Dict[str, Any]:
        """Permanently remove a file and its results from Mathpix-owned storage.

        See File.delete for the full semantics (terminal-state requirement,
        idempotent repeats, customer-owned buckets unaffected).

        Args:
            file_id: The file's identifier.

        Returns:
            dict: Response containing 'file_id' and 'status': 'deleted'.

        Raises:
            FilesApiError: If the file does not exist, belongs to a different
                group, or is still processing.
        """
        return File(auth=self.auth, file_id=file_id, request_options=self.request_options).delete()

    def file_job_get(self, job_id: str) -> FileJob:
        """Fetch an existing job and return its FileJob instance.

        Performs GET /files/v1/jobs/{job_id} and seeds the returned FileJob's
        file_count from the response.

        Args:
            job_id: The job's identifier.

        Returns:
            FileJob: A FileJob instance seeded with the job's current file_count.

        Raises:
            FilesApiError: If the job does not exist ('not_found').
            MathpixClientError: If the request fails without a Files API error body.
        """
        job: FileJob = FileJob(auth=self.auth, job_id=job_id, request_options=self.request_options)
        job_status: Dict[str, Any] = job.status()
        job.file_count = job_status.get('file_count')
        return job

    def onboarding_identities(self) -> Dict[str, Any]:
        """Get the Mathpix identities you grant cloud storage access to.

        Call this BEFORE setting up cloud-side grants: it returns the Mathpix
        AWS trust account id, the Azure application/tenant ids, and the GCS
        impersonator service-account email, plus your per-group external_id.
        The external_id is generated on the first call and is immutable
        thereafter; it is used in the AWS IAM trust policy and as the GCS
        bucket-control verification id. The endpoint is idempotent.

        Returns:
            dict: Response with 'aws' (trust_account_id, external_id), 'azure'
                (app_id, tenant_id), and 'gcp' (service_account_email,
                external_id) blocks.

        Raises:
            FilesApiError: If the request fails.
            MathpixClientError: If the request cannot be made.
        """
        logger.debug("Getting data source onboarding identities")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/onboarding/identities')
        try:
            response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
            has_failed: bool = not response.ok
            if has_failed:
                raise error_from_response(response)
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix onboarding identities request failed: {e}")

    def data_source_new(
            self,
            provider: str,
            bucket: str,
            auth_method: str,
            provider_specific_details: Dict[str, str],
            name: Optional[str] = None,
            region: Optional[str] = None,
            secret: Optional[str] = None,
            exist_ok: bool = False,
    ) -> DataSource:
        """Register a bucket or container as a Files API data source.

        Complete the cloud-side grant first (IAM role for AWS, RBAC assignment
        for Azure, service-account impersonation binding plus the
        .mathpix-verify object for GCS); see
        https://docs.mathpix.com/reference/files-v1-data-sources for the
        per-provider guides. Use onboarding_identities() to fetch the Mathpix
        identities and your external_id before setting up grants.

        For AWS and Azure, call DataSource.test() afterward to verify the grant
        end-to-end. GCS registration only succeeds once bucket-control
        verification passes, so a successful return already confirms the grant.

        Args:
            provider: One of 'aws', 'azure', 'gcp'.
            bucket: Bucket / container name (S3 bucket, Azure container, or GCS
                bucket).
            auth_method: Grant type: 'iam_role' or 'access_key' for aws,
                'azure_ad' for azure, 'service_account' for gcp.
            provider_specific_details: Non-secret provider-shaped metadata, e.g.
                {'iam_role_arn': ..., 'aws_external_id': ...} for aws/iam_role,
                {'azure_tenant_id': ..., 'storage_account': ...} for azure, or
                {'gcp_project_id': ..., 'target_sa_email': ...} for gcp.
            name: Optional human-readable label (max 128 chars).
            region: Bucket region; required for aws with 'access_key', optional
                for 'iam_role' (discovered via the bucket).
            secret: Only for aws with 'access_key' (legacy fallback); rejected
                for the keyless providers.
            exist_ok: A data source for the same (provider, bucket) may already
                exist; the API returns a conflict carrying the existing id. When
                True, return a DataSource for that existing id instead of
                raising.

        Returns:
            DataSource: A new DataSource instance for the registered (or, with
            exist_ok, the pre-existing) data source.

        Raises:
            ValidationError: If provider or auth_method is invalid, the
                auth_method does not belong to the provider, or a secret is
                supplied for a keyless provider.
            FilesApiError: If the API rejects the registration ('bad_request',
                including GCS bucket-control verification failures), the
                (provider, bucket) pair already exists and exist_ok is False
                ('conflict'), or the GCS verification probe could not reach the
                bucket ('unavailable', 503; retryable).
            MathpixClientError: If the request cannot be made.
        """
        is_valid_provider: bool = provider in PROVIDERS
        if not is_valid_provider:
            raise ValidationError(f"provider must be one of: {', '.join(PROVIDERS)}")
        is_valid_auth_method: bool = auth_method in AUTH_METHODS_BY_PROVIDER[provider]
        if not is_valid_auth_method:
            raise ValidationError(
                f"auth_method for provider '{provider}' must be one of: "
                f"{', '.join(AUTH_METHODS_BY_PROVIDER[provider])}"
            )
        has_bucket: bool = bool(bucket)
        if not has_bucket:
            raise ValidationError("bucket is required")
        has_secret: bool = secret is not None
        is_keyless_auth_method: bool = auth_method != 'access_key'
        if has_secret and is_keyless_auth_method:
            raise ValidationError("secret is only accepted for aws with auth_method 'access_key'")
        logger.debug(f"Registering data source: provider={provider}, bucket={bucket}, auth_method={auth_method}")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/data-sources')
        body: Dict[str, Any] = {
            "provider": provider,
            "bucket": bucket,
            "auth_method": auth_method,
            "provider_specific_details": provider_specific_details,
        }
        if name:
            body["name"] = name
        if region:
            body["region"] = region
        if has_secret:
            body["secret"] = secret
        try:
            response: requests.Response = post(endpoint, json=body, headers=self.auth.headers, **self.request_options)
            is_conflict: bool = response.status_code == 409
            if is_conflict:
                existing_id: Optional[str] = None
                try:
                    conflict_body: Dict[str, Any] = response.json()
                    existing_id = (
                        conflict_body.get('data_source_id')
                        or (conflict_body.get('error_info') or {}).get('data_source_id')
                    )
                except ValueError:
                    pass
                has_existing_id: bool = existing_id is not None
                if exist_ok and has_existing_id:
                    logger.debug(f"Data source already exists, returning existing id: {existing_id}")
                    return DataSource(auth=self.auth, data_source_id=existing_id, request_options=self.request_options)
                raise FilesApiError(
                    f"A data source for ({provider}, {bucket}) already exists"
                    + (f" with data_source_id {existing_id}" if has_existing_id else ""),
                    error_id='conflict',
                    http_status=409,
                )
            has_failed: bool = not response.ok
            if has_failed:
                raise error_from_response(response)
            response_json: Dict[str, Any] = response.json()
            data_source_id: str = response_json['data_source_id']
            logger.debug(f"Data source registered, data_source_id: {data_source_id}")
            return DataSource(auth=self.auth, data_source_id=data_source_id, request_options=self.request_options)
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix data source registration failed: {e}")

    def data_sources_list(self) -> Dict[str, Any]:
        """List the data sources registered for your group.

        Secrets (for aws 'access_key' sources) are never returned.

        Returns:
            dict: Response containing 'data_sources', each with data_source_id,
                name, provider, bucket, region, auth_method, and created_at.

        Raises:
            FilesApiError: If the request fails.
            MathpixClientError: If the request cannot be made.
        """
        logger.debug("Listing data sources")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/data-sources')
        try:
            response: requests.Response = get(endpoint, headers=self.auth.headers, **self.request_options)
            has_failed: bool = not response.ok
            if has_failed:
                raise error_from_response(response)
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix data sources list request failed: {e}")

    def data_source_get(self, data_source_id: str) -> DataSource:
        """Get a DataSource instance for an existing data_source_id.

        Constructs the handle without making a request; call DataSource.test()
        to verify it.

        Args:
            data_source_id: The data source's identifier.

        Returns:
            DataSource: A DataSource instance for the given id.
        """
        return DataSource(auth=self.auth, data_source_id=data_source_id, request_options=self.request_options)

    def data_source_test(self, data_source_id: str) -> Dict[str, Any]:
        """Verify Mathpix can reach a registered bucket.

        See DataSource.test for the full semantics: HTTP 200 for both outcomes;
        the {'result', 'checks', 'message'} probe body is returned as-is and a
        failed probe does not raise.

        Args:
            data_source_id: The data source's identifier.

        Returns:
            dict: The probe body ('result', 'checks', 'message').

        Raises:
            FilesApiError: If the request itself fails (e.g. 'not_found').
        """
        return self.data_source_get(data_source_id).test()

    def data_source_delete(self, data_source_id: str) -> Dict[str, Any]:
        """Permanently remove a data source.

        See DataSource.delete for the full semantics (in-flight jobs keep their
        cached credentials; cloud-side grants must be revoked separately).

        Args:
            data_source_id: The data source's identifier.

        Returns:
            dict: Response containing 'data_source_id' and 'status': 'deleted'.

        Raises:
            FilesApiError: If the data source does not exist or belongs to a
                different group.
        """
        return self.data_source_get(data_source_id).delete()

    @deprecated("scs_file_new is deprecated; use file_new(source_uri=...) instead")
    def scs_file_new(
            self,
            file_path: Optional[str] = None,
            url: Optional[str] = None,
            source_s3_uri: Optional[str] = None,
            filename: Optional[str] = None,
            scs_job_id: Optional[str] = None,
            conversion_formats: Optional[Dict[str, bool]] = None,
            conversion_options: Optional[Dict[str, object]] = None,
            destination_s3_uri: Optional[str] = None,
            destination_basename: Optional[str] = None,
            s3_region: Optional[str] = None,
            image_output_mode: Optional[str] = None,
            include_page_info: Optional[bool] = None,
            metadata: Optional[Dict[str, object]] = None,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            rm_spaces: Optional[bool] = True,
            rm_fonts: Optional[bool] = False,
            idiomatic_eqn_arrays: Optional[bool] = False,
            include_equation_tags: Optional[bool] = False,
            include_smiles: Optional[bool] = True,
            include_chemistry_as_image: Optional[bool] = False,
            include_diagram_text: Optional[bool] = False,
            numbers_default_to_math: Optional[bool] = False,
            math_inline_delimiters: Optional[Tuple[str, str]] = None,
            math_display_delimiters: Optional[Tuple[str, str]] = None,
            page_ranges: Optional[str] = None,
            enable_spell_check: Optional[bool] = False,
            auto_number_sections: Optional[bool] = False,
            remove_section_numbering: Optional[bool] = False,
            preserve_section_numbering: Optional[bool] = True,
            enable_tables_fallback: Optional[bool] = False,
            fullwidth_punctuation: Optional[bool] = None,
    ) -> ScsFile:
        """Upload a file via files-api v1 for async processing.

        Deprecated: use file_new instead. This wrapper translates url and
        source_s3_uri to source_uri, scs_job_id to job_id, and
        destination_s3_uri to destination_uri, then forwards to file_new.

        Args:
            file_path: Path to a local file to upload via multipart POST /files/v1.
            url: URL of a remote file, forwarded as source_uri.
            source_s3_uri: S3 URI (s3://bucket/key), forwarded as source_uri.
            filename: Optional display name for the file.
            scs_job_id: Forwarded as job_id.
            conversion_formats: Dict of format names to enable (e.g., {'mmd': True, 'docx': True}).
            conversion_options: Additional conversion options dict.
            destination_s3_uri: Forwarded as destination_uri.
            destination_basename: Optional basename for output files (defaults to file_id).
            s3_region: Region of the destination_s3_uri bucket.
            image_output_mode: Image output mode (e.g., 'local').
            include_page_info: Include per-page information in the output.
            metadata: Optional dict to attach metadata to the request.
            alphabets_allowed: Optional dict to list alphabets allowed in the output.
            rm_spaces: Remove extra white space from equations (default True).
            rm_fonts: Remove font commands from equations (default False).
            idiomatic_eqn_arrays: Use aligned/gathered/cases instead of array (default False).
            include_equation_tags: Include equation number tags in LaTeX (default False).
            include_smiles: Enable chemistry diagram OCR via SMILES (default True).
            include_chemistry_as_image: Return image crop for chemical diagrams (default False).
            include_diagram_text: Enable text extraction from diagrams (default False).
            numbers_default_to_math: Numbers are always math (default False).
            math_inline_delimiters: Tuple of (begin, end) delimiters for inline math.
            math_display_delimiters: Tuple of (begin, end) delimiters for display math.
            page_ranges: Page range string (e.g., "2,4-6" or "2--2").
            enable_spell_check: Enable predictive mode for English handwriting (default False).
            auto_number_sections: Auto-number sections (default False).
            remove_section_numbering: Remove existing section numbering (default False).
            preserve_section_numbering: Keep existing section numbering (default True).
            enable_tables_fallback: Enable advanced table processing (default False).
            fullwidth_punctuation: Use fullwidth Unicode punctuation (default None).

        Returns:
            ScsFile: A new ScsFile instance for polling status and downloading results.

        Raises:
            ValidationError: If not exactly one of file_path, url, or source_s3_uri is provided.
            FileNotFoundError: If the specified file_path does not exist.
            FilesApiError: If the API rejects the submission.
            MathpixClientError: If the request fails.
        """
        source_count: int = sum(x is not None for x in [file_path, url, source_s3_uri])
        has_exactly_one_source: bool = source_count == 1
        if not has_exactly_one_source:
            logger.error("Invalid parameters: Exactly one of file_path, url, or source_s3_uri must be provided")
            raise ValidationError("Exactly one of file_path, url, or source_s3_uri must be provided")
        resolved_source_uri: Optional[str] = url if url is not None else source_s3_uri
        submitted_file: File = self.file_new(
            source_uri=resolved_source_uri,
            file_path=file_path,
            job_id=scs_job_id,
            filename=filename,
            conversion_formats=conversion_formats,
            conversion_options=conversion_options,
            destination_uri=destination_s3_uri,
            destination_basename=destination_basename,
            s3_region=s3_region,
            image_output_mode=image_output_mode,
            include_page_info=include_page_info,
            metadata=metadata,
            alphabets_allowed=alphabets_allowed,
            rm_spaces=rm_spaces,
            rm_fonts=rm_fonts,
            idiomatic_eqn_arrays=idiomatic_eqn_arrays,
            include_equation_tags=include_equation_tags,
            include_smiles=include_smiles,
            include_chemistry_as_image=include_chemistry_as_image,
            include_diagram_text=include_diagram_text,
            numbers_default_to_math=numbers_default_to_math,
            math_inline_delimiters=math_inline_delimiters,
            math_display_delimiters=math_display_delimiters,
            page_ranges=page_ranges,
            enable_spell_check=enable_spell_check,
            auto_number_sections=auto_number_sections,
            remove_section_numbering=remove_section_numbering,
            preserve_section_numbering=preserve_section_numbering,
            enable_tables_fallback=enable_tables_fallback,
            fullwidth_punctuation=fullwidth_punctuation,
        )
        return ScsFile(auth=self.auth, file_id=submitted_file.file_id, request_options=self.request_options)

    @deprecated("list_scs_files is deprecated; use file_job_get(job_id).files() instead")
    def list_scs_files(
            self,
            scs_job_id: Optional[str] = None,
            filename: Optional[str] = None,
            limit: int = 100,
            paging_state: Optional[str] = None,
    ):
        """List files from files-api v1.

        Deprecated: for listing a job's files use file_job_get(job_id).files()
        instead, which targets the public GET /files/v1/jobs/{job_id}/files
        endpoint and supports a status filter.

        Args:
            scs_job_id: Filter by job ID.
            filename: Filter by filename.
            limit: Maximum number of results (default 100).
            paging_state: Optional paging state for pagination.

        Returns:
            dict: Response containing 'file_ids' list and 'next_page_token' for pagination.
        """
        logger.debug("Listing files from files-api")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/list')
        params: Dict[str, object] = {"limit": limit}
        if scs_job_id:
            params["scs_job_id"] = scs_job_id
        if filename:
            params["filename"] = filename
        if paging_state:
            params["paging_state"] = paging_state
        try:
            response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix files-api list request failed: {e}")

    @deprecated("list_scs_jobs is deprecated; use file_job_list instead")
    def list_scs_jobs(
            self,
            start: Optional[str] = None,
            end: Optional[str] = None,
            limit: int = 100,
            paging_state: Optional[str] = None,
    ):
        """List SCS jobs from files-api v1.

        Deprecated: use file_job_list instead, which targets the public
        GET /files/v1/jobs endpoint. During the deprecation window this method
        stays on the legacy GET /files/v1/scs-jobs endpoint so existing callers
        keep receiving the legacy job entries and response metadata.

        Args:
            start: Optional start date filter (ISO format).
            end: Optional end date filter (ISO format).
            limit: Maximum number of results (default 100).
            paging_state: Optional paging state for pagination.

        Returns:
            dict: Response containing 'jobs' list and optionally 'paging_state' for next page.
        """
        logger.debug("Listing jobs from files-api")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/scs-jobs')
        params: Dict[str, object] = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if paging_state:
            params["paging_state"] = paging_state
        try:
            response: requests.Response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix files-api list jobs request failed: {e}")

    @deprecated("scs_job_status is deprecated; use file_job_get(job_id).status() instead")
    def scs_job_status(self, scs_job_id: str):
        """Get the current status of an SCS job.

        Deprecated: use file_job_get(job_id).status() instead, which targets the
        public GET /files/v1/jobs/{job_id} endpoint. During the deprecation
        window this method stays on the legacy GET /files/v1/scs-jobs/status
        endpoint so existing callers keep receiving the legacy response shape.

        Args:
            scs_job_id: The job ID to get status for.

        Returns:
            JSON response containing job status information.
        """
        logger.debug(f"Getting status for SCS job {scs_job_id}")
        endpoint: str = urljoin(self.auth.files_api_url, '/files/v1/scs-jobs/status')
        params: Dict[str, str] = {'scs_job_id': scs_job_id}
        try:
            response: requests.Response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix files-api job status request failed: {e}")

    def query_usage(
            self,
            from_date: Optional[str] = None,
            to_date: Optional[str] = None,
            app_id: Optional[str] = None,
            usage_type: Optional[str] = None,
            request_args_hash: Optional[str] = None,
            timespan: Optional[str] = None,
            group_by: Optional[List[str]] = None,
            page: int = 1,
            per_page: int = 100,
    ):
        """Query API usage statistics.

        Args:
            from_date: Start date for usage query (ISO 8601 format).
            to_date: End date for usage query (ISO 8601 format).
            app_id: Filter by application ID.
            usage_type: Filter by usage type (e.g., 'image', 'pdf-page', 'strokes-session').
            request_args_hash: Filter by request args hash.
            timespan: Aggregation period ('hour', 'day', 'month', 'year').
            group_by: Fields to group by (['app_id', 'usage_type', 'request_args_hash']).
            page: Page number (1-100, default 1).
            per_page: Results per page (1-1000, default 100).

        Returns:
            dict: Response with 'ocr_usage' list containing usage records.
        """
        logger.debug("Querying usage statistics")
        endpoint = urljoin(self.auth.api_url, 'v3/ocr-usage')
        params: Dict[str, object] = {'page': page, 'per_page': per_page}
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if app_id:
            params['app_id'] = app_id
        if usage_type:
            params['usage_type'] = usage_type
        if request_args_hash:
            params['request_args_hash'] = request_args_hash
        if timespan:
            params['timespan'] = timespan
        if group_by:
            params['group_by'] = group_by
        try:
            response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix usage query failed: {e}")

    def query_ocr_results(
            self,
            from_date: Optional[str] = None,
            to_date: Optional[str] = None,
            app_id: Optional[str] = None,
            request_id: Optional[str] = None,
            pdf_id: Optional[str] = None,
            tags: Optional[List[str]] = None,
            include_null_results: bool = False,
            page: int = 1,
            per_page: int = 100,
            contains_chemistry: Optional[bool] = None,
            contains_diagram: Optional[bool] = None,
            is_handwritten: Optional[bool] = None,
            is_printed: Optional[bool] = None,
            contains_table: Optional[bool] = None,
            contains_triangle: Optional[bool] = None,
            contains_algorithm: Optional[bool] = None,
    ):
        """Query historical OCR results.

        Args:
            from_date: Start date for results query (ISO 8601 format).
            to_date: End date for results query (ISO 8601 format).
            app_id: Filter by application ID.
            request_id: Filter by image request ID.
            pdf_id: Filter by PDF ID.
            tags: Filter by tags (JSONB containment filter).
            include_null_results: Include results where result is null (default False).
            page: Page number (1-100, default 1).
            per_page: Results per page (1-1000, default 100).
            contains_chemistry: Filter by chemistry content detection.
            contains_diagram: Filter by diagram content detection.
            is_handwritten: Filter by handwritten content detection.
            is_printed: Filter by printed content detection.
            contains_table: Filter by table content detection.
            contains_triangle: Filter by triangle content detection.
            contains_algorithm: Filter by algorithm content detection.

        Returns:
            dict: Response with 'ocr_results' list.
        """
        logger.debug("Querying OCR results")
        endpoint = urljoin(self.auth.api_url, 'v3/ocr-results')
        params: Dict[str, object] = {'page': page, 'per_page': per_page}
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if app_id:
            params['app_id'] = app_id
        if request_id:
            params['request_id'] = request_id
        if pdf_id:
            params['pdf_id'] = pdf_id
        if tags:
            params['tags'] = tags
        if include_null_results:
            params['include_null_results'] = include_null_results
        if contains_chemistry is not None:
            params['contains_chemistry'] = contains_chemistry
        if contains_diagram is not None:
            params['contains_diagram'] = contains_diagram
        if is_handwritten is not None:
            params['is_handwritten'] = is_handwritten
        if is_printed is not None:
            params['is_printed'] = is_printed
        if contains_table is not None:
            params['contains_table'] = contains_table
        if contains_triangle is not None:
            params['contains_triangle'] = contains_triangle
        if contains_algorithm is not None:
            params['contains_algorithm'] = contains_algorithm
        try:
            response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix OCR results query failed: {e}")

    def query_pdf_results(
            self,
            from_date: Optional[str] = None,
            to_date: Optional[str] = None,
            app_id: Optional[str] = None,
            pdf_id: Optional[str] = None,
            page: int = 1,
            per_page: int = 100,
    ):
        """Query historical PDF results.

        Args:
            from_date: Start date for results query (ISO 8601 format).
            to_date: End date for results query (ISO 8601 format).
            app_id: Filter by application ID.
            pdf_id: Filter by PDF ID.
            page: Page number (1-1000, default 1).
            per_page: Results per page (1-100, default 100).

        Returns:
            dict: Response with 'pdfs' list.
        """
        logger.debug("Querying PDF results")
        endpoint = urljoin(self.auth.api_url, 'v3/pdf-results')
        params: Dict[str, Any] = {'page': page, 'per_page': per_page}
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if app_id:
            params['app_id'] = app_id
        if pdf_id:
            params['pdf_id'] = pdf_id
        try:
            response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix PDF results query failed: {e}")

    def query_converter_results(
            self,
            from_date: Optional[str] = None,
            to_date: Optional[str] = None,
            app_id: Optional[str] = None,
            page: int = 1,
            per_page: int = 100,
    ):
        """Query historical converter results.

        Args:
            from_date: Start date for results query (ISO 8601 format).
            to_date: End date for results query (ISO 8601 format).
            app_id: Filter by application ID.
            page: Page number (1-1000, default 1).
            per_page: Results per page (1-100, default 100).

        Returns:
            dict: Response with 'documents' list containing conversion results.
                Each document has: id, input_file, status, created_at, modified_at, request_args.
        """
        logger.debug("Querying converter results")
        endpoint = urljoin(self.auth.api_url, 'v3/converter-results')
        params: Dict[str, Any] = {'page': page, 'per_page': per_page}
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if app_id:
            params['app_id'] = app_id
        try:
            response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix converter results query failed: {e}")

    def strokes_new(
            self,
            strokes: Dict[str, List[List[int]]],
            strokes_session_id: Optional[str] = None,
    ):
        """Recognize handwritten strokes.

        Args:
            strokes: Dict with 'x' and 'y' keys, each containing list of strokes.
                Example: {"x": [[33, 34, 36], [65, 64]], "y": [[188, 190, 194], [192, 194]]}
            strokes_session_id: Optional session ID for incremental stroke submission.

        Returns:
            dict: API response with latex, text, confidence, etc.
        """
        if 'x' not in strokes or 'y' not in strokes:
            raise ValidationError("Strokes must contain 'x' and 'y' keys")
        if not strokes['x'] or not strokes['y']:
            raise ValidationError("Strokes 'x' and 'y' must be non-empty lists")
        if len(strokes['x']) != len(strokes['y']):
            raise ValidationError("Strokes 'x' and 'y' must have the same number of strokes")
        for i, (x_stroke, y_stroke) in enumerate(zip(strokes['x'], strokes['y'])):
            if len(x_stroke) != len(y_stroke):
                raise ValidationError(f"Stroke {i}: x and y must have the same number of points")
            if len(x_stroke) == 0:
                raise ValidationError(f"Stroke {i}: cannot be empty")
        endpoint = urljoin(self.auth.api_url, 'v3/strokes')
        body: Dict[str, Any] = {"strokes": {"strokes": strokes}}
        if strokes_session_id:
            body["strokes_session_id"] = strokes_session_id
        try:
            response = post(endpoint, json=body, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix strokes request failed: {e}")

    def app_token_new(
            self,
            expires: Optional[int] = None,
            include_strokes_session_id: bool = False,
            user_id: Optional[str] = None,
    ):
        """Create a new app token.

        App tokens are short-lived tokens for client-side authentication.
        They can optionally include a strokes session ID for incremental
        handwriting recognition.

        Args:
            expires: Token expiration in seconds (30-43200, default 300).
                If include_strokes_session_id is True, max is 300.
            include_strokes_session_id: If True, creates a strokes session
                and returns strokes_session_id. Max expiration becomes 300s.
            user_id: Optional user ID to associate with this token.

        Returns:
            dict: Response containing:
                - app_token: The generated token string
                - app_token_expires_at: Expiration timestamp (ms since epoch)
                - strokes_session_id: Session ID (only if include_strokes_session_id=True)

        Raises:
            MathpixClientError: If the API request fails.
        """
        logger.debug("Creating new app token")
        endpoint = urljoin(self.auth.api_url, 'v3/app-tokens')
        body: Dict[str, Any] = {}
        if expires is not None:
            body['expires'] = expires
        if include_strokes_session_id:
            body['include_strokes_session_id'] = True
        if user_id is not None:
            body['user_id'] = user_id
        try:
            response = post(endpoint, json=body, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Failed to create app token: {e}")

    def app_token_get(self, app_token: str):
        """Get information about an app token.

        Args:
            app_token: The app token to query.

        Returns:
            dict: Response containing:
                - app_token: The token string
                - app_token_expires_at: Expiration timestamp (ms since epoch)
                - app_id: Application ID
                - group_id: Group ID
                - user_id: User ID

        Raises:
            MathpixClientError: If the API request fails or token not found.
        """
        logger.debug(f"Getting app token info: {app_token[:20]}...")
        endpoint = urljoin(self.auth.api_url, f'v3/app-tokens/{app_token}')
        try:
            response = get(endpoint, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Failed to get app token: {e}")

    def app_token_delete(self, app_token: str):
        """Delete an app token.

        Args:
            app_token: The app token to delete.

        Returns:
            dict: Response containing:
                - app_token: The deleted token string
                - app_id: Application ID
                - group_id: Group ID
                - user_id: User ID

        Raises:
            MathpixClientError: If the API request fails or token not found.
        """
        logger.debug(f"Deleting app token: {app_token[:20]}...")
        endpoint = urljoin(self.auth.api_url, f'v3/app-tokens/{app_token}')
        try:
            response = requests.delete(endpoint, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Failed to delete app token: {e}")

    def batch_new(
            self,
            urls: Dict[str, Any],
            ocr_behavior: str = "latex",
            callback: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None,
            formats: Optional[List[str]] = None,
            data_options: Optional[Dict[str, Any]] = None,
            include_detected_alphabets: bool = False,
            alphabets_allowed: Optional[Dict[str, str]] = None,
            confidence_threshold: Optional[float] = None,
            confidence_rate_threshold: Optional[float] = None,
    ) -> Batch:
        """Submit multiple images for batch processing.

        Args:
            urls: Dict mapping keys to image sources. Values can be:
                - String URL: "https://example.com/image.jpg"
                - Data URL: "data:image/jpg;base64,..."
                - Object with options: {"url": "...", "formats": [...], "region": {...}}
            ocr_behavior: Processing mode - "latex" (default) or "text".
            callback: Optional callback configuration for async notification.
                Example: {"post": "https://...", "reply": {}, "body": {}, "headers": {}}
            metadata: Optional metadata dict to attach to the request.
            formats: Optional list of output formats (applies to all items unless overridden).
            data_options: Optional DataOptions dict for text mode.
            include_detected_alphabets: Return detected alphabets in results.
            alphabets_allowed: Dict specifying allowed alphabets.
            confidence_threshold: File-level confidence threshold (0-1).
            confidence_rate_threshold: Symbol-level confidence threshold (0-1).

        Returns:
            Batch: A Batch instance for tracking progress and retrieving results.

        Raises:
            ValidationError: If urls is empty or invalid.
            MathpixClientError: If the API request fails.
        """
        if not urls:
            raise ValidationError("urls dict must not be empty")
        logger.debug(f"Submitting batch with {len(urls)} images")
        endpoint = urljoin(self.auth.api_url, 'v3/batch')
        body: Dict[str, Any] = {
            "urls": urls,
            "ocr_behavior": ocr_behavior,
        }
        if callback:
            body["callback"] = callback
        if metadata:
            body["metadata"] = metadata
        if formats:
            body["formats"] = formats
        if data_options:
            body["data_options"] = data_options
        if include_detected_alphabets:
            body["include_detected_alphabets"] = include_detected_alphabets
        if alphabets_allowed:
            body["alphabets_allowed"] = alphabets_allowed
        if confidence_threshold is not None:
            body["confidence_threshold"] = confidence_threshold
        if confidence_rate_threshold is not None:
            body["confidence_rate_threshold"] = confidence_rate_threshold
        if not self.improve_mathpix:
            if "metadata" not in body:
                body["metadata"] = {}
            body["metadata"]["improve_mathpix"] = False
        try:
            response = post(endpoint, json=body, headers=self.auth.headers, **self.request_options)
            response.raise_for_status()
            result = response.json()
            batch_id = result.get('batch_id')
            if not batch_id:
                raise MathpixClientError(f"No batch_id in response: {result}")
            logger.debug(f"Batch created with ID: {batch_id}")
            return Batch(auth=self.auth, batch_id=batch_id, request_options=self.request_options)
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix batch request failed: {e}")
