from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from typing import List
import pytest
from mpxpy.mathpix_client import MathpixClient
from mpxpy.scs_file import ScsFile
from mpxpy.errors import ValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    """Create client with separate files_api_url for local docker testing."""
    return MathpixClient()


def test_file_upload_local(client: MathpixClient):
    """Test uploading a local file via files-api."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert isinstance(file, ScsFile)
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_upload_local_with_scs_job_id(client: MathpixClient):
    """Test uploading a local file with an scs_job_id."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = 'test-job-123'
    file = client.scs_file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert file.wait_until_complete(timeout=120)


def test_file_upload_url(client: MathpixClient):
    """Test uploading from a remote URL via files-api."""
    pdf_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    file = client.scs_file_new(
        url=pdf_url,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert isinstance(file, ScsFile)
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_upload_s3(client: MathpixClient):
    """Test uploading from an S3 URI via files-api."""
    file = client.scs_file_new(
        source_s3_uri="s3://mathpix-ocr-examples/bitcoin-7.pdf",
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    assert isinstance(file, ScsFile)
    assert file.wait_until_complete(timeout=120)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_upload_s3_with_options(client: MathpixClient):
    """Test S3 upload with additional options (destination, region, etc.)."""
    file = client.scs_file_new(
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
    assert isinstance(file, ScsFile)
    assert file.wait_until_complete(timeout=180)
    status = file.status()
    assert status['status'] == 'completed'


def test_file_status(client: MathpixClient):
    """Test getting file status."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    status = file.status()
    assert 'file_id' in status
    assert 'status' in status
    assert status['status'] in ['pending', 'split', 'completed', 'error']


def test_file_download_mmd(client: MathpixClient):
    """Test downloading MMD output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
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
    file = client.scs_file_new(
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
    file = client.scs_file_new(
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
        client.scs_file_new()


def test_file_new_requires_exactly_one_source_multiple(client: MathpixClient):
    """Test that file_new raises ValidationError when multiple sources are provided."""
    with pytest.raises(ValidationError):
        client.scs_file_new(
            file_path='/some/path.pdf',
            url='https://example.com/file.pdf',
        )


def test_list_files_by_job_id(client: MathpixClient):
    """Test listing files by job ID."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = 'test-list-files-job'
    file = client.scs_file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    result = client.list_scs_files(scs_job_id=scs_job_id, limit=10)
    assert 'file_ids' in result


def test_list_files_by_filename(client: MathpixClient):
    """Test listing files by filename."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    test_filename = 'test-list-by-filename.pdf'
    file = client.scs_file_new(
        file_path=pdf_path,
        filename=test_filename,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    result = client.list_scs_files(filename=test_filename, limit=10)
    assert 'file_ids' in result


def test_list_files_pagination(client: MathpixClient):
    """Test listing multiple files by job ID."""
    import uuid
    import time
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = f'test-pagination-job-{uuid.uuid4().hex[:8]}'
    # Create multiple files
    files: List[ScsFile] = []
    for _ in range(3):
        f = client.scs_file_new(
            file_path=pdf_path,
            scs_job_id=scs_job_id,
            conversion_formats={'mmd': True},
        )
        files.append(f)
    # Poll until files are indexed (ScyllaDB eventual consistency)
    indexed_count = 0
    result = None
    for _ in range(30):
        result = client.list_scs_files(scs_job_id=scs_job_id, limit=10)
        indexed_count = len(result.get('file_ids', []))
        if indexed_count >= 3:
            break
        time.sleep(1)
    assert indexed_count >= 3, "Files not indexed within timeout"
    # Verify all files are returned
    assert result is not None
    assert 'file_ids' in result
    assert len(result['file_ids']) >= 3


def test_list_jobs(client: MathpixClient):
    """Test listing SCS jobs."""
    result = client.list_scs_jobs(limit=10)
    assert 'jobs' in result or 'error' not in result


def test_list_jobs_with_date_range(client: MathpixClient):
    """Test listing SCS jobs with start/end date filters."""
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    result = client.list_scs_jobs(start=start, end=end, limit=10)
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
    file = client.scs_file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    assert file.file_id is not None
    # Get job status
    status = client.scs_job_status(scs_job_id)
    assert 'scs_job_id' in status or 'error' in status


def test_job_status_after_file_complete(client: MathpixClient):
    """Test job status after file processing completes."""
    import uuid
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    scs_job_id = f'test-job-wait-{uuid.uuid4().hex[:8]}'
    file = client.scs_file_new(
        file_path=pdf_path,
        scs_job_id=scs_job_id,
        conversion_formats={'mmd': True},
    )
    # First wait for the file itself to complete
    assert file.wait_until_complete(timeout=120)
    # Then verify the job status endpoint returns a response
    status = client.scs_job_status(scs_job_id)
    assert 'scs_job_id' in status or 'error' in status


def test_file_download_tex(client: MathpixClient):
    """Test downloading TEX output.

    Note: The conversion format is 'latex' but the download extension is 'tex'.
    """
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'latex': True},  # Must use 'latex' not 'tex'
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('latex', timeout=60)
    tex_text = file.to_tex_text()
    assert tex_text is not None
    assert len(tex_text) > 0


def test_file_download_pptx(client: MathpixClient):
    """Test downloading PPTX output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'pptx': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('pptx', timeout=60)
    pptx_bytes = file.to_pptx_bytes()
    assert pptx_bytes is not None
    assert len(pptx_bytes) > 0


def test_file_download_pdf(client: MathpixClient):
    """Test downloading PDF output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'pdf': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('pdf', timeout=60)
    pdf_bytes = file.to_pdf_bytes()
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0


def test_file_download_latex_pdf(client: MathpixClient):
    """Test downloading LaTeX-rendered PDF output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'latex.pdf': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('latex.pdf', timeout=60)
    latex_pdf_bytes = file.to_latex_pdf_bytes()
    assert latex_pdf_bytes is not None
    assert len(latex_pdf_bytes) > 0


def test_file_download_html(client: MathpixClient):
    """Test downloading HTML output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'html': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('html', timeout=60)
    html_bytes = file.to_html_bytes()
    assert html_bytes is not None
    assert len(html_bytes) > 0


def test_file_download_tex_zip(client: MathpixClient):
    """Test downloading tex.zip output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'tex.zip': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('tex.zip', timeout=60)
    tex_zip_bytes = file.to_tex_zip_bytes()
    assert tex_zip_bytes is not None
    assert len(tex_zip_bytes) > 0


def test_file_download_md_zip(client: MathpixClient):
    """Test downloading md.zip output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'md.zip': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('md.zip', timeout=60)
    md_zip_bytes = file.to_md_zip_bytes()
    assert md_zip_bytes is not None
    assert len(md_zip_bytes) > 0


def test_file_download_mmd_zip(client: MathpixClient):
    """Test downloading mmd.zip output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd.zip': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('mmd.zip', timeout=60)
    mmd_zip_bytes = file.to_mmd_zip_bytes()
    assert mmd_zip_bytes is not None
    assert len(mmd_zip_bytes) > 0


def test_file_download_html_zip(client: MathpixClient):
    """Test downloading html.zip output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'html.zip': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('html.zip', timeout=60)
    html_zip_bytes = file.to_html_zip_bytes()
    assert html_zip_bytes is not None
    assert len(html_zip_bytes) > 0


def test_file_download_xlsx(client: MathpixClient):
    """Test downloading XLSX output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'xlsx': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('xlsx', timeout=60)
    xlsx_bytes = file.to_xlsx_bytes()
    assert xlsx_bytes is not None
    assert len(xlsx_bytes) > 0


def test_file_download_jpg(client: MathpixClient):
    """Test downloading JPG output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'jpg': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('jpg', timeout=60)
    jpg_bytes = file.to_jpg_bytes()
    assert jpg_bytes is not None
    assert len(jpg_bytes) > 0
    # Verify JPEG magic bytes
    assert jpg_bytes[:2] == b'\xff\xd8'


def test_file_download_png(client: MathpixClient):
    """Test downloading PNG output."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'png': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('png', timeout=60)
    png_bytes = file.to_png_bytes()
    assert png_bytes is not None
    assert len(png_bytes) > 0
    # Verify PNG magic bytes
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'


def test_file_download_lines_json(client: MathpixClient):
    """Test downloading lines.json output.

    Note: lines.json doesn't have a dedicated status column - it's available
    when the overall job status is 'completed'.
    """
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},  # lines.json is generated from primary OCR
    )
    assert file.wait_until_complete(timeout=120)
    # No wait_for_format needed - lines.json is available when job completes
    lines_json = file.to_lines_json()
    assert lines_json is not None
    assert isinstance(lines_json, dict)


def test_file_download_lines_mmd_json(client: MathpixClient):
    """Test downloading lines.mmd.json output.

    Note: lines.mmd.json doesn't have a dedicated status column - it's available
    when the overall job status is 'completed'.
    """
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},  # lines.mmd.json is generated from primary OCR
    )
    assert file.wait_until_complete(timeout=120)
    # No wait_for_format needed - lines.mmd.json is available when job completes
    lines_mmd_json = file.to_lines_mmd_json()
    assert lines_mmd_json is not None
    assert isinstance(lines_mmd_json, dict)


def test_file_save_mmd(client: MathpixClient, tmp_path: Path):
    """Test saving MMD output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    assert file.wait_until_complete(timeout=120)
    output_path = str(tmp_path / 'output.mmd')
    saved_path = file.to_mmd_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_md(client: MathpixClient, tmp_path: Path):
    """Test saving MD output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'md': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('md', timeout=60)
    output_path = str(tmp_path / 'output.md')
    saved_path = file.to_md_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_docx(client: MathpixClient, tmp_path: Path):
    """Test saving DOCX output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'docx': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('docx', timeout=60)
    output_path = str(tmp_path / 'output.docx')
    saved_path = file.to_docx_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_pptx(client: MathpixClient, tmp_path: Path):
    """Test saving PPTX output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'pptx': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('pptx', timeout=60)
    output_path = str(tmp_path / 'output.pptx')
    saved_path = file.to_pptx_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_pdf(client: MathpixClient, tmp_path: Path):
    """Test saving PDF output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'pdf': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('pdf', timeout=60)
    output_path = str(tmp_path / 'output.pdf')
    saved_path = file.to_pdf_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_html(client: MathpixClient, tmp_path: Path):
    """Test saving HTML output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'html': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('html', timeout=60)
    output_path = str(tmp_path / 'output.html')
    saved_path = file.to_html_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_tex_zip(client: MathpixClient, tmp_path: Path):
    """Test saving tex.zip output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'tex.zip': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('tex.zip', timeout=60)
    output_path = str(tmp_path / 'output.tex.zip')
    saved_path = file.to_tex_zip_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_xlsx(client: MathpixClient, tmp_path: Path):
    """Test saving XLSX output to file."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'xlsx': True},
    )
    assert file.wait_until_complete(timeout=120)
    assert file.wait_for_format('xlsx', timeout=60)
    output_path = str(tmp_path / 'output.xlsx')
    saved_path = file.to_xlsx_file(output_path)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0


def test_file_save_to_directory(client: MathpixClient, tmp_path: Path):
    """Test saving output to directory (auto-generates filename)."""
    pdf_path = os.path.join(current_dir, 'files', 'pdfs', 'sample.pdf')
    file = client.scs_file_new(
        file_path=pdf_path,
        conversion_formats={'mmd': True},
    )
    assert file.wait_until_complete(timeout=120)
    output_dir = str(tmp_path) + '/'
    saved_path = file.to_mmd_file(output_dir)
    assert os.path.exists(saved_path)
    assert saved_path.endswith('.mmd')
    assert os.path.getsize(saved_path) > 0

