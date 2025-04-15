import os
from dotenv import load_dotenv
from mathpix.logger import logger

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
            ValueError: If app_id or app_key cannot be resolved from arguments
                or environment variables.
        """
        possible_paths = [
            'local.env',
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local.env')
        ]
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(".env file found")
                load_dotenv(path)
                break
        self.app_id = app_id or os.getenv('MATHPIX_APP_ID')
        self.app_key = app_key or os.getenv('MATHPIX_APP_KEY')
        self.api_url = api_url or os.getenv('MATHPIX_URL', 'https://api.mathpix.com')
        if not self.app_id:
            logger.error("Client requires an App ID")
            raise ValueError("Client requires an App ID")
        if not self.app_key:
            logger.error("Client requires an App Key")
            raise ValueError("Client requires an App Key")
        self.headers = {
            'app_id': self.app_id,
            'app_key': self.app_key,
        }