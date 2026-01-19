import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from urllib.parse import urljoin
from mpxpy.pdf import Pdf
from mpxpy.image import Image
from mpxpy.file_batch import FileBatch
from mpxpy.conversion import Conversion
from mpxpy.files_api import FilesApiFile
from mpxpy.scs_job import ScsJob
from mpxpy.auth import Auth
from mpxpy.logger import logger, configure_logging
from mpxpy.errors import MathpixClientError, ValidationError
from mpxpy.request_handler import post, get


class MathpixClient:
    """Client for interacting with the Mathpix API.

    This class provides methods to create and manage various Mathpix resources
    such as image processing, PDF conversions, and batch operations.

    Attributes:
        auth: An Auth instance managing API credentials and endpoints.
    """
    def __init__(self, app_id: str = None, app_key: str = None, api_url: str = None, files_api_url: str = None, improve_mathpix: bool = True, request_options: dict = None):
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
        """Process an image either from a local file or remote URL.

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
        image_options = {
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
        """Uploads a PDF, document, or ebook from a local file or remote URL and optionally requests conversions.

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
            file_path: Optional[str] = None,
            url: Optional[str] = None,
            s3_uri: Optional[str] = None,
            filename: Optional[str] = None,
            scs_job_id: Optional[str] = None,
            conversion_formats: Optional[Dict[str, bool]] = None,
            conversion_options: Optional[Dict[str, Any]] = None,
            destination_s3_uri: Optional[str] = None,
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
    ) -> FilesApiFile:
        """Upload a file via files-api v1 for async processing.

        Supports three upload modes (exactly one must be provided):
        - file_path: Multipart upload from local file
        - url: Upload from HTTP URL or S3 presigned URL
        - s3_uri: Copy from S3 bucket (requires IAM role access)

        Args:
            file_path: Path to a local file to upload.
            url: URL of a remote file (HTTP/HTTPS or S3 presigned URL).
            s3_uri: S3 URI (s3://bucket/key) to copy from.
            filename: Optional filename to use (defaults to file basename).
            scs_job_id: Optional job ID to group files together.
            conversion_formats: Dict of format names to enable (e.g., {'mmd': True, 'docx': True}).
            conversion_options: Additional conversion options dict.
            destination_s3_uri: Optional S3 URI to write output files.
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
            FilesApiFile: A new FilesApiFile instance for tracking processing status.

        Raises:
            ValidationError: If not exactly one of file_path, url, or s3_uri is provided.
            FileNotFoundError: If the specified file_path does not exist.
            MathpixClientError: If the API request fails.
        """
        source_count = sum(x is not None for x in [file_path, url, s3_uri])
        if source_count != 1:
            logger.error("Invalid parameters: Exactly one of file_path, url, or s3_uri must be provided")
            raise ValidationError("Exactly one of file_path, url, or s3_uri must be provided")
        options: Dict[str, object] = {
            "conversion_formats": conversion_formats or {},
            "metadata": {
                "mpxpy": True,
                **(metadata or {})
            },
        }
        if scs_job_id:
            options["scs_job_id"] = scs_job_id
        if destination_s3_uri:
            options["destination_s3_uri"] = destination_s3_uri
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
        if conversion_options:
            options.update(conversion_options)
        if file_path:
            logger.debug(f"Creating new file via files-api: path={file_path}")
            path = Path(file_path)
            if not path.is_file():
                logger.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"File path not found: {file_path}")
            endpoint = urljoin(self.auth.files_api_url, '/files/v1')
            data = {"options_json": json.dumps(options)}
            if filename:
                data["filename"] = filename
            with path.open("rb") as f:
                files = {"file": f}
                try:
                    response = post(endpoint, data=data, files=files, headers=self.auth.headers, **self.request_options)
                    response.raise_for_status()
                    response_json = response.json()
                    file_id = response_json['file_id']
                    logger.debug(f"File upload started, file_id: {file_id}")
                    return FilesApiFile(auth=self.auth, file_id=file_id, request_options=self.request_options)
                except requests.exceptions.RequestException as e:
                    raise MathpixClientError(f"Mathpix files-api request failed: {e}")
        elif url:
            logger.debug(f"Creating new file via files-api: url={url}")
            endpoint = urljoin(self.auth.files_api_url, '/files/v1/url')
            options["url"] = url
            if filename:
                options["filename"] = filename
            try:
                response = post(endpoint, json=options, headers=self.auth.headers, **self.request_options)
                response.raise_for_status()
                response_json = response.json()
                file_id = response_json['file_id']
                logger.debug(f"File from URL started, file_id: {file_id}")
                return FilesApiFile(auth=self.auth, file_id=file_id, request_options=self.request_options)
            except requests.exceptions.RequestException as e:
                raise MathpixClientError(f"Mathpix files-api request failed: {e}")
        else:
            logger.debug(f"Creating new file via files-api: s3_uri={s3_uri}")
            endpoint = urljoin(self.auth.files_api_url, '/files/v1/s3')
            options["s3_uri"] = s3_uri
            if filename:
                options["filename"] = filename
            try:
                response = post(endpoint, json=options, headers=self.auth.headers, **self.request_options)
                response.raise_for_status()
                response_json = response.json()
                file_id = response_json['file_id']
                logger.debug(f"File from S3 started, file_id: {file_id}")
                return FilesApiFile(auth=self.auth, file_id=file_id, request_options=self.request_options)
            except requests.exceptions.RequestException as e:
                raise MathpixClientError(f"Mathpix files-api request failed: {e}")

    def list_files(
            self,
            scs_job_id: Optional[str] = None,
            filename: Optional[str] = None,
            limit: int = 100,
            paging_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files from files-api v1.

        Args:
            scs_job_id: Optional job ID to filter by.
            filename: Optional filename to filter by.
            limit: Maximum number of results (default 100).
            paging_state: Optional paging state for pagination.

        Returns:
            dict: Response containing 'files' list and optionally 'paging_state' for next page.
        """
        logger.debug("Listing files from files-api")
        endpoint = urljoin(self.auth.files_api_url, '/files/v1/list')
        params = {"limit": limit}
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

    def list_jobs(
            self,
            start: Optional[str] = None,
            end: Optional[str] = None,
            limit: int = 100,
            paging_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List SCS jobs from files-api v1.

        Args:
            start: Optional start date filter (ISO format).
            end: Optional end date filter (ISO format).
            limit: Maximum number of results (default 100).
            paging_state: Optional paging state for pagination.

        Returns:
            dict: Response containing 'jobs' list and optionally 'paging_state' for next page.
        """
        logger.debug("Listing jobs from files-api")
        endpoint = urljoin(self.auth.files_api_url, '/files/v1/scs-jobs')
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if paging_state:
            params["paging_state"] = paging_state
        try:
            response = get(endpoint, headers=self.auth.headers, params=params, **self.request_options)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise MathpixClientError(f"Mathpix files-api list jobs request failed: {e}")

    def job_status(self, scs_job_id: str) -> ScsJob:
        """Get an ScsJob instance for tracking job status.

        Args:
            scs_job_id: The job ID to track.

        Returns:
            ScsJob: An ScsJob instance for the given job ID.
        """
        return ScsJob(auth=self.auth, scs_job_id=scs_job_id, request_options=self.request_options)
