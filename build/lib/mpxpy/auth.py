import os
import pathlib
import urllib.parse
from dotenv import load_dotenv
from mpxpy.logger import logger
from mpxpy.errors import AuthenticationError, ValidationError


class Auth:
    """Authentication and configuration handler for Mathpix API.

    This class manages the authentication credentials and API endpoint
    configuration for Mathpix API requests. It can load values from
    environment variables or use explicitly provided values.

    Attributes:
        app_id: The Mathpix application ID used for authentication.
        app_key: The Mathpix application key used for authentication.
        api_url: The base URL for the Mathpix API.
        headers: Dictionary of HTTP headers to use for API requests.
    """
    def __init__(self, app_id: str = None, app_key: str = None, api_url: str = None):
        """Initialize authentication configuration.

        Loads authentication credentials from provided arguments or environment
        variables. Environment variables are loaded from a 'local.env' file
        if present.

        Args:
            app_id: Optional Mathpix application ID. If None, will use the
                MATHPIX_APP_ID environment variable.
            app_key: Optional Mathpix application key. If None, will use the
                MATHPIX_APP_KEY environment variable.
            api_url: Optional Mathpix API URL. If None, will use the
                MATHPIX_URL environment variable or default to 'https://api.mathpix.com'.

        Raises:
            AuthenticationError: If app_id or app_key cannot be resolved from arguments
                or environment variables.
            ValidationError: If provided configuration values are invalid.
        """
        self.load_config()
        self.app_id = app_id or os.getenv('MATHPIX_APP_ID')
        self.app_key = app_key or os.getenv('MATHPIX_APP_KEY')
        raw_api_url = api_url or os.getenv('MATHPIX_URL', 'https://api.mathpix.com')
        if not self.app_id:
            logger.error("Client requires an App ID")
            raise AuthenticationError("Mathpix App ID is required")
        if not self.app_key:
            logger.error("Client requires an App Key")
            raise AuthenticationError("Mathpix App Key is required")
        self.api_url = self._validate_api_url(raw_api_url)
        self.headers = {
            'app_id': self.app_id,
            'app_key': self.app_key,
        }

    def load_config(self):
        """
        Attempts to load configuration files in order of preference.

        Searches for config files in the following locations and order:
        1. ~/.mpx/config
        2. .env in current directory
        3. local.env in current directory

        Returns:
            bool: True if any config file was successfully loaded, False otherwise
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))  # Gets the directory of the current file (auth.py)
        root_dir = os.path.dirname(base_dir)
        config_locations = [
            pathlib.Path.home() / ".mpx" / "config",  # ~/.mpx/config
            pathlib.Path(root_dir) / ".env",
            pathlib.Path(root_dir) / "local.env",
        ]
        for config_path in config_locations:
            if config_path.exists():
                try:
                    logger.info(f"Loading config from {config_path}")
                    load_dotenv(config_path)
                    return True
                except Exception as e:
                    logger.warning(f"Error loading config from {config_path}: {str(e)}")
        logger.info("No config files found")
        return False

    def _validate_api_url(self, url: str) -> str:
        """Validate and normalize the API URL."""
        try:
            parsed_url = urllib.parse.urlparse(url)
            if not parsed_url.scheme:
                raise ValidationError("URL must include http:// or https:// scheme")
            if parsed_url.scheme not in ['http', 'https']:
                raise ValidationError(f"URL scheme must be http or https, got: {parsed_url.scheme}")
            if not parsed_url.netloc:
                raise ValidationError("URL must include a valid domain")
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            path = parsed_url.path.rstrip('/')
            normalized_url = f"{base_url}{path}"
            return normalized_url
        except Exception as e:
            if not isinstance(e, ValidationError):
                logger.error(f"Invalid API URL format: {url}")
                raise ValidationError(f"Invalid API URL: {str(e)}")
            raise