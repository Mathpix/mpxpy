import os
import time
from typing import Optional
from urllib.parse import urljoin
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.request_handler import get
from mpxpy.errors import FilesystemError, ValidationError, ConversionIncompleteError


class Conversion:
    """Manages a Mathpix conversion through the v3/converter endpoint.

    This class handles operations on Mathpix conversions, including checking status,
    downloading results in different formats, and waiting for conversion to complete.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        conversion_id: The unique identifier for this conversion.
        convert_to_docx: Optional boolean to automatically convert your result to docx
        convert_to_md: Optional boolean to automatically convert your result to md
        convert_to_tex_zip: Optional boolean to automatically convert your result to tex.zip
        convert_to_html: Optional boolean to automatically convert your result to html
        convert_to_pdf: Optional boolean to automatically convert your result to pdf
        convert_to_latex_pdf: Optional boolean to automatically convert your result to pdf containing LaTeX
        convert_to_md_zip: Optional boolean to automatically convert your result to md.zip
        convert_to_mmd_zip: Optional boolean to automatically convert your result to mmd.zip
        convert_to_pptx: Optional boolean to automatically convert your result to pptx
    """
    def __init__(
            self,
            auth: Auth ,
            conversion_id: str = None,
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
        """Initialize a Conversion instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            conversion_id: The unique identifier for the conversion.

        Raises:
            ValidationError: If auth is not provided or conversion_id is empty.
        """
        self.auth = auth
        if not self.auth:
            logger.error("Conversion requires an authenticated client")
            raise ValidationError("Conversion requires an authenticated client")
        self.conversion_id = conversion_id or ''
        if not self.conversion_id:
            logger.error("Conversion requires a Conversion ID")
            raise ValidationError("Conversion requires a Conversion ID")
        self.convert_to_docx = convert_to_docx
        self.convert_to_md = convert_to_md
        self.convert_to_tex_zip = convert_to_tex_zip
        self.convert_to_html = convert_to_html
        self.convert_to_pdf = convert_to_pdf
        self.convert_to_latex_pdf = convert_to_latex_pdf
        self.convert_to_md_zip = convert_to_md_zip
        self.convert_to_mmd_zip = convert_to_mmd_zip
        self.convert_to_pptx = convert_to_pptx

    def wait_until_complete(self, timeout: int=60):
        """Wait for the conversion to complete.

        Polls the conversion status until it's complete or the timeout is reached.

        Args:
            timeout: Maximum number of seconds to wait. Must be a positive, non-zero integer.

        Returns:
            bool: True if the conversion completed successfully, False if it timed out.

        Raises:
            ValidationError: If timeout is an invalid value
        """
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError("Timeout must be a positive, non-zero integer")
        logger.info(f"Waiting for conversion {self.conversion_id} to complete (timeout: {timeout}s)")
        attempt = 1
        completed = False
        while attempt < timeout and not completed:
            logger.info(f'Checking conversion status... ({attempt}/{timeout})')
            conversion_status = self.conversion_status()
            if (conversion_status['status'] == 'completed' and all(
                    format_data['status'] == 'completed' or format_data['status'] == 'error'
                    for _, format_data in conversion_status['conversion_status'].items()
            )):
                completed = True
                logger.info(f"Conversion {self.conversion_id} completed successfully")
                break
            elif conversion_status['status'] == 'error':
                break
            time.sleep(1)
            attempt += 1
        if not completed:
            logger.warning(f"Conversion {self.conversion_id} did not complete within timeout period ({timeout}s)")
        return completed

    def conversion_status(self):
        """Get the current status of the conversion.

        Returns:
            dict: JSON response containing conversion status information.
        """
        logger.info(f"Getting status for conversion {self.conversion_id}")
        endpoint = urljoin(self.auth.api_url, f'v3/converter/{self.conversion_id}')
        response = get(endpoint, headers=self.auth.headers)
        return response.json()

    def save_file(self, path: str, conversion_format: str) -> str:
        """Helper function to save the processed conversion result to a local path.

        Args:
            path: The local file path where the output will be saved
            conversion_format: The format in which the output will be saved

        Returns:
            output_path: The path of the saved Markdown file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        if path.endswith('/') or path.endswith('\\'):
            filename = f"{self.conversion_id}.{conversion_format}"
            path = os.path.join(path, filename)
        logger.info(f"Downloading output for Conversion {self.conversion_id} in format {conversion_format} to path {path}")
        endpoint = urljoin(self.auth.api_url, f'v3/converter/{self.conversion_id}.{conversion_format}')
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

    def text_result(self, conversion_format: str) -> str:
        """Helper method to download the processed conversion result as text.

        Args:
            conversion_format: Output format extension

        Returns:
            text: The result as a string (md, mmd)

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.info(f"Downloading output for conversion {self.conversion_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.api_url, f'v3/converter/{self.conversion_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        return response.text

    def bytes_result(self, conversion_format: str) -> bytes:
        """Helper method to download the processed conversion result bytes.

        Args:
            conversion_format: Output format extension

        Returns:
            bytes: The binary content of the result (docx, html, tex.zip, pdf, latex.pdf)

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        logger.info(f"Downloading output for conversion {self.conversion_id} in format: {conversion_format}")
        endpoint = urljoin(self.auth.api_url, f'v3/converter/{self.conversion_id}.{conversion_format}')
        response = get(endpoint, headers=self.auth.headers)
        if response.status_code == 404:
            raise ConversionIncompleteError("Conversion not complete")
        return response.content

    def to_docx_file(self, path: str) -> str:
        """Save the processed conversion result to a DOCX file at a local path.

        Args:
            path: The local file path where the DOCX output will be saved

        Returns:
            output_path: The path of the saved DOCX file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='docx')

    def to_docx_bytes(self) -> bytes:
        """Get the processed conversion result as DOCX bytes.

        Returns:
            bytes: The binary content of the DOCX result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='docx')

    def to_md_file(self, path: str) -> str:
        """Save the processed conversion result to a Markdown file at a local path.

        Args:
            path: The local file path where the Markdown output will be saved

        Returns:
            output_path: The path of the saved Markdown file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='md')

    def to_md_text(self) -> str:
        """Get the processed conversion result as a Markdown string.

        Returns:
            text: The text content of the Markdown result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.text_result(conversion_format='md')

    def to_mmd_file(self, path: str) -> str:
        """Save the processed conversion result to a Mathpix Markdown file at a local path.

        Args:
            path: The local file path where the Mathpix Markdown output will be saved

        Returns:
            output_path: The path of the saved Mathpix Markdown file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='mmd')

    def to_mmd_text(self) -> str:
        """Get the processed conversion result as a Mathpix Markdown string.

        Returns:
            text: The text content of the Mathpix Markdown result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.text_result(conversion_format='mmd')

    def to_tex_zip_file(self, path: str) -> str:
        """Save the processed conversion result to a tex.zip file at a local path.

        Args:
            path: The local file path where the tex.zip output will be saved

        Returns:
            output_path: The path of the saved tex.zip file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='tex.zip')

    def to_tex_zip_bytes(self) -> bytes:
        """Get the processed conversion result in tex.zip format as bytes.

        Returns:
            bytes: The binary content of the tex.zip result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='tex.zip')

    def to_html_file(self, path: str) -> str:
        """Save the processed conversion result to a HTML file at a local path.

        Args:
            path: The local file path where the HTML output will be saved

        Returns:
            output_path: The path of the saved HTML file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='html')

    def to_html_bytes(self) -> bytes:
        """Get the processed conversion result in HTML format as bytes.

        Returns:
            bytes: The binary content of the HTML result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='html')

    def to_pdf_file(self, path: str) -> str:
        """Save the processed conversion result to a PDF file at a local path.

        Args:
            path: The local file path where the PDF output will be saved

        Returns:
            output_path: The path of the saved PDF file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='pdf')

    def to_pdf_bytes(self) -> bytes:
        """Get the processed conversion result in PDF format as bytes.

        Returns:
            bytes: The binary content of the PDF result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='pdf')

    def to_latex_pdf_file(self, path: str) -> str:
        """Save the processed conversion result to a PDF file containing LaTeX at a local path.

        Args:
            path: The local file path where the PDF output will be saved

        Returns:
            output_path: The path of the saved PDF file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='latex.pdf')

    def to_latex_pdf_bytes(self) -> bytes:
        """Get the processed conversion result in PDF format as bytes (with LaTeX).

        Returns:
            bytes: The binary content of the PDF result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='latex.pdf')

    def to_md_zip_file(self, path: str) -> str:
        """Save the processed conversion result to a ZIP file containing markdown output and any embedded images.

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
        """Get the processed conversion result in ZIPPED markdown format as bytes.

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
        """Save the processed conversion result to a ZIP file containing Mathpix Markdown output and any embedded images.

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
        """Get the processed conversion result in ZIPPED Mathpix Markdown format as bytes.

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
        """Save the processed conversion result to a PPTX file.

        Args:
            path: The local file path where the PPTX output will be saved

        Returns:
            output_path: The path of the saved PPTX file

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.save_file(path=path, conversion_format='pptx')

    def to_pptx_bytes(self) -> bytes:
        """Get the processed conversion result in PPTX format as bytes.

        Returns:
            bytes: The binary content of the PPTX result

        Raises:
            ConversionIncompleteError: If the conversion is not complete
        """
        return self.bytes_result(conversion_format='pptx')