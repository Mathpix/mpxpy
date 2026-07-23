"""Integration tests for the public Files API v1 client surface.

These tests make real requests. Point them at a local Files API deployment via
the MATHPIX_FILES_API_URL environment variable (or the files_api_url client
argument), the same override tests/test_scs.py uses for local docker testing.
"""
import time
import uuid
from typing import Any, Dict
import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.file import File
from mpxpy.file_job import FileJob, FileSubmission
from mpxpy.errors import FilesApiError

SAMPLE_PDF_URL: str = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
BAD_PDF_URL: str = "https://mathpix-ocr-examples.s3.amazonaws.com/does-not-exist-mpxpy-test.pdf"


@pytest.fixture
def client() -> MathpixClient:
    return MathpixClient()


def unique_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def wait_for_file_by_custom_id(job: FileJob, custom_id: str, timeout: float = 60.0) -> File:
    """Poll until a submitted item is registered in the job.

    Job submission is accept-and-defer: items are enqueued in the background,
    so a lookup immediately after submit can be a not_found miss.
    """
    deadline: float = time.monotonic() + timeout
    while True:
        try:
            return job.file_by_custom_id(custom_id)
        except FilesApiError as error:
            is_not_registered_yet: bool = error.error_id == 'not_found'
            has_time_left: bool = time.monotonic() < deadline
            can_retry: bool = is_not_registered_yet and has_time_left
            if not can_retry:
                raise
            time.sleep(1.0)


def onboarding_identities_or_skip(client: MathpixClient) -> Dict[str, Any]:
    """Fetch onboarding identities, skipping when the deployment lacks them.

    The endpoint depends on deployment configuration; deployments without it
    return a 500 internal_error.
    """
    try:
        return client.onboarding_identities()
    except FilesApiError as error:
        is_unconfigured_deployment: bool = error.http_status == 500
        if is_unconfigured_deployment:
            pytest.skip("onboarding identities are not configured on this deployment")
        raise


def test_file_new_uri_lifecycle(client: MathpixClient) -> None:
    """Submit a public URL, wait, download mmd, then delete (idempotently)."""
    file = client.file_new(
        source_uri=SAMPLE_PDF_URL,
        conversion_formats={'md': True},
    )
    assert isinstance(file, File)
    assert file.file_id
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'
    mmd_text = file.to_mmd_text()
    assert mmd_text
    # Delete, then delete again: the repeat must return the same success body.
    result = file.delete()
    assert result['status'] == 'deleted'
    repeat = file.delete()
    assert repeat['status'] == 'deleted'


def test_file_new_idempotency_key(client: MathpixClient) -> None:
    """Re-submitting with the same Idempotency-Key returns the original file_id."""
    key = unique_id('mpxpy-idem')
    first = client.file_new(source_uri=SAMPLE_PDF_URL, idempotency_key=key)
    second = client.file_new(source_uri=SAMPLE_PDF_URL, idempotency_key=key)
    assert first.file_id == second.file_id


def test_file_job_lifecycle(client: MathpixClient) -> None:
    """Submit a 2-file job with one bad URI; poll; verify the error listing and
    custom_id lookups."""
    job_id = unique_id('mpxpy-job')
    job = client.file_job_new(
        files=[
            FileSubmission(source_uri=SAMPLE_PDF_URL, custom_id='good'),
            FileSubmission(source_uri=BAD_PDF_URL, custom_id='bad'),
        ],
        job_id=job_id,
        conversion_formats={'md': True},
    )
    assert isinstance(job, FileJob)
    assert job.job_id == job_id
    assert job.file_count == 2
    assert job.wait_until_complete(timeout=300, interval=5.0)
    status = job.status()
    assert status['status'] == 'completed'
    assert status['file_count'] == 2
    assert status['files_completed'] == 1
    assert status['files_errored'] == 1
    errored = list(job.files_iter(status='error'))
    assert [f['custom_id'] for f in errored] == ['bad']
    good_file = job.file_by_custom_id('good')
    assert isinstance(good_file, File)
    assert good_file.status()['status'] == 'completed'


def test_file_job_custom_id_idempotency(client: MathpixClient) -> None:
    """Re-submitting the same (job_id, custom_id) returns the original file_id."""
    job_id = unique_id('mpxpy-idem-job')
    client.file_job_new(
        files=[{'source_uri': SAMPLE_PDF_URL, 'custom_id': 'doc-1'}],
        job_id=job_id,
    )
    first = wait_for_file_by_custom_id(client.file_job_get(job_id), 'doc-1')
    client.file_job_new(
        files=[{'source_uri': SAMPLE_PDF_URL, 'custom_id': 'doc-1'}],
        job_id=job_id,
    )
    second = wait_for_file_by_custom_id(client.file_job_get(job_id), 'doc-1')
    assert first.file_id == second.file_id


def test_file_job_list(client: MathpixClient) -> None:
    """A submitted job appears in the jobs listing."""
    job_id = unique_id('mpxpy-list-job')
    client.file_job_new(
        files=[{'source_uri': SAMPLE_PDF_URL}],
        job_id=job_id,
    )
    found = False
    paging_state = None
    for _ in range(10):
        result = client.file_job_list(limit=100, paging_state=paging_state)
        if any(job['job_id'] == job_id for job in result['jobs']):
            found = True
            break
        paging_state = result.get('next_page_token')
        if not paging_state:
            break
    assert found, f"Job {job_id} not found in the jobs listing"


def test_file_job_status_unknown_job(client: MathpixClient) -> None:
    with pytest.raises(FilesApiError):
        client.file_job_get(unique_id('mpxpy-missing')).status()


# Data sources.
# These use a dummy AWS role ARN: registration stores metadata without probing
# the grant (only GCS verifies at registration), so no real bucket is needed.

def test_onboarding_identities_shape(client: MathpixClient) -> None:
    identities = onboarding_identities_or_skip(client)
    assert 'aws' in identities
    assert 'azure' in identities
    assert 'gcp' in identities
    assert identities['aws']['external_id']
    # Idempotent: a second call returns the same external_id.
    repeat = client.onboarding_identities()
    assert repeat['aws']['external_id'] == identities['aws']['external_id']


def test_data_source_lifecycle(client: MathpixClient) -> None:
    """Register (dummy grant) -> conflict -> exist_ok -> test probe -> list -> delete."""
    external_id = onboarding_identities_or_skip(client)['aws']['external_id']
    bucket = unique_id('mpxpy-test-bucket')
    details = {
        'iam_role_arn': 'arn:aws:iam::123456789012:role/mpxpy-integration-dummy',
        'aws_external_id': external_id,
    }
    data_source = client.data_source_new(
        provider='aws',
        bucket=bucket,
        auth_method='iam_role',
        provider_specific_details=details,
        name='mpxpy integration test',
        region='us-east-1',
    )
    assert data_source.data_source_id
    try:
        # Re-registering the same (provider, bucket) conflicts...
        with pytest.raises(FilesApiError) as exc_info:
            client.data_source_new(provider='aws', bucket=bucket, auth_method='iam_role',
                                   provider_specific_details=details)
        assert exc_info.value.error_id == 'conflict'
        # ...unless exist_ok resolves to the existing id.
        existing = client.data_source_new(provider='aws', bucket=bucket, auth_method='iam_role',
                                          provider_specific_details=details, exist_ok=True)
        assert existing.data_source_id == data_source.data_source_id
        # The dummy role can't be assumed, so the probe reports failure without raising.
        probe = data_source.test()
        assert probe['result'] in ('ok', 'failed')
        assert 'checks' in probe
        # The source appears in the listing.
        listing = client.data_sources_list()
        listed_ids = [entry['data_source_id'] for entry in listing['data_sources']]
        assert data_source.data_source_id in listed_ids
    finally:
        result = data_source.delete()
        assert result['status'] == 'deleted'
    # Deleting again reports not_found.
    with pytest.raises(FilesApiError) as exc_info:
        data_source.delete()
    assert exc_info.value.error_id == 'not_found'


def test_data_source_external_id_mismatch_rejected(client: MathpixClient) -> None:
    """An aws_external_id that doesn't match the group's is a bad_request."""
    onboarding_identities_or_skip(client)  # mismatch detection needs a configured deployment
    bucket = unique_id('mpxpy-badid-bucket')
    with pytest.raises(FilesApiError) as exc_info:
        client.data_source_new(
            provider='aws',
            bucket=bucket,
            auth_method='iam_role',
            provider_specific_details={
                'iam_role_arn': 'arn:aws:iam::123456789012:role/mpxpy-integration-dummy',
                'aws_external_id': 'not-the-group-external-id',
            },
        )
    assert exc_info.value.http_status in (400, 403)
