import requests
from mpxpy.errors import MathpixClientError
from mpxpy.logger import logger


def make_request(method, url, **kwargs):
    """
    Make an HTTP request with standardized error handling.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: The URL to request
        **kwargs: Additional arguments to pass to requests

    Returns:
        requests.Response object

    Raises:
        MathpixClientError: For any request-related failures
    """
    try:
        response = requests.request(method, url, **kwargs, verify=False)
        return response
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(error_msg)
        raise MathpixClientError(error_msg)
    except requests.exceptions.Timeout as e:
        error_msg = f"Request timed out: {str(e)}"
        logger.error(error_msg)
        raise MathpixClientError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(error_msg)
        raise MathpixClientError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        raise MathpixClientError(error_msg)


def get(url, **kwargs):
    return make_request('GET', url, **kwargs)


def post(url, **kwargs):
    return make_request('POST', url, **kwargs)


def put(url, **kwargs):
    return make_request('PUT', url, **kwargs)


def delete(url, **kwargs):
    return make_request('DELETE', url, **kwargs)