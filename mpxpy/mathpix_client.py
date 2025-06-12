import json
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import urljoin
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
    def __init__(self, app_id: str = None, app_key: str = None, api_url: str = None, improve_mathpix: bool = True):
        """Initialize a new Mathpix client.

        Args:
            app_id: Optional Mathpix application ID. If None, will use environment variable.
            app_key: Optional Mathpix application key. If None, will use environment variable.
            api_url: Optional Mathpix API URL. If None, will use environment variable or default to the production API.
            improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true.
        """
        logger.info("Initializing MathpixClient")
        self.auth = Auth(app_id=app_id, app_key=app_key, api_url=api_url)
        self.improve_mathpix = improve_mathpix
        logger.info(f"MathpixClient initialized with API URL: {self.auth.api_url}")

    def image_new(
            self,
            file_path: Optional[str] = None,
            url: Optional[str] = None,
            improve_mathpix: Optional[bool] = True,
    ):
        """Process an image either from a local file or remote URL.

        Args:
            file_path: Path to a local image file.
            url: URL of a remote image.
            improve_mathpix: Optional boolean to enable Mathpix to retain user output.

        Returns:
            Image: A new Image instance.

        Raises:
            ValueError: If exactly one of file_path and url are not provided.
        """
        if (file_path is None and url is None) or (file_path is not None and url is not None):
            logger.error("Invalid parameters: Exactly one of file_path or url must be provided")
            raise ValidationError("Exactly one of file_path or url must be provided")
        if not self.improve_mathpix:
            logger.info('improve_mathpix set to False on the client')
            improve_mathpix = False
        elif not improve_mathpix:
            improve_mathpix = False
        if file_path:
            logger.info(f"Creating new Image: path={file_path}")
            return Image(auth=self.auth, file_path=file_path, improve_mathpix=improve_mathpix)
        else:
            logger.info(f"Creating new Image: url={url}")
            return Image(auth=self.auth, url=url, improve_mathpix=improve_mathpix)

    def pdf_new(
            self,
            file_path: Optional[str] = None,
            url: Optional[str] = None,
            convert_to_docx: Optional[bool] = False,
            convert_to_md: Optional[bool] = False,
            convert_to_mmd: Optional[bool] = False,
            convert_to_tex_zip: Optional[bool] = False,
            convert_to_html: Optional[bool] = False,
            convert_to_pdf: Optional[bool] = False,
            convert_to_md_zip: Optional[bool] = False,
            convert_to_mmd_zip: Optional[bool] = False,
            convert_to_pptx: Optional[bool] = False,
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
            convert_to_docx: Optional boolean to automatically convert your result to docx
            convert_to_md: Optional boolean to automatically convert your result to md
            convert_to_mmd: Optional boolean to automatically convert your result to mmd
            convert_to_tex_zip: Optional boolean to automatically convert your result to tex.zip
            convert_to_html: Optional boolean to automatically convert your result to html
            convert_to_pdf: Optional boolean to automatically convert your result to pdf
            convert_to_md_zip: Optional boolean to automatically convert your result to md.zip
            convert_to_mmd_zip: Optional boolean to automatically convert your result to mmd.zip
            convert_to_pptx: Optional boolean to automatically convert your result to pptx
            improve_mathpix: Optional boolean to enable Mathpix to retain user output. Default is true
            file_batch_id: Optional batch ID to associate this file with. (Not yet enabled)
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
            logger.info('improve_mathpix set to False on the client')
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
            },
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
        if (convert_to_mmd_zip or convert_to_md_zip) and self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("md.zip and mmd.zip features not available in production API")
            raise NotImplementedError(
                "md.zip and mmd.zip features are not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        if convert_to_md_zip:
            options["conversion_formats"]['md.zip'] = True
        if convert_to_mmd_zip:
            options["conversion_formats"]['mmd.zip'] = True
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
                        convert_to_docx=convert_to_docx,
                        convert_to_md=convert_to_md,
                        convert_to_mmd=convert_to_mmd,
                        convert_to_tex_zip=convert_to_tex_zip,
                        convert_to_html=convert_to_html,
                        convert_to_pdf=convert_to_pdf,
                        convert_to_md_zip=convert_to_md_zip,
                        convert_to_mmd_zip=convert_to_mmd_zip,
                        convert_to_pptx=convert_to_pptx,
                        improve_mathpix=improve_mathpix,
                        file_batch_id=file_batch_id,
                        webhook_url=webhook_url,
                        mathpix_webhook_secret=mathpix_webhook_secret,
                        webhook_payload=webhook_payload,
                        webhook_enabled_events=webhook_enabled_events,
                    )
                except requests.exceptions.RequestException as e:
                    logger.error(f"PDF upload failed: {e}")
                    raise MathpixClientError(f"Mathpix PDF request failed: {e}")
        else:
            logger.info(f"Creating new PDF: url={url}")
            options["url"] = url
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
                        improve_mathpix=improve_mathpix,
                        file_batch_id=file_batch_id,
                        webhook_url=webhook_url,
                        mathpix_webhook_secret=mathpix_webhook_secret,
                        webhook_payload=webhook_payload,
                        webhook_enabled_events=webhook_enabled_events,
                    )
            except requests.exceptions.RequestException as e:
                logger.error(f"URL processing failed: {e}")
                raise MathpixClientError(f"Mathpix PDF request failed: {e}")

    def file_batch_new(self):
        """Creates a new file batch ID that can be used to group multiple file uploads.

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
        endpoint = urljoin(self.auth.api_url, 'v3/file-batches')
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

        Returns:
            Conversion: A new Conversion instance.

        Raises:
            MathpixClientError: If the API request fails.
        """
        logger.info(f"Starting new MMD conversions to")
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
        if (convert_to_mmd_zip or convert_to_md_zip) and self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("md.zip and mmd.zip features not available in production API")
            raise NotImplementedError(
                "md.zip and mmd.zip features are not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        if convert_to_md_zip:
            options["formats"]['md.zip'] = True
        if convert_to_mmd_zip:
            options["formats"]['mmd.zip'] = True
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
            logger.info(f"Conversion created, ID: {conversion_id}")
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
                convert_to_pptx=convert_to_pptx
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Conversion request failed: {e}")
            raise MathpixClientError(f"Conversion request failed: {e}")
