import json
import os
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
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
    """
    def __init__(
            self,
            auth: Auth,
            pdf_id: str = None,
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
            improve_mathpix: Optional[bool] = False,
            file_batch_id: Optional[str] = None,
            webhook_url: Optional[str] = None,
            mathpix_webhook_secret: Optional[str] = None,
            webhook_payload: Optional[Dict[str, Any]] = None,
            webhook_enabled_events: Optional[List[str]] = None,
    ):
        """Initialize a PDF instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            pdf_id: The unique identifier for the PDF.
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
        self.url = url
        self.convert_to_docx=convert_to_docx
        self.convert_to_md=convert_to_md
        self.convert_to_mmd=convert_to_mmd
        self.convert_to_tex_zip=convert_to_tex_zip
        self.convert_to_html=convert_to_html
        self.convert_to_pdf=convert_to_pdf
        self.convert_to_md_zip = convert_to_md_zip
        self.convert_to_mmd_zip = convert_to_mmd_zip
        self.convert_to_pptx = convert_to_pptx
        self.improve_mathpix=improve_mathpix
        self.file_batch_id = file_batch_id
        self.webhook_url = webhook_url
        self.mathpix_webhook_secret = mathpix_webhook_secret
        self.webhook_payload = webhook_payload
        self.webhook_enabled_events = webhook_enabled_events

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
        automatic_conversion_requested = self.convert_to_docx or self.convert_to_md or self.convert_to_mmd or self.convert_to_tex_zip or self.convert_to_html or self.convert_to_pdf
        if pdf_completed and automatic_conversion_requested and not ignore_conversions:
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
        result = pdf_completed and (conversion_completed or ignore_conversions or not automatic_conversion_requested)
        logger.info(f"Wait completed for PDF {self.pdf_id}, result: {result}")
        return result

    def pdf_status(self):
        """Get the current status of the PDF processing.

        Returns:
            dict: JSON response containing PDF processing status information.
        """
        logger.info(f"Getting status for PDF {self.pdf_id}")
        endpoint = urljoin(self.auth.api_url, f'v3/pdf/{self.pdf_id}')
        response = get(endpoint, headers=self.auth.headers)
        return response.json()

    def pdf_conversion_status(self):
        """Get the current status of the PDF conversions.

        Returns:
            dict: JSON response containing conversion status information.
        """
        logger.info(f"Getting conversion status for PDF {self.pdf_id}")
        endpoint = urljoin(self.auth.api_url, f'v3/converter/{self.pdf_id}')
        response = get(endpoint, headers=self.auth.headers)
        return response.json()

    def save_file(self, path: str, conversion_format: str) -> str:
        """Helper function to save the processed PDF result to a local path.

        Args:
            path: The local file path where the output will be saved
            conversion_format: The format in which the output will be saved

        Returns:
            output_path: The path of the saved Markdown file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if path.endswith('/') or path.endswith('\\'):
            filename = f"{self.pdf_id}.{conversion_format}"
            path = os.path.join(path, filename)
        logger.info(f"Downloading output for PDF {self.pdf_id} in format {conversion_format} to path {path}")
        endpoint = urljoin(self.auth.api_url, f'v3/pdf/{self.pdf_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception:
            raise FilesystemError('Failed to save file to system')
        logger.info(f"File saved successfully to {path}")
        return path

    def json_result(self, conversion_format: str) -> Dict:
        """Helper method to download the processed PDF result JSON.

        Args:
            conversion_format: Output format extension

        Returns:
            text: The result as a string (lines.json, lines.mmd.json)

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.api_url, f'v3/pdf/{self.pdf_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        return json.loads(response.text)

    def text_result(self, conversion_format: str) -> str:
        """Helper method to download the processed PDF result as text.

        Args:
            conversion_format: Output format extension

        Returns:
            text: The result as a string (md, mmd)

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.api_url, f'v3/pdf/{self.pdf_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        return response.text

    def bytes_result(self, conversion_format: str) -> bytes:
        """Helper method to download the processed PDF result bytes.

        Args:
            conversion_format: Output format extension

        Returns:
            bytes: The binary content of the result (docx, html, tex.zip, pdf)

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.info(f"Downloading output for PDF {self.pdf_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.api_url, f'v3/pdf/{self.pdf_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        return response.content

    def to_docx_file(self, path: str) -> str:
        """Save the processed PDF result to a DOCX file at a local path.

        Args:
            path: The local file path where the DOCX output will be saved

        Returns:
            output_path: The path of the saved DOCX file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='docx')

    def to_docx_bytes(self) -> bytes:
        """Get the processed PDF result as DOCX bytes.

        Returns:
            bytes: The binary content of the DOCX result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='docx')

    def to_md_file(self, path: str) -> str:
        """Save the processed PDF result to a Markdown file at a local path.

        Args:
            path: The local file path where the Markdown output will be saved

        Returns:
            output_path: The path of the saved Markdown file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='md')

    def to_md_text(self) -> str:
        """Get the processed PDF result as a Markdown string.

        Returns:
            text: The text content of the Markdown result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.text_result(conversion_format='md')

    def to_mmd_file(self, path: str) -> str:
        """Save the processed PDF result to a Mathpix Markdown file at a local path.

        Args:
            path: The local file path where the Mathpix Markdown output will be saved

        Returns:
            output_path: The path of the saved Mathpix Markdown file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='mmd')

    def to_mmd_text(self) -> str:
        """Get the processed PDF result as a Mathpix Markdown string.

        Returns:
            text: The text content of the Mathpix Markdown result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.text_result(conversion_format='mmd')

    def to_tex_zip_file(self, path: str) -> str:
        """Save the processed PDF result to a tex.zip file at a local path.

        Args:
            path: The local file path where the tex.zip output will be saved

        Returns:
            output_path: The path of the saved tex.zip file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='tex.zip')

    def to_tex_zip_bytes(self) -> bytes:
        """Get the processed PDF result in tex.zip format as bytes.

        Returns:
            bytes: The binary content of the tex.zip result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='tex.zip')

    def to_html_file(self, path: str) -> str:
        """Save the processed PDF result to a HTML file at a local path.

        Args:
            path: The local file path where the HTML output will be saved

        Returns:
            output_path: The path of the saved HTML file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='html')

    def to_html_bytes(self) -> bytes:
        """Get the processed PDF result in HTML format as bytes.

        Returns:
            bytes: The binary content of the HTML result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='html')

    def to_pdf_file(self, path: str) -> str:
        """Save the processed PDF result to a PDF file at a local path.

        Args:
            path: The local file path where the PDF output will be saved

        Returns:
            output_path: The path of the saved PDF file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='pdf')

    def to_pdf_bytes(self) -> bytes:
        """Get the processed PDF result in PDF format as bytes.

        Returns:
            bytes: The binary content of the PDF result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='pdf')

    def to_lines_json_file(self, path: str) -> str:
        """Save the processed PDF line-by-line result to a JSON file at a local path.

        Args:
            path: The local file path where the JSON output will be saved

        Returns:
            output_path: The path of the saved JSON file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='lines.json')

    def to_lines_json(self) -> Dict:
        """Get the processed PDF result in JSON format.

        Returns:
            json: Line-by-line results in JSON format

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.json_result(conversion_format='lines.json')

    def to_lines_mmd_json_file(self, path: str) -> str:
        """Save the processed PDF line-by-line result, including Mathpix Markdown, to a JSON file at a local path.

        Args:
            path: The local file path where the JSON output will be saved

        Returns:
            output_path: The path of the saved JSON file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='lines.mmd.json')

    def to_lines_mmd_json(self) -> Dict:
        """Get the processed PDF result in JSON format with text in Mathpix Markdown.

        Returns:
            json: Line-by-line results in JSON format with text in Mathpix Markdown

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.json_result(conversion_format='lines.mmd.json')

    def to_md_zip_file(self, path: str) -> str:
        """Save the processed PDF result to a ZIP file containing markdown output and any embedded images.

        Args:
            path: The local file path where the ZIP output will be saved

        Returns:
            output_path: The path of the saved ZIP file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("md.zip feature not available in production API")
            raise NotImplementedError(
                "md.zip feature is not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        return self.save_file(path=path, conversion_format='md.zip')

    def to_md_zip_bytes(self) -> bytes:
        """Get the processed PDF result in ZIPPED markdown format as bytes.

        Returns:
            bytes: The binary content of the ZIP result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("md.zip feature not available in production API")
            raise NotImplementedError(
                "md.zip feature is not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        return self.bytes_result(conversion_format='md.zip')

    def to_mmd_zip_file(self, path: str) -> str:
        """Save the processed PDF result to a ZIP file containing Mathpix Markdown output and any embedded images.

        Args:
            path: The local file path where the ZIP output will be saved

        Returns:
            output_path: The path of the saved ZIP file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("mmd.zip feature not available in production API")
            raise NotImplementedError(
                "mmd.zip feature is not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        return self.save_file(path=path, conversion_format='mmd.zip')

    def to_mmd_zip_bytes(self) -> bytes:
        """Get the processed PDF result in ZIPPED Mathpix Markdown format as bytes.

        Returns:
            bytes: The binary content of the ZIP result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if self.auth.api_url == 'https://api.mathpix.com':
            logger.warning("mmd.zip feature not available in production API")
            raise NotImplementedError(
                "mmd.zip feature is not yet available in the production API. "
                "This feature will be enabled in a future release."
            )
        return self.bytes_result(conversion_format='mmd.zip')

    def to_pptx_file(self, path: str) -> str:
        """Save the processed PDF result to a PPTX file.

        Args:
            path: The local file path where the PPTX output will be saved

        Returns:
            output_path: The path of the saved PPTX file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='pptx')

    def to_pptx_bytes(self) -> bytes:
        """Get the processed PDF result in PPTX format as bytes.

        Returns:
            bytes: The binary content of the PPTX result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='pptx')