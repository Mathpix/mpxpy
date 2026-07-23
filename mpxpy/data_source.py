from typing import Optional, Dict, Any, Tuple
from urllib.parse import urljoin, quote
import requests
from mpxpy.auth import Auth
from mpxpy.logger import logger
from mpxpy.request_handler import post, delete
from mpxpy.errors import ValidationError, error_from_response

PROVIDERS: Tuple[str, ...] = ('aws', 'azure', 'gcp')

AUTH_METHODS_BY_PROVIDER: Dict[str, Tuple[str, ...]] = {
    'aws': ('iam_role', 'access_key'),
    'azure': ('azure_ad',),
    'gcp': ('service_account',),
}


class DataSource:
    """Manages a registered Files API data source.

    A data source is a registered pointer from your Mathpix account to a bucket
    or container you own, with an attached access grant. Once registered, the
    bucket can be referenced via source_uri (read) or destination_uri (write)
    on Files API submissions.

    Attributes:
        auth: An Auth instance with Mathpix credentials.
        data_source_id: The unique identifier for this data source.
    """
    def __init__(
            self,
            auth: Auth,
            data_source_id: Optional[str] = None,
            request_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a DataSource instance.

        Args:
            auth: Auth instance containing Mathpix API credentials.
            data_source_id: The unique identifier for the data source.
            request_options: Optional dict of kwargs to pass to requests.

        Raises:
            ValidationError: If auth is not provided or data_source_id is empty.
        """
        self.auth: Auth = auth
        has_auth: bool = self.auth is not None
        if not has_auth:
            logger.error("DataSource requires an authenticated client")
            raise ValidationError("DataSource requires an authenticated client")
        self.data_source_id: str = data_source_id or ''
        has_data_source_id: bool = bool(self.data_source_id)
        if not has_data_source_id:
            logger.error("DataSource requires a Data Source ID")
            raise ValidationError("DataSource requires a Data Source ID")
        self.request_options: Dict[str, Any] = request_options or {}

    def test(self) -> Dict[str, Any]:
        """Verify Mathpix can reach the bucket using the registered credentials.

        Performs a read probe (and, where applicable, a write probe). The API
        returns HTTP 200 for both outcomes; this method returns the probe body
        as-is and does NOT raise on a failed probe — the message is diagnostic
        data. This is the canonical check after any customer-side IAM change.

        Returns:
            dict: Response containing 'result' ('ok' or 'failed'), 'checks'
                (per-probe booleans, e.g. {'read': True, 'write': False}), and
                'message' (diagnostic detail for failures).

        Raises:
            FilesApiError: If the request itself fails (e.g. 'not_found' for an
                unknown data source id).
        """
        logger.debug(f"Testing data source {self.data_source_id}")
        endpoint: str = urljoin(
            self.auth.files_api_url,
            f'/files/v1/data-sources/{quote(self.data_source_id, safe="")}/test'
        )
        response: requests.Response = post(endpoint, headers=self.auth.headers, **self.request_options)
        has_failed: bool = not response.ok
        if has_failed:
            raise error_from_response(response)
        return response.json()

    def delete(self) -> Dict[str, Any]:
        """Permanently remove the data source.

        Subsequent submissions that reference the bucket return
        'data_source_not_found'. In-flight jobs that already started against
        this data source continue to completion using their cached credentials.
        To fully revoke access, also remove the cloud-side grant (IAM role,
        Azure role assignment, or GCS service-account binding).

        Returns:
            dict: Response containing 'data_source_id' and 'status': 'deleted'.

        Raises:
            FilesApiError: If no data source has this id or it was already
                deleted ('not_found'), or it belongs to a different group
                ('forbidden').
        """
        logger.debug(f"Deleting data source {self.data_source_id}")
        endpoint: str = urljoin(
            self.auth.files_api_url,
            f'/files/v1/data-sources/{quote(self.data_source_id, safe="")}'
        )
        response: requests.Response = delete(endpoint, headers=self.auth.headers, **self.request_options)
        has_failed: bool = not response.ok
        if has_failed:
            raise error_from_response(response)
        return response.json()
