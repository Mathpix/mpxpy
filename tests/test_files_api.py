from datetime import datetime, timedelta, timezone
import os
from typing import List
import pytest
from mpxpy.mathpix_client import MathpixClient, FilesApiFile
from mpxpy.errors import ValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    """Create client with separate files_api_url for local docker testing."""
    return MathpixClient()


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


def test_file_upload_s3(client: MathpixClient):
    """Test uploading from an S3 URI via files-api."""
    file = client.file_new(
        source_s3_uri="s3://mathpix-ocr-examples/bitcoin-7.pdf",
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert isinstance(file, FilesApiFile)
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_upload_s3_with_options(client: MathpixClient):
    """Test S3 upload with additional options (destination, region, etc.)."""
    file = client.file_new(
        source_s3_uri="s3://mathpix-ocr-examples/bitcoin-7.pdf",
        filename="test-bitcoin.pdf",
        scs_job_id="test-s3-options-job",
        conversion_formats={'mmd': True, 'md': True},
        destination_s3_uri="s3://mathpix-ocr-examples/test_pdf_outputs",
        destination_basename="test-bitcoin",
        s3_region="us-east-1",
        include_equation_tags=True,
        preserve_section_numbering=True,
    )
    assert file.file_id is not None
    assert isinstance(file, FilesApiFile)
    assert file.wait_until_complete(timeout=180)
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
    assert file.wait_for_format('md', timeout=60)
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
    assert file.wait_for_format('docx', timeout=60)
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


def test_list_files_by_job_id(client: MathpixClient):
    """Test listing files by job ID."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = 'test-list-files-job'
    file = client.file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    result = client.list_files(scs_job_id=scs_job_id, limit=10)
    assert 'file_ids' in result


def test_list_files_by_filename(client: MathpixClient):
    """Test listing files by filename."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    test_filename = 'test-list-by-filename.pdf'
    file = client.file_new(
        file_path=pdf_path,
        filename=test_filename,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    result = client.list_files(filename=test_filename, limit=10)
    assert 'file_ids' in result


def test_list_files_pagination(client: MathpixClient):
    """Test listing multiple files by job ID."""
    import uuid
    import time
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = f'test-pagination-job-{uuid.uuid4().hex[:8]}'
    # Create multiple files
    files: List[FilesApiFile] = []
    for _ in range(3):
        f = client.file_new(
            file_path=pdf_path,
            scs_job_id=scs_job_id,
            conversion_formats={'mmd': True},
        )
        files.append(f)
    # Poll until files are indexed (ScyllaDB eventual consistency)
    indexed_count = 0
    for _ in range(30):
        result = client.list_files(scs_job_id=scs_job_id, limit=10)
        indexed_count = len(result.get('file_ids', []))
        if indexed_count >= 3:
            break
        time.sleep(1)
    assert indexed_count >= 3, "Files not indexed within timeout"
    # Verify all files are returned
    assert 'file_ids' in result
    assert len(result['file_ids']) >= 3


def test_list_jobs(client: MathpixClient):
    """Test listing SCS jobs."""
    result = client.list_jobs(limit=10)
    assert 'jobs' in result or 'error' not in result


def test_list_jobs_with_date_range(client: MathpixClient):
    """Test listing SCS jobs with start/end date filters."""
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    result = client.list_jobs(start=start, end=end, limit=10)
    assert 'jobs' in result
    # Verify returned jobs are within date range
    for job in result['jobs']:
        assert 'created_at' in job
        created = job['created_at'][:10]  # Extract YYYY-MM-DD
        assert created >= start, f"Job created_at {created} is before start {start}"
        assert created <= end, f"Job created_at {created} is after end {end}"


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
    status = client.job_status(scs_job_id)
    assert 'scs_job_id' in status or 'error' in status


def test_job_status_after_file_complete(client: MathpixClient):
    """Test job status after file processing completes."""
    import uuid
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = f'test-job-wait-{uuid.uuid4().hex[:8]}'
    file = client.file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    # First wait for the file itself to complete
    assert file.wait_until_complete(timeout=120)
    # Then verify the job status endpoint returns a response
    status = client.job_status(scs_job_id)
    assert 'scs_job_id' in status or 'error' in status
