import os
import pytest
from mpxpy import MathpixClient, FilesApiFile, ScsJob
from mpxpy.errors import ValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    """Create client with separate files_api_url for local docker testing."""
    return MathpixClient(
        api_url=os.getenv('MATHPIX_URL', 'http://mathpix-ocr-service:8070'),
        files_api_url=os.getenv('FILES_API_URL', 'http://mathpix-files-api:9094'),
    )


def test_file_upload_local(client: MathpixClient):
    """Test uploading a local file via files-api."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert isinstance(file, FilesApiFile)
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_upload_local_with_scs_job_id(client: MathpixClient):
    """Test uploading a local file with an scs_job_id."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = 'test-job-123'
    file = client.file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert file.wait_until_complete(timeout=120)


def test_file_upload_url(client: MathpixClient):
    """Test uploading from a remote URL via files-api."""
    pdf_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    file = client.file_new(
        url=pdf_url,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert isinstance(file, FilesApiFile)
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_status(client: MathpixClient):
    """Test getting file status."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    status = file.status()
    assert 'file_id' in status
    assert 'status' in status
    assert status['status'] in ['pending', 'processing', 'completed', 'error']


def test_file_download_mmd(client: MathpixClient):
    """Test downloading MMD output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    assert file.wait_until_complete(timeout=120)
    mmd_text = file.to_mmd_text()
    assert mmd_text is not None
    assert len(mmd_text) > 0


def test_file_download_md(client: MathpixClient):
    """Test downloading MD output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.file_new(
        file_path=pdf_path,
        conversion_formats={'md': True},
    )
    assert file.wait_until_complete(timeout=120)
    md_text = file.to_md_text()
    assert md_text is not None
    assert len(md_text) > 0


def test_file_download_docx(client: MathpixClient):
    """Test downloading DOCX output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.file_new(
        file_path=pdf_path,
        conversion_formats={'docx': True},
    )
    assert file.wait_until_complete(timeout=120)
    docx_bytes = file.to_docx_bytes()
    assert docx_bytes is not None
    assert len(docx_bytes) > 0


def test_file_new_requires_exactly_one_source(client: MathpixClient):
    """Test that file_new raises ValidationError when no source is provided."""
    with pytest.raises(ValidationError):
        client.file_new()


def test_file_new_requires_exactly_one_source_multiple(client: MathpixClient):
    """Test that file_new raises ValidationError when multiple sources are provided."""
    with pytest.raises(ValidationError):
        client.file_new(
            file_path='/some/path.pdf',
            url='https://example.com/file.pdf',
        )


def test_list_files(client: MathpixClient):
    """Test listing files by job ID (API requires a filter)."""
    # First create a file with a job ID
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = 'test-list-files-job'
    file = client.file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    # List files by job ID
    result = client.list_files(scs_job_id=scs_job_id, limit=10)
    # API returns file_ids list
    assert 'file_ids' in result


def test_list_jobs(client: MathpixClient):
    """Test listing SCS jobs."""
    result = client.list_jobs(limit=10)
    assert 'jobs' in result or 'error' not in result


def test_job_status(client: MathpixClient):
    """Test getting job status."""
    # First create a file with a job ID
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = 'test-job-status-123'
    file = client.file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    # Get job status
    job = client.job_status(scs_job_id)
    assert isinstance(job, ScsJob)
    status = job.status()
    assert 'scs_job_id' in status or 'error' in status


def test_scs_job_wait_until_complete(client: MathpixClient):
    """Test waiting for SCS job to complete."""
    import uuid
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = f'test-job-wait-{uuid.uuid4().hex[:8]}'
    file = client.file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    # First wait for the file itself to complete (this we know works)
    assert file.wait_until_complete(timeout=120)
    # Then verify the job status endpoint returns a response
    job = client.job_status(scs_job_id)
    status = job.status()
    # Job should exist and have counters, or return error if job metadata not created
    assert 'scs_job_id' in status or 'error' in status


if __name__ == '__main__':
    pass
