"""Unit tests for the public Files API v1 client surface.

These tests mock the request layer; no network access is required.
"""
import json
import logging
from typing import Any, Dict, Iterator, Optional
from unittest.mock import patch
import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.file import File
from mpxpy.file_job import FileJob, FileSubmission
from mpxpy.data_source import DataSource
from mpxpy.scs_file import ScsFile
from mpxpy.errors import (
    ValidationError,
    ConversionIncompleteError,
    MathpixClientError,
    FilesApiError,
)


class FakeResponse:
    def __init__(
            self,
            status_code: int = 200,
            json_body: Optional[Dict[str, Any]] = None,
            content: bytes = b'',
            text: str = '',
    ) -> None:
        self.status_code: int = status_code
        self._json_body: Optional[Dict[str, Any]] = json_body
        self.content: bytes = content
        self.text: str = text

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self) -> Dict[str, Any]:
        has_json_body: bool = self._json_body is not None
        if not has_json_body:
            raise ValueError("No JSON body")
        return self._json_body or {}

    def raise_for_status(self) -> None:
        has_failed: bool = not self.ok
        if has_failed:
            import requests
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        yield self.content


@pytest.fixture
def client() -> MathpixClient:
    return MathpixClient(app_id='test-app', app_key='test-key')


# file_new

def test_file_new_uri_request_shape(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'abc-123'})
        file = client.file_new(
            source_uri='s3://bucket/doc.pdf',
            job_id='job-1',
            custom_id='doc-1',
            conversion_formats={'docx': True},
            destination_uri='s3://bucket/outputs/doc-1/',
            page_ranges='1-5',
        )
    assert isinstance(file, File)
    assert file.file_id == 'abc-123'
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1/uri')
    body = kwargs['json']
    assert body['source_uri'] == 's3://bucket/doc.pdf'
    assert body['job_id'] == 'job-1'
    assert body['custom_id'] == 'doc-1'
    assert body['conversion_formats'] == {'docx': True}
    assert body['destination_uri'] == 's3://bucket/outputs/doc-1/'
    assert body['page_ranges'] == '1-5'
    assert 'metadata' not in body


def test_requests_carry_mpxpy_user_agent(client: MathpixClient) -> None:
    assert client.auth.headers['User-Agent'].startswith('mpxpy/')
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'abc-123'})
        client.file_new(source_uri='https://example.com/doc.pdf')
    _, kwargs = mock_post.call_args
    assert kwargs['headers']['User-Agent'].startswith('mpxpy/')


def test_file_new_sends_idempotency_key_header(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'abc-123'})
        client.file_new(source_uri='https://example.com/doc.pdf', idempotency_key='retry-key-1')
    _, kwargs = mock_post.call_args
    assert kwargs['headers']['Idempotency-Key'] == 'retry-key-1'
    assert kwargs['headers']['app_key'] == 'test-key'


def test_file_new_requires_source_uri(client: MathpixClient) -> None:
    with pytest.raises(ValidationError):
        client.file_new(source_uri='')


def test_file_new_custom_id_requires_job_id(client: MathpixClient) -> None:
    with pytest.raises(ValidationError):
        client.file_new(source_uri='s3://b/k.pdf', custom_id='doc-1')


def test_file_new_requires_exactly_one_source(client: MathpixClient) -> None:
    with pytest.raises(ValidationError):
        client.file_new()
    with pytest.raises(ValidationError):
        client.file_new(source_uri='s3://b/k.pdf', file_path='/tmp/doc.pdf')


def test_file_new_local_upload_multipart(client: MathpixClient, tmp_path) -> None:
    doc = tmp_path / 'doc.pdf'
    doc.write_bytes(b'%PDF-1.4 test')
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'f-local'})
        file = client.file_new(
            file_path=str(doc),
            job_id='job-1',
            filename='doc.pdf',
            destination_uri='s3://bucket/out/',
            s3_region='us-east-1',
            include_page_info=True,
        )
    assert isinstance(file, File)
    assert file.file_id == 'f-local'
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1')
    assert not args[0].endswith('/files/v1/uri')
    # The multipart endpoint uses the legacy field names
    options = json.loads(kwargs['data']['options_json'])
    assert options['scs_job_id'] == 'job-1'
    assert options['destination_s3_uri'] == 's3://bucket/out/'
    assert options['s3_region'] == 'us-east-1'
    assert options['include_page_info'] is True
    assert kwargs['data']['filename'] == 'doc.pdf'


def test_file_new_local_upload_forwards_custom_id_and_idempotency_key(client: MathpixClient, tmp_path) -> None:
    # The multipart endpoint accepts custom_id as a form field and
    # Idempotency-Key as a header, same as the URI transport.
    doc = tmp_path / 'doc.pdf'
    doc.write_bytes(b'%PDF-1.4 test')
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'f-local'})
        client.file_new(
            file_path=str(doc),
            job_id='job-1',
            custom_id='doc-1',
            idempotency_key='retry-key-1',
        )
    _, kwargs = mock_post.call_args
    assert kwargs['data']['custom_id'] == 'doc-1'
    assert kwargs['data']['scs_job_id'] == 'job-1'
    assert kwargs['headers']['Idempotency-Key'] == 'retry-key-1'


def test_file_new_local_upload_custom_id_requires_job_id(client: MathpixClient, tmp_path) -> None:
    doc = tmp_path / 'doc.pdf'
    doc.write_bytes(b'%PDF-1.4 test')
    with pytest.raises(ValidationError):
        client.file_new(file_path=str(doc), custom_id='doc-1')


def test_file_new_raises_files_api_error(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(
            status_code=404,
            json_body={'error': 'data_source_not_found',
                       'error_info': {'id': 'data_source_not_found',
                                      'message': 'No data source registered for source'}},
        )
        with pytest.raises(FilesApiError) as exc_info:
            client.file_new(source_uri='s3://unregistered/doc.pdf')
    assert exc_info.value.error_id == 'data_source_not_found'
    assert exc_info.value.http_status == 404


def test_file_new_does_not_log_signed_uri_credentials(client: MathpixClient, caplog) -> None:
    # Signed URLs carry bearer credentials in their query strings; logs must
    # only ever contain the redacted scheme/host.
    signed_uri = 'https://bucket.s3.amazonaws.com/doc.pdf?X-Amz-Credential=AKIAEXAMPLE&X-Amz-Signature=sigvalue'
    with caplog.at_level(logging.DEBUG, logger='mathpix'):
        with patch('mpxpy.mathpix_client.post') as mock_post:
            mock_post.return_value = FakeResponse(json_body={'file_id': 'abc-123'})
            client.file_new(source_uri=signed_uri)
    assert 'X-Amz-Signature' not in caplog.text
    assert 'sigvalue' not in caplog.text
    assert 'AKIAEXAMPLE' not in caplog.text


def test_file_new_non_envelope_error_is_client_error(client: MathpixClient) -> None:
    # A failure without a Files API error body (e.g. an HTML 502 from a proxy)
    # must not be dressed up as a FilesApiError.
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(status_code=502, text='<html>Bad Gateway</html>')
        with pytest.raises(MathpixClientError) as exc_info:
            client.file_new(source_uri='s3://bucket/doc.pdf')
    assert not isinstance(exc_info.value, FilesApiError)


def test_file_new_metadata_and_optional_fields_forwarded(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'abc-123'})
        client.file_new(
            source_uri='s3://bucket/doc.pdf',
            filename='doc.pdf',
            s3_region='us-east-1',
            include_page_info=True,
            metadata={'batch': 'july'},
        )
    _, kwargs = mock_post.call_args
    body = kwargs['json']
    assert body['filename'] == 'doc.pdf'
    assert body['s3_region'] == 'us-east-1'
    assert body['include_page_info'] is True
    assert body['metadata'] == {'batch': 'july'}


def test_file_new_rejects_reserved_extra_options(client: MathpixClient) -> None:
    for reserved_key in ('source_uri', 'job_id', 'custom_id', 'metadata'):
        with pytest.raises(ValidationError):
            client.file_new(
                source_uri='s3://bucket/doc.pdf',
                extra_options={reserved_key: 'injected'},
            )


# file_job_new

def test_file_job_new_request_shape(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'job_id': 'job-1', 'file_count': 2})
        job = client.file_job_new(
            files=[
                FileSubmission(source_uri='s3://bucket/a.pdf', custom_id='a'),
                {'source_uri': 'https://example.com/b.pdf', 'custom_id': 'b'},
            ],
            job_id='job-1',
            conversion_formats={'md': True},
        )
    assert isinstance(job, FileJob)
    assert job.job_id == 'job-1'
    assert job.file_count == 2
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1/jobs')
    body = kwargs['json']
    assert body['job_id'] == 'job-1'
    assert body['conversion_formats'] == {'md': True}
    assert body['files'] == [
        {'source_uri': 's3://bucket/a.pdf', 'custom_id': 'a'},
        {'source_uri': 'https://example.com/b.pdf', 'custom_id': 'b'},
    ]


def test_file_job_new_validation(client: MathpixClient) -> None:
    with pytest.raises(ValidationError):
        client.file_job_new(files=[])
    # custom_id without job_id
    with pytest.raises(ValidationError):
        client.file_job_new(files=[{'source_uri': 's3://b/k', 'custom_id': 'a'}])
    # duplicate custom_id within batch
    with pytest.raises(ValidationError):
        client.file_job_new(
            files=[{'source_uri': 's1', 'custom_id': 'a'}, {'source_uri': 's2', 'custom_id': 'a'}],
            job_id='j',
        )
    # missing source_uri
    with pytest.raises(ValidationError):
        client.file_job_new(files=[{'filename': 'x.pdf'}])


def test_file_job_new_rejects_reserved_extra_options(client: MathpixClient) -> None:
    for reserved_key in ('files', 'job_id', 'metadata'):
        with pytest.raises(ValidationError):
            client.file_job_new(
                files=[{'source_uri': 's3://bucket/a.pdf'}],
                extra_options={reserved_key: 'injected'},
            )


def test_file_job_new_idempotency_key_header(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'job_id': 'derived-1', 'file_count': 1})
        job = client.file_job_new(
            files=[{'source_uri': 'https://example.com/a.pdf'}],
            idempotency_key='batch-key-1',
        )
    assert job.job_id == 'derived-1'
    _, kwargs = mock_post.call_args
    assert kwargs['headers']['Idempotency-Key'] == 'batch-key-1'


# file_job_list

def test_file_job_list_params(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body={'jobs': [], 'next_page_token': None})
        result = client.file_job_list(start='2026-07-01', end='2026-07-31', limit=50, paging_state='cursor')
    assert result == {'jobs': [], 'next_page_token': None}
    args, kwargs = mock_get.call_args
    assert args[0].endswith('/files/v1/jobs')
    assert kwargs['params'] == {'limit': 50, 'start': '2026-07-01', 'end': '2026-07-31', 'paging_state': 'cursor'}


# file_get / file_job_get fetch semantics

def test_file_get_fetches_and_seeds_status(client: MathpixClient) -> None:
    status_body = {'file_id': 'f-1', 'status': 'completed', 'custom_id': 'doc-1', 'num_pages': 4}
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=status_body)
        file = client.file_get('f-1')
    assert isinstance(file, File)
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/f-1')
    # Seeded from the fetch; no extra status request needed
    assert file.custom_id == 'doc-1'
    assert file.num_pages == 4
    assert mock_get.call_count == 1


def test_file_get_unknown_id_raises(client: MathpixClient) -> None:
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=404, json_body={'error': 'not_found'})
        with pytest.raises(FilesApiError) as exc_info:
            client.file_get('f-missing')
    assert exc_info.value.error_id == 'not_found'


def test_file_job_get_fetches_and_seeds_file_count(client: MathpixClient) -> None:
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.return_value = FakeResponse(
            json_body={'job_id': 'job-1', 'status': 'completed', 'file_count': 7},
        )
        job = client.file_job_get('job-1')
    assert isinstance(job, FileJob)
    assert job.file_count == 7
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/jobs/job-1')


def test_file_job_get_unknown_id_raises(client: MathpixClient) -> None:
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=404, json_body={'error': 'not_found'})
        with pytest.raises(FilesApiError) as exc_info:
            client.file_job_get('job-missing')
    assert exc_info.value.error_id == 'not_found'


# FileJob

def test_file_job_status_endpoint(client: MathpixClient) -> None:
    job = FileJob(auth=client.auth, job_id='job-1')
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body={'job_id': 'job-1', 'status': 'completed'})
        status = job.status()
    assert status['status'] == 'completed'
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/jobs/job-1')


def test_file_job_files_status_filter_passthrough(client: MathpixClient) -> None:
    # Filter values are the server's contract; the client passes them through
    job = FileJob(auth=client.auth, job_id='job-1')
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body={'files': [], 'next_page_token': None})
        job.files(status='error')
    _, kwargs = mock_get.call_args
    assert kwargs['params'] == {'status': 'error'}


def test_file_job_files_iter_pagination(client: MathpixClient) -> None:
    job = FileJob(auth=client.auth, job_id='job-1')
    pages = [
        FakeResponse(json_body={'files': [{'file_id': 'f1'}, {'file_id': 'f2'}], 'next_page_token': 'p2'}),
        FakeResponse(json_body={'files': [{'file_id': 'f3'}], 'next_page_token': None}),
    ]
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.side_effect = pages
        files = list(job.files_iter(status='error'))
    assert [f['file_id'] for f in files] == ['f1', 'f2', 'f3']
    assert mock_get.call_count == 2
    second_params = mock_get.call_args_list[1][1]['params']
    assert second_params['paging_state'] == 'p2'
    assert second_params['status'] == 'error'


def test_file_job_file_by_custom_id(client: MathpixClient) -> None:
    job = FileJob(auth=client.auth, job_id='job-1')
    status_body = {'file_id': 'f-9', 'status': 'completed', 'custom_id': 'doc-9', 'num_pages': 3}
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=status_body)
        file = job.file_by_custom_id('doc-9')
    assert isinstance(file, File)
    assert file.file_id == 'f-9'
    # Seeded from the response; no extra status request needed
    assert file.custom_id == 'doc-9'
    assert file.num_pages == 3
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/jobs/job-1/files/doc-9')


def test_file_job_file_by_custom_id_not_found(client: MathpixClient) -> None:
    job = FileJob(auth=client.auth, job_id='job-1')
    with patch('mpxpy.file_job.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=404, json_body={'error': 'not_found'})
        with pytest.raises(FilesApiError) as exc_info:
            job.file_by_custom_id('unknown')
    assert exc_info.value.error_id == 'not_found'


# File.status

def test_file_status_raises_on_error_response(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-missing')
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=404, json_body={'error': 'not_found'})
        with pytest.raises(FilesApiError) as exc_info:
            file.status()
    assert exc_info.value.error_id == 'not_found'


def test_file_status_non_envelope_error_is_client_error(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=500, text='oops')
        with pytest.raises(MathpixClientError) as exc_info:
            file.status()
    assert not isinstance(exc_info.value, FilesApiError)


# File downloads: error disambiguation

def test_download_format_not_ready_is_conversion_incomplete(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(
            status_code=404,
            json_body={'error': 'format_not_ready', 'status': 'split'},
        )
        with pytest.raises(ConversionIncompleteError):
            file.text_result('docx')


def test_download_not_found_is_client_error(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=404, json_body={'error': 'not_found'})
        with pytest.raises(MathpixClientError) as exc_info:
            file.text_result('mmd')
    assert not isinstance(exc_info.value, ConversionIncompleteError)


def test_download_unsupported_format_is_validation_error(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=415, json_body={'error': 'unsupported_format'})
        with pytest.raises(ValidationError):
            file.bytes_result('docx')


def test_download_legacy_409_is_conversion_incomplete(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.get') as mock_get:
        mock_get.return_value = FakeResponse(status_code=409)
        with pytest.raises(ConversionIncompleteError):
            file.bytes_result('docx')


# File.delete

def test_file_delete_success(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.delete') as mock_delete:
        mock_delete.return_value = FakeResponse(json_body={'file_id': 'f-1', 'status': 'deleted'})
        result = file.delete()
    assert result == {'file_id': 'f-1', 'status': 'deleted'}
    args, _ = mock_delete.call_args
    assert args[0].endswith('/files/v1/f-1')


def test_file_delete_conflict_while_processing(client: MathpixClient) -> None:
    file = File(auth=client.auth, file_id='f-1')
    with patch('mpxpy.file.delete') as mock_delete:
        mock_delete.return_value = FakeResponse(
            status_code=409,
            json_body={'error': 'conflict', 'error_info': {'id': 'conflict', 'message': 'File is still processing'}},
        )
        with pytest.raises(FilesApiError) as exc_info:
            file.delete()
    assert exc_info.value.error_id == 'conflict'
    assert exc_info.value.http_status == 409


# Data sources

def test_onboarding_identities(client: MathpixClient) -> None:
    identities = {
        'aws': {'trust_account_id': '123456789012', 'external_id': 'group-uuid'},
        'azure': {'app_id': 'app-uuid', 'tenant_id': 'tenant-uuid'},
        'gcp': {'service_account_email': 'ingest@example.iam.gserviceaccount.com', 'external_id': 'group-uuid'},
    }
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=identities)
        result = client.onboarding_identities()
    assert result == identities
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/onboarding/identities')


def test_onboarding_identities_gcp_block_is_optional(client: MathpixClient) -> None:
    identities = {
        'aws': {'trust_account_id': '123456789012', 'external_id': 'group-uuid'},
        'azure': {'app_id': 'app-uuid', 'tenant_id': 'tenant-uuid'},
    }
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=identities)
        result = client.onboarding_identities()
    assert result == identities
    assert 'gcp' not in result


def test_data_source_new_request_shape(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'data_source_id': 'ds-1'})
        data_source = client.data_source_new(
            provider='aws',
            bucket='my-bucket',
            auth_method='iam_role',
            provider_specific_details={
                'iam_role_arn': 'arn:aws:iam::123456789012:role/MathpixReader',
                'aws_external_id': 'group-uuid',
            },
            name='prod-source',
            region='us-east-1',
        )
    assert isinstance(data_source, DataSource)
    assert data_source.data_source_id == 'ds-1'
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1/data-sources')
    body = kwargs['json']
    assert body['provider'] == 'aws'
    assert body['bucket'] == 'my-bucket'
    assert body['auth_method'] == 'iam_role'
    assert body['name'] == 'prod-source'
    assert body['region'] == 'us-east-1'
    assert 'secret' not in body


def test_data_source_new_requires_shape_fields(client: MathpixClient) -> None:
    # Only required-value checks are client-side; provider/auth_method
    # combinations are the server's contract.
    details = {'iam_role_arn': 'arn', 'aws_external_id': 'x'}
    with pytest.raises(ValidationError):
        client.data_source_new(provider='', bucket='b', auth_method='iam_role',
                               provider_specific_details=details)
    with pytest.raises(ValidationError):
        client.data_source_new(provider='aws', bucket='', auth_method='iam_role',
                               provider_specific_details=details)
    with pytest.raises(ValidationError):
        client.data_source_new(provider='aws', bucket='b', auth_method='',
                               provider_specific_details=details)
    with pytest.raises(ValidationError):
        client.data_source_new(provider='aws', bucket='b', auth_method='iam_role',
                               provider_specific_details={})


def test_data_source_new_bucket_conflict_raises(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(
            status_code=409,
            json_body={'error': 'conflict',
                       'error_info': {'id': 'conflict',
                                      'message': 'A data source for this bucket is already registered.'}},
        )
        with pytest.raises(FilesApiError) as exc_info:
            client.data_source_new(provider='aws', bucket='b', auth_method='iam_role',
                                   provider_specific_details={'iam_role_arn': 'arn', 'aws_external_id': 'x'})
    assert exc_info.value.error_id == 'conflict'
    assert exc_info.value.http_status == 409
    assert 'bucket is already registered' in str(exc_info.value)


def test_data_source_new_duplicate_name_conflict_raises(client: MathpixClient) -> None:
    # The same 409 'conflict' also covers a duplicate name; the server message
    # is preserved so the two cases are distinguishable.
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(
            status_code=409,
            json_body={'error': 'conflict',
                       'error_info': {'id': 'conflict',
                                      'message': 'A data source with this name is already registered.'}},
        )
        with pytest.raises(FilesApiError) as exc_info:
            client.data_source_new(provider='aws', bucket='other-bucket', auth_method='iam_role',
                                   provider_specific_details={'iam_role_arn': 'arn', 'aws_external_id': 'x'},
                                   name='taken-name')
    assert exc_info.value.error_id == 'conflict'
    assert 'name is already registered' in str(exc_info.value)


def test_data_source_new_azure_request_shape(client: MathpixClient) -> None:
    details = {'azure_tenant_id': 'tenant-uuid', 'storage_account': 'mystorageacct'}
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'data_source_id': 'ds-az'})
        client.data_source_new(provider='azure', bucket='my-container', auth_method='azure_ad',
                               provider_specific_details=details)
    _, kwargs = mock_post.call_args
    body = kwargs['json']
    assert body['provider'] == 'azure'
    assert body['bucket'] == 'my-container'
    assert body['auth_method'] == 'azure_ad'
    assert body['provider_specific_details'] == details
    assert 'secret' not in body


def test_data_source_new_gcp_request_shape(client: MathpixClient) -> None:
    details = {'gcp_project_id': 'my-project', 'target_sa_email': 'ingest@my-project.iam.gserviceaccount.com'}
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'data_source_id': 'ds-gcp'})
        client.data_source_new(provider='gcp', bucket='my-bucket', auth_method='service_account',
                               provider_specific_details=details)
    _, kwargs = mock_post.call_args
    body = kwargs['json']
    assert body['provider'] == 'gcp'
    assert body['auth_method'] == 'service_account'
    assert body['provider_specific_details'] == details
    assert 'secret' not in body


def test_data_source_new_aws_access_key_request_shape(client: MathpixClient) -> None:
    details = {'aws_access_key_id': 'AKIAEXAMPLE'}
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'data_source_id': 'ds-key'})
        client.data_source_new(provider='aws', bucket='my-bucket', auth_method='access_key',
                               provider_specific_details=details, secret='key-material',
                               region='us-east-1')
    _, kwargs = mock_post.call_args
    body = kwargs['json']
    assert body['provider'] == 'aws'
    assert body['bucket'] == 'my-bucket'
    assert body['auth_method'] == 'access_key'
    assert body['provider_specific_details'] == {'aws_access_key_id': 'AKIAEXAMPLE'}
    assert body['secret'] == 'key-material'
    assert body['region'] == 'us-east-1'


def test_data_source_test_returns_failed_probe_without_raising(client: MathpixClient) -> None:
    probe = {'result': 'failed', 'checks': {'read': True, 'write': False},
             'message': 'Write probe failed: 403 AccessDenied (missing s3:PutObject)'}
    with patch('mpxpy.data_source.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body=probe)
        result = client.data_source_test('ds-1')
    assert result == probe
    args, _ = mock_post.call_args
    assert args[0].endswith('/files/v1/data-sources/ds-1/test')


def test_data_source_delete(client: MathpixClient) -> None:
    with patch('mpxpy.data_source.delete') as mock_delete:
        mock_delete.return_value = FakeResponse(json_body={'data_source_id': 'ds-1', 'status': 'deleted'})
        result = client.data_source_delete('ds-1')
    assert result == {'data_source_id': 'ds-1', 'status': 'deleted'}
    args, _ = mock_delete.call_args
    assert args[0].endswith('/files/v1/data-sources/ds-1')


def test_data_source_delete_not_found(client: MathpixClient) -> None:
    with patch('mpxpy.data_source.delete') as mock_delete:
        mock_delete.return_value = FakeResponse(status_code=404, json_body={'error': 'not_found'})
        with pytest.raises(FilesApiError) as exc_info:
            client.data_source_delete('ds-missing')
    assert exc_info.value.error_id == 'not_found'


def test_data_source_list(client: MathpixClient) -> None:
    listing = {'data_sources': [{'data_source_id': 'ds-1', 'provider': 'aws', 'bucket': 'b'}]}
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=listing)
        result = client.data_source_list()
    assert result == listing
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/data-sources')


# Deprecated wrappers

def test_scs_file_new_url_delegates_to_file_new(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'f-1'})
        with pytest.warns(DeprecationWarning):
            file = client.scs_file_new(
                url='https://example.com/doc.pdf',
                scs_job_id='job-1',
                filename='doc.pdf',
                destination_s3_uri='s3://bucket/out/',
                s3_region='us-east-1',
                include_page_info=True,
            )
    assert isinstance(file, ScsFile)
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1/uri')
    body = kwargs['json']
    assert body['source_uri'] == 'https://example.com/doc.pdf'
    assert body['job_id'] == 'job-1'
    assert body['filename'] == 'doc.pdf'
    assert body['destination_uri'] == 's3://bucket/out/'
    assert body['s3_region'] == 'us-east-1'
    assert body['include_page_info'] is True


def test_scs_file_new_s3_delegates_to_file_new(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'f-1'})
        with pytest.warns(DeprecationWarning):
            client.scs_file_new(source_s3_uri='s3://bucket/doc.pdf')
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1/uri')
    assert kwargs['json']['source_uri'] == 's3://bucket/doc.pdf'


def test_list_scs_jobs_stays_on_legacy_endpoint(client: MathpixClient) -> None:
    legacy_body = {'jobs': [{'scs_job_id': 'job-1', 'group_id': 'g-1', 'app_id': 'a-1'}], 'paging_state': None}
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=legacy_body)
        with pytest.warns(DeprecationWarning):
            result = client.list_scs_jobs(limit=10)
    assert result == legacy_body
    args, kwargs = mock_get.call_args
    assert args[0].endswith('/files/v1/scs-jobs')
    assert kwargs['params'] == {'limit': 10}


def test_scs_job_status_stays_on_legacy_endpoint(client: MathpixClient) -> None:
    legacy_body = {'scs_job_id': 'job-1', 'group_id': 'g-1', 'app_id': 'a-1', 'num_pages_completed': 5}
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body=legacy_body)
        with pytest.warns(DeprecationWarning):
            status = client.scs_job_status('job-1')
    assert status == legacy_body
    args, kwargs = mock_get.call_args
    assert args[0].endswith('/files/v1/scs-jobs/status')
    assert kwargs['params'] == {'scs_job_id': 'job-1'}


def test_scs_file_direct_use_warns(client: MathpixClient) -> None:
    with pytest.warns(DeprecationWarning):
        file = ScsFile(auth=client.auth, file_id='f-1')
    assert file.file_id == 'f-1'


def test_scs_file_new_file_path_multipart(client: MathpixClient, tmp_path) -> None:
    doc = tmp_path / 'doc.pdf'
    doc.write_bytes(b'%PDF-1.4 test')
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value = FakeResponse(json_body={'file_id': 'f-1'})
        with pytest.warns(DeprecationWarning):
            file = client.scs_file_new(file_path=str(doc), scs_job_id='job-1')
    assert isinstance(file, ScsFile)
    args, kwargs = mock_post.call_args
    assert args[0].endswith('/files/v1')
    assert not args[0].endswith('/files/v1/uri')
    assert kwargs['data']['scs_job_id'] == 'job-1'


def test_list_scs_files_deprecated(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.get') as mock_get:
        mock_get.return_value = FakeResponse(json_body={'file_ids': [], 'next_page_token': None})
        with pytest.warns(DeprecationWarning):
            client.list_scs_files(scs_job_id='job-1')
    args, _ = mock_get.call_args
    assert args[0].endswith('/files/v1/list')
